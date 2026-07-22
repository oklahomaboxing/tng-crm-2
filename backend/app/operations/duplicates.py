from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.dependencies import current_user
from ..core.permissions import require_admin
from ..database import get_db
from ..models import Attendance, Member, Sale, User

router = APIRouter()


@router.get("/api/duplicates/members")
def find_duplicate_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    members = db.query(Member).all()
    results = []

    def member_summary(member: Member):
        payments = (
            db.query(Sale)
            .filter(Sale.member_id == member.id)
            .all()
        )

        payment_count = len(payments)
        lifetime_value = sum(
            sale.amount or 0
            for sale in payments
        )

        attendance_count = (
            db.query(Attendance)
            .filter(Attendance.member_id == member.id)
            .count()
        )

        score = 0

        if member.clover_customer_id:
            score += 100

        if payment_count:
            score += payment_count * 10

        if attendance_count:
            score += min(attendance_count, 50)

        if member.photo_url:
            score += 15

        if member.membership_status == "active":
            score += 20

        if member.email:
            score += 5

        if member.phone:
            score += 5

        return {
            "id": member.id,
            "name": (
                f"{member.first_name or ''} "
                f"{member.last_name or ''}"
            ).strip(),
            "email": member.email,
            "phone": member.phone,
            "member_number": member.member_number,
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
            "clover_customer_id": member.clover_customer_id,
            "photo_url": member.photo_url,
            "payment_count": payment_count,
            "lifetime_value": lifetime_value,
            "attendance_count": attendance_count,
            "created_at": (
                member.created_at.isoformat()
                if member.created_at
                else None
            ),
            "score": score,
        }

    for index, member_a in enumerate(members):
        for member_b in members[index + 1:]:
            reasons = []
            confidence = 0

            if (
                member_a.email
                and member_b.email
                and member_a.email.lower()
                == member_b.email.lower()
            ):
                reasons.append("Same email")
                confidence = max(confidence, 100)

            if (
                member_a.phone
                and member_b.phone
                and member_a.phone == member_b.phone
            ):
                reasons.append("Same phone")
                confidence = max(confidence, 100)

            if (
                member_a.clover_customer_id
                and member_b.clover_customer_id
                and member_a.clover_customer_id
                == member_b.clover_customer_id
            ):
                reasons.append("Same Clover Customer ID")
                confidence = max(confidence, 100)

            if (
                member_a.first_name
                and member_b.first_name
                and member_a.last_name
                and member_b.last_name
                and member_a.first_name.lower()
                == member_b.first_name.lower()
                and member_a.last_name.lower()
                == member_b.last_name.lower()
            ):
                reasons.append("Same first and last name")
                confidence = max(confidence, 90)

            if not reasons:
                continue

            summary_a = member_summary(member_a)
            summary_b = member_summary(member_b)

            if summary_a["score"] >= summary_b["score"]:
                recommended_keep_id = member_a.id
                recommended_merge_id = member_b.id
            else:
                recommended_keep_id = member_b.id
                recommended_merge_id = member_a.id

            results.append(
                {
                    "member_a": summary_a,
                    "member_b": summary_b,
                    "reasons": reasons,
                    "confidence": confidence,
                    "recommended_keep_id": recommended_keep_id,
                    "recommended_merge_id": recommended_merge_id,
                }
            )

    return results


@router.post("/api/duplicates/members/merge")
def merge_duplicate_members(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    keep_id = data.get("keep_id")
    merge_id = data.get("merge_id")

    if (
        not keep_id
        or not merge_id
        or keep_id == merge_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid merge request",
        )

    keep = (
        db.query(Member)
        .filter(Member.id == keep_id)
        .first()
    )

    merge = (
        db.query(Member)
        .filter(Member.id == merge_id)
        .first()
    )

    if not keep or not merge:
        raise HTTPException(
            status_code=404,
            detail="Member not found",
        )

    db.query(Attendance).filter(
        Attendance.member_id == merge.id
    ).update(
        {"member_id": keep.id},
        synchronize_session=False,
    )

    db.query(Sale).filter(
        Sale.member_id == merge.id
    ).update(
        {"member_id": keep.id},
        synchronize_session=False,
    )

    fields = [
        "email",
        "phone",
        "photo_url",
        "clover_customer_id",
        "membership_type",
        "membership_status",
        "membership_start",
        "membership_end",
        "billing_cycle",
        "monthly_rate",
        "next_billing_date",
        "autopay_enabled",
        "billing_status",
        "last_payment_date",
        "past_due_amount",
        "notes",
    ]

    for field in fields:
        keep_value = getattr(keep, field, None)
        merge_value = getattr(merge, field, None)

        if not keep_value and merge_value:
            setattr(keep, field, merge_value)

    keep.total_checkins = (
        (keep.total_checkins or 0)
        + (merge.total_checkins or 0)
    )

    keep.checkins = (
        (keep.checkins or 0)
        + (merge.checkins or 0)
    )

    if merge.last_checkin and (
        not keep.last_checkin
        or merge.last_checkin > keep.last_checkin
    ):
        keep.last_checkin = merge.last_checkin

    db.delete(merge)
    db.commit()
    db.refresh(keep)

    return {
        "message": "Members merged successfully",
        "kept_member_id": keep.id,
        "deleted_member_id": merge_id,
    }
