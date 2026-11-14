"""Read-only customer follow-up classification; never infers a decline from pending."""
import csv,io
from datetime import timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from app.database import get_db
from app.core.dependencies import staff_user
from app.matchmaker.models import BoxingEvent
from .models import TicketOrder,EventSeller
from .delivery import normalize_ticket_phone
router=APIRouter(prefix='/api/ticketing',tags=['Checkout follow-up'])
def phone_key(value):
    try:return normalize_ticket_phone(value)
    except ValueError:return ''
def paid_matches(orders):
    email_index={};phone_index={}
    for o in orders:
        if o.payment_status!='paid':continue
        email_index.setdefault(o.buyer_email.strip().casefold(),set()).add(o.id)
        phone=phone_key(o.buyer_phone)
        if phone:phone_index.setdefault(phone,set()).add(o.id)
    return {o.id:sorted(email_index.get(o.buyer_email.strip().casefold(),set())|phone_index.get(phone_key(o.buyer_phone),set())) for o in orders if o.payment_status in ('pending','failed')}
def followup_csv(db,event_id,include_completed=False):
    if not db.get(BoxingEvent,event_id):raise HTTPException(404,'Event not found')
    orders=db.query(TicketOrder).filter_by(event_id=event_id).order_by(TicketOrder.id).all();matches=paid_matches(orders)
    sellers={s.id:s.display_name for s in db.query(EventSeller).filter_by(event_id=event_id)}
    groups={}
    for o in orders:
        if o.payment_status not in ('pending','failed') or (matches[o.id] and not include_completed):continue
        groups.setdefault(o.buyer_email.strip().casefold(),[]).append(o)
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['Customer','Phone','Email','Unfinished order IDs','Receipts','Latest attempt (Oklahoma City)','Checkout values (USD; not paid revenue)','Fighter / seller','Payment review status','Other paid order IDs','Call guidance','Clover checkout references'])
    def safe(value):
        value=str(value or '')
        return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
    for email,group in groups.items():
        latest=group[-1];paid=sorted({i for o in group for i in matches[o.id]})
        guidance='Customer has another paid purchase. Do not request another payment.' if paid else 'Ask whether payment completed. If paid, obtain Clover receipt and verify before asking them to pay again.'
        if not latest.buyer_phone:guidance+=' No phone saved; email only.'
        writer.writerow([safe(x) for x in [latest.buyer_name,latest.buyer_phone,email,', '.join(str(o.id) for o in group),', '.join(o.receipt_number for o in group),latest.created_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d %I:%M %p CT'),', '.join(f'#{o.id}: ${o.total_cents/100:.2f}' for o in group),', '.join(sorted({sellers.get(o.seller_id,'Direct') for o in group})),'Another paid purchase exists' if paid else 'Payment failed' if all(o.payment_status=='failed' for o in group) else 'Payment not confirmed; outcome unknown',', '.join(map(str,paid)),guidance,', '.join(o.clover_checkout_id or 'No checkout reference' for o in group)]])
    return '\ufeff'+out.getvalue()
@router.get('/events/{event_id}/unfinished-customers.csv')
def download_followup(event_id:int,include_completed:bool=False,db=Depends(get_db),user=Depends(staff_user)):
    body=followup_csv(db,event_id,include_completed)
    return Response(body,media_type='text/csv',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="tng_event_{event_id}_customer_followup.csv"'})
