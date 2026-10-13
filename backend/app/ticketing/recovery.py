"""Staff reconciliation of missing payments against read-only Clover evidence."""
import json
import os
import re
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import staff_user
from app.core.permissions import require_admin
from app.database import get_db
from .models import TicketOrder, IssuedTicket, TicketDelivery, TicketRecovery
from .service import issue_paid_order
from .delivery import queue_deliveries, deliver_order, ticket_page_url

router = APIRouter(prefix="/api/ticketing", tags=["ticketing-recovery"])


@router.get("/events/{event_id}/orders/incident")
def incident_orders(event_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    orders = db.query(TicketOrder).filter_by(event_id=event_id).order_by(TicketOrder.id).all()
    return [{"order_id": o.id, "seller_id": o.seller_id, "payment_status": o.payment_status,
             "total_cents": o.total_cents, "clover_checkout_id": o.clover_checkout_id,
             "payment_id": o.payment_id,
             "issued_tickets": db.query(IssuedTicket).filter_by(order_id=o.id).count(),
             "deliveries": [{"channel": d.channel, "status": d.status, "attempts": d.attempts,
                             "last_error": d.last_error} for d in
                            db.query(TicketDelivery).filter_by(order_id=o.id).all()]} for o in orders]


@router.post("/orders/{order_id}/recover")
def recover_paid_order(order_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    order = db.query(TicketOrder).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.payment_status != "paid":
        raise HTTPException(409, "Payment must be verified before recovering tickets")
    try:
        issued = issue_paid_order(db, order, json.loads(order.items_json or "[]"))
        queue_deliveries(db, order)
        db.commit()
    except (ValueError, RuntimeError, IntegrityError):
        db.rollback()
        raise HTTPException(409, "Order requires manual review; no tickets changed")
    return {"order_id": order.id, "tickets_issued": len(issued),
            "ticket_url": ticket_page_url(order), "deliveries": deliver_order(db, order)}


class CloverReconciliation(BaseModel):
    clover_order_id: str
    confirm_checkout_id: str


@router.post("/orders/{order_id}/reconcile-clover")
def reconcile_clover(order_id: int, body: CloverReconciliation,
                     db: Session = Depends(get_db), user=Depends(staff_user)):
    require_admin(user)
    order = db.query(TicketOrder).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not order.clover_checkout_id or order.clover_checkout_id != body.confirm_checkout_id:
        raise HTTPException(409, "Confirm the exact TNG checkout associated with the Clover order")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", body.clover_order_id):
        raise HTTPException(400, "Invalid Clover order ID")
    merchant = os.getenv("CLOVER_MERCHANT_ID")
    token = os.getenv("CLOVER_API_TOKEN")
    if not merchant or not token:
        raise HTTPException(503, "Clover merchant API credentials are required for reconciliation")
    base = "https://api.clover.com" if os.getenv("CLOVER_ENV", "production").lower() == "production" else "https://apisandbox.dev.clover.com"
    try:
        response = requests.get(f"{base}/v3/merchants/{merchant}/orders/{body.clover_order_id}",
            params={"expand": "payments"}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        evidence = response.json()
    except (requests.RequestException, ValueError):
        raise HTTPException(502, "Clover payment evidence could not be verified")
    payments = evidence.get("payments", {}).get("elements", [])
    # Never use a browser redirect, amount alone, or a receipt screenshot as payment proof.
    if (evidence.get("id") != body.clover_order_id or evidence.get("paymentState") != "PAID"
            or evidence.get("currency", "USD") != "USD" or not payments
            or any(p.get("result") != "SUCCESS" or not p.get("id")
                   or p.get("voided") or p.get("refunded") or p.get("refunds", {}).get("elements") for p in payments)):
        raise HTTPException(409, "Clover order is not fully paid or needs refund/void review")
    payment_ids = sorted({str(p["id"]) for p in payments})
    total = sum(int(p.get("amount", 0)) for p in payments)
    if len(payment_ids) != len(payments) or total != order.total_cents or evidence.get("total") != order.total_cents or total <= 0:
        raise HTTPException(409, "Clover payment total does not match this ticket order")
    # Expanded order payments can omit refund details. Read each authoritative
    # payment with refunds before crediting an old purchase.
    for payment in payments:
        try:
            detail_response = requests.get(
                f"{base}/v3/merchants/{merchant}/payments/{payment['id']}",
                params={"expand": "refunds"}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            detail_response.raise_for_status()
            detail = detail_response.json()
        except (requests.RequestException, ValueError):
            raise HTTPException(502, "Clover payment/refund evidence could not be verified")
        if (detail.get("id") != payment["id"] or detail.get("result") != "SUCCESS"
                or detail.get("amount") != payment.get("amount")
                or detail.get("order", {}).get("id") != body.clover_order_id
                or detail.get("voided") or detail.get("refunded")
                or detail.get("refunds", {}).get("elements")):
            raise HTTPException(409, "Clover payment association or refund/void evidence requires review")
    db.query(TicketOrder).filter_by(id=order.id).update(
        {TicketOrder.payment_status: TicketOrder.payment_status}, synchronize_session=False)
    db.refresh(order)
    existing = db.query(TicketRecovery).filter_by(clover_order_id=body.clover_order_id).first()
    if existing and existing.order_id != order.id:
        raise HTTPException(409, "Clover order is already assigned to another ticket order")
    stored_id = payment_ids[0] if len(payment_ids) == 1 else "CLOVER-ORDER-" + body.clover_order_id
    duplicate = db.query(TicketOrder).filter(TicketOrder.id != order.id,
        TicketOrder.payment_id.in_(payment_ids + [stored_id])).first()
    if duplicate or order.payment_status in ("refunded", "partial_refund"):
        raise HTTPException(409, "Payment is already assigned or requires refund review")
    if order.payment_id and order.payment_id != stored_id:
        raise HTTPException(409, "Order already has a different payment")
    if not existing:
        if db.query(TicketRecovery).filter_by(order_id=order.id).first():
            raise HTTPException(409, "Order already reconciled against another Clover order")
        db.add(TicketRecovery(order_id=order.id, clover_order_id=body.clover_order_id,
            payment_ids_json=json.dumps(payment_ids), verified_total_cents=total, confirmed_by_user_id=user.id))
    order.payment_status = "paid"
    order.payment_id = stored_id
    order.paid_at = order.paid_at or datetime.utcnow()
    try:
        issued = issue_paid_order(db, order, json.loads(order.items_json or "[]"))
        queue_deliveries(db, order)
        db.commit()
    except (ValueError, RuntimeError, IntegrityError):
        db.rollback()
        raise HTTPException(409, "Order items or QR configuration require review; no payment state changed")
    return {"order_id": order.id, "seller_id": order.seller_id, "tickets_issued": len(issued),
            "ticket_url": ticket_page_url(order), "deliveries": deliver_order(db, order)}
