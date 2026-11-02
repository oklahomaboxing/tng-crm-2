from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.dependencies import current_user
from ..core.permissions import require_admin
from ..database import get_db
from ..models import Attendance, Member, Sale, User

from app.services.contact_consolidation import ConsolidatedContact

router = APIRouter()


@router.get("/api/duplicates/members")
def find_duplicate_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    members = db.query(Member).order_by(Member.id).all()
    from app.services.member_profiles import phone_key
    summaries={}
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
                and member_a.email.strip().casefold()
                == member_b.email.strip().casefold()
            ):
                reasons.append("Same email")
                confidence = max(confidence, 100)

            if (
                member_a.phone
                and member_b.phone
                and phone_key(member_a.phone)
                and phone_key(member_a.phone) == phone_key(member_b.phone)
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

            if member_a.id not in summaries:summaries[member_a.id]=member_summary(member_a)
            if member_b.id not in summaries:summaries[member_b.id]=member_summary(member_b)
            summary_a = summaries[member_a.id]
            summary_b = summaries[member_b.id]

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
                    "contact_match": any(reason in reasons for reason in ('Same email','Same phone','Same Clover Customer ID')),
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

    from app.services.contact_consolidation import merge_profiles
    keep_id,source_id=data.get('keep_id'),data.get('merge_id')
    if type(keep_id) is not int or type(source_id) is not int or keep_id<=0 or source_id<=0:
        raise HTTPException(400, 'Choose two valid profile IDs.')
    try:
        result=merge_profiles(db,user,keep_id,source_id,allow_linked=True,reviewed_contact=True)
        from app.services.portal_accounts import prepare_accounts
        prepare_accounts(db,{result['member_id']})
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Merge could not be saved because linked records conflict. No records were changed.')
    return {'message':'Profiles consolidated; history and original card identifiers retained.',
        'kept_member_id':result['member_id'],'deleted_member_id':result['source_id']}


@router.get('/api/duplicates/contacts/preview')
def preview_contact_consolidation(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    from app.services.contact_consolidation import confirmed_plan
    plan = confirmed_plan(db)
    return {'confirmed_duplicates':len(plan), 'profiles':plan}


@router.post('/api/duplicates/contacts/consolidate')
def consolidate_contacts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    from app.services.contact_consolidation import consolidate
    return consolidate(db, user)
