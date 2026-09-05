from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session
from .models import EventSeller, EventTicketType, TicketOrder, IssuedTicket, TicketScanLog
from .security import make_raw_token, hash_token, verify_token, encrypt_token
import secrets

def cents_from_commission(ticket_type: EventTicketType, price_cents: int) -> int:
    if ticket_type.commission_type == "none":
        return 0
    if ticket_type.commission_type == "flat":
        return int(Decimal(ticket_type.commission_value) * 100)
    pct = Decimal(ticket_type.commission_value) / Decimal(100)
    return int(Decimal(price_cents) * pct)

def generate_public_code(event_id: int, seller_type: str) -> str:
    return f"{seller_type[:1].upper()}{event_id}-{secrets.token_hex(4).upper()}"

def generate_receipt_number(event_id: int) -> str:
    return f"TNG-{event_id}-{datetime.utcnow().strftime('%y%m%d')}-{secrets.token_hex(3).upper()}"

def generate_ticket_number(event_id: int) -> str:
    return f"TNG-{event_id}-{secrets.token_hex(5).upper()}"

def issue_paid_order(db: Session, order: TicketOrder, line_items: list[dict]) -> list[dict]:
    if order.payment_status != "paid":
        raise ValueError("Cannot issue tickets until order is paid")
    issued = []
    for item in line_items:
        ticket_type = db.query(EventTicketType).filter(EventTicketType.id == item["ticket_type_id"]).one()
        qty = int(item["quantity"])
        for _ in range(qty):
            ticket_number = generate_ticket_number(order.event_id)
            raw = make_raw_token(order.event_id, ticket_number)
            ticket = IssuedTicket(
                order_id=order.id,
                event_id=order.event_id,
                ticket_type_id=ticket_type.id,
                seller_id=order.seller_id,
                ticket_number=ticket_number,
                qr_token_hash=hash_token(raw),
                qr_token_encrypted=encrypt_token(raw),
                price_cents=ticket_type.price_cents,
                commission_cents=cents_from_commission(ticket_type, ticket_type.price_cents),
                status="valid",
                attendee_email=order.buyer_email,
            )
            db.add(ticket)
            db.flush()
            issued.append({"ticket": ticket, "raw_qr_token": raw})
    db.commit()
    return issued

def scan_ticket(db: Session, event_id: int, raw_token: str, scanned_by_user_id: int | None, device_label: str | None = None):
    if not verify_token(raw_token):
        return {"ok": False, "result": "invalid"}

    token_hash = hash_token(raw_token)
    ticket = db.query(IssuedTicket).filter(IssuedTicket.qr_token_hash == token_hash).first()
    if not ticket:
        return {"ok": False, "result": "invalid"}
    if ticket.event_id != event_id:
        result = "wrong_event"
    elif ticket.status == "used":
        result = "already_used"
    elif ticket.status in ("void", "refunded"):
        result = ticket.status
    else:
        ticket.status = "used"
        ticket.scanned_at = datetime.utcnow()
        ticket.scanned_by_user_id = scanned_by_user_id
        result = "admitted"

    db.add(TicketScanLog(
        ticket_id=ticket.id,
        event_id=event_id,
        scanned_by_user_id=scanned_by_user_id,
        result=result,
        device_label=device_label,
    ))
    db.commit()
    return {
        "ok": result == "admitted",
        "result": result,
        "ticket_number": ticket.ticket_number,
        "status": ticket.status,
        "ticket_type_id": ticket.ticket_type_id,
        "scanned_at": ticket.scanned_at.isoformat() if ticket.scanned_at else None,
    }

def seller_totals(db: Session, event_id: int):
    rows = (
        db.query(
            EventSeller.id.label("seller_id"),
            EventSeller.display_name,
            EventSeller.seller_type,
            EventSeller.public_code,
            func.count(IssuedTicket.id).label("tickets_sold"),
            func.coalesce(func.sum(IssuedTicket.price_cents), 0).label("gross_sales_cents"),
            func.coalesce(func.sum(IssuedTicket.commission_cents), 0).label("commission_cents"),
        )
        .outerjoin(IssuedTicket, (IssuedTicket.seller_id == EventSeller.id) & (IssuedTicket.status != "refunded"))
        .filter(EventSeller.event_id == event_id)
        .group_by(EventSeller.id, EventSeller.display_name, EventSeller.seller_type, EventSeller.public_code)
        .order_by(func.coalesce(func.sum(IssuedTicket.price_cents), 0).desc())
        .all()
    )
    return [dict(r._mapping) for r in rows]
