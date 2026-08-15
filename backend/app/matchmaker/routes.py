import os
import json
import urllib.request
import urllib.error
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from .models import BoxingFighter, BoxingEvent, BoxingBout, BoxingEventChecklist, BoxingEventFee
from .schemas import FighterCreate, EventCreate, BoutCreate, PublicFighterRegistration
from .service import fighter_dict, ranked_matches


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

        bout_rows = []

        fighter_ids = set()

        for bout in bouts:
            fighter_ids.add(bout.red_fighter_id)
            fighter_ids.add(bout.blue_fighter_id)

            bout_rows.append({
                "id": bout.id,
                "bout_order": bout.bout_order or 0,
                "status": bout.status,
                "weight_agreed": bout.weight_agreed,
                "rounds": bout.rounds,
                "bout_type": bout.bout_type,
                "red_purse": bout.red_purse,
                "blue_purse": bout.blue_purse,
                "match_score": bout.match_score,
                "notes": bout.notes,
                "red": fighter_dict(bout.red_fighter),
                "blue": fighter_dict(bout.blue_fighter),
            })

        fighters = []

        if fighter_ids:
            fighter_rows = (
                db.query(BoxingFighter)
                .filter(BoxingFighter.id.in_(fighter_ids))
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
