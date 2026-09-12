import resend
from datetime import datetime
import os
import json
import urllib.request
import urllib.error
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, inspect, text
from ..database import get_db, engine
from .models import BoxingContract, BoxingFighter, BoxingEvent, BoxingBout, BoxingEventChecklist, BoxingEventFee, BoxingSeries, BoxingSeriesFighter, BoxingSignedFighter, BoxingEventPublication
from .schemas import FighterCreate, EventCreate, BoutCreate, PublicFighterRegistration
from .service import fighter_dict, ranked_matches


def ensure_contract_travel_schema():
    """
    Add travel/lodging/per-diem columns to an existing
    boxing contract table.

    Works with PostgreSQL and SQLite.
    """
    table_name = BoxingContract.__tablename__
    inspector = inspect(engine)

    if table_name not in inspector.get_table_names():
        return

    existing = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    required_columns = {
        "travel_type": "VARCHAR",
        "travel_paid_by": "VARCHAR",
        "hotel_provided": "VARCHAR",
        "hotel_name": "VARCHAR",
        "hotel_nights": "INTEGER",
        "per_diem_daily": "FLOAT",
        "per_diem_days": "INTEGER",
        "per_diem_total": "FLOAT",
    }

    missing = [
        (name, sql_type)
        for name, sql_type in required_columns.items()
        if name not in existing
    ]

    if not missing:
        return

    with engine.begin() as connection:
        for name, sql_type in missing:
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {name} {sql_type}"
                )
            )


ensure_contract_travel_schema()


PROMOTER_CHECKLIST = [
    (
        "promoter_license",
        "Promoter License Application, Payment & Surety Bond current."
    ),
    (
        "event_permit",
        "Event Permit to Commission and Payment."
    ),
    (
        "ticket_disclosure",
        "Disclosure of ticket prices, sponsorships, VIP tables, etc."
    ),
    (
        "insurance",
        "$10,000 Medical and $10,000 accidental death insurance submitted to Commission at least 24-48 hours prior to event."
    ),
    (
        "official_fees",
        "Official fees and other fees provided to Commission at weigh-in."
    ),
    (
        "ring_inspection",
        "Ring/cage set up for inspection a minimum of 2 hours prior to start."
    ),
    (
        "tickets_credentials",
        "Everyone entering venue has a ticket with price clearly marked or a Commission-issued credential."
    ),
    (
        "vip_sponsorship",
        "VIP and sponsorship table prices disclosed for assessment."
    ),
    (
        "canvas_cleaning",
        "Individuals assigned to wipe blood and clean canvas between rounds and bouts."
    ),
    (
        "safety_barrier",
        "Bicycle rack or other Commission-acceptable barrier between spectators and ringside."
    ),
    (
        "security",
        "Commission briefed on security measures; security posted at entrances, exits and dressing rooms."
    ),
    (
        "pregnancy_tests",
        "Pregnancy tests purchased and available for female fighters at pre-fight physicals."
    ),
    (
        "fighter_restrooms",
        "Restrooms accessible to fighters."
    ),
    (
        "dressing_room_water",
        "Water available in dressing rooms and at ringside."
    ),
    (
        "ringside_towels",
        "Towels available at ringside."
    ),
    (
        "ringside_tables",
        "Tables and chairs completely around ring for official use only; no ticketed seating inside safety barrier."
    ),
    (
        "corner_chairs",
        "Four chairs in each corner for Commission Inspector and three corners."
    ),
    (
        "judge_stools",
        "Three raised stools centered between corners for judges."
    ),
    (
        "ring_setup_brief",
        "Commission briefed on ring/cage setup and authorized apron personnel."
    ),
    (
        "commission_contact",
        "Individuals appointed to handle Commission concerns and available immediately."
    ),
    (
        "ambulance",
        "Ambulance with licensed transport/resuscitation medical personnel on site before and during event."
    ),
]


MATCHMAKER_CHECKLIST = [
    (
        "matchmaker_license",
        "Matchmaker License Application and Payment."
    ),
    (
        "bout_submission",
        "Bout information submitted to Commission at least 7-14 business days prior, including legal names, DOB, location, order, corner, sport, rounds and weight class."
    ),
    (
        "weigh_in_info",
        "Weigh-in time and location submitted to Commission."
    ),
    (
        "bout_contracts",
        "Bout contracts prepared for Commission at weigh-in."
    ),
    (
        "bloodwork",
        "All fighter bloodwork results turned into Commission prior to weigh-in."
    ),
    (
        "youth_release",
        "Special parent release form for youth kickboxers under 18 received by Commission 7-10 days before event when applicable."
    ),
    (
        "age_40_medicals",
        "Special medical exams for fighters age 40 and older received by Commission 7-10 days before event when applicable."
    ),
]


EVENT_FEES = [
    {
        "name": "Promoter License",
        "amount": "$250 + $10,000 Surety Bond",
    },
    {
        "name": "Matchmaker License",
        "amount": "$150",
    },
    {
        "name": "Event Permit",
        "amount": "$50 or $100 depending on event type",
    },
    {
        "name": "Sport Permits",
        "amount": "Permit required for each sport on card",
    },
    {
        "name": "Fighter Insurance",
        "amount": "Depends on carrier and number of bouts",
    },
    {
        "name": "Officials",
        "amount": "Promoter responsibility; varies by bouts, rounds, title fights and travel",
    },
    {
        "name": "Assessment",
        "amount": "5% gross ticket sales or $450 minimum",
    },
    {
        "name": "Vendor Assessment",
        "amount": "5% gross vendor sales",
    },
    {
        "name": "Streaming / Broadcast",
        "amount": "5% assessment",
    },
]


def seed_event_fees(db, event_id):
    existing = (
        db.query(BoxingEventFee)
        .filter(BoxingEventFee.event_id == event_id)
        .count()
    )

    if existing:
        return

    for index, fee in enumerate(EVENT_FEES):
        key = (
            fee["name"]
            .lower()
            .replace(" / ", "_")
            .replace(" ", "_")
            .replace("-", "_")
        )

        db.add(
            BoxingEventFee(
                event_id=event_id,
                fee_key=key,
                name=fee["name"],
                estimate=fee["amount"],
                paid=False,
            )
        )

    db.commit()


def seed_event_checklist(db, event_id):
    existing = (
        db.query(BoxingEventChecklist)
        .filter(BoxingEventChecklist.event_id == event_id)
        .count()
    )

    if existing:
        return

    order = 0

    for key, label in PROMOTER_CHECKLIST:
        db.add(
            BoxingEventChecklist(
                event_id=event_id,
                section="promoter",
                item_key=key,
                label=label,
                sort_order=order,
            )
        )
        order += 1

    order = 0

    for key, label in MATCHMAKER_CHECKLIST:
        db.add(
            BoxingEventChecklist(
                event_id=event_id,
                section="matchmaker",
                item_key=key,
                label=label,
                sort_order=order,
            )
        )
        order += 1

    db.commit()


