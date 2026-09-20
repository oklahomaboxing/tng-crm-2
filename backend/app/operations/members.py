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

router = APIRouter(dependencies=[Depends(staff_user)])


@router.get("/api/members")
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    paid_membership_member_ids = (
        db.query(Sale.member_id)
        .join(
            MembershipProduct,
            MembershipProduct.id == Sale.product_id,
        )
        .filter(
            Sale.payment_status == "paid",
            Sale.member_id != None,
            MembershipProduct.is_membership == True,
            MembershipProduct.category == "membership",
            Sale.refunded.isnot(True),
        )
        .distinct()
        .subquery()
    )

    members = (
        db.query(Member)
        .filter(
            Member.id.in_(
                db.query(paid_membership_member_ids.c.member_id)
            ),
            Member.member_type == "MEMBER",
        )
        .order_by(
            Member.last_name.asc(),
            Member.first_name.asc(),
        )
        .all()
    )

    results = []

    for member in members:
        results.append({
            "id": member.id,
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
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    return {
        "id": member.id,
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
