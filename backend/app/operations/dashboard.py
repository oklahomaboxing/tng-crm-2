from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.core.dependencies import current_user
from app.database import get_db
from app.models import Attendance, Lead, Member, Sale, User
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

    cutoff_date = datetime(2026, 7, 20, 23, 59, 59)

    paid_member_ids = [
        row[0]
        for row in (
            db.query(Sale.member_id)
            .join(
                MembershipProduct,
                MembershipProduct.id == Sale.product_id,
            )
            .filter(
                Sale.payment_status == "paid",
                Sale.member_id != None,
                or_(
                    Sale.sale_type == "membership",
                    MembershipProduct.is_membership == True,
                    MembershipProduct.category == "membership",
                ),
            )
            .distinct()
            .all()
        )
        if row[0] is not None
    ]

    dashboard_members = (
        db.query(Member)
        .filter(
            or_(
                Member.id.in_(paid_member_ids),
                Member.membership_status == "active",
            )
        )
        .all()
    )

    visible_members = []

    for member in dashboard_members:
        recalculate_member_from_payments(member, db)

        if (
            member.membership_end
            and member.membership_end <= cutoff_date
        ):
            continue

        visible_members.append(member)

    db.commit()

    total_members = len(visible_members)
    active_members = len(visible_members)
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
        "recent_checkins": recent,
    }