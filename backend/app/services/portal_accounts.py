"""Prepare restricted member logins, never grant gym access from contact details alone."""
import hashlib
import re
import secrets
from collections import Counter
from datetime import datetime
from sqlalchemy import func
from app.auth import hash_password
from app.models import Member,User,SecurityLog
from app.member_portal.models import MemberAccount,PortalAccountSetup


def fingerprint(user):
    return hashlib.sha256(user.password_hash.encode()).hexdigest()


def needs_password_setup(db, account, user):
    setup=db.query(PortalAccountSetup).filter_by(member_id=account.member_id,user_id=user.id).first()
    return bool(setup and setup.claimed_at is None and secrets.compare_digest(setup.password_fingerprint,fingerprint(user)))


def eligible(member):
    return bool(((member.first_name or '')+' '+(member.last_name or '')).strip()
        and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',(member.email or '').strip())
        and 10<=len(re.sub(r'\D','',member.phone or ''))<=15)


def prepare_accounts(db, member_ids=None):
    from app.services.member_profiles import lock_profiles
    lock_profiles(db)
    members=db.query(Member).order_by(Member.id).all()
    from app.services.member_profiles import phone_key
    identities=Counter((' '.join(((m.first_name or '')+' '+(m.last_name or '')).casefold().split()),phone_key(m.phone)) for m in members if phone_key(m.phone))
    emails=Counter((m.email or '').strip().lower() for m in members if m.email)
    counts={'created':0,'already_active':0,'missing_contact_details':0,'shared_email_review':0,'disabled':0}
    for row in members:
        if member_ids is not None and row.id not in member_ids:continue
        member=db.query(Member).filter_by(id=row.id).with_for_update().one()
        account=db.query(MemberAccount).filter_by(member_id=member.id).first()
        if account:
            user=db.get(User,account.user_id)
            counts['already_active' if user and user.active else 'disabled']+=1
            continue
        if not eligible(member):counts['missing_contact_details']+=1;continue
        email=member.email.strip().lower()
        identity=(' '.join(((member.first_name or '')+' '+(member.last_name or '')).casefold().split()),phone_key(member.phone))
        if emails[email]>1 or identities[identity]>1:counts['shared_email_review']+=1;continue
        user=db.query(User).filter(func.lower(func.trim(User.email))==email).with_for_update().first()
        if user and (user.role!='member' or db.query(MemberAccount).filter_by(user_id=user.id).first()):
            counts['shared_email_review']+=1;continue
        if user and not user.active:counts['disabled']+=1;continue
        if user:
            # Existing unbound credentials must prove email ownership through setup.
            counts['shared_email_review']+=1;continue
        user=User(name=f'{member.first_name} {member.last_name}'.strip(),email=email,
            role='member',active=True,password_hash=hash_password(secrets.token_urlsafe(48)))
        db.add(user);db.flush()
        db.add(MemberAccount(member_id=member.id,user_id=user.id))
        db.add(PortalAccountSetup(member_id=member.id,user_id=user.id,password_fingerprint=fingerprint(user)))
        db.add(SecurityLog(action='MEMBER_ACCOUNT_PREPARED',description=f'Prepared restricted portal account for profile #{member.id}; password ownership verification required, no membership grant'))
        counts['created']+=1
    db.flush()
    return counts


def prepare_all_accounts(db,batch_size=15):
    identities=[identity for (identity,) in db.query(Member.id).order_by(Member.id).all()]
    totals={key:0 for key in ('created','already_active','missing_contact_details','shared_email_review','disabled')}
    for start in range(0,len(identities),batch_size):
        result=prepare_accounts(db,set(identities[start:start+batch_size]))
        db.commit()
        for key in totals:totals[key]+=result[key]
    return totals
