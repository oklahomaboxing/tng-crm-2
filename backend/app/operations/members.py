import os
import shutil
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..core.permissions import require_admin
from ..core.dependencies import current_user, staff_user
from ..database import get_db
from ..models import Member, MembershipProduct, Sale, User
from ..services.memberships import (
    is_membership_product,
    recalculate_member_from_payments,
    effective_membership_status,
)

from app.services.portal_accounts import prepare_accounts
from app.services.purchase_history import CloverPurchaseDetail

router = APIRouter(dependencies=[Depends(staff_user)])


from pydantic import BaseModel, Field
import re


class CreateMemberProfileIn(BaseModel):
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=40)
    address: str = Field(default="", max_length=300)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    zip_code: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=4000)
    activate_membership: bool = True
    membership_name: str = Field(default='Monthly Membership',min_length=1,max_length=120)
    membership_rate: float = Field(default=150,ge=0,le=100000,allow_inf_nan=False)
    membership_months: int = Field(default=1,ge=1,le=120)


@router.post("/api/members", status_code=201)
def create_member_profile(data: CreateMemberProfileIn, db: Session = Depends(get_db),
                          user: User = Depends(current_user)):
    require_admin(user)
    from app.services.member_profiles import lock_profiles, matching_profile, ensure_profile_identity, audit_profile
    first, last = data.first_name.strip(), data.last_name.strip()
    email, phone = data.email.strip().lower(), data.phone.strip()
    if not first and not last:
        raise HTTPException(422, "Enter the member's name.")
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Enter a valid email address.")
    if phone and not 10 <= len(re.sub(r"\D", "", phone)) <= 15:
        raise HTTPException(422, "Enter a phone number with area code.")
    lock_profiles(db)
    from sqlalchemy import func
    from app.services.member_profiles import phone_key
    existing=db.query(Member).filter(func.lower(func.trim(Member.email))==email).first() if email else None
    if not existing and phone_key(phone):
        requested=' '.join((first+' '+last).casefold().split())
        existing=next((m for m in db.query(Member).filter(Member.phone.isnot(None)).all()
            if phone_key(m.phone)==phone_key(phone) and ' '.join(((m.first_name or '')+' '+(m.last_name or '')).casefold().split())==requested),None)
    if existing:
        raise HTTPException(409, f"Profile #{existing.id} already uses this email or phone. Search for the existing profile instead.")
    member = Member(first_name=first, last_name=last, email=email, phone=phone,
                    address=data.address.strip(), city=data.city.strip(), state=data.state.strip(),
                    zip_code=data.zip_code.strip(), notes=data.notes.strip(),
                    member_type="MEMBER", status="pending", membership_status="pending", waiver_signed=False)
    db.add(member)
    ensure_profile_identity(db, member)
    if data.activate_membership:
        from app.services.assigned_memberships import assign_membership
        assign_membership(db,member,data.membership_name,data.membership_rate,data.membership_months,activate=True,user_id=user.id)
    access=prepare_accounts(db,{member.id})
    audit_profile(db, user.id, "MEMBER_PROFILE_CREATED", f"Created profile {member.id}; assigned membership={data.activate_membership}, rate={data.membership_rate}; no payment recorded")
    db.commit()
    return {"id": member.id, "first_name": member.first_name, "last_name": member.last_name,
            "email": member.email, "phone": member.phone, "member_number": member.member_number,
            "membership_status": member.membership_status, "member_type": member.member_type, "account_access":access}


