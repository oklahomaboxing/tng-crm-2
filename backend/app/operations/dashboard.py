from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.core.dependencies import current_user
from app.database import get_db
from app.models import Attendance, Lead, Member, MembershipProduct, Sale, User
from app.services.memberships import recalculate_member_from_payments


router = APIRouter(
    prefix="/api",
    tags=["Operations - Dashboard"],
)


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    today = datetime.utcnow().date()
    now = datetime.utcnow()

    paid_membership_member_ids = (
        db.query(Sale.member_id)
        .join(
            MembershipProduct,
            MembershipProduct.id == Sale.product_id,
        )
        .filter(
            Sale.payment_status == "paid",
            Sale.member_id.isnot(None),
            or_(
                MembershipProduct.is_membership == True,
                MembershipProduct.category == "membership",
            ),
        )
        .distinct()
        .subquery()
    )

    dashboard_members = (
        db.query(Member)
        .filter(
            Member.id.in_(
                db.query(paid_membership_member_ids.c.member_id)
            ),
            Member.member_type == "MEMBER",
        )
        .all()
    )

    total_members = 0
    active_members = 0
    active_member_ids = set()

    for member in dashboard_members:
        recalculate_member_from_payments(member, db)
        total_members += 1

        if (
            member.membership_status == "active"
            and (
                member.membership_end is None
                or member.membership_end >= now
            )
        ):
            active_members += 1
            active_member_ids.add(member.id)

    db.commit()

    total_leads = db.query(Lead).count()

    today_checkins = (
        db.query(Attendance)
        .filter(func.date(Attendance.checkin_time) == today)
        .count()
    )

    month_sales = (
        db.query(Sale)
        .filter(
            extract("month", Sale.sale_date) == now.month,
            extract("year", Sale.sale_date) == now.year,
        )
        .all()
    )

    revenue_this_month = sum(
        sale.amount or 0
        for sale in month_sales
    )


    active_member_revenue_this_month = sum(
        sale.amount or 0
        for sale in month_sales
        if (
            sale.member_id is not None
            and sale.member_id in active_member_ids
            and sale.payment_status == "paid"
        )
    )

    recent_checkins = (
        db.query(Attendance)
        .order_by(Attendance.checkin_time.desc())
        .limit(10)
        .all()
    )

    recent = []

    for attendance in recent_checkins:
        member = (
            db.query(Member)
            .filter(Member.id == attendance.member_id)
            .first()
        )

        recent.append(
            {
                "member": (
                    f"{member.first_name} {member.last_name}"
                    if member
                    else "Unknown"
                ),
                "time": (
                    attendance.checkin_time.isoformat()
                    if attendance.checkin_time
                    else None
                ),
                "method": attendance.method,
            }
        )

    return {
        "total_members": total_members,
        "active_members": active_members,
        "total_leads": total_leads,
        "today_checkins": today_checkins,
        "sales_this_month": len(month_sales),
        "revenue_this_month": revenue_this_month,
        "active_member_revenue_this_month": active_member_revenue_this_month,
        "recent_checkins": recent,
    }
