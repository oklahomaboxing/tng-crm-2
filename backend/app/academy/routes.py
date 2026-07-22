from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .dependencies import academy_current_user
from .models import AcademyClass, AcademyProgram, TrainingSession, TrainingSessionParticipant
from .schemas import (
    AcademyClassCreate,
    AcademyClassOut,
    AcademyDashboardOut,
    AcademyProgramCreate,
    AcademyProgramOut,
    ParticipantOut,
    TrainingSessionCreate,
    TrainingSessionOut,
    TrainingSessionUpdate,
)
from .service import attach_members_checked_in_today, participant_payload

router = APIRouter(
    prefix="/api/academy",
    tags=["TNG Academy"],
    dependencies=[Depends(academy_current_user)],
)


def session_payload(db: Session, item: TrainingSession) -> dict:
    count = (
        db.query(TrainingSessionParticipant)
        .filter(TrainingSessionParticipant.session_id == item.id)
        .count()
    )
    return {
        "id": item.id,
        "academy_class_id": item.academy_class_id,
        "title": item.title,
        "coach_name": item.coach_name,
        "focus": item.focus,
        "status": item.status,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "coach_notes": item.coach_notes,
        "homework": item.homework,
        "created_at": item.created_at,
        "participant_count": count,
    }


@router.get("/dashboard", response_model=AcademyDashboardOut)
def academy_dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    day_start = datetime.combine(now.date(), time.min)
    day_end = datetime.combine(now.date(), time.max)
    recent = db.query(TrainingSession).order_by(TrainingSession.created_at.desc()).limit(8).all()
    sessions_today = db.query(TrainingSession).filter(TrainingSession.created_at >= day_start, TrainingSession.created_at <= day_end).count()
    today_session_ids = [row.id for row in db.query(TrainingSession).filter(TrainingSession.created_at >= day_start, TrainingSession.created_at <= day_end).all()]
    athletes_today = 0
    if today_session_ids:
        athletes_today = db.query(TrainingSessionParticipant.member_id).filter(TrainingSessionParticipant.session_id.in_(today_session_ids)).distinct().count()
    return {
        "active_programs": db.query(AcademyProgram).filter(AcademyProgram.active.is_(True)).count(),
        "active_classes": db.query(AcademyClass).filter(AcademyClass.active.is_(True)).count(),
        "sessions_today": sessions_today,
        "athletes_today": athletes_today,
        "recent_sessions": [session_payload(db, item) for item in recent],
    }


@router.get("/programs", response_model=list[AcademyProgramOut])
def list_programs(db: Session = Depends(get_db)):
    return db.query(AcademyProgram).order_by(AcademyProgram.name.asc()).all()


@router.post("/programs", response_model=AcademyProgramOut, status_code=201)
def create_program(data: AcademyProgramCreate, db: Session = Depends(get_db)):
    duplicate = db.query(AcademyProgram).filter(AcademyProgram.name == data.name.strip()).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Program name already exists")
    item = AcademyProgram(**data.model_dump())
    item.name = item.name.strip()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/classes", response_model=list[AcademyClassOut])
def list_classes(db: Session = Depends(get_db)):
    return db.query(AcademyClass).order_by(AcademyClass.created_at.desc()).all()


@router.post("/classes", response_model=AcademyClassOut, status_code=201)
def create_class(data: AcademyClassCreate, db: Session = Depends(get_db)):
    if not db.query(AcademyProgram).filter(AcademyProgram.id == data.program_id).first():
        raise HTTPException(status_code=404, detail="Program not found")
    item = AcademyClass(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/sessions", response_model=list[TrainingSessionOut])
def list_sessions(db: Session = Depends(get_db)):
    rows = db.query(TrainingSession).order_by(TrainingSession.created_at.desc()).limit(100).all()
    return [session_payload(db, item) for item in rows]


@router.post("/sessions", response_model=TrainingSessionOut, status_code=201)
def create_session(data: TrainingSessionCreate, db: Session = Depends(get_db)):
    if data.academy_class_id and not db.query(AcademyClass).filter(AcademyClass.id == data.academy_class_id).first():
        raise HTTPException(status_code=404, detail="Academy class not found")
    values = data.model_dump(exclude={"attach_checked_in_members"})
    item = TrainingSession(**values, status="live", started_at=datetime.utcnow())
    db.add(item)
    db.flush()
    if data.attach_checked_in_members:
        attach_members_checked_in_today(db, item)
    db.commit()
    db.refresh(item)
    return session_payload(db, item)


@router.patch("/sessions/{session_id}", response_model=TrainingSessionOut)
def update_session(session_id: int, data: TrainingSessionUpdate, db: Session = Depends(get_db)):
    item = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Training session not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    if data.status == "completed" and not item.ended_at:
        item.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return session_payload(db, item)


@router.post("/sessions/{session_id}/attach-checked-in")
def attach_checked_in(session_id: int, db: Session = Depends(get_db)):
    item = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Training session not found")
    attached = attach_members_checked_in_today(db, item)
    db.commit()
    return {"attached": attached, "session_id": session_id}


@router.get("/sessions/{session_id}/participants", response_model=list[ParticipantOut])
def list_participants(session_id: int, db: Session = Depends(get_db)):
    rows = db.query(TrainingSessionParticipant).filter(TrainingSessionParticipant.session_id == session_id).all()
    return [participant_payload(db, row) for row in rows]