@router.get("/api/members")
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    members = db.query(Member).order_by(Member.last_name.asc(), Member.first_name.asc()).all()
    from app.member_portal.models import MemberAccount, MemberInvite
    accounts = {account.member_id: bool(account_user.active) for account, account_user in
                db.query(MemberAccount, User).join(User, User.id == MemberAccount.user_id).all()}
    invited = {row.member_id for row in db.query(MemberInvite).filter(
        MemberInvite.used_at.is_(None), MemberInvite.expires_at > datetime.utcnow()).all()}

    from collections import Counter
    from app.services.member_profiles import phone_key
    emails = Counter((m.email or "").strip().lower() for m in members if (m.email or "").strip())
    phones = Counter(phone_key(m.phone) for m in members if phone_key(m.phone))
    from app.services.member_reporting import membership_evidence, membership_report
    from app.services.contact_consolidation import ConsolidatedContact, name_key
    import json
    paid_ids=membership_evidence(db); now=datetime.utcnow()
    from app.member_portal.models import AssignedMembership
    assignments={a.member_id:a for a in db.query(AssignedMembership).all()}
    aliases={}
    for alias in db.query(ConsolidatedContact).all():
        saved=json.loads(alias.source_snapshot)
        aliases.setdefault(alias.member_id,[]).extend(filter(None,[saved.get('email'),saved.get('phone'),alias.member_number]))
    results = []

    for member in members:
        shared_contact = emails.get((member.email or "").strip().lower(), 0) > 1 or phones.get(phone_key(member.phone), 0) > 1
        results.append({
            "id": member.id,
            **membership_report(member,paid_ids,now),
            "contact_aliases": aliases.get(member.id,[]),
            "assigned_rate":assignments[member.id].rate if member.id in assignments else member.monthly_rate,
            "assigned_months":assignments[member.id].months if member.id in assignments else None,
            "same_name_contact_review": any(other.id != member.id and name_key(member) and name_key(other)==name_key(member)
                and (((member.email or '').strip() and (member.email or '').strip().casefold()==(other.email or '').strip().casefold())
                or (phone_key(member.phone) and phone_key(member.phone)==phone_key(other.phone))) for other in members),
            "member_type": member.member_type,
            "profile_source": "clover" if member.clover_customer_id else "tngos",
            "shared_contact_needs_review": shared_contact,
            "portal_status": ("active" if accounts[member.id] else "disabled") if member.id in accounts
                else "invited" if member.id in invited else "needs_review" if shared_contact else "not_invited" if member.email else "needs_email",
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "phone": member.phone,
            "status": member.status,
            "member_number": member.member_number,
            "barcode": member.barcode,
            "qr_code": member.qr_code,
            "digital_member_id": member.digital_member_id,
            "membership_type": member.membership_type,
            "membership_status": effective_membership_status(member),
            "assigned_coach": member.assigned_coach,
            "emergency_contact": member.emergency_contact,
            "emergency_phone": member.emergency_phone,
            "notes": member.notes,
            "membership_start": (
                member.membership_start.isoformat()
                if member.membership_start
                else None
            ),
            "membership_end": (
                member.membership_end.isoformat()
                if member.membership_end
                else None
            ),
            "last_payment_date": (
                member.last_payment_date.isoformat()
                if member.last_payment_date
                else None
            ),
            "next_billing_date": (
                member.next_billing_date.isoformat()
                if member.next_billing_date
                else None
            ),
            "billing_status": member.billing_status,
            "clover_customer_id": member.clover_customer_id,
            "last_checkin": (
                member.last_checkin.isoformat()
                if member.last_checkin
                else None
            ),
            "total_checkins": member.total_checkins or 0,
            "photo_url": member.photo_url,
            "created_at": (
                member.created_at.isoformat()
                if member.created_at
                else None
            ),
        })

    return results

@router.get("/api/members/{member_id}")
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    member = (
        db.query(Member)
        .filter(Member.id == member_id)
        .first()
    )

    if not member:
        from app.services.contact_consolidation import ConsolidatedContact
        alias=db.query(ConsolidatedContact).filter_by(source_member_id=member_id).first()
        if alias: member=db.get(Member,alias.member_id)

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    from app.services.member_reporting import membership_evidence, membership_report
    reporting=membership_report(member,membership_evidence(db))
    from app.member_portal.models import AssignedMembership
    assignment=db.query(AssignedMembership).filter_by(member_id=member.id).first()
    reporting.update(assigned_rate=assignment.rate if assignment else member.monthly_rate,
        assigned_months=assignment.months if assignment else None)
    return {
        "id": member.id,
        **reporting,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "email": member.email,
        "phone": member.phone,
        "status": member.status,
        "member_number": member.member_number,
        "barcode": member.barcode,
        "qr_code": member.qr_code,
        "digital_member_id": member.digital_member_id,
        "membership_type": member.membership_type,
        "membership_status": effective_membership_status(member),
        "assigned_coach": member.assigned_coach,
        "emergency_contact": member.emergency_contact,
        "emergency_phone": member.emergency_phone,
        "notes": member.notes,
        "address": member.address,
        "city": member.city,
        "state": member.state,
        "zip_code": member.zip_code,
        "date_of_birth": member.date_of_birth,
        "waiver_signed": member.waiver_signed,
        "membership_start": (
            member.membership_start.isoformat()
            if member.membership_start
            else None
        ),
        "membership_end": (
            member.membership_end.isoformat()
            if member.membership_end
            else None
        ),
        "billing_cycle": member.billing_cycle,
        "monthly_rate": member.monthly_rate,
        "next_billing_date": (
            member.next_billing_date.isoformat()
            if member.next_billing_date
            else None
        ),
        "autopay_enabled": member.autopay_enabled,
        "billing_status": member.billing_status,
        "last_payment_date": (
            member.last_payment_date.isoformat()
            if member.last_payment_date
            else None
        ),
        "clover_subscription_id": member.clover_subscription_id,
        "past_due_amount": member.past_due_amount,
        "clover_customer_id": member.clover_customer_id,
        "last_checkin": (
            member.last_checkin.isoformat()
            if member.last_checkin
            else None
        ),
        "total_checkins": member.total_checkins or 0,
        "photo_url": member.photo_url,
        "created_at": (
            member.created_at.isoformat()
            if member.created_at
            else None
        ),
    }


