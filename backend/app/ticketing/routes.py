from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import current_user
from .models import EventSeller, EventTicketType, TicketOrder, IssuedTicket
from .service import generate_public_code, generate_receipt_number, scan_ticket, seller_totals
from datetime import datetime
import io
import base64
import qrcode
import json
import csv
from reportlab.pdfgen import canvas
from app.ticketing.emailing import send_fighter_report
from app.ticketing.security import decrypt_token
from fastapi.responses import StreamingResponse
from app.models import User
from app.core.permissions import require_admin_or_staff

router = APIRouter(prefix="/api/ticketing", tags=["ticketing"])

class SellerCreate(BaseModel):
    seller_type: str
    seller_ref_id: int
    display_name: str
    email: EmailStr | None = None

class ScanRequest(BaseModel):
    event_id: int
    token: str
    device_label: str | None = None

class PublicTicketOrderCreate(BaseModel):
    buyer_name: str
    buyer_email: EmailStr
    buyer_phone: str | None = None
    seller_code: str | None = None
    items: list[dict]


@router.post("/public/events/{event_id}/orders")
def create_public_ticket_order(
    event_id: int,
    body: PublicTicketOrderCreate,
    db: Session = Depends(get_db),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    seller_record = None
    if body.seller_code:
        seller_record = db.query(EventSeller).filter(
            EventSeller.event_id == event_id,
            EventSeller.public_code == body.seller_code,
            EventSeller.active == True,
        ).first()

    subtotal_cents = 0
    valid_ticket_count = 0

    for item in body.items:
        ticket_type_id = int(item.get("ticket_type_id"))
        quantity = int(item.get("quantity", 0))

        if quantity <= 0:
            continue

        ticket_type = db.query(EventTicketType).filter(
            EventTicketType.id == ticket_type_id,
            EventTicketType.event_id == event_id,
            EventTicketType.active == True,
        ).first()

        if not ticket_type:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticket type {ticket_type_id}",
            )

        subtotal_cents += ticket_type.price_cents * quantity
        valid_ticket_count += quantity

    if valid_ticket_count <= 0:
        raise HTTPException(
            status_code=400,
            detail="At least one ticket is required",
        )

    order = TicketOrder(
        event_id=event_id,
        seller_id=seller_record.id if seller_record else None,
        buyer_name=body.buyer_name.strip(),
        buyer_email=str(body.buyer_email).lower(),
        buyer_phone=(body.buyer_phone or "").strip(),
        subtotal_cents=subtotal_cents,
        fee_cents=0,
        total_cents=subtotal_cents,
        payment_provider="clover",
        payment_status="pending",
        items_json=json.dumps(body.items),
        receipt_number=generate_receipt_number(event_id),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "receipt_number": order.receipt_number,
        "event_id": event_id,
        "seller_id": order.seller_id,
        "subtotal_cents": order.subtotal_cents,
        "total_cents": order.total_cents,
        "payment_status": order.payment_status,
    }

