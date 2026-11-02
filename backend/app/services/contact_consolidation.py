"""Admin-reviewed profile merges retain identifiers, history and original snapshots."""
import json
import base64
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, inspect, select, text, delete
from fastapi import HTTPException
from app.database import Base
from app.models import Member, SecurityLog

class ConsolidatedContact(Base):
    __tablename__ = 'consolidated_member_contacts'
    id = Column(Integer, primary_key=True)
    source_member_id = Column(Integer, nullable=False, unique=True)
    member_id = Column(Integer, ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    clover_customer_id = Column(String, nullable=True, index=True)
    member_number = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    qr_code = Column(String, nullable=True)
    source_snapshot = Column(Text, nullable=False)
    target_snapshot = Column(Text, nullable=True)
    moved_records = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MergedMemberLogin(Base):
    __tablename__ = 'merged_member_logins'
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)


class MergedRecordSnapshot(Base):
    __tablename__ = 'merged_member_record_snapshots'
    id = Column(Integer, primary_key=True)
    consolidation_id = Column(Integer, ForeignKey('consolidated_member_contacts.id'), nullable=False)
    table_name = Column(String, nullable=False)
    record_json = Column(Text, nullable=False)


def contact_match(a, b):
    from app.services.member_profiles import phone_key
    email=(a.email or '').strip().casefold()
    phone=phone_key(a.phone)
    return bool((email and email==(b.email or '').strip().casefold()) or (phone and phone==phone_key(b.phone))
        or (a.clover_customer_id and a.clover_customer_id==b.clover_customer_id))


def clover_member(db, identity):
    if not identity: return None
    direct = db.query(Member).filter_by(clover_customer_id=identity).limit(2).all()
    if len(direct)>1: raise HTTPException(409, 'Clover identity requires duplicate review.')
    alias = db.query(ConsolidatedContact).filter_by(clover_customer_id=identity).first()
    if direct and alias and direct[0].id != alias.member_id:
        raise HTTPException(409, 'Clover identity requires duplicate review.')
    return direct[0] if direct else db.get(Member, alias.member_id) if alias else None


def name_key(member):
    return ' '.join(((member.first_name or '')+' '+(member.last_name or '')).casefold().split())


def member_references(db):
    inspector = inspect(db.connection())
    result = []
    for table in inspector.get_table_names():
        for key in inspector.get_foreign_keys(table):
            if key.get('referred_table') == 'members':
                result.append((table,key['constrained_columns'][0]))
    return result


def reference_counts(db, member_id, references=None):
    quote = db.get_bind().dialect.identifier_preparer.quote
    counts = {}
    for table,column in references if references is not None else member_references(db):
        count = db.execute(text(f'SELECT count(*) FROM {quote(table)} WHERE {quote(column)}=:identity'), {'identity':member_id}).scalar()
        if count: counts[table] = count
    return counts


def confirmed_plan(db, references=None):
    from app.services.member_profiles import phone_key
    references = member_references(db) if references is None else references
    members = db.query(Member).order_by(Member.id).all()
    plan = []
    for source in members:
        if source.member_type != 'CUSTOMER' or source.membership_start or source.membership_end:
            continue
        email = (source.email or '').strip().casefold(); phone = phone_key(source.phone)
        if not (source.first_name or '').strip() or not (source.last_name or '').strip() or not email or not phone: continue
        candidates = [target for target in members if target.id != source.id
            and (target.member_type == 'MEMBER' or (target.member_type == 'CUSTOMER' and target.id < source.id))
            and name_key(target)==name_key(source) and (not target.email or target.email.strip().casefold()==email)
            and phone_key(target.phone)==phone
            and not (target.date_of_birth and source.date_of_birth and target.date_of_birth.date()!=source.date_of_birth.date())]
        if len(candidates) != 1 or reference_counts(db, source.id, references): continue
        plan.append({'source_id':source.id, 'member_id':candidates[0].id})
    return plan