@router.put("/api/members/{member_id}")
def update_member(
    member_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    member = (
        db.query(Member)
        .filter(Member.id == member_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    changed_rate=False
    if 'monthly_rate' in data:
        import math
        try: rate=float(data['monthly_rate'])
        except (ValueError,TypeError):raise HTTPException(422,'Enter a valid monthly rate.')
        if not math.isfinite(rate) or not 0<=rate<=100000:raise HTTPException(422,'Enter a valid monthly rate.')
        changed_rate=round(rate,2)!=round(float(member.monthly_rate or 0),2)
        if changed_rate:require_admin(user)

    allowed_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "photo_url",
        "membership_type",
        "membership_status",
        "assigned_coach",
        "emergency_contact",
        "emergency_phone",
        "billing_cycle",
        "monthly_rate",
        "next_billing_date",
        "membership_start",
        "membership_end",
        "autopay_enabled",
        "billing_status",
        "clover_subscription_id",
        "last_payment_date",
        "past_due_amount",
        "notes",
    ]

    date_fields = [
        "membership_start",
        "membership_end",
        "next_billing_date",
        "last_payment_date",
    ]

    for field in date_fields:
        if field in data:
            if data[field]:
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid date format for {field}. "
                            "Use YYYY-MM-DD or ISO format."
                        ),
                    )
            else:
                data[field] = None

    for field in allowed_fields:
        if field in data:
            setattr(member, field, data[field])

    if changed_rate and member.billing_cycle=='30_day':
        from app.services.assigned_memberships import assign_membership
        assign_membership(db,member,member.membership_type or 'Monthly Membership',rate,1,activate=False,user_id=user.id)

    db.commit()
    db.refresh(member)

    return {
        "id": member.id,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "email": member.email,
        "phone": member.phone,
        "photo_url": member.photo_url,
        "member_number": member.member_number,
        "barcode": member.barcode,
        "qr_code": member.qr_code,
        "digital_member_id": member.digital_member_id,
        "membership_type": member.membership_type,
        "membership_status": effective_membership_status(member),
        "assigned_coach": member.assigned_coach,
        "emergency_contact": member.emergency_contact,
        "emergency_phone": member.emergency_phone,
        "notes": member.notes,
        "membership_start": (
            member.membership_start.isoformat()
            if member.membership_start
            else None
        ),
        "membership_end": (
            member.membership_end.isoformat()
            if member.membership_end
            else None
        ),
        "last_checkin": (
            member.last_checkin.isoformat()
            if member.last_checkin
            else None
        ),
        "total_checkins": member.total_checkins or 0,
        "billing_cycle": member.billing_cycle,
        "monthly_rate": member.monthly_rate,
        "next_billing_date": (
            member.next_billing_date.isoformat()
            if member.next_billing_date
            else None
        ),
        "autopay_enabled": member.autopay_enabled,
        "billing_status": member.billing_status,
        "clover_subscription_id": member.clover_subscription_id,
        "last_payment_date": (
            member.last_payment_date.isoformat()
            if member.last_payment_date
            else None
        ),
        "past_due_amount": member.past_due_amount,
    }
@router.post("/api/members/{member_id}/photo")
def upload_member_photo(
    member_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    member = (
        db.query(Member)
        .filter(Member.id == member_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    if not file.filename or "." not in file.filename:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a valid extension",
        )

    extension = file.filename.rsplit(".", 1)[-1].lower()

    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "webp",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP files are allowed",
        )

    upload_directory = os.path.join(
        "uploads",
        "members",
    )

    os.makedirs(
        upload_directory,
        exist_ok=True,
    )

    filename = f"{member_id}.{extension}"

    filepath = os.path.join(
        upload_directory,
        filename,
    )

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )
    finally:
        file.file.close()

    member.photo_url = f"/uploads/members/{filename}"

    db.commit()
    db.refresh(member)

    return {
        "message": "Photo uploaded successfully",
        "photo_url": member.photo_url,
    }
