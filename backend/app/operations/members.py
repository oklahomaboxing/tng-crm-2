
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.dependencies import current_user
from ..database import get_db
from ..models import Member, Sale, User
from ..services.memberships import recalculate_member_from_payments


router = APIRouter()


@router.get("/api/members")
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cutoff_date = datetime(2026, 7, 20, 23, 59, 59)

    paid_sale_member_ids = (
        db.query(Sale.member_id)
        .filter(
            Sale.payment_status == "paid",
            Sale.member_id != None,
        )
        .distinct()
        .subquery()
    )

    members = (
        db.query(Member)
        .filter(
            Member.id.in_(
                db.query(paid_sale_member_ids.c.member_id)
            )
        )
        .order_by(
            Member.last_name.asc(),
            Member.first_name.asc(),
        )
        .all()
    )

    results = []

    for member in members:
        recalculate_member_from_payments(member, db)

        if (
            member.membership_end
            and member.membership_end <= cutoff_date
        ):
            continue

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
            "membership_status": member.membership_status,
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

    db.commit()

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

    recalculate_member_from_payments(member, db)

    db.commit()
    db.refresh(member)

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
        "membership_status": member.membership_status,
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
        "membership_status": member.membership_status,
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