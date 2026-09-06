import json
import os

import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import TicketOrder, EventTicketType
from app.ticketing.service import issue_paid_order


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

    if order.payment_status == "paid":
        return {
            "order_id": order.id,
            "status": "paid",
            "message": "Order is already paid",
        }

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

        unit_price = int(ticket_type.price_cents or 0)

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
            detail="Ticket order total does not match current ticket prices",
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

        db.commit()
        db.refresh(order)

        return {
            "success": True,
            "order_id": order.id,
            "status": "paid",
            "payment_provider": "comp",
            "total_cents": 0,
            "tickets_issued": len(issued),
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

    success_url = (
        f"{app_url}/events/{order.event_id}/tickets"
        f"?ticket_payment=success"
        f"&order={order.id}"
    )

    failure_url = (
        f"{app_url}/events/{order.event_id}/tickets"
        f"?ticket_payment=failure"
        f"&order={order.id}"
    )

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

    response = requests.post(
        f"{base_url}/invoicingcheckoutservice/v1/checkouts",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Clover ticket checkout error "
                f"{response.status_code}: {response.text}"
            ),
        )

    clover_data = response.json()

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
        raise HTTPException(
            status_code=500,
            detail="Clover did not return a checkout ID",
        )

    if not checkout_url:
        raise HTTPException(
            status_code=500,
            detail="Clover did not return a checkout URL",
        )

    order.clover_checkout_id = str(checkout_id)

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