@router.post("/api/members/{member_id}/renew")
def renew_member(
    member_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = (
        db.query(Member)
        .filter(Member.id == member_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    try:
        months = int(data.get("months", 1))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Months must be a number",
        )

    if months not in [1, 3]:
        raise HTTPException(
            status_code=400,
            detail="Renewal must be 1 or 3 months",
        )

    today = datetime.utcnow()

    if member.membership_end and member.membership_end > today:
        current_end = member.membership_end
    else:
        current_end = today

    new_end = current_end + relativedelta(months=months)

    member.membership_start = member.membership_start or today
    member.membership_end = new_end
    member.membership_status = "active"
    member.billing_status = "active"
    member.past_due_amount = 0

    if months == 3:
        member.billing_cycle = "3_month_prepaid"
        member.next_billing_date = None
        member.autopay_enabled = False
    else:
        member.billing_cycle = "monthly"
        member.next_billing_date = new_end

    db.commit()
    db.refresh(member)

    return {
        "message": f"Membership renewed for {months} month(s)",
        "membership_start": (
            member.membership_start.isoformat()
            if member.membership_start
            else None
        ),
        "membership_end": (
            member.membership_end.isoformat()
            if member.membership_end
            else None
        ),
        "billing_cycle": member.billing_cycle,
        "next_billing_date": (
            member.next_billing_date.isoformat()
            if member.next_billing_date
            else None
        ),
        "membership_status": member.membership_status,
        "billing_status": member.billing_status,
    }
@router.post("/api/members/{member_id}/recalculate-membership")
def recalculate_membership(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = (
        db.query(Member)
        .filter(Member.id == member_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    recalculate_member_from_payments(member, db)

    db.commit()
    db.refresh(member)

    return {
        "message": "Membership recalculated",
        "membership_start": (
            member.membership_start.isoformat()
            if member.membership_start
            else None
        ),
        "membership_end": (
            member.membership_end.isoformat()
            if member.membership_end
            else None
        ),
        "billing_cycle": member.billing_cycle,
        "next_billing_date": (
            member.next_billing_date.isoformat()
            if member.next_billing_date
            else None
        ),
        "last_payment_date": (
            member.last_payment_date.isoformat()
            if member.last_payment_date
            else None
        ),
    }


@router.post("/api/members/recalculate-all")
def recalculate_all_memberships(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    members = db.query(Member).all()

    updated = 0
    skipped = 0

    for member in members:
        before_start = member.membership_start
        before_end = member.membership_end
        before_status = member.membership_status
        before_billing_status = member.billing_status

        recalculate_member_from_payments(member, db)

        changed = (
            member.membership_start != before_start
            or member.membership_end != before_end
            or member.membership_status != before_status
            or member.billing_status != before_billing_status
        )

        if changed:
            updated += 1
        else:
            skipped += 1

    db.commit()

    return {
        "message": "All memberships recalculated",
        "updated": updated,
        "skipped": skipped,
    }


@router.post('/api/members/prepare-accounts')
def prepare_customer_accounts(db: Session = Depends(get_db),user: User = Depends(current_user)):
    require_admin(user)
    from app.services.portal_accounts import prepare_all_accounts
    from app.services.assigned_memberships import preserve_recorded_rates
    rates=preserve_recorded_rates(db,user.id)
    result=prepare_all_accounts(db)
    result["agreed_rates_preserved"]=rates
    return {'message':'Eligible customer accounts are ready. Members set their own password securely; no bulk messages sent.',**result}


class AssignedMembershipIn(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    rate: float = Field(ge=0,le=100000,allow_inf_nan=False)
    months: int = Field(default=1,ge=1,le=120)
    activate: bool = False


@router.put('/api/members/{member_id}/assigned-membership')
def set_assigned_membership(member_id: int,data: AssignedMembershipIn,db: Session=Depends(get_db),user: User=Depends(current_user)):
    require_admin(user)
    member=db.query(Member).filter_by(id=member_id).with_for_update().first()
    if not member: raise HTTPException(404,'Member not found')
    if not data.name.strip(): raise HTTPException(422,'Enter a membership name')
    from app.services.assigned_memberships import assign_membership
    assignment=assign_membership(db,member,data.name,data.rate,data.months,activate=data.activate,user_id=user.id)
    db.commit()
    return {'saved':True,'rate':assignment.rate,'months':assignment.months,'membership_status':effective_membership_status(member)}
