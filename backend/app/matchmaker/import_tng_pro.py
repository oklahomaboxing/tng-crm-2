import sys
import sqlite3
from ..database import SessionLocal, engine, Base
from .models import BoxingFighter, BoxingEvent, BoxingBout

Base.metadata.create_all(bind=engine)

def import_pro(path):
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    db = SessionLocal()
    fighter_map = {}
    event_map = {}

    try:
        for r in src.execute("SELECT * FROM fighters"):
            existing = db.query(BoxingFighter).filter(
                BoxingFighter.source == "tng_pro",
                BoxingFighter.source_id == r["id"],
            ).first()
            if existing:
                fighter_map[r["id"]] = existing.id
                continue

            f = BoxingFighter(
                legal_name=r["legal_name"],
                dob=r["dob"] or "",
                phone=r["phone"] or "",
                stance=r["stance"] or "",
                gym=r["gym"] or "",
                coach=r["coach"] or "",
                height_in=r["height_in"],
                reach_in=r["reach_in"],
                walk_weight=r["walk_weight"],
                fight_weight=r["fight_weight"],
                pro_record=r["pro_record"] or "",
                amateur_record=r["amateur_record"] or "",
                boxrec_url=r["boxrec_url"] or "",
                ok_license_status=r["ok_license_status"] or "unknown",
                federal_id_status=r["federal_id_status"] or "unknown",
                suspension_status=r["suspension_status"] or "needs_review",
                source="tng_pro",
                source_id=r["id"],
                available=True,
            )

            bw = src.execute(
                "SELECT status, expires_on FROM bloodwork WHERE fighter_id=? ORDER BY collected_on DESC LIMIT 1",
                (r["id"],)
            ).fetchone()
            if bw:
                f.bloodwork_status = bw["status"] or "missing"
                f.bloodwork_expires = bw["expires_on"] or ""

            db.add(f)
            db.flush()
            fighter_map[r["id"]] = f.id

        for r in src.execute("SELECT * FROM events"):
            existing = db.query(BoxingEvent).filter(BoxingEvent.slug == r["slug"]).first()
            if existing:
                event_map[r["id"]] = existing.id
                continue

            e = BoxingEvent(
                slug=r["slug"],
                name=r["name"],
                venue=r["venue"] or "",
                venue_address=r["venue_address"] or "",
                event_date=r["event_date"] or "",
            )
            db.add(e)
            db.flush()
            event_map[r["id"]] = e.id

        for r in src.execute("SELECT * FROM bouts"):
            red = fighter_map.get(r["red_fighter_id"])
            blue = fighter_map.get(r["blue_fighter_id"])
            if not red or not blue:
                continue

            exists = db.query(BoxingBout).filter(
                BoxingBout.event_id == event_map.get(r["event_id"]),
                BoxingBout.red_fighter_id == red,
                BoxingBout.blue_fighter_id == blue,
            ).first()
            if exists:
                continue

            purse = src.execute(
                "SELECT red_amount, blue_amount FROM purses WHERE bout_id=? LIMIT 1",
                (r["id"],)
            ).fetchone()

            db.add(BoxingBout(
                event_id=event_map.get(r["event_id"]),
                red_fighter_id=red,
                blue_fighter_id=blue,
                weight_agreed=r["weight_agreed"],
                rounds=r["rounds"] or 4,
                bout_type=r["bout_type"] or "pro",
                status=r["status"] or "draft",
                red_purse=(purse["red_amount"] if purse else 0) or 0,
                blue_purse=(purse["blue_amount"] if purse else 0) or 0,
                notes=f"Imported from TNG Pro bout #{r['id']}",
            ))

        db.commit()
        print(f"Imported {len(fighter_map)} fighters and {len(event_map)} events.")
    finally:
        db.close()
        src.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m backend.app.matchmaker.import_tng_pro PATH_TO_PRO_DB")
    import_pro(sys.argv[1])
