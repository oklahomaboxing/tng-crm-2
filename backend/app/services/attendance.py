"""Shared attendance write, serialized per member on PostgreSQL."""
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models import Member, Attendance
from app.services.memberships import effective_membership_status
from fastapi import HTTPException


def record_attendance(db, member, *, method='barcode', location='Front Desk', duplicate_seconds=120):
    member = db.execute(select(Member).where(Member.id == member.id).with_for_update().execution_options(populate_existing=True)).scalar_one()
    if effective_membership_status(member) != 'active':
        raise HTTPException(403, 'Membership is inactive or expired. Please visit the front desk.')
    now = datetime.utcnow()
    recent = db.query(Attendance).filter(Attendance.member_id == member.id,
        Attendance.checkin_time >= now - timedelta(seconds=duplicate_seconds)).first()
    if recent:
        return False, member
    db.add(Attendance(member_id=member.id, checkin_time=now, method=method, location=location))
    member.last_checkin = now
    member.checkins = (member.checkins or 0) + 1
    member.total_checkins = (member.total_checkins or 0) + 1
    db.flush()
    return True, member