@router.post("/events/{event_id}/sellers")
def create_seller(event_id: int, body: SellerCreate, db: Session = Depends(get_db), user=Depends(current_user)):
    existing = db.query(EventSeller).filter(
        EventSeller.event_id == event_id,
        EventSeller.seller_type == body.seller_type,
        EventSeller.seller_ref_id == body.seller_ref_id,
    ).first()
    if existing:
        return existing
    seller = EventSeller(
        event_id=event_id,
        seller_type=body.seller_type,
        seller_ref_id=body.seller_ref_id,
        display_name=body.display_name,
        email=str(body.email) if body.email else None,
        public_code=generate_public_code(event_id, body.seller_type),
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller
@router.get("/public/orders/{order_id}/tickets")
def public_order_tickets(
    order_id: int,
    email: str,
    db: Session = Depends(get_db),
):
    order = db.query(TicketOrder).filter(TicketOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_email.lower() != email.strip().lower():
        raise HTTPException(status_code=403, detail="Email does not match order")

    if order.payment_status != "paid":
        return {
            "order_id": order.id,
            "payment_status": order.payment_status,
            "tickets": [],
        }

    tickets = db.query(IssuedTicket).filter(
        IssuedTicket.order_id == order.id
    ).order_by(IssuedTicket.id.asc()).all()

    return {
        "order_id": order.id,
        "receipt_number": order.receipt_number,
        "payment_status": order.payment_status,
        "tickets": [
            {
                "id": t.id,
                "ticket_number": t.ticket_number,
                "status": t.status,
                "price_cents": t.price_cents,
                "ticket_type_id": t.ticket_type_id,
                "qr_png_base64": (
                    generate_ticket_qr_base64(t.qr_token_encrypted)
                    if t.qr_token_encrypted
                    else None
                ),
            }
                       for t in tickets
        ],
    }


@router.post("/events/{event_id}/fighters/{fighter_id}/enable-ticket-sales")
def enable_fighter_sales(event_id: int, fighter_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    # Adapt Fighter import/path to current Matchmaker model.
    from app.matchmaker.models import BoxingFighter
    fighter = db.query(BoxingFighter).filter(BoxingFighter.id == fighter_id).first()
    if not fighter:
        raise HTTPException(404, "Fighter not found")
    existing = db.query(EventSeller).filter(
        EventSeller.event_id == event_id,
        EventSeller.seller_type == "fighter",
        EventSeller.seller_ref_id == fighter_id,
    ).first()
    if existing:
        return existing
    seller = EventSeller(
        event_id=event_id,
        seller_type="fighter",
        seller_ref_id=fighter_id,
        display_name=getattr(fighter, "legal_name", None) or f"Fighter {fighter_id}",
        email=getattr(fighter, "email", None),
        public_code=generate_public_code(event_id, "fighter"),
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller
def generate_ticket_qr_base64(encrypted_token: str) -> str:
    raw_token = decrypt_token(encrypted_token)

    img = qrcode.make(raw_token)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return base64.b64encode(buf.getvalue()).decode()



@router.get("/events/{event_id}/sellers/{seller_id}/qr")
def seller_ticket_qr(
    event_id: int,
    seller_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    seller = db.query(EventSeller).filter(
        EventSeller.id == seller_id,
        EventSeller.event_id == event_id,
    ).first()

    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    url = f"https://tngos.tngboxinggym.com/events/{event_id}/tickets?seller={seller.public_code}"

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return {
        "seller_id": seller.id,
        "name": seller.display_name,
        "seller_code": seller.public_code,
        "url": url,
        "qr_png_base64": base64.b64encode(buf.getvalue()).decode(),
    }
@router.get("/public/events/{event_id}/tickets")
def public_event_tickets(
    event_id: int,
    seller: str | None = None,
    db: Session = Depends(get_db),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    seller_record = None
    if seller:
        seller_record = db.query(EventSeller).filter(
            EventSeller.event_id == event_id,
            EventSeller.public_code == seller,
            EventSeller.active == True,
        ).first()

    ticket_types = db.query(EventTicketType).filter(
        EventTicketType.event_id == event_id,
        EventTicketType.active == True,
    ).all()

    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "venue": event.venue,
            "venue_address": event.venue_address,
            "event_date": event.event_date,
        },
        "seller": {
            "id": seller_record.id,
            "name": seller_record.display_name,
            "code": seller_record.public_code,
        } if seller_record else None,
        "ticket_types": [
            {
                "id": t.id,
                "name": t.name,
                "price_cents": t.price_cents,
                "inventory": t.inventory,
            }
            for t in ticket_types
        ],
    }

@router.get("/events/{event_id}/sellers/live")
def live_seller_sales(event_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return {"event_id": event_id, "sellers": seller_totals(db, event_id)}

@router.post("/scan")
def scan(body: ScanRequest, db: Session = Depends(get_db), user=Depends(current_user)):
    return scan_ticket(db, body.event_id, body.token, getattr(user, "id", None), body.device_label)

@router.get("/events/{event_id}/report")
def event_report(event_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    sellers = seller_totals(db, event_id)
    tickets = db.query(IssuedTicket).filter(IssuedTicket.event_id == event_id).all()
    return {
        "event_id": event_id,
        "tickets_sold": sum(1 for t in tickets if t.status != "refunded"),
        "tickets_scanned": sum(1 for t in tickets if t.status == "used"),
        "gross_sales_cents": sum(t.price_cents for t in tickets if t.status != "refunded"),
        "commission_cents": sum(t.commission_cents for t in tickets if t.status != "refunded"),
        "sellers": sellers,
    }

@router.post("/events/{event_id}/email-seller-reports")
def email_seller_reports(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    sellers = seller_totals(db, event_id)

    results = []

    for seller in sellers:
        seller_record = db.query(EventSeller).filter(
            EventSeller.id == seller["seller_id"]
        ).first()

        if not seller_record or not seller_record.email:
            results.append({
                "seller_id": seller["seller_id"],
                "name": seller["display_name"],
                "status": "skipped_no_email",
            })
            continue

        send_fighter_report(
            seller_record.email,
            seller["display_name"],
            event.name,
            seller["tickets_sold"],
            seller["gross_sales_cents"],
            seller["commission_cents"],
            0,
        )

        results.append({
            "seller_id": seller["seller_id"],
            "name": seller["display_name"],
            "status": "sent",
            "email": seller_record.email,
        })

    return {
        "event_id": event_id,
        "event_name": event.name,
        "reports": results,
    }
@router.get("/events/{event_id}/report.csv")
def download_event_report_csv(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    sellers = seller_totals(db, event_id)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Seller",
        "Seller Type",
        "Seller Code",
        "Tickets Sold",
        "Gross Sales",
        "Commission Earned",
    ])

    for seller in sellers:
        writer.writerow([
            seller["display_name"],
            seller["seller_type"],
            seller["public_code"],
            seller["tickets_sold"],
            f"${seller['gross_sales_cents'] / 100:.2f}",
            f"${seller['commission_cents'] / 100:.2f}",
        ])

    output.seek(0)

    filename = f"tng_event_{event_id}_ticket_report.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
@router.get("/events/{event_id}/sellers/{seller_id}/report.csv")
def download_seller_report_csv(
    event_id: int,
    seller_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    seller = db.query(EventSeller).filter(
        EventSeller.id == seller_id,
        EventSeller.event_id == event_id,
    ).first()

    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    tickets = db.query(IssuedTicket).filter(
        IssuedTicket.event_id == event_id,
        IssuedTicket.seller_id == seller_id,
    ).order_by(IssuedTicket.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Ticket Number",
        "Status",
        "Price",
        "Commission",
        "Issued At",
        "Scanned At",
    ])

    for ticket in tickets:
        writer.writerow([
            ticket.ticket_number,
            ticket.status,
            f"${ticket.price_cents / 100:.2f}",
            f"${ticket.commission_cents / 100:.2f}",
            ticket.issued_at,
            ticket.scanned_at or "",
        ])

    output.seek(0)

    filename = f"tng_event_{event_id}_seller_{seller_id}_report.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
@router.get("/events/{event_id}/sellers/{seller_id}/report.pdf")
def download_seller_report_pdf(
    event_id: int,
    seller_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    seller = db.query(EventSeller).filter(
        EventSeller.id == seller_id,
        EventSeller.event_id == event_id,
    ).first()

    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    tickets = db.query(IssuedTicket).filter(
        IssuedTicket.event_id == event_id,
        IssuedTicket.seller_id == seller_id,
    ).order_by(IssuedTicket.id.asc()).all()

    gross_sales_cents = sum(
        t.price_cents for t in tickets if t.status != "refunded"
    )

    commission_cents = sum(
        t.commission_cents for t in tickets if t.status != "refunded"
    )

    output = io.BytesIO()
    pdf = canvas.Canvas(output)

    pdf.setTitle(
        f"{event.name} - {seller.display_name} Ticket Sales Report"
    )

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 800, "TNG Promotions")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 775, event.name)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50, 750,
        f"Seller: {seller.display_name}"
    )
    pdf.drawString(
        50, 733,
        f"Seller Code: {seller.public_code}"
    )
    pdf.drawString(
        50, 716,
        f"Tickets Sold: {len([t for t in tickets if t.status != 'refunded'])}"
    )
    pdf.drawString(
        50, 699,
        f"Gross Sales: ${gross_sales_cents / 100:.2f}"
    )
    pdf.drawString(
        50, 682,
        f"Commission Earned: ${commission_cents / 100:.2f}"
    )

    y = 645

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(50, y, "Ticket")
    pdf.drawString(180, y, "Status")
    pdf.drawString(270, y, "Price")
    pdf.drawString(350, y, "Commission")

    y -= 18
    pdf.setFont("Helvetica", 9)

    for ticket in tickets:
        if y < 60:
            pdf.showPage()
            y = 800

        pdf.drawString(50, y, ticket.ticket_number)
        pdf.drawString(180, y, ticket.status)
        pdf.drawString(
            270, y,
            f"${ticket.price_cents / 100:.2f}"
        )
        pdf.drawString(
            350, y,
            f"${ticket.commission_cents / 100:.2f}"
        )

        y -= 16

    pdf.save()
    output.seek(0)

    filename = f"tng_event_{event_id}_seller_{seller_id}_report.pdf"

    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
@router.get("/events/{event_id}/report.pdf")
def download_event_report_pdf(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    from app.matchmaker.models import BoxingEvent

    event = db.query(BoxingEvent).filter(BoxingEvent.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    sellers = seller_totals(db, event_id)

    tickets = db.query(IssuedTicket).filter(
        IssuedTicket.event_id == event_id
    ).all()

    tickets_sold = sum(
        1 for t in tickets if t.status != "refunded"
    )

    tickets_scanned = sum(
        1 for t in tickets if t.status == "used"
    )

    gross_sales_cents = sum(
        t.price_cents for t in tickets if t.status != "refunded"
    )

    commission_cents = sum(
        t.commission_cents for t in tickets if t.status != "refunded"
    )

    output = io.BytesIO()
    pdf = canvas.Canvas(output)

    pdf.setTitle(f"{event.name} - Master Ticket Sales Report")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 800, "TNG Promotions")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 775, event.name)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50, 750,
        f"Event Date: {event.event_date}"
    )
    pdf.drawString(
        50, 733,
        f"Venue: {event.venue}"
    )

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 695, "Event Totals")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50, 675,
        f"Tickets Sold: {tickets_sold}"
    )
    pdf.drawString(
        50, 658,
        f"Tickets Scanned: {tickets_scanned}"
    )
    pdf.drawString(
        50, 641,
        f"Gross Ticket Sales: ${gross_sales_cents / 100:.2f}"
    )
    pdf.drawString(
        50, 624,
        f"Total Commission Earned: ${commission_cents / 100:.2f}"
    )

    y = 585

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Seller")
    pdf.drawString(180, y, "Tickets")
    pdf.drawString(240, y, "Gross")
    pdf.drawString(330, y, "Commission")

    y -= 20

    pdf.setFont("Helvetica", 9)

    for seller in sellers:
        if y < 60:
            pdf.showPage()
            y = 800

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(50, y, "Seller")
            pdf.drawString(180, y, "Tickets")
            pdf.drawString(240, y, "Gross")
            pdf.drawString(330, y, "Commission")

            y -= 20
            pdf.setFont("Helvetica", 9)

        pdf.drawString(
            50, y,
            seller["display_name"][:24]
        )

        pdf.drawString(
            180, y,
            str(seller["tickets_sold"])
        )

        pdf.drawString(
            240, y,
            f"${seller['gross_sales_cents'] / 100:.2f}"
        )

        pdf.drawString(
            330, y,
            f"${seller['commission_cents'] / 100:.2f}"
        )

        y -= 18

    pdf.save()
    output.seek(0)

    filename = f"tng_event_{event_id}_master_report.pdf"

    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

@router.post("/events/{event_id}/ticket-types")
def create_event_ticket_type(
    event_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    name = str(data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ticket type name is required.")

    try:
        price_cents = int(data.get("price_cents"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Valid price_cents is required.")

    inventory = data.get("inventory")
    if inventory is not None:
        try:
            inventory = int(inventory)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Inventory must be an integer.")

    commission_type = str(data.get("commission_type") or "percent")
    commission_value = data.get("commission_value", 0)

    existing = (
        db.query(EventTicketType)
        .filter(
            EventTicketType.event_id == event_id,
            EventTicketType.name == name,
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=409, detail="Ticket type already exists.")

    row = EventTicketType(
        event_id=event_id,
        name=name,
        price_cents=price_cents,
        inventory=inventory,
        commission_type=commission_type,
        commission_value=commission_value,
        active=True,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "event_id": row.event_id,
        "name": row.name,
        "price_cents": row.price_cents,
        "inventory": row.inventory,
        "commission_type": row.commission_type,
        "commission_value": float(row.commission_value or 0),
        "active": row.active,
    }
