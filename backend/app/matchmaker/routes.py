from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from .models import BoxingFighter, BoxingEvent, BoxingBout
from .schemas import FighterCreate, EventCreate, BoutCreate, PublicFighterRegistration
from .service import fighter_dict, ranked_matches

def build_matchmaker_router(current_user_dependency):
    router = APIRouter(prefix="/api/boxing", tags=["boxing-matchmaker"])

    def require_staff(user):
        if getattr(user, "role", None) not in ("admin", "staff"):
            raise HTTPException(status_code=403, detail="Admin or staff access required")

    @router.post("/register-fighter")
    def public_register_fighter(
        data: PublicFighterRegistration,
        db: Session = Depends(get_db),
    ):
        legal_name = (data.legal_name or "").strip()

        if not legal_name:
            raise HTTPException(
                status_code=400,
                detail="Fighter name is required",
            )

        low = data.available_weight_min
        high = data.available_weight_max

        if low is not None and high is not None and low > high:
            low, high = high, low

        boxrec_id = (data.boxrec_id or "").strip()

        if boxrec_id:
            existing = (
                db.query(BoxingFighter)
                .filter(BoxingFighter.boxrec_id == boxrec_id)
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"This BoxRec ID is already registered to "
                        f"{existing.legal_name}"
                    ),
                )

        fight_weight = data.fight_weight

        if fight_weight is None and low is not None and high is not None:
            fight_weight = round((low + high) / 2, 1)

        row = BoxingFighter(
            legal_name=legal_name,
            boxrec_id=boxrec_id,
            boxrec_url=(
                f"https://boxrec.com/en/box-pro/{boxrec_id}"
                if boxrec_id
                else ""
            ),
            pro_record=(data.pro_record or "").strip(),
            stance=(data.stance or "").strip(),
            gym=(data.gym or "").strip(),

            city=(data.city or "").strip(),
            state=(data.state or "").strip(),
            country=(data.country or "").strip(),

            phone=(data.phone or "").strip(),
            email=(data.email or "").strip().lower(),

            instagram=(data.instagram or "").strip(),
            facebook=(data.facebook or "").strip(),
            tiktok=(data.tiktok or "").strip(),
            twitter=(data.twitter or "").strip(),

            submitted_by_name=(data.submitted_by_name or "").strip(),
            submitted_by_role=(data.submitted_by_role or "boxer").strip().lower(),
            submitted_by_phone=(data.submitted_by_phone or "").strip(),
            submitted_by_email=(data.submitted_by_email or "").strip().lower(),

            fight_weight=fight_weight,
            available_weight_min=low,
            available_weight_max=high,

            available=True,

            # Public registration does not automatically verify
            # commission/medical eligibility.
            suspension_status="needs_review",
            bloodwork_status="missing",
            ok_license_status="unknown",
            federal_id_status="unknown",

            source="fighter_registration",
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return {
            "success": True,
            "fighter": fighter_dict(row),
            "message": (
                f"{row.legal_name} was submitted to the TNG fighter pool."
            ),
        }


    @router.get("/contacts")
    def boxing_contacts(
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighters = (
            db.query(BoxingFighter)
            .order_by(BoxingFighter.legal_name.asc())
            .all()
        )

        contacts = {}

        def add_contact(
            name,
            role,
            phone,
            email,
            fighter,
            instagram="",
            facebook="",
            tiktok="",
            twitter="",
        ):
            name = (name or "").strip()
            phone = (phone or "").strip()
            email = (email or "").strip().lower()

            if not name and not phone and not email:
                return

            key = (
                email
                or phone
                or f"{role}:{name.lower()}"
            )

            if key not in contacts:
                contacts[key] = {
                    "name": name,
                    "role": role,
                    "phone": phone,
                    "email": email,
                    "instagram": instagram or "",
                    "facebook": facebook or "",
                    "tiktok": tiktok or "",
                    "twitter": twitter or "",
                    "fighters": [],
                }

            contacts[key]["fighters"].append(
                {
                    "id": fighter.id,
                    "name": fighter.legal_name,
                    "record": fighter.pro_record or "",
                    "low_weight": fighter.available_weight_min,
                    "high_weight": fighter.available_weight_max,
                    "fight_weight": fighter.fight_weight,
                    "boxrec_id": fighter.boxrec_id or "",
                }
            )

        for fighter in fighters:
            add_contact(
                fighter.legal_name,
                "boxer",
                fighter.phone,
                fighter.email,
                fighter,
                fighter.instagram,
                fighter.facebook,
                fighter.tiktok,
                fighter.twitter,
            )

            add_contact(
                fighter.submitted_by_name,
                fighter.submitted_by_role or "contact",
                fighter.submitted_by_phone,
                fighter.submitted_by_email,
                fighter,
            )

            if fighter.manager_name:
                add_contact(
                    fighter.manager_name,
                    "manager",
                    fighter.manager_phone,
                    fighter.manager_email,
                    fighter,
                )

            if fighter.coach:
                add_contact(
                    fighter.coach,
                    "coach",
                    "",
                    "",
                    fighter,
                )

        return list(contacts.values())


    @router.get("/fighters")
    def list_fighters(db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)
        return [
            fighter_dict(f)
            for f in db.query(BoxingFighter).order_by(BoxingFighter.legal_name.asc()).all()
        ]

    @router.get("/fighters/by-boxrec/{boxrec_id}")
    def get_fighter_by_boxrec(
        boxrec_id: str,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        normalized = str(boxrec_id or "").strip()

        if not normalized:
            raise HTTPException(status_code=400, detail="BoxRec ID is required")

        row = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.boxrec_id == normalized)
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Fighter with this BoxRec ID is not in the TNG database yet",
            )

        return fighter_dict(row)

    @router.post("/fighters")
    def create_fighter(data: FighterCreate, db: Session = Depends(get_db), user=Depends(current_user_dependency)):
        require_staff(user)

        payload = data.model_dump()
        boxrec_id = str(payload.get("boxrec_id") or "").strip()
        payload["boxrec_id"] = boxrec_id

        if boxrec_id:
            existing = (
                db.query(BoxingFighter)
                .filter(BoxingFighter.boxrec_id == boxrec_id)
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"BoxRec ID {boxrec_id} is already assigned to {existing.legal_name}",
                )

        row = BoxingFighter(**payload)
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
