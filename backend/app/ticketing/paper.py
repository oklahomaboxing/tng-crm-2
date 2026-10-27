"""Printable fighter allocations; no sale, commission or admission until recorded."""
import json
from datetime import datetime
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.dependencies import staff_user
from app.database import get_db
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent, BoxingEventPublication
from .paper_design import render_tickets
from .models import PaperTicketBatch, PaperTicket, EventSeller, EventTicketType, TicketOrder, IssuedTicket
from .security import make_raw_token, hash_token, encrypt_token, decrypt_token
from .service import generate_ticket_number, generate_receipt_number, seller_commission_cents

router = APIRouter(prefix='/api/ticketing', tags=['paper-tickets'])

class BatchCreate(BaseModel):
    seller_id: int
    ticket_type_id: int
    quantity: int = Field(ge=1, le=200, strict=True)
    request_key: UUID

class BatchSelection(BaseModel):
    ticket_ids: list[int] = Field(min_length=1, max_length=200)

class PaperSale(BatchSelection):
    confirm_total_cents: int = Field(ge=0, strict=True)


def batch_or_404(db, batch_id):
    batch = db.get(PaperTicketBatch, batch_id)
    if not batch:
        raise HTTPException(404, 'Paper ticket batch not found')
    return batch


def batch_summary(db, batch):
    counts = dict(db.query(PaperTicket.status, func.count(PaperTicket.id)).filter_by(
        batch_id=batch.id).group_by(PaperTicket.status).all())
    seller, kind = db.get(EventSeller, batch.seller_id), db.get(EventTicketType, batch.ticket_type_id)
    sold = counts.get('sold', 0)
    earned = db.query(func.coalesce(func.sum(IssuedTicket.commission_cents), 0)).join(
        PaperTicket, PaperTicket.order_id == IssuedTicket.order_id).filter(
        PaperTicket.batch_id == batch.id, IssuedTicket.status.in_(('valid', 'used'))).scalar()
    return {'id': batch.id, 'event_id': batch.event_id, 'seller_id': batch.seller_id,
        'seller_name': seller.display_name if seller else 'Unknown seller',
        'ticket_type_id': batch.ticket_type_id, 'ticket_type_name': kind.name if kind else 'Ticket',
        'quantity': batch.quantity, 'price_cents': batch.price_cents,
        'allocation_commission_estimate_cents': batch.commission_cents,
        'allocated': counts.get('allocated', 0), 'sold': sold, 'returned': counts.get('returned', 0),
        'sold_total_cents': sold * batch.price_cents, 'commission_cents': int(earned),
        'created_at': batch.created_at.isoformat()}