def merge_profiles(db, user, keep_id, source_id, *, allow_linked=False, reviewed_contact=False):
    if keep_id == source_id: raise HTTPException(400, 'Choose two different profiles.')
    from app.services.member_profiles import lock_profiles
    lock_profiles(db)
    prior=db.query(ConsolidatedContact).filter_by(source_member_id=source_id,member_id=keep_id).first()
    if prior and not db.get(Member,source_id):return {'source_id':source_id,'member_id':keep_id}
    rows = db.execute(select(Member).where(Member.id.in_([keep_id, source_id])).order_by(Member.id)
        .with_for_update().execution_options(populate_existing=True)).scalars().all()
    if len(rows)!=2: raise HTTPException(404, 'Profile not found.')
    target=next(m for m in rows if m.id==keep_id);source=next(m for m in rows if m.id==source_id)
    reviewed_contact=reviewed_contact and contact_match(target,source)
    if not reviewed_contact and (not name_key(target) or name_key(target)!=name_key(source)):
        raise HTTPException(409, 'Names differ. Verify and correct the profiles before merging.')
    if not reviewed_contact and target.date_of_birth and source.date_of_birth and target.date_of_birth.date()!=source.date_of_birth.date():
        raise HTTPException(409, 'Birthdates differ. Verify the profiles before merging.')
    references = member_references(db)
    linked = reference_counts(db, source.id, references)
    if linked and not allow_linked:
        raise HTTPException(409, 'Linked records require individual duplicate review.')
    snapshot=lambda member:{c.name:getattr(member,c.name) for c in Member.__table__.columns}
    archive=ConsolidatedContact(source_member_id=source.id, member_id=target.id,clover_customer_id=source.clover_customer_id,
        member_number=source.member_number,barcode=source.barcode,qr_code=source.qr_code,
        source_snapshot=json.dumps(snapshot(source),default=str),target_snapshot=json.dumps(snapshot(target),default=str))
    db.add(archive);db.flush()
    from app.services.memberships import is_ticket_purchase_name
    source_gym_term=bool(source.member_type=='MEMBER' and not is_ticket_purchase_name(source.membership_type) and source.membership_end)
    target_gym_term=bool(target.member_type=='MEMBER' and not is_ticket_purchase_name(target.membership_type) and target.membership_end)
    source_term_wins=bool(source_gym_term and (not target_gym_term or source.membership_end>target.membership_end))
    from app.member_portal.models import MemberAccount,MemberInvite,AssignedMembership
    if reviewed_contact:
        # An invitation sent to the former profile must never claim the kept login.
        db.query(MemberInvite).filter_by(member_id=source.id,used_at=None).update({'used_at':datetime.utcnow()},synchronize_session=False)
    def retain_and_remove(table,column,identity):
        records=db.execute(text(f'SELECT * FROM {quote(table)} WHERE {quote(column)}=:id'),{'id':identity}).mappings().all()
        for record in records:
            serial=lambda value:{'base64':base64.b64encode(value).decode()} if isinstance(value,(bytes,bytearray,memoryview)) else str(value)
            db.add(MergedRecordSnapshot(consolidation_id=archive.id,table_name=table,record_json=json.dumps(dict(record),default=serial)))
        db.execute(text(f'DELETE FROM {quote(table)} WHERE {quote(column)}=:id'),{'id':identity})
        return records
    # Resolve known single-profile records, retaining the superseded rows in the audit archive.
    inspector = inspect(db.connection());quote=db.get_bind().dialect.identifier_preparer.quote
    if reviewed_contact and source_term_wins and not db.query(AssignedMembership).filter_by(member_id=source.id).first():
        retain_and_remove('member_assigned_memberships','member_id',target.id)
    if reviewed_contact and not source_term_wins and target.membership_end and not db.query(AssignedMembership).filter_by(member_id=target.id).first():
        retain_and_remove('member_assigned_memberships','member_id',source.id)
    if reviewed_contact and db.query(MemberAccount).filter_by(member_id=source.id).first() and db.query(MemberAccount).filter_by(member_id=target.id).first():
        retain_and_remove('member_portal_account_setups','member_id',source.id)
    for table,column in references:
        if table not in linked: continue
        constraints=inspector.get_unique_constraints(table)
        indexes=inspector.get_indexes(table)
        unique = any(c.get('column_names')==[column] for c in constraints) or any(c.get('unique') and c.get('column_names')==[column] for c in indexes)
        if unique and db.execute(text(f'SELECT count(*) FROM {quote(table)} WHERE {quote(column)}=:id'),{'id':target.id}).scalar():
            if not reviewed_contact or table not in ('member_accounts','member_portal_account_setups','member_assigned_memberships','member_profile_photos'):
                raise HTTPException(409, 'Linked records conflict. No changes were saved.')
            discard_id=target.id if table=='member_assigned_memberships' and source_term_wins else source.id
            records=retain_and_remove(table,column,discard_id)
            for record in records:
                if table=='member_accounts':
                    from app.models import User
                    login=db.get(User,record['user_id'])
                    if not login or login.role!='member':raise HTTPException(409,'Only member portal accounts can be combined.')
                    db.add(MergedMemberLogin(member_id=target.id,user_id=login.id))
    moved={}
    for table,column in references:
        if table not in linked: continue
        identities=list(db.execute(text(f'SELECT id FROM {quote(table)} WHERE {quote(column)}=:id'),{'id':source.id}).scalars())
        moved[f'{table}.{column}']=identities
        db.execute(text(f'UPDATE {quote(table)} SET {quote(column)}=:target WHERE {quote(column)}=:source'),{'target':target.id,'source':source.id})
    archive.moved_records=json.dumps(moved)
    db.add(archive)
    # Retain the later recorded term, without replaying sales or inventing paid time.
    if allow_linked and source_term_wins:
        for field in ('member_type','status','membership_type','membership_status','membership_start','membership_end',
            'billing_cycle','monthly_rate','next_billing_date','autopay_enabled','billing_status','last_payment_date','past_due_amount'):
            setattr(target,field,getattr(source,field))
    for field in ('email','phone','photo_url','address','city','state','zip_code','emergency_contact','emergency_phone','date_of_birth','clover_customer_id'):
        if not getattr(target,field) and getattr(source,field):setattr(target,field,getattr(source,field))
    if source.notes and source.notes not in (target.notes or ''):target.notes='\n'.join(filter(None,[target.notes,source.notes]))
    if allow_linked: target.waiver_signed=bool(target.waiver_signed or source.waiver_signed)
    target.total_checkins=(target.total_checkins or 0)+(source.total_checkins or 0)
    target.checkins=(target.checkins or 0)+(source.checkins or 0)
    if source.last_checkin and (not target.last_checkin or source.last_checkin>target.last_checkin):target.last_checkin=source.last_checkin
    db.flush()
    db.execute(delete(Member).where(Member.id==source.id).execution_options(synchronize_session=False))
    db.expunge(source)
    db.add(SecurityLog(user_id=user.id,action='CONTACT_CONSOLIDATED',description=f'Consolidated profile #{source.id} into #{target.id}; identifiers, original snapshots and linked records retained'))
    db.flush()
    return {'source_id':source_id,'member_id':keep_id}


def consolidate(db, user):
    from app.services.member_profiles import lock_profiles
    lock_profiles(db)
    plan=confirmed_plan(db);merged=[]
    for pair in plan:
        merged.append(merge_profiles(db,user,pair['member_id'],pair['source_id']))
    db.commit()
    return {'merged':len(merged),'profiles':merged,'message':'Confirmed duplicate contacts consolidated. Membership history and shared-contact families retained.'}
