"""Staff reconciliation of missing payments against read-only Clover evidence."""
import json
import os
import re
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import staff_user
from app.core.permissions import require_admin
from app.database import get_db
from app.models import SecurityLog
from .models import TicketOrder, IssuedTicket, TicketDelivery, TicketRecovery, EventSeller
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


@router.get("/events/{event_id}/recovery-dashboard")
def recovery_dashboard(event_id: int, q: str = Query("", max_length=160),
                       issue: str = Query("all", pattern="^(all|attention|pending|unattributed)$"),
                       page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                       db: Session = Depends(get_db), user=Depends(staff_user)):
    from app.matchmaker.models import BoxingEvent
    if not db.get(BoxingEvent, event_id):
        raise HTTPException(404, "Event not found")
    orders = db.query(TicketOrder, EventSeller.display_name).outerjoin(
        EventSeller, EventSeller.id == TicketOrder.seller_id).filter(
        TicketOrder.event_id == event_id).order_by(TicketOrder.id.desc()).all()
    # Batch aggregates avoid loading QR credentials or querying once per order.
    counts = {r.order_id: r for r in db.query(
        IssuedTicket.order_id, func.count(IssuedTicket.id).label("issued"),
        func.sum(case((IssuedTicket.status.in_(("valid", "used")), 1), else_=0)).label("usable"),
        func.sum(case((IssuedTicket.status.in_(("valid", "used")), IssuedTicket.commission_cents), else_=0)).label("commission")
    ).filter(IssuedTicket.event_id == event_id).group_by(IssuedTicket.order_id).all()}
    deliveries = {}
    for d in db.query(TicketDelivery).join(TicketOrder, TicketOrder.id == TicketDelivery.order_id).filter(
            TicketOrder.event_id == event_id).all():
        deliveries.setdefault(d.order_id, []).append({"channel": d.channel, "status": d.status,
            "attempts": d.attempts, "last_error": d.last_error,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None})
    summary = {"orders": len(orders), "paid_orders": 0, "paid_total_cents": 0,
               "pending_orders": 0, "needs_attention": 0, "unattributed_paid_orders": 0,
               "commission_earned_cents": 0}
    rows = []
    query = q.strip().casefold()
    for o, seller_name in orders:
        stats = counts.get(o.id)
        issued, usable = (int(stats.issued), int(stats.usable or 0)) if stats else (0, 0)
        commission = int(stats.commission or 0) if stats and o.payment_status == "paid" else 0
        try:
            items = json.loads(o.items_json or "[]")
            expected = sum(int(item["quantity"]) for item in items)
            if not items or any(int(item["quantity"]) <= 0 for item in items):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            expected = None
        ds = sorted(deliveries.get(o.id, []), key=lambda d: d["channel"])
        problems = []
        if o.payment_status == "paid":
            summary["paid_orders"] += 1
            summary["paid_total_cents"] += o.total_cents
            summary["commission_earned_cents"] += commission
            if not o.seller_id:
                summary["unattributed_paid_orders"] += 1
            if expected is None:
                problems.append("Order items need review")
            elif issued != expected:
                problems.append("Ticket count does not match order")
            elif usable != expected:
                problems.append("Voided or refunded tickets need review")
            channels = {d["channel"] for d in ds}
            for channel in (["email", "sms"] if o.buyer_phone else ["email"]):
                if channel not in channels:
                    problems.append(f"{channel.upper()} delivery not queued")
            for d in ds:
                if d["status"] not in ("sent", "delivered"):
                    problems.append(f'{d["channel"].upper()} {d["status"]}')
            if problems:
                summary["needs_attention"] += 1
        if o.payment_status == "pending":
            summary["pending_orders"] += 1
        row = {"order_id": o.id, "receipt_number": o.receipt_number,
               "buyer_name": o.buyer_name, "buyer_email": o.buyer_email,
               "buyer_phone": o.buyer_phone, "seller_id": o.seller_id,
               "seller_name": seller_name, "payment_status": o.payment_status,
               "total_cents": o.total_cents, "payment_id": o.payment_id,
               "clover_checkout_id": o.clover_checkout_id,
               "expected_tickets": expected, "issued_tickets": issued, "usable_tickets": usable,
               "commission_cents": commission, "deliveries": ds, "issues": problems,
               "can_recover": o.payment_status == "paid" and expected is not None and
                   (issued == 0 or issued == usable == expected),
               "created_at": o.created_at.isoformat() if o.created_at else None}
        if query and query not in " ".join(str(row[k] or "") for k in (
                "order_id", "receipt_number", "buyer_name", "buyer_email", "seller_name", "clover_checkout_id", "payment_id")).casefold():
            continue
        if issue == "attention" and not problems:
            continue
        if issue == "pending" and o.payment_status != "pending":
            continue
        if issue == "unattributed" and (o.seller_id or o.payment_status != "paid"):
            continue
        rows.append(row)
    return {"summary": summary, "orders": rows[(page-1)*page_size:page*page_size],
            "total": len(rows), "page": page, "page_size": page_size,
            "can_reconcile": user.role == "admin"}


@router.get("/orders/{order_id}/ticket-page")
def staff_ticket_page(order_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    order = db.get(TicketOrder, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.payment_status != "paid" or not db.query(IssuedTicket.id).filter(
            IssuedTicket.order_id == order.id, IssuedTicket.status.in_(("valid", "used"))).first():
        raise HTTPException(409, "Only paid orders with issued tickets have a ticket page")
    return {"ticket_url": ticket_page_url(order)}


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
        db.add(SecurityLog(user_id=user.id, action="TICKET_RECOVERY_REQUESTED",
            description=f"Paid order {order.id}; ticket and delivery recovery requested",
            endpoint=f"/api/ticketing/orders/{order.id}/recover", success=True))
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
