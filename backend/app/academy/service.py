from datetime import datetime, time

from sqlalchemy.orm import Session

from ..models import Attendance, Member
from .models import TrainingSession, TrainingSessionParticipant


def attach_members_checked_in_today(db: Session, session: TrainingSession) -> int:
    now = datetime.utcnow()
    start = datetime.combine(now.date(), time.min)
    end = datetime.combine(now.date(), time.max)

    rows = (
        db.query(Attendance.member_id)
        .filter(Attendance.checkin_time >= start, Attendance.checkin_time <= end)
        .distinct()
        .all()
    )

    attached = 0
    for (member_id,) in rows:
        exists = (
            db.query(TrainingSessionParticipant)
            .filter(
                TrainingSessionParticipant.session_id == session.id,
                TrainingSessionParticipant.member_id == member_id,
            )
            .first()
        )
        if not exists:
            db.add(TrainingSessionParticipant(session_id=session.id, member_id=member_id))
            attached += 1

    db.flush()
    return attached


def participant_payload(db: Session, participant: TrainingSessionParticipant) -> dict:
    member = db.query(Member).filter(Member.id == participant.member_id).first()
    name = "Unknown member"
    if member:
        name = f"{member.first_name} {member.last_name}".strip()
    return {
        "id": participant.id,
        "member_id": participant.member_id,
        "member_name": name,
        "attended": participant.attended,
        "performance_notes": participant.performance_notes,
    }
