from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from app.core.dependencies import current_user, staff_user
from app.database import get_db
from app.models import Attendance, Lead, Member, MembershipProduct, Sale, User
from app.services.memberships import effective_membership_status
from app.services.business_time import reporting_periods


router = APIRouter(
    prefix="/api",
    tags=["Operations - Dashboard"],
    dependencies=[Depends(staff_user)],
)


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    now = datetime.utcnow()
    period = reporting_periods(now)

    from app.services.member_reporting import membership_evidence, membership_report, membership_totals
    dashboard_members = db.query(Member).all()
    paid_ids=membership_evidence(db)
    roster=membership_totals(dashboard_members,paid_ids,now)
    total_members=roster['members']
    active_members=roster['active']
    active_member_ids={m.id for m in dashboard_members if membership_report(m,paid_ids,now)['is_current_member']}

    total_leads = db.query(Lead).count()

    today_checkins = (
        db.query(Attendance)
        .filter(Attendance.checkin_time >= period["day_start"], Attendance.checkin_time < period["day_end"])
        .count()
    )

    month_sales = (
        db.query(Sale)
        .filter(
            Sale.sale_date >= period["month_start"],
            Sale.sale_date < period["month_end"],
        )
        .all()
    )

    revenue_this_month = sum(
        max(0, (sale.amount or 0) - (sale.refund_amount or 0))
        for sale in month_sales
        if sale.payment_status == "paid" and not sale.refunded
    )


    nutrition_club_sales_this_month = sum(
        max(0, (sale.amount or 0) - (sale.refund_amount or 0))
        for sale in month_sales
        if (
            sale.payment_status == "paid"
            and not sale.refunded
            and sale.sale_type == "nexgen_nutrition"
        )
    )


    active_member_revenue_this_month = sum(
        max(0, (sale.amount or 0) - (sale.refund_amount or 0))
        for sale in month_sales
        if (
            sale.member_id is not None
            and sale.member_id in active_member_ids
            and sale.payment_status == "paid"
            and not sale.refunded
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
        "expiring_members": roster["expiring"],
        "expired_members": roster["expired"],
        "inactive_members": roster["inactive"],
        "contacts": roster["contact"],
        "membership_review": roster["review"],
        "total_leads": total_leads,
        "today_checkins": today_checkins,
        "sales_this_month": sum(1 for sale in month_sales if sale.payment_status == "paid" and not sale.refunded),
        "transactions_this_month": len(month_sales),
        "timezone": "America/Chicago",
        "revenue_this_month": revenue_this_month,
        "nutrition_club_sales_this_month": nutrition_club_sales_this_month,
        "active_member_revenue_this_month": active_member_revenue_this_month,
        "recent_checkins": recent,
    }
