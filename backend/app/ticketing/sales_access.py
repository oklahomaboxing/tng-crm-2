"""New-sales access only. Never used by payment settlement, admission or ticket delivery."""
import json
from datetime import datetime, timezone
from fastapi import HTTPException
from .models import EventSalesWindow, EventSeller


def sales_access(db, event_id, seller=None, now=None):
    window = db.get(EventSalesWindow, event_id)
    exempt_ids = json.loads(window.exempt_seller_ids_json or "[]") if window else []
    exempt = bool(seller and seller.id in exempt_ids)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    expired = bool(window and window.cutoff_at and now >= window.cutoff_at and not exempt)
    active = bool(seller.active) if seller else True
    return {"sales_open": active and not expired, "active": active,
            "cutoff_exempt": exempt, "cutoff_reached": expired,
            "sales_status": "paused" if not active else "cutoff" if expired else "open"}


def require_sales_open(db, event_id, seller=None):
    state = sales_access(db, event_id, seller)
    if not state["sales_open"]:
        raise HTTPException(403, "Ticket sales through this link are closed. Please contact TNG Promotions.")
