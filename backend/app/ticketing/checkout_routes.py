import json
import os

import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import TicketOrder, EventTicketType, TicketCheckoutAttempt, TicketCheckoutRequest
from app.ticketing.service import issue_paid_order
from app.ticketing.delivery import queue_deliveries, deliver_order, ticket_page_url


router = APIRouter(
    prefix="/api/ticketing",
    tags=["ticketing-checkout"],
)


@router.post("/public/orders/{order_id}/checkout")
def create_ticket_clover_checkout(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = db.query(TicketOrder).filter(
        TicketOrder.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Ticket order not found",
        )

    db.query(TicketOrder).filter_by(id=order.id).update(
        {TicketOrder.payment_status: TicketOrder.payment_status}, synchronize_session=False)
    db.refresh(order)

    if order.payment_status == "paid":
        return {
            "order_id": order.id,
            "status": "paid",
            "message": "Order is already paid",
        }

    if order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="Order cannot start another checkout")
    from .sales_access import require_sales_open
    from .models import EventSeller
    require_sales_open(db, order.event_id, db.get(EventSeller, order.seller_id) if order.seller_id else None)
    saved = db.query(TicketCheckoutAttempt).filter_by(order_id=order.id).first()
    if saved:
        return {"success": True, "order_id": order.id, "status": order.payment_status,
                "clover_checkout_id": saved.checkout_id, "checkout_url": saved.checkout_url,
                "total_cents": order.total_cents}
    if order.clover_checkout_id:
        raise HTTPException(status_code=409, detail="Checkout already exists; use the original payment link or contact TNG")

    event = db.query(BoxingEvent).filter(
        BoxingEvent.id == order.event_id
    ).first()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    try:
        items = json.loads(order.items_json or "[]")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Ticket order items are invalid",
        )

    if not items:
        raise HTTPException(
            status_code=400,
            detail="Ticket order has no items",
        )

    line_items = []
    calculated_total = 0

    for item in items:
        ticket_type_id = int(item.get("ticket_type_id") or 0)
        quantity = int(item.get("quantity") or 0)

        if quantity < 1:
            continue

        ticket_type = db.query(EventTicketType).filter(
            EventTicketType.id == ticket_type_id,
            EventTicketType.event_id == order.event_id,
        ).first()

        if not ticket_type:
            raise HTTPException(
                status_code=400,
                detail=f"Ticket type {ticket_type_id} not found",
            )

        unit_price = int(item.get("price_cents", ticket_type.price_cents or 0))

        calculated_total += unit_price * quantity

        line_items.append({
            "name": f"{event.name} - {ticket_type.name}",
            "note": "TNG Promotions Event Ticket",
            "price": unit_price,
            "unitQty": quantity,
        })

    if not line_items:
        raise HTTPException(
            status_code=400,
            detail="No valid tickets found",
        )

    if calculated_total != int(order.total_cents or 0):
        raise HTTPException(
            status_code=400,
            detail="Ticket order total does not match ticket prices",
        )

    # --------------------------------------------------------
    # FREE / COMP ORDER
    # $0 orders do not go to Clover.
    # Mark paid and issue unique QR tickets immediately.
    # --------------------------------------------------------
    if calculated_total == 0:
        order.payment_status = "paid"
        order.payment_provider = "comp"
        order.payment_id = f"COMP-{order.id}"
        order.paid_at = datetime.utcnow()

        db.flush()

        issued = issue_paid_order(
            db,
            order,
            items,
        )

        queue_deliveries(db, order)
        db.commit()
        db.refresh(order)
        deliveries = deliver_order(db, order)

        return {
            "success": True,
            "order_id": order.id,
            "status": "paid",
            "payment_provider": "comp",
            "total_cents": 0,
            "tickets_issued": len(issued),
            "ticket_url": ticket_page_url(order),
            "deliveries": deliveries,
            "checkout_url": None,
        }

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")

    api_token = (
        os.getenv("CLOVER_ECOMMERCE_PRIVATE_KEY")
        or os.getenv("CLOVER_API_TOKEN")
    )

    clover_env = os.getenv(
        "CLOVER_ENV",
        "production",
    ).lower()

    if not merchant_id or not api_token:
        raise HTTPException(
            status_code=500,
            detail="Clover credentials missing",
        )

    base_url = (
        "https://api.clover.com"
        if clover_env == "production"
        else "https://apisandbox.dev.clover.com"
    )

    app_url = os.getenv(
        "TNG_APP_URL",
        "https://tngos.tngboxinggym.com",
    ).rstrip("/")

    buyer_name = (
        order.buyer_name
        or "Ticket Customer"
    ).strip()

    parts = buyer_name.split(maxsplit=1)

    customer = {
        "firstName": parts[0] if parts else "Customer",
        "lastName": parts[1] if len(parts) > 1 else "",
        "email": order.buyer_email,
    }

    if order.buyer_phone:
        customer["phoneNumber"] = order.buyer_phone

    success_url = ticket_page_url(order)

    failure_url = success_url.replace("ticket_payment=success", "ticket_payment=failure")

    payload = {
        "customer": customer,
        "redirectUrls": {
            "success": success_url,
            "failure": failure_url,
        },
        "shoppingCart": {
            "lineItems": line_items,
        },
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "X-Clover-Merchant-Id": merchant_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    claim = db.get(TicketCheckoutRequest, order.id)
    if claim and claim.status != "rejected":
        raise HTTPException(409, "Checkout is already processing or its outcome is uncertain. Do not pay again; contact TNG with your order number.")
    if not claim:
        claim = TicketCheckoutRequest(order_id=order.id, status="creating"); db.add(claim)
    else:
        claim.status = "creating"
    db.commit()  # Persist the claim before contacting Clover; timeout retries cannot create another checkout.
    try:
        response = requests.post(f"{base_url}/invoicingcheckoutservice/v1/checkouts",
            json=payload, headers=headers, timeout=30)
    except requests.RequestException:
        claim.status = "unknown"; db.commit()
        raise HTTPException(503, "Checkout confirmation was interrupted. Your order is saved. Do not start another payment; contact TNG with your order number.")
    if response.status_code >= 400:
        claim.status = "rejected" if 400 <= response.status_code < 500 else "unknown"
        db.commit()
        raise HTTPException(503, "Secure checkout could not be opened. Your order is saved. This is not a card-decline confirmation; contact TNG if it persists." if claim.status == "rejected" else "Checkout outcome is uncertain. Your order is saved. Do not pay again; contact TNG with your order number.")
    try:
        clover_data = response.json()
        if not isinstance(clover_data, dict): raise ValueError()
    except ValueError:
        claim.status = "unknown"; db.commit()
        raise HTTPException(503, "Clover checkout response could not be confirmed. Do not pay again; contact TNG.")

    checkout_id = (
        clover_data.get("checkoutSessionId")
        or clover_data.get("id")
    )

    checkout_url = (
        clover_data.get("href")
        or clover_data.get("url")
        or clover_data.get("checkoutUrl")
        or clover_data.get("checkout_url")
    )

    if not checkout_id:
        claim.status = "unknown"; db.commit()
        raise HTTPException(
            status_code=500,
            detail="Clover did not return a checkout ID",
        )

    if not checkout_url:
        claim.status = "unknown"; db.commit()
        raise HTTPException(
            status_code=500,
            detail="Clover did not return a checkout URL",
        )

    claim.status = "ready"
    order.clover_checkout_id = str(checkout_id)
    db.add(TicketCheckoutAttempt(order_id=order.id, checkout_id=str(checkout_id), checkout_url=checkout_url))

    db.commit()
    db.refresh(order)

    return {
        "success": True,
        "order_id": order.id,
        "clover_checkout_id": order.clover_checkout_id,
        "checkout_url": checkout_url,
        "total_cents": order.total_cents,
        "status": order.payment_status,
    }