@router.get('/events/{event_id}/paper-batches')
def list_batches(event_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    if not db.get(BoxingEvent, event_id):
        raise HTTPException(404, 'Event not found')
    batches = db.query(PaperTicketBatch).filter_by(event_id=event_id).order_by(PaperTicketBatch.id.desc()).all()
    return {'batches': [batch_summary(db, b) for b in batches]}


@router.post('/events/{event_id}/paper-batches')
def create_batch(event_id: int, body: BatchCreate, db: Session = Depends(get_db), user=Depends(staff_user)):
    if not db.get(BoxingEvent, event_id):
        raise HTTPException(404, 'Event not found')
    # Serialize allocation against the ticket type. Recheck request key under this lock.
    kind = db.query(EventTicketType).filter_by(id=body.ticket_type_id, event_id=event_id, active=True).first()
    seller = db.query(EventSeller).filter_by(id=body.seller_id, event_id=event_id, active=True).first()
    if not kind or not seller:
        raise HTTPException(400, 'Select an active ticket type and seller for this event')
    db.query(EventTicketType).filter_by(id=kind.id).update({EventTicketType.active: EventTicketType.active}, synchronize_session=False)
    existing = db.query(PaperTicketBatch).filter_by(request_key=str(body.request_key)).first()
    if existing:
        if (existing.event_id, existing.seller_id, existing.ticket_type_id, existing.quantity) != (event_id, body.seller_id, body.ticket_type_id, body.quantity):
            raise HTTPException(409, 'This request key belongs to a different allocation')
        return batch_summary(db, existing)
    if kind.inventory is not None:
        sold = db.query(IssuedTicket).filter(IssuedTicket.ticket_type_id == kind.id, IssuedTicket.status.in_(('valid','used'))).count()
        held = db.query(PaperTicket).join(PaperTicketBatch).filter(PaperTicketBatch.ticket_type_id == kind.id, PaperTicket.status == 'allocated').count()
        if sold + held + body.quantity > kind.inventory:
            raise HTTPException(409, 'Not enough unallocated ticket inventory for this batch')
    commission = seller_commission_cents(db, kind, kind.price_cents, seller.id)
    if kind.price_cents < 0 or commission < 0 or commission > kind.price_cents:
        raise HTTPException(409, 'Ticket price or commission needs review before printing')
    batch = PaperTicketBatch(event_id=event_id, seller_id=seller.id, ticket_type_id=kind.id,
        quantity=body.quantity, price_cents=kind.price_cents, commission_cents=commission,
        request_key=str(body.request_key), created_by_user_id=user.id)
    try:
        db.add(batch); db.flush()
        for _ in range(body.quantity):
            number = generate_ticket_number(event_id)
            raw = make_raw_token(event_id, number)
            db.add(PaperTicket(batch_id=batch.id, ticket_number=number,
                qr_token_hash=hash_token(raw), qr_token_encrypted=encrypt_token(raw)))
        db.add(SecurityLog(user_id=user.id, action='PAPER_TICKET_BATCH_CREATED',
            description=f'Event {event_id}; batch {batch.id}; seller {seller.id}; quantity {body.quantity}', success=True))
        db.commit()
    except (ValueError, RuntimeError, IntegrityError):
        db.rollback()
        raise HTTPException(409, 'Allocation could not be created. Refresh batches before retrying with the same request key.')
    return batch_summary(db, batch)


@router.get('/paper-batches/{batch_id}')
def get_batch(batch_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    batch = batch_or_404(db, batch_id)
    return {**batch_summary(db, batch), 'tickets': [{'id': t.id, 'ticket_number': t.ticket_number,
        'status': t.status, 'order_id': t.order_id} for t in db.query(PaperTicket).filter_by(batch_id=batch_id).order_by(PaperTicket.id).all()]}


def selection(db, batch_id, ids):
    if len(set(ids)) != len(ids):
        raise HTTPException(400, 'Select each ticket only once')
    # Batch lock serializes staff actions, including repeat sale submissions.
    db.query(PaperTicketBatch).filter_by(id=batch_id).update({PaperTicketBatch.quantity: PaperTicketBatch.quantity}, synchronize_session=False)
    rows = db.query(PaperTicket).filter(PaperTicket.batch_id == batch_id, PaperTicket.id.in_(ids)).populate_existing().order_by(PaperTicket.id).all()
    if len(rows) != len(ids):
        raise HTTPException(400, 'One or more selected tickets do not belong to this batch')
    return rows


@router.post('/paper-batches/{batch_id}/record-sales')
def record_sales(batch_id: int, body: PaperSale, db: Session = Depends(get_db), user=Depends(staff_user)):
    batch = batch_or_404(db, batch_id)
    rows = selection(db, batch_id, body.ticket_ids)
    if body.confirm_total_cents != len(rows) * batch.price_cents:
        raise HTTPException(409, 'Confirm the full face value of the selected tickets')
    if any(t.status == 'returned' for t in rows):
        raise HTTPException(409, 'Returned tickets cannot be activated or sold')
    kind = db.get(EventTicketType, batch.ticket_type_id)
    commission = seller_commission_cents(db, kind, batch.price_cents, batch.seller_id)
    if not 0 <= commission <= batch.price_cents:
        raise HTTPException(409, 'Current commission terms need review before recording the sale')
    recorded = 0
    for t in rows:
        if t.status == 'sold':
            continue  # Exact replay never creates another order or commission.
        if t.status != 'allocated':
            raise HTTPException(409, 'Ticket state requires review')
        now = datetime.utcnow()
        order = TicketOrder(event_id=batch.event_id, seller_id=batch.seller_id,
            buyer_name='Paper ticket customer', buyer_email='', buyer_phone='',
            subtotal_cents=batch.price_cents, fee_cents=0, total_cents=batch.price_cents,
            payment_provider='paper_cash', payment_status='paid', payment_id=f'PAPER-CASH-{t.id}',
            receipt_number=generate_receipt_number(batch.event_id), paid_at=now,
            items_json=json.dumps([{'ticket_type_id': batch.ticket_type_id, 'quantity':1,
                'price_cents': batch.price_cents, 'commission_cents': commission}]))
        db.add(order); db.flush()
        db.add(IssuedTicket(order_id=order.id, event_id=batch.event_id, ticket_type_id=batch.ticket_type_id,
            seller_id=batch.seller_id, ticket_number=t.ticket_number, qr_token_hash=t.qr_token_hash,
            qr_token_encrypted=t.qr_token_encrypted, status='valid', price_cents=batch.price_cents,
            commission_cents=commission))
        t.status='sold';t.order_id=order.id;t.sold_at=now;recorded+=1
    db.add(SecurityLog(user_id=user.id, action='PAPER_TICKET_SALES_RECORDED',
        description=f'Batch {batch_id}; new sales {recorded}; staff attested customer cash payment. Not fighter remittance.', success=True))
    db.commit()
    return {**batch_summary(db, batch), 'new_sales_recorded':recorded}


@router.post('/paper-batches/{batch_id}/return-unsold')
def return_unsold(batch_id: int, body: BatchSelection, db: Session = Depends(get_db), user=Depends(staff_user)):
    batch = batch_or_404(db, batch_id)
    rows = selection(db, batch_id, body.ticket_ids)
    if any(t.status == 'sold' for t in rows):
        raise HTTPException(409, 'A sold ticket cannot be returned through the unsold-ticket flow')
    for t in rows:
        t.status='returned';t.returned_at=t.returned_at or datetime.utcnow()
    db.add(SecurityLog(user_id=user.id, action='PAPER_TICKETS_RETURNED', description=f'Batch {batch_id}; ticket IDs {body.ticket_ids}',success=True))
    db.commit()
    return batch_summary(db, batch)


@router.get('/paper-batches/{batch_id}/print.pdf')
def print_batch(batch_id: int, layout: Literal['fight-night'] = 'fight-night', db: Session = Depends(get_db), user=Depends(staff_user)):
    batch = batch_or_404(db, batch_id)
    event = db.get(BoxingEvent, batch.event_id)
    seller, kind = db.get(EventSeller, batch.seller_id), db.get(EventTicketType, batch.ticket_type_id)
    tickets = db.query(PaperTicket).filter(PaperTicket.batch_id == batch_id, PaperTicket.status != 'returned').order_by(PaperTicket.id).all()
    if not tickets:
        raise HTTPException(409, 'All tickets in this batch have been returned')
    items=[{'number':t.ticket_number,'raw':decrypt_token(t.qr_token_encrypted),'status':t.status} for t in tickets]
    content=render_tickets(event,seller.display_name,kind.name,batch.price_cents,items,layout,
        schedule=event_schedule(db,event.id),batch_id=batch.id)
    return Response(content,media_type='application/pdf',headers={
        'Content-Disposition':f'attachment; filename="TNG-event-{batch.event_id}-paper-batch-{batch.id}.pdf"',
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


def event_schedule(db,event_id):
    publication=db.query(BoxingEventPublication).filter_by(event_id=event_id).first()
    if not publication:return ''
    def clock(value):
        try:return datetime.strptime(value,'%H:%M').strftime('%I:%M %p').lstrip('0')
        except ValueError:return value
    return '  |  '.join(label+clock(value) for label,value in [('Doors: ',publication.doors_time),('First bout: ',publication.first_bout_time)] if value)


@router.get('/events/{event_id}/paper-ticket-preview.pdf')
def preview_design(event_id:int,ticket_type_id:int,seller_id:int | None=None,
    layout:Literal['fight-night']='fight-night',db:Session=Depends(get_db),user=Depends(staff_user)):
    event=db.get(BoxingEvent,event_id)
    if not event:raise HTTPException(404,'Event not found')
    kind=db.get(EventTicketType,ticket_type_id)
    if not kind or kind.event_id!=event_id:raise HTTPException(404,'Ticket type not found for this event')
    seller=db.get(EventSeller,seller_id) if seller_id else None
    if seller_id and (not seller or seller.event_id!=event_id):raise HTTPException(404,'Seller not found for this event')
    count=4
    items=[{'number':f'SAMPLE-{n+1:04d}','raw':'TNG-DESIGN-PREVIEW-NOT-VALID','status':'sample'} for n in range(count)]
    content=render_tickets(event,seller.display_name if seller else 'TNG Boxing',kind.name,kind.price_cents,items,
        layout,schedule=event_schedule(db,event_id),sample=True)
    return Response(content,media_type='application/pdf',headers={
        'Content-Disposition':f'attachment; filename="TNG-event-{event_id}-design-preview.pdf"',
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
