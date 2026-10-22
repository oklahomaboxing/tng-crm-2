"""Persistent notification status; payment and ticket issuance never depend on providers."""
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

from .models import TicketDelivery, IssuedTicket, TicketOrder
from .security import order_access_token


def normalize_ticket_phone(value):
    value = (value or "").strip()
    if not value:
        return ""
    digits = re.sub(r"[^0-9]", "", value)
    if value.startswith("+"):
        number = "+" + digits
    elif len(digits) == 10:
        number = "+1" + digits
    elif len(digits) == 11 and digits.startswith("1"):
        number = "+" + digits
    else:
        raise ValueError("Enter a mobile phone with country code, e.g. +1 followed by 10 digits")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", number):
        raise ValueError("Invalid mobile phone number")
    return number


def ticket_page_url(order):
    base = os.getenv("TNG_APP_URL", "https://tngos.tngboxinggym.com").rstrip("/")
    query = urlencode({"ticket_payment": "success", "order": order.id,
                       "access_token": order_access_token(order)})
    return f"{base}/events/{order.event_id}/tickets?{query}"

def sms_status_url(delivery_id):
    base = os.getenv("TNG_BACKEND_URL", "https://sea-lion-app-2-gxyfr.ondigitalocean.app").rstrip("/")
    return f"{base}/api/ticketing/sms/status?delivery_id={delivery_id}"


def queue_deliveries(db, order):
    if order.payment_provider == "paper_cash":
        return  # Customer already holds the paper ticket; no automatic messages.
    for channel in ("sms", "email"):
        if channel == "sms" and not order.buyer_phone:
            continue
        if not db.query(TicketDelivery).filter_by(order_id=order.id, channel=channel).first():
            db.add(TicketDelivery(order_id=order.id, channel=channel))
    db.flush()


def deliver_order(db, order, force=True):
    from app.matchmaker.models import BoxingEvent
    from app.services.sms_service import send_sms
    from .emailing import send_ticket_email
    from .routes import generate_ticket_qr_base64

    event = db.query(BoxingEvent).filter_by(id=order.event_id).one()
    tickets = db.query(IssuedTicket).filter_by(order_id=order.id).all()
    if order.payment_status != "paid" or not tickets:
        raise ValueError("Only issued paid orders can be delivered")
    queue_deliveries(db, order)
    db.commit()
    ids = [row.id for row in db.query(TicketDelivery).filter_by(order_id=order.id).all()]
    for delivery_id in ids:
        # Serialize retries on PostgreSQL; sent means provider accepted, not handset delivered.
        db.query(TicketDelivery).filter_by(id=delivery_id).update(
            {TicketDelivery.status: TicketDelivery.status}, synchronize_session=False)
        delivery = db.query(TicketDelivery).filter_by(id=delivery_id).populate_existing().one()
        if delivery.status in ("sent", "delivered"):
            db.commit()
            continue
        if not force and (delivery.attempts >= 8 or
                (delivery.next_attempt_at and delivery.next_attempt_at > datetime.utcnow())):
            db.commit()
            continue
        delivery.attempts += 1
        try:
            if delivery.channel == "sms":
                provider_id = send_sms(normalize_ticket_phone(order.buyer_phone),
                    f"Your TNG tickets for {event.name} are ready. View your QR tickets: {ticket_page_url(order)} Reply STOP to opt out.",
                    status_callback=sms_status_url(delivery.id))
            else:
                result = send_ticket_email(order.buyer_email, event.name, order.receipt_number,
                    [{"ticket_number": t.ticket_number, "status": t.status, "price_cents": t.price_cents,
                      "qr_png_base64": generate_ticket_qr_base64(t.qr_token_encrypted)} for t in tickets],
                    order.total_cents)
                provider_id = result.get("id") if isinstance(result, dict) else None
            if not provider_id:
                raise RuntimeError("Delivery provider did not acknowledge notification")
            delivery.status = "sent"
            delivery.provider_id = str(provider_id)
            delivery.sent_at = datetime.utcnow()
            delivery.last_error = None
            delivery.next_attempt_at = None
        except Exception as exc:
            delivery.status = "failed"
            # Do not persist provider response bodies or credentials.
            delivery.last_error = type(exc).__name__
            code = getattr(exc, "code", None)
            if isinstance(code, int):
                delivery.last_error += f" (provider code {code})"
            delivery.next_attempt_at = datetime.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(delivery.attempts, 7)))
            if code in (21211, 21610, 30034):
                delivery.next_attempt_at = datetime.max
        db.commit()
    return [{"channel": d.channel, "status": d.status, "attempts": d.attempts,
             "last_error": d.last_error} for d in db.query(TicketDelivery).filter_by(order_id=order.id).all()]
