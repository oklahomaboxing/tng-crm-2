from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from .models import BoxingFighter, BoxingEvent, BoxingBout
from .schemas import FighterCreate, EventCreate, BoutCreate
from .service import fighter_dict, ranked_matches

def build_matchmaker_router(current_user_dependency):
    router = APIRouter(prefix="/api/boxing", tags=["boxing-matchmaker"])

    def require_staff(user):
        if getattr(user, "role", None) not in ("admin", "staff"):
            raise HTTPException(status_code=403, detail="Admin or staff access required")

    @router.get("/fighters")
    def list_fighters(db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)
        return [
            fighter_dict(f)
            for f in db.query(BoxingFighter).order_by(BoxingFighter.legal_name.asc()).all()
        ]

    @router.post("/fighters")
    def create_fighter(data: FighterCreate, db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)
        row = BoxingFighter(**data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return fighter_dict(row)

    @router.get("/events")
    def list_events(db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)
        rows = db.query(BoxingEvent).order_by(BoxingEvent.event_date.desc()).all()
        return [
            {
                "id": e.id,
                "slug": e.slug,
                "name": e.name,
                "venue": e.venue,
                "venue_address": e.venue_address,
                "event_date": e.event_date,
                "status": e.status,
            }
            for e in rows
        ]

    @router.post("/events")
    def create_event(data: EventCreate, db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)
        if db.query(BoxingEvent).filter(BoxingEvent.slug == data.slug).first():
            raise HTTPException(status_code=400, detail="Event slug already exists")
        row = BoxingEvent(**data.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"id": row.id, "slug": row.slug, "name": row.name}

    @router.get("/match/{fighter_id}")
    def find_matches(
        fighter_id: int,
        event_id: int | None = None,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)
        base, matches = ranked_matches(db, fighter_id, event_id)
        if not base:
            raise HTTPException(status_code=404, detail="Fighter not found")
        return {"fighter": base, "event_id": event_id, "matches": matches}

    @router.post("/bouts")
    def create_bout(data: BoutCreate, db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)

        if data.red_fighter_id == data.blue_fighter_id:
            raise HTTPException(status_code=400, detail="Pick two different fighters")

        if data.event_id:
            conflict = db.query(BoxingBout).filter(
                BoxingBout.event_id == data.event_id,
                BoxingBout.status.notin_(["void", "cancelled"]),
                or_(
                    BoxingBout.red_fighter_id.in_([data.red_fighter_id, data.blue_fighter_id]),
                    BoxingBout.blue_fighter_id.in_([data.red_fighter_id, data.blue_fighter_id]),
                ),
            ).first()
            if conflict:
                raise HTTPException(status_code=400, detail="One fighter is already booked on this event")

        row = BoxingBout(**data.model_dump(), status="draft")
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"id": row.id, "status": row.status}

    return router
