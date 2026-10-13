"""Authenticate Twilio callbacks and track actual carrier delivery."""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from app.database import get_db
from .models import TicketDelivery
from .delivery import sms_status_url

router = APIRouter(prefix="/api/ticketing", tags=["ticketing-notifications"])


@router.post("/sms/status")
async def sms_status(delivery_id: int, request: Request, db: Session = Depends(get_db)):
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not token:
        raise HTTPException(503, "SMS callback verification is not configured")
    form = await request.form()
    if not RequestValidator(token).validate(sms_status_url(delivery_id), form,
                                            request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(401, "Invalid SMS status signature")
    if form.get("AccountSid") != os.getenv("TWILIO_ACCOUNT_SID"):
        raise HTTPException(401, "SMS account does not match")
    db.query(TicketDelivery).filter_by(id=delivery_id).update(
        {TicketDelivery.status: TicketDelivery.status}, synchronize_session=False)
    delivery = db.query(TicketDelivery).filter_by(id=delivery_id, channel="sms").populate_existing().first()
    if not delivery:
        raise HTTPException(404, "SMS delivery not found")
    if delivery.provider_id != form.get("MessageSid"):
        raise HTTPException(409, "SMS message does not match current delivery attempt")
    state = form.get("MessageStatus", "")
    if delivery.status == "delivered":
        return {"received": True}
    if state == "delivered":
        delivery.status = "delivered"
        delivery.last_error = None
        delivery.next_attempt_at = None
    elif state in ("failed", "undelivered", "canceled"):
        try:
            code = int(form.get("ErrorCode") or 0)
        except (ValueError, TypeError):
            code = 0
        delivery.status = "failed"
        delivery.last_error = f"Twilio {state} (provider code {code})"
        delivery.next_attempt_at = (datetime.max if code in (21211, 21610, 30034) else
            datetime.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(delivery.attempts, 7))))
    db.commit()
    return {"received": True}