def ensure_first_five_series(db):
    series = (
        db.query(BoxingSeries)
        .filter(BoxingSeries.slug == "first-5-fights")
        .first()
    )

    if series:
        return series

    series = BoxingSeries(
        name="First 5 Fights Series",
        slug="first-5-fights",
        description=(
            "TNG developmental series promoting fighters "
            "through their next five professional fights."
        ),
        target_fights=5,
        active=True,
    )

    db.add(series)
    db.commit()
    db.refresh(series)

    return series


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


    @router.get("/signed-fighters")
    def list_signed_fighters(
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        rows = (
            db.query(BoxingSignedFighter)
            .order_by(
                BoxingSignedFighter.id.asc()
            )
            .all()
        )

        results = []

        for row in rows:
            fighter = (
                db.query(BoxingFighter)
                .filter(
                    BoxingFighter.id ==
                    row.fighter_id
                )
                .first()
            )

            if not fighter:
                continue

            results.append({
                "id": row.id,
                "fighter_id": row.fighter_id,

                "fighter":
                    fighter_dict(fighter),

                "signed_date":
                    row.signed_date,

                "start_date":
                    row.start_date,

                "end_date":
                    row.end_date,

                "agreement_type":
                    row.agreement_type,

                "status":
                    row.status,

                "exclusive":
                    bool(row.exclusive),

                "contract_on_file":
                    bool(row.contract_on_file),

                "notes":
                    row.notes,
            })

        return results


    @router.post("/signed-fighters")
    def sign_fighter(
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighter_id = data.get("fighter_id")

        try:
            fighter_id = int(fighter_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="fighter_id is required",
            )

        fighter = (
            db.query(BoxingFighter)
            .filter(
                BoxingFighter.id ==
                fighter_id
            )
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        existing = (
            db.query(BoxingSignedFighter)
            .filter(
                BoxingSignedFighter.fighter_id ==
                fighter_id
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Fighter is already signed",
            )

        row = BoxingSignedFighter(
            fighter_id=fighter_id,

            signed_date=str(
                data.get("signed_date") or ""
            ).strip(),

            start_date=str(
                data.get("start_date") or ""
            ).strip(),

            end_date=str(
                data.get("end_date") or ""
            ).strip(),

            agreement_type=str(
                data.get("agreement_type")
                or "development"
            ).strip(),

            status=str(
                data.get("status")
                or "active"
            ).strip(),

            exclusive=bool(
                data.get("exclusive", False)
            ),

            contract_on_file=bool(
                data.get(
                    "contract_on_file",
                    False
                )
            ),

            notes=str(
                data.get("notes") or ""
            ).strip(),
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "fighter_id": row.fighter_id,
            "fighter": fighter_dict(fighter),
            "signed_date": row.signed_date,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "agreement_type": row.agreement_type,
            "status": row.status,
            "exclusive": bool(row.exclusive),
            "contract_on_file":
                bool(row.contract_on_file),
            "notes": row.notes,
        }


    @router.patch(
        "/signed-fighters/{signed_fighter_id}"
    )
    def update_signed_fighter(
        signed_fighter_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        row = (
            db.query(BoxingSignedFighter)
            .filter(
                BoxingSignedFighter.id ==
                signed_fighter_id
            )
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Signed fighter not found",
            )

        for field in (
            "signed_date",
            "start_date",
            "end_date",
            "agreement_type",
            "status",
            "notes",
        ):
            if field in data:
                setattr(
                    row,
                    field,
                    str(
                        data.get(field) or ""
                    ).strip(),
                )

        if "exclusive" in data:
            row.exclusive = bool(
                data.get("exclusive")
            )

        if "contract_on_file" in data:
            row.contract_on_file = bool(
                data.get("contract_on_file")
            )

        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "fighter_id": row.fighter_id,
            "signed_date": row.signed_date,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "agreement_type":
                row.agreement_type,
            "status": row.status,
            "exclusive":
                bool(row.exclusive),
            "contract_on_file":
                bool(row.contract_on_file),
            "notes": row.notes,
        }


    @router.delete(
        "/signed-fighters/{signed_fighter_id}"
    )
    def release_signed_fighter(
        signed_fighter_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        row = (
            db.query(BoxingSignedFighter)
            .filter(
                BoxingSignedFighter.id ==
                signed_fighter_id
            )
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Signed fighter not found",
            )

        db.delete(row)
        db.commit()

        return {
            "ok": True,
            "id": signed_fighter_id,
        }


    @router.get("/series")
    def list_series(
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        ensure_first_five_series(db)

        rows = (
            db.query(BoxingSeries)
            .order_by(BoxingSeries.id.asc())
            .all()
        )

        return [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
                "target_fights": row.target_fights,
                "active": bool(row.active),
            }
            for row in rows
        ]


    @router.get("/series/{series_id}/fighters")
    def list_series_fighters(
        series_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        rows = (
            db.query(BoxingSeriesFighter)
            .filter(
                BoxingSeriesFighter.series_id == series_id
            )
            .order_by(BoxingSeriesFighter.id.asc())
            .all()
        )

        results = []

        for row in rows:
            fighter = (
                db.query(BoxingFighter)
                .filter(
                    BoxingFighter.id == row.fighter_id
                )
                .first()
            )

            if not fighter:
                continue

            results.append({
                "id": row.id,
                "series_id": row.series_id,
                "fighter_id": row.fighter_id,

                "fighter": fighter_dict(fighter),

                "signed_date": row.signed_date,
                "start_record": row.start_record,

                "target_fights": row.target_fights,
                "fights_completed": row.fights_completed,

                "status": row.status,
                "notes": row.notes,

                "progress_label": (
                    f"{row.fights_completed} of "
                    f"{row.target_fights}"
                ),
            })

        return results


    @router.post("/series/{series_id}/fighters")
    def add_fighter_to_series(
        series_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        series = (
            db.query(BoxingSeries)
            .filter(BoxingSeries.id == series_id)
            .first()
        )

        if not series:
            raise HTTPException(
                status_code=404,
                detail="Series not found",
            )

        fighter_id = data.get("fighter_id")

        try:
            fighter_id = int(fighter_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="fighter_id is required",
            )

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        existing = (
            db.query(BoxingSeriesFighter)
            .filter(
                BoxingSeriesFighter.series_id == series_id,
                BoxingSeriesFighter.fighter_id == fighter_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Fighter is already in this series",
            )

        signed_date = str(
            data.get("signed_date") or ""
        ).strip()

        start_record = str(
            data.get("start_record")
            or fighter.pro_record
            or ""
        ).strip()

        row = BoxingSeriesFighter(
            series_id=series_id,
            fighter_id=fighter_id,

            signed_date=signed_date,
            start_record=start_record,

            target_fights=int(
                data.get("target_fights")
                or series.target_fights
                or 5
            ),

            fights_completed=int(
                data.get("fights_completed") or 0
            ),

            status="active",

            notes=str(
                data.get("notes") or ""
            ).strip(),
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "series_id": row.series_id,
            "fighter_id": row.fighter_id,
            "fighter": fighter_dict(fighter),
            "signed_date": row.signed_date,
            "start_record": row.start_record,
            "target_fights": row.target_fights,
            "fights_completed": row.fights_completed,
            "status": row.status,
            "notes": row.notes,
            "progress_label": (
                f"{row.fights_completed} of "
                f"{row.target_fights}"
            ),
        }


    @router.patch("/series-fighters/{series_fighter_id}")
    def update_series_fighter(
        series_fighter_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        row = (
            db.query(BoxingSeriesFighter)
            .filter(
                BoxingSeriesFighter.id ==
                series_fighter_id
            )
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Series fighter not found",
            )

        if "signed_date" in data:
            row.signed_date = str(
                data.get("signed_date") or ""
            ).strip()

        if "start_record" in data:
            row.start_record = str(
                data.get("start_record") or ""
            ).strip()

        if "notes" in data:
            row.notes = str(
                data.get("notes") or ""
            ).strip()

        if "fights_completed" in data:
            try:
                count = int(
                    data.get("fights_completed") or 0
                )
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid fight count",
                )

            count = max(
                0,
                min(count, row.target_fights or 5),
            )

            row.fights_completed = count

            if count >= (row.target_fights or 5):
                row.status = "graduated"

        if "status" in data:
            status = str(
                data.get("status") or ""
            ).strip().lower()

            allowed = {
                "active",
                "graduated",
                "released",
                "paused",
            }

            if status not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid series status",
                )

            row.status = status

        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "fighter_id": row.fighter_id,
            "signed_date": row.signed_date,
            "start_record": row.start_record,
            "target_fights": row.target_fights,
            "fights_completed": row.fights_completed,
            "status": row.status,
            "notes": row.notes,
            "progress_label": (
                f"{row.fights_completed} of "
                f"{row.target_fights}"
            ),
        }


    @router.delete("/series-fighters/{series_fighter_id}")
    def remove_series_fighter(
        series_fighter_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        row = (
            db.query(BoxingSeriesFighter)
            .filter(
                BoxingSeriesFighter.id ==
                series_fighter_id
            )
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Series fighter not found",
            )

        db.delete(row)
        db.commit()

        return {
            "ok": True,
            "id": series_fighter_id,
        }


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

    @router.patch("/fighters/{fighter_id}")
    def update_fighter(
        fighter_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        allowed = {
            "legal_name",
            "dob",
            "phone",
            "email",
            "city",
            "state",
            "country",
            "stance",
            "gym",
            "coach",

            "height_in",
            "reach_in",

            "walk_weight",
            "fight_weight",
            "available_weight_min",
            "available_weight_max",

            "pro_record",
            "amateur_record",

            "boxrec_id",
            "boxrec_url",

            "instagram",
            "facebook",
            "tiktok",
            "twitter",

            "manager_name",
            "manager_phone",
            "manager_email",

            "ok_license_status",
            "federal_id_status",
            "suspension_status",

            "bloodwork_status",
            "bloodwork_expires",

            "last_fight_date",
            "available",
        }

        if "boxrec_id" in data:
            boxrec_id = str(
                data.get("boxrec_id") or ""
            ).strip()

            if boxrec_id:
                duplicate = (
                    db.query(BoxingFighter)
                    .filter(
                        BoxingFighter.boxrec_id == boxrec_id,
                        BoxingFighter.id != fighter_id,
                    )
                    .first()
                )

                if duplicate:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"BoxRec ID {boxrec_id} is already "
                            f"assigned to {duplicate.legal_name}"
                        ),
                    )

        numeric_fields = {
            "height_in",
            "reach_in",
            "walk_weight",
            "fight_weight",
            "available_weight_min",
            "available_weight_max",
        }

        for key, value in data.items():
            if key not in allowed:
                continue

            if key in numeric_fields:
                if value in ("", None):
                    setattr(fighter, key, None)
                else:
                    try:
                        setattr(fighter, key, float(value))
                    except (TypeError, ValueError):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid value for {key}",
                        )

                continue

            if key == "available":
                setattr(
                    fighter,
                    key,
                    bool(value),
                )
                continue

            setattr(
                fighter,
                key,
                value if value is not None else "",
            )

        # Keep BoxRec URL synced with BoxRec ID.
        if fighter.boxrec_id:
            fighter.boxrec_url = (
                f"https://boxrec.com/en/box-pro/"
                f"{fighter.boxrec_id}"
            )

        db.commit()
        db.refresh(fighter)

        return fighter_dict(fighter)


    @router.patch("/fighters/{fighter_id}/bloodwork")
    def update_fighter_bloodwork(
        fighter_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        allowed_statuses = {
            "missing",
            "requested",
            "pending",
            "verified",
            "expired",
        }

        if "bloodwork_status" in data:
            status = str(
                data.get("bloodwork_status") or ""
            ).strip()

            if status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid bloodwork status",
                )

            fighter.bloodwork_status = status

        for field in (
            "bloodwork_provider",
            "bloodwork_requested_date",
            "bloodwork_completed_date",
            "bloodwork_expires",
            "bloodwork_notes",
        ):
            if field in data:
                setattr(
                    fighter,
                    field,
                    str(data.get(field) or "").strip(),
                )

        db.commit()
        db.refresh(fighter)

        return fighter_dict(fighter)


    @router.post("/fighters/{fighter_id}/find-socials")
    def find_fighter_socials(
        fighter_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured.",
            )

        context = f"""
Fighter name: {fighter.legal_name}
BoxRec ID: {getattr(fighter, "boxrec_id", "") or ""}
BoxRec URL: {getattr(fighter, "boxrec_url", "") or ""}
Pro record: {fighter.pro_record or ""}
Gym: {fighter.gym or ""}
Coach: {fighter.coach or ""}
City: {fighter.city or ""}
State: {fighter.state or ""}
Country: {fighter.country or ""}
"""

        prompt = f"""
Search the public web for the most likely official
or authentic social media profiles for this
professional boxer.

{context}

Search specifically for:

Instagram
Facebook
TikTok
X / Twitter

Use boxing identity clues including:
- exact fighter name
- BoxRec identity
- city/state/country
- boxing gym
- coach
- boxing-related profile descriptions
- fight photos/posts
- matching professional boxing information

DO NOT guess.

If there is not enough evidence, omit the result.

Return ONLY valid JSON in exactly this shape:

{{
  "candidates": [
    {{
      "platform": "instagram",
      "url": "https://...",
      "handle": "@example",
      "confidence": 92,
      "reason": "Name, boxing gym and location match"
    }}
  ]
}}

Rules:
- confidence must be 0 through 100
- only public profile URLs
- do not return fan pages unless clearly labeled
- do not invent URLs
- maximum 3 candidates per platform
"""

        payload = {
            "model": "gpt-5.6",
            "tools": [
                {
                    "type": "web_search"
                }
            ],
            "tool_choice": "required",
            "input": prompt,
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(
                    exc.read().decode("utf-8")
                )

                detail = (
                    body.get("error", {})
                    .get("message")
                    or "Social search failed."
                )

            except Exception:
                detail = "Social search failed."

            raise HTTPException(
                status_code=502,
                detail=detail,
            )

        output_text = ""

        for item in result.get("output", []):
            if item.get("type") != "message":
                continue

            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text += content.get("text", "")

        cleaned = output_text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "")
            cleaned = cleaned.replace("```", "")
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="AI returned an invalid social-search response.",
            )

        allowed_domains = {
            "instagram": (
                "instagram.com",
            ),
            "facebook": (
                "facebook.com",
                "fb.com",
            ),
            "tiktok": (
                "tiktok.com",
            ),
            "twitter": (
                "x.com",
                "twitter.com",
            ),
        }

        clean_candidates = []

        for candidate in data.get("candidates", []):

            platform = str(
                candidate.get("platform") or ""
            ).strip().lower()

            if platform == "x":
                platform = "twitter"

            if platform not in allowed_domains:
                continue

            url = str(
                candidate.get("url") or ""
            ).strip()

            if not url.startswith(("http://", "https://")):
                continue

            if not any(
                domain in url.lower()
                for domain in allowed_domains[platform]
            ):
                continue

            try:
                confidence = int(
                    candidate.get("confidence") or 0
                )
            except Exception:
                confidence = 0

            confidence = max(
                0,
                min(100, confidence),
            )

            clean_candidates.append({
                "platform": platform,
                "url": url,
                "handle": str(
                    candidate.get("handle") or ""
                ).strip(),
                "confidence": confidence,
                "reason": str(
                    candidate.get("reason") or ""
                ).strip(),
            })

        clean_candidates.sort(
            key=lambda x: -x["confidence"]
        )

        return {
            "fighter": fighter_dict(fighter),
            "candidates": clean_candidates,
        }


    @router.patch("/fighters/{fighter_id}/socials")
    def save_fighter_social(
        fighter_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        allowed = {
            "instagram",
            "facebook",
            "tiktok",
            "twitter",
        }

        for key, value in data.items():
            if key not in allowed:
                continue

            setattr(
                fighter,
                key,
                str(value or "").strip(),
            )

        db.commit()
        db.refresh(fighter)

        return fighter_dict(fighter)


    @router.get("/calendar")
    def get_fight_calendar(
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        events = (
            db.query(BoxingEvent)
            .order_by(
                BoxingEvent.event_date.asc(),
                BoxingEvent.id.asc(),
            )
            .all()
        )

        publication_rows = (
            db.query(BoxingEventPublication)
            .all()
        )

        publication_by_event = {
            row.event_id: row
            for row in publication_rows
        }

        results = []

        for event in events:
            publication = publication_by_event.get(
                event.id
            )

            results.append({
                "id": event.id,
                "slug": event.slug,
                "name": event.name,
                "venue": event.venue,
                "venue_address": event.venue_address,
                "event_date": event.event_date,
                "status": event.status,

                "published": (
                    bool(publication.published)
                    if publication
                    else False
                ),

                "public_title": (
                    publication.public_title
                    if publication
                    else ""
                ),

                "doors_time": (
                    publication.doors_time
                    if publication
                    else ""
                ),

                "first_bout_time": (
                    publication.first_bout_time
                    if publication
                    else ""
                ),

                "ticket_url": (
                    publication.ticket_url
                    if publication
                    else ""
                ),

                "poster_url": (
                    publication.poster_url
                    if publication
                    else ""
                ),

                "public_notes": (
                    publication.public_notes
                    if publication
                    else ""
                ),
            })

        return results


    @router.patch("/calendar/{event_id}")
    def update_calendar_publication(
        event_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        event = (
            db.query(BoxingEvent)
            .filter(BoxingEvent.id == event_id)
            .first()
        )

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            )

        row = (
            db.query(BoxingEventPublication)
            .filter(
                BoxingEventPublication.event_id ==
                event_id
            )
            .first()
        )

        if not row:
            row = BoxingEventPublication(
                event_id=event_id
            )

            db.add(row)

        if "published" in data:
            row.published = bool(
                data.get("published")
            )

        for field in (
            "public_title",
            "doors_time",
            "first_bout_time",
            "ticket_url",
            "poster_url",
            "public_notes",
        ):
            if field in data:
                setattr(
                    row,
                    field,
                    str(
                        data.get(field) or ""
                    ).strip(),
                )

        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "event_id": row.event_id,
            "published": bool(row.published),
            "public_title": row.public_title,
            "doors_time": row.doors_time,
            "first_bout_time": row.first_bout_time,
            "ticket_url": row.ticket_url,
            "poster_url": row.poster_url,
            "public_notes": row.public_notes,
        }


    @router.get("/public/fight-calendar")
    def public_fight_calendar(
        db: Session = Depends(get_db),
    ):
        rows = (
            db.query(
                BoxingEvent,
                BoxingEventPublication,
            )
            .join(
                BoxingEventPublication,
                BoxingEventPublication.event_id ==
                BoxingEvent.id,
            )
            .filter(
                BoxingEventPublication.published ==
                True
            )
            .order_by(
                BoxingEvent.event_date.asc(),
                BoxingEvent.id.asc(),
            )
            .all()
        )

        return [
            {
                "id": event.id,
                "slug": event.slug,

                "name": (
                    publication.public_title
                    or event.name
                ),

                "venue": event.venue,
                "venue_address":
                    event.venue_address,

                "event_date":
                    event.event_date,

                "doors_time":
                    publication.doors_time,

                "first_bout_time":
                    publication.first_bout_time,

                "ticket_url":
                    publication.ticket_url,

                "poster_url":
                    publication.poster_url,

                "public_notes":
                    publication.public_notes,
            }
            for event, publication in rows
        ]


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

    @router.get("/events/{event_id}/workspace")
    def get_event_workspace(
        event_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        event = (
            db.query(BoxingEvent)
            .filter(BoxingEvent.id == event_id)
            .first()
        )

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            )

        seed_event_checklist(db, event_id)
        seed_event_fees(db, event_id)

        bouts = (
            db.query(BoxingBout)
            .filter(BoxingBout.event_id == event_id)
            .order_by(BoxingBout.bout_order.asc(), BoxingBout.id.asc())
            .all()
        )

        fighter_ids = set()
        active_bout_count = 0
        cancelled_bout_count = 0

        for bout in bouts:
            bout_status = (bout.status or "draft").lower()
            is_active_bout = bout_status not in ("cancelled", "void")

            if is_active_bout:
                active_bout_count += 1

                if bout.red_fighter_id:
                    fighter_ids.add(bout.red_fighter_id)

                if bout.blue_fighter_id:
                    fighter_ids.add(bout.blue_fighter_id)
            else:
                cancelled_bout_count += 1


        first_five_series = (
            db.query(BoxingSeries)
            .filter(
                BoxingSeries.slug == "first-5-fights"
            )
            .first()
        )

        series_by_fighter = {}

        if first_five_series and fighter_ids:
            series_rows = (
                db.query(BoxingSeriesFighter)
                .filter(
                    BoxingSeriesFighter.series_id ==
                    first_five_series.id,

                    BoxingSeriesFighter.fighter_id.in_(
                        fighter_ids
                    ),
                )
                .all()
            )

            series_by_fighter = {
                row.fighter_id: row
                for row in series_rows
            }


        def event_series_payload(fighter_id):
            row = series_by_fighter.get(fighter_id)

            if not row:
                return None

            completed = int(
                row.fights_completed or 0
            )

            target = int(
                row.target_fights or 5
            )

            if completed >= target:
                next_fight_number = target
            else:
                next_fight_number = completed + 1

            return {
                "id": row.id,
                "series_id": row.series_id,
                "name": (
                    first_five_series.name
                    if first_five_series
                    else "First 5 Fights Series"
                ),
                "slug": "first-5-fights",
                "signed_date": row.signed_date,
                "start_record": row.start_record,
                "fights_completed": completed,
                "target_fights": target,
                "next_fight_number": next_fight_number,
                "status": row.status,
                "notes": row.notes,
            }


        bout_rows = []

        for bout in bouts:
            bout_status = (bout.status or "draft").lower()
            is_active_bout = bout_status not in ("cancelled", "void")

            red_contract = (
                db.query(BoxingContract)
                .filter(
                    BoxingContract.bout_id == bout.id,
                    BoxingContract.fighter_id ==
                    bout.red_fighter_id,
                )
                .first()
            )

            blue_contract = (
                db.query(BoxingContract)
                .filter(
                    BoxingContract.bout_id == bout.id,
                    BoxingContract.fighter_id ==
                    bout.blue_fighter_id,
                )
                .first()
            )

            def contract_summary(contract):
                if not contract:
                    return None

                change_request = ""

                terms = str(
                    contract.additional_terms or ""
                )

                marker = "[FIGHTER CHANGE REQUEST]"

                if marker in terms:
                    change_request = (
                        terms.split(marker)[-1].strip()
                    )

                return {
                    "id": contract.id,
                    "fighter_id": contract.fighter_id,
                    "status": contract.status or "draft",
                    "contract_date":
                        contract.contract_date or "",
                    "maximum_weight":
                        contract.maximum_weight,
                    "gross_purse":
                        contract.gross_purse or 0,
                    "travel_expense":
                        contract.travel_expense or 0,
                    "change_request":
                        change_request,
                }

            bout_rows.append({
                "id": bout.id,
                "bout_order": bout.bout_order or 0,
                "status": bout.status,
                "is_active": is_active_bout,
                "weight_agreed": bout.weight_agreed,
                "rounds": bout.rounds,
                "bout_type": bout.bout_type,
                "red_purse": bout.red_purse,
                "blue_purse": bout.blue_purse,
                "match_score": bout.match_score,
                "notes": bout.notes,

                "red": fighter_dict(
                    bout.red_fighter
                ),

                "blue": fighter_dict(
                    bout.blue_fighter
                ),

                "red_series":
                    event_series_payload(
                        bout.red_fighter_id
                    ),

                "blue_series":
                    event_series_payload(
                        bout.blue_fighter_id
                    ),

                "red_contract":
                    contract_summary(red_contract),

                "blue_contract":
                    contract_summary(blue_contract),
            })


        fighters = []

        if fighter_ids:
            fighter_rows = (
                db.query(BoxingFighter)
                .filter(
                    BoxingFighter.id.in_(
                        fighter_ids
                    )
                )
                .all()
            )

            fighters = [
                fighter_dict(f)
                for f in fighter_rows
            ]


        checklist = (
            db.query(BoxingEventChecklist)
            .filter(BoxingEventChecklist.event_id == event_id)
            .order_by(
                BoxingEventChecklist.section.asc(),
                BoxingEventChecklist.sort_order.asc(),
            )
            .all()
        )

        checklist_rows = [
            {
                "id": row.id,
                "section": row.section,
                "item_key": row.item_key,
                "label": row.label,
                "status": row.status,
                "due_date": row.due_date,
                "assigned_to": row.assigned_to,
                "notes": row.notes,
            }
            for row in checklist
        ]

        return {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "name": event.name,
                "venue": event.venue,
                "venue_address": event.venue_address,
                "event_date": event.event_date,
                "status": event.status,
            },
            "bouts": bout_rows,
            "active_bout_count": active_bout_count,
            "cancelled_bout_count": cancelled_bout_count,
            "fighters": fighters,
            "checklist": checklist_rows,
            "fees": [
                {
                    "id": fee.id,
                    "fee_key": fee.fee_key,
                    "name": fee.name,
                    "estimate": fee.estimate,
                    "actual_amount": fee.actual_amount,
                    "paid": bool(fee.paid),
                    "due_date": fee.due_date,
                    "payee": fee.payee,
                    "notes": fee.notes,
                }
                for fee in (
                    db.query(BoxingEventFee)
                    .filter(BoxingEventFee.event_id == event_id)
                    .order_by(BoxingEventFee.id.asc())
                    .all()
                )
            ],
        }


    @router.patch("/events/{event_id}/fees/{fee_id}")
    def update_event_fee(
        event_id: int,
        fee_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        fee = (
            db.query(BoxingEventFee)
            .filter(
                BoxingEventFee.id == fee_id,
                BoxingEventFee.event_id == event_id,
            )
            .first()
        )

        if not fee:
            raise HTTPException(
                status_code=404,
                detail="Fee not found",
            )

        if "actual_amount" in data:
            value = data.get("actual_amount")

            if value in ("", None):
                fee.actual_amount = None
            else:
                try:
                    fee.actual_amount = float(value)
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid actual amount",
                    )

        if "paid" in data:
            fee.paid = bool(data.get("paid"))

        for field in (
            "due_date",
            "payee",
            "notes",
        ):
            if field in data:
                setattr(
                    fee,
                    field,
                    str(data.get(field) or "").strip(),
                )

        db.commit()
        db.refresh(fee)

        return {
            "id": fee.id,
            "actual_amount": fee.actual_amount,
            "paid": bool(fee.paid),
            "due_date": fee.due_date,
            "payee": fee.payee,
            "notes": fee.notes,
        }


    @router.post("/events/{event_id}/generate-promo")
    def generate_event_promo(
        event_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured on the server.",
            )

        event = (
            db.query(BoxingEvent)
            .filter(BoxingEvent.id == event_id)
            .first()
        )

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            )

        bouts = (
            db.query(BoxingBout)
            .filter(BoxingBout.event_id == event_id)
            .order_by(
                BoxingBout.bout_order.asc(),
                BoxingBout.id.asc(),
            )
            .all()
        )

        bout_lines = []

        for index, bout in enumerate(bouts, start=1):

            red = (
                db.query(BoxingFighter)
                .filter(
                    BoxingFighter.id ==
                    bout.red_fighter_id
                )
                .first()
            )

            blue = (
                db.query(BoxingFighter)
                .filter(
                    BoxingFighter.id ==
                    bout.blue_fighter_id
                )
                .first()
            )

            red_name = (
                red.legal_name
                if red
                else "TBA"
            )

            blue_name = (
                blue.legal_name
                if blue
                else "TBA"
            )

            order = bout.bout_order or index

            weight = (
                f"{bout.weight_agreed:g} LB"
                if bout.weight_agreed
                else "WEIGHT TBA"
            )

            rounds = (
                f"{bout.rounds} ROUNDS"
                if bout.rounds
                else ""
            )

            bout_lines.append(
                f"BOUT {order}: "
                f"{red_name} VS {blue_name} — "
                f"{weight} {rounds}".strip()
            )

        card = "\n".join(bout_lines)

        if not card:
            card = "FIGHT CARD TO BE ANNOUNCED"

        event_name = (
            event.name or "TNG BOXING"
        )

        event_date = (
            str(event.event_date)
            if event.event_date
            else "DATE TBA"
        )

        venue = (
            event.venue or "VENUE TBA"
        )

        location = (
            event.venue_address or ""
        )

        prompt = f"""
Create a premium vertical professional boxing
event promotional poster.

BRAND:
TNG Boxing / The Next Generation

EVENT:
{event_name}

DATE:
{event_date}

VENUE:
{venue}

LOCATION:
{location}

OFFICIAL FIGHT CARD IN EXACT BOUT ORDER:
{card}

DESIGN DIRECTION:
High-end professional boxing promotion.
Dramatic arena lighting.
Black, deep red, white, metallic accents.
Premium championship fight-night atmosphere.
Strong visual hierarchy.
Modern combat sports advertising.
Powerful but clean.
Suitable for Facebook, Instagram and print.

Keep the event title highly visible.

Represent the fighters as dramatic boxing
figures, silhouettes, gloves, ring lighting,
smoke, ropes, arena lights or premium
fight-poster imagery.

IMPORTANT:
Use the fighter names and bout information
provided above.
Do not invent additional fighters.
Do not invent additional bouts.
Do not change the bout order.
Do not add fake sponsors.
Do not add fake ticket information.
"""

        payload = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1536",
            "quality": "medium",
            "output_format": "png",
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=180,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(
                    exc.read().decode("utf-8")
                )

                detail = (
                    error_body
                    .get("error", {})
                    .get("message")
                    or "OpenAI image generation failed."
                )

            except Exception:
                detail = "OpenAI image generation failed."

            raise HTTPException(
                status_code=502,
                detail=detail,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Promo generation failed: {exc}",
            )

        images = result.get("data") or []

        if not images:
            raise HTTPException(
                status_code=502,
                detail="OpenAI did not return an image.",
            )

        image_base64 = (
            images[0].get("b64_json") or ""
        )

        if not image_base64:
            raise HTTPException(
                status_code=502,
                detail="Generated image data was missing.",
            )

        return {
            "image": (
                "data:image/png;base64,"
                + image_base64
            ),
            "event_id": event_id,
            "prompt": prompt,
        }


    @router.patch("/events/{event_id}/checklist/{item_id}")
    def update_event_checklist(
        event_id: int,
        item_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        row = (
            db.query(BoxingEventChecklist)
            .filter(
                BoxingEventChecklist.id == item_id,
                BoxingEventChecklist.event_id == event_id,
            )
            .first()
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Checklist item not found",
            )

        allowed_statuses = {
            "not_started",
            "in_progress",
            "submitted",
            "complete",
            "needs_attention",
        }

        if "status" in data:
            status = str(data.get("status") or "").strip()

            if status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid checklist status",
                )

            row.status = status

        if "due_date" in data:
            row.due_date = str(
                data.get("due_date") or ""
            ).strip()

        if "assigned_to" in data:
            row.assigned_to = str(
                data.get("assigned_to") or ""
            ).strip()

        if "notes" in data:
            row.notes = str(
                data.get("notes") or ""
            ).strip()

        db.commit()
        db.refresh(row)

        return {
            "id": row.id,
            "status": row.status,
            "due_date": row.due_date,
            "assigned_to": row.assigned_to,
            "notes": row.notes,
        }


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

    @router.get("/bouts/{bout_id}/contracts")
    def list_bout_contracts(
        bout_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        rows = (
            db.query(BoxingContract)
            .filter(BoxingContract.bout_id == bout_id)
            .order_by(BoxingContract.id.asc())
            .all()
        )

        return [
            {
                "id": row.id,
                "bout_id": row.bout_id,
                "fighter_id": row.fighter_id,
                "opponent_id": row.opponent_id,
                "corner": row.corner,
                "contract_date": row.contract_date,
                "boxer_name": row.boxer_name,
                "boxer_federal_id": row.boxer_federal_id,
                "boxer_address": row.boxer_address,
                "boxer_phone": row.boxer_phone,
                "boxer_manager": row.boxer_manager,
                "opponent_name": row.opponent_name,
                "rounds": row.rounds,
                "maximum_weight": row.maximum_weight,
                "event_name": row.event_name,
                "event_date": row.event_date,
                "venue": row.venue,
                "venue_address": row.venue_address,
                "promoter_name": row.promoter_name,
                "promoter_address": row.promoter_address,
                "promoter_phone": row.promoter_phone,
                "promoter_matchmaker": row.promoter_matchmaker,
                "gross_purse": row.gross_purse,
                "travel_type": row.travel_type,
                "travel_paid_by": row.travel_paid_by,
                "travel_expense": row.travel_expense,
                "hotel_provided": row.hotel_provided,
                "hotel_name": row.hotel_name,
                "hotel_nights": row.hotel_nights,
                "per_diem_daily": row.per_diem_daily,
                "per_diem_days": row.per_diem_days,
                "per_diem_total": row.per_diem_total,
                "deductions": row.deductions,
                "boxer_paid": row.boxer_paid,
                "additional_terms": row.additional_terms,
                "cancellation_pay": row.cancellation_pay,
                "status": row.status,
            }
            for row in rows
        ]


    @router.post("/bouts/{bout_id}/contracts/{corner}")
    def generate_bout_contract(
        bout_id: int,
        corner: str,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        corner = str(corner or "").lower().strip()

        if corner not in ("red", "blue"):
            raise HTTPException(
                status_code=400,
                detail="Corner must be red or blue",
            )

        bout = (
            db.query(BoxingBout)
            .filter(BoxingBout.id == bout_id)
            .first()
        )

        if not bout:
            raise HTTPException(
                status_code=404,
                detail="Bout not found",
            )

        if not bout.event_id:
            raise HTTPException(
                status_code=400,
                detail="Bout must be assigned to an event",
            )

        event = (
            db.query(BoxingEvent)
            .filter(BoxingEvent.id == bout.event_id)
            .first()
        )

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            )

        if corner == "red":
            fighter_id = bout.red_fighter_id
            opponent_id = bout.blue_fighter_id
            purse = bout.red_purse or 0
        else:
            fighter_id = bout.blue_fighter_id
            opponent_id = bout.red_fighter_id
            purse = bout.blue_purse or 0

        fighter = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == fighter_id)
            .first()
        )

        opponent = (
            db.query(BoxingFighter)
            .filter(BoxingFighter.id == opponent_id)
            .first()
        )

        if not fighter or not opponent:
            raise HTTPException(
                status_code=404,
                detail="Fighter information missing",
            )

        contract = (
            db.query(BoxingContract)
            .filter(
                BoxingContract.bout_id == bout.id,
                BoxingContract.fighter_id == fighter.id,
            )
            .first()
        )

        if not contract:
            contract = BoxingContract(
                event_id=event.id,
                bout_id=bout.id,
                fighter_id=fighter.id,
                opponent_id=opponent.id,
                corner=corner,
            )
            db.add(contract)

        now = datetime.utcnow()

        contract.contract_date = str(
            data.get("contract_date")
            or now.strftime("%m/%d/%Y")
        )

        contract.boxer_name = fighter.legal_name or ""
        contract.boxer_federal_id = (
            getattr(fighter, "federal_id_number", "")
            or ""
        )

        address_parts = [
            getattr(fighter, "address", "") or "",
            fighter.city or "",
            fighter.state or "",
            fighter.country or "",
        ]

        contract.boxer_address = ", ".join(
            part.strip()
            for part in address_parts
            if str(part).strip()
        )

        contract.boxer_phone = fighter.phone or ""
        contract.boxer_manager = (
            getattr(fighter, "manager_name", "")
            or ""
        )

        contract.opponent_name = opponent.legal_name or ""

        contract.rounds = int(
            data.get("rounds")
            or bout.rounds
            or 4
        )

        contract.maximum_weight = (
            float(data.get("maximum_weight"))
            if data.get("maximum_weight") not in ("", None)
            else bout.weight_agreed
        )

        contract.event_name = event.name or ""
        contract.event_date = event.event_date or ""
        contract.venue = event.venue or ""
        contract.venue_address = event.venue_address or ""

        contract.promoter_name = str(
            data.get("promoter_name")
            or "Maurice Williams"
        ).strip()

        contract.promoter_address = str(
            data.get("promoter_address")
            or ""
        ).strip()

        contract.promoter_phone = str(
            data.get("promoter_phone")
            or "651-239-0916"
        ).strip()

        contract.promoter_matchmaker = str(
            data.get("promoter_matchmaker")
            or "Maurice Williams"
        ).strip()

        contract.gross_purse = float(
            data.get("gross_purse")
            if data.get("gross_purse") not in ("", None)
            else purse
        )

        contract.travel_type = str(
            data.get("travel_type") or ""
        ).strip()

        contract.travel_paid_by = str(
            data.get("travel_paid_by") or ""
        ).strip()

        contract.travel_expense = float(
            data.get("travel_expense") or 0
        )

        contract.hotel_provided = str(
            data.get("hotel_provided") or ""
        ).strip()

        contract.hotel_name = str(
            data.get("hotel_name") or ""
        ).strip()

        contract.hotel_nights = int(
            float(data.get("hotel_nights") or 0)
        )

        contract.per_diem_daily = float(
            data.get("per_diem_daily") or 0
        )

        contract.per_diem_days = int(
            float(data.get("per_diem_days") or 0)
        )

        contract.per_diem_total = (
            contract.per_diem_daily
            * contract.per_diem_days
        )

        contract.deductions = float(
            data.get("deductions") or 0
        )

        contract.boxer_paid = (
            contract.gross_purse
            + contract.travel_expense
            + contract.per_diem_total
            - contract.deductions
        )

        contract.additional_terms = str(
            data.get("additional_terms")
            or ""
        ).strip()

        contract.cancellation_pay = float(
            data.get("cancellation_pay") or 0
        )

        contract.status = str(
            data.get("status")
            or "generated"
        )

        db.commit()
        db.refresh(contract)

        return {
            "id": contract.id,
            "bout_id": contract.bout_id,
            "fighter_id": contract.fighter_id,
            "opponent_id": contract.opponent_id,
            "corner": contract.corner,
            "contract_date": contract.contract_date,
            "boxer_name": contract.boxer_name,
            "boxer_federal_id": contract.boxer_federal_id,
            "boxer_address": contract.boxer_address,
            "boxer_phone": contract.boxer_phone,
            "boxer_manager": contract.boxer_manager,
            "opponent_name": contract.opponent_name,
            "rounds": contract.rounds,
            "maximum_weight": contract.maximum_weight,
            "event_name": contract.event_name,
            "event_date": contract.event_date,
            "venue": contract.venue,
            "venue_address": contract.venue_address,
            "promoter_name": contract.promoter_name,
            "promoter_address": contract.promoter_address,
            "promoter_phone": contract.promoter_phone,
            "promoter_matchmaker": contract.promoter_matchmaker,
            "gross_purse": contract.gross_purse,
            "travel_type": contract.travel_type,
            "travel_paid_by": contract.travel_paid_by,
            "travel_expense": contract.travel_expense,
            "hotel_provided": contract.hotel_provided,
            "hotel_name": contract.hotel_name,
            "hotel_nights": contract.hotel_nights,
            "per_diem_daily": contract.per_diem_daily,
            "per_diem_days": contract.per_diem_days,
            "per_diem_total": contract.per_diem_total,
            "deductions": contract.deductions,
            "boxer_paid": contract.boxer_paid,
            "additional_terms": contract.additional_terms,
            "cancellation_pay": contract.cancellation_pay,
            "status": contract.status,
        }


    @router.post("/contracts/{contract_id}/send-email")
    def send_contract_email(
        contract_id: int,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        contract = (
            db.query(BoxingContract)
            .filter(BoxingContract.id == contract_id)
            .first()
        )

        if not contract:
            raise HTTPException(
                status_code=404,
                detail="Contract not found",
            )

        fighter = (
            db.query(BoxingFighter)
            .filter(
                BoxingFighter.id == contract.fighter_id
            )
            .first()
        )

        if not fighter:
            raise HTTPException(
                status_code=404,
                detail="Fighter not found",
            )

        fighter_email = str(
            fighter.email or ""
        ).strip()

        if not fighter_email:
            raise HTTPException(
                status_code=400,
                detail="Fighter does not have an email address.",
            )

        resend_api_key = os.getenv("RESEND_API_KEY")

        if not resend_api_key:
            raise HTTPException(
                status_code=500,
                detail="RESEND_API_KEY is not configured.",
            )

        resend.api_key = resend_api_key

        sender_email = os.getenv(
            "RESEND_FROM_EMAIL",
            "TNG Boxing <marketing@tngboxinggym.com>",
        )

        frontend_url = os.getenv(
            "FRONTEND_URL",
            "https://tngos.tngboxinggym.com",
        ).rstrip("/")

        portal_url = frontend_url

        subject = (
            f"TNG Boxing Contract - "
            f"{contract.event_name or 'Fight Agreement'}"
        )

        boxer_name = (
            contract.boxer_name
            or fighter.legal_name
            or "Fighter"
        )

        opponent_name = (
            contract.opponent_name
            or "Opponent TBD"
        )

        event_name = (
            contract.event_name
            or "TNG Boxing Event"
        )

        event_date = contract.event_date or ""

        resend.Emails.send(
            {
                "from": sender_email,
                "to": [fighter_email],
                "subject": subject,
                "html": f"""
                <div style="
                    font-family:Arial,sans-serif;
                    max-width:620px;
                    margin:auto;
                    padding:24px;
                    color:#18181b;
                ">
                    <h2 style="margin-bottom:8px;">
                        TNG Boxing Fight Contract
                    </h2>

                    <p>
                        {boxer_name}, your fight contract
                        is ready for review.
                    </p>

                    <div style="
                        border:1px solid #ddd;
                        border-radius:10px;
                        padding:16px;
                        margin:20px 0;
                    ">
                        <p>
                            <strong>Event:</strong>
                            {event_name}
                        </p>

                        <p>
                            <strong>Date:</strong>
                            {event_date}
                        </p>

                        <p>
                            <strong>Opponent:</strong>
                            {opponent_name}
                        </p>

                        <p>
                            <strong>Weight:</strong>
                            {contract.maximum_weight or ""}
                            lbs
                        </p>

                        <p>
                            <strong>Gross Purse:</strong>
                            ${float(contract.gross_purse or 0):,.2f}
                        </p>
                    </div>

                    <p>
                        Log in to your TNGOS Fighter Portal
                        to review the agreement and respond.
                    </p>

                    <p style="margin:30px 0;">
                        <a
                            href="{portal_url}"
                            style="
                                background:#111;
                                color:#fff;
                                padding:12px 20px;
                                text-decoration:none;
                                border-radius:6px;
                                font-weight:bold;
                            "
                        >
                            Open Fighter Portal
                        </a>
                    </p>

                    <p>
                        You will also be able to download,
                        sign, or upload your signed contract
                        from the portal as those contract
                        options are enabled.
                    </p>

                    <p style="margin-top:30px;">
                        <strong>
                            TNG Boxing - Earned Not Given
                        </strong>
                    </p>
                </div>
                """,
            }
        )

        return {
            "ok": True,
            "contract_id": contract.id,
            "fighter_id": fighter.id,
            "email": fighter_email,
            "message": (
                f"Contract email sent to {fighter_email}."
            ),
        }


    @router.patch("/contracts/{contract_id}")
    def update_contract(
        contract_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        contract = (
            db.query(BoxingContract)
            .filter(BoxingContract.id == contract_id)
            .first()
        )

        if not contract:
            raise HTTPException(
                status_code=404,
                detail="Contract not found",
            )

        allowed = {
            "contract_date",
            "promoter_name",
            "promoter_address",
            "promoter_phone",
            "promoter_matchmaker",
            "gross_purse",
            "travel_expense",
            "deductions",
            "additional_terms",
            "cancellation_pay",
            "status",
        }

        money_fields = {
            "gross_purse",
            "travel_expense",
            "deductions",
            "cancellation_pay",
        }

        for key, value in data.items():
            if key not in allowed:
                continue

            if key in money_fields:
                setattr(
                    contract,
                    key,
                    float(value or 0),
                )
            else:
                setattr(
                    contract,
                    key,
                    str(value or "").strip(),
                )

        contract.boxer_paid = (
            (contract.gross_purse or 0)
            + (contract.travel_expense or 0)
            - (contract.deductions or 0)
        )

        db.commit()
        db.refresh(contract)

        return {
            "id": contract.id,
            "status": contract.status,
            "gross_purse": contract.gross_purse,
            "travel_expense": contract.travel_expense,
            "deductions": contract.deductions,
            "boxer_paid": contract.boxer_paid,
        }


    @router.patch("/bouts/{bout_id}/cancel")
    def cancel_bout(
        bout_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        reason = str(
            data.get("notes")
            or data.get("reason")
            or ""
        ).strip()

        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Cancellation notes are required",
            )

        bout = (
            db.query(BoxingBout)
            .filter(BoxingBout.id == bout_id)
            .first()
        )

        if not bout:
            raise HTTPException(
                status_code=404,
                detail="Bout not found",
            )

        previous_notes = (bout.notes or "").strip()

        cancellation_note = (
            "BOUT CANCELLED / REMOVED\n"
            f"Reason: {reason}"
        )

        bout.notes = (
            f"{previous_notes}\n\n{cancellation_note}"
            if previous_notes
            else cancellation_note
        )

        bout.status = "cancelled"

        db.commit()
        db.refresh(bout)

        return {
            "id": bout.id,
            "event_id": bout.event_id,
            "status": bout.status,
            "notes": bout.notes,
        }


    @router.patch("/bouts/{bout_id}/purse")
    def update_bout_purse(
        bout_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        bout = (
            db.query(BoxingBout)
            .filter(BoxingBout.id == bout_id)
            .first()
        )

        if not bout:
            raise HTTPException(
                status_code=404,
                detail="Bout not found",
            )

        for field in ("red_purse", "blue_purse"):
            if field not in data:
                continue

            value = data.get(field)

            if value in ("", None):
                amount = 0.0
            else:
                try:
                    amount = float(value)
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid {field}",
                    )

            if amount < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Purse cannot be negative",
                )

            setattr(bout, field, amount)

        db.commit()
        db.refresh(bout)

        return {
            "id": bout.id,
            "red_purse": bout.red_purse or 0,
            "blue_purse": bout.blue_purse or 0,
            "total_purse": (
                (bout.red_purse or 0)
                + (bout.blue_purse or 0)
            ),
        }


    @router.patch("/bouts/{bout_id}/order")
    def update_bout_order(
        bout_id: int,
        data: dict,
        db: Session = Depends(get_db),
        user=Depends(current_user_dependency),
    ):
        require_staff(user)

        bout = (
            db.query(BoxingBout)
            .filter(BoxingBout.id == bout_id)
            .first()
        )

        if not bout:
            raise HTTPException(
                status_code=404,
                detail="Bout not found",
            )

        try:
            order = int(data.get("bout_order"))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Bout order must be a number",
            )

        if order < 1:
            raise HTTPException(
                status_code=400,
                detail="Bout order must be 1 or higher",
            )

        bout.bout_order = order
        db.commit()
        db.refresh(bout)

        return {
            "id": bout.id,
            "bout_order": bout.bout_order,
        }


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
