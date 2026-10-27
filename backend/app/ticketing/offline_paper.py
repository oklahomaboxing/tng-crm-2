"""Owner-authorized admission stock, separate from paid cash sales."""
import json
from fastapi import HTTPException
from app.core.permissions import require_admin
from app.models import SecurityLog
from .models import PaperTicketBatch,PaperTicket

UNRECORDED=('allocated','released','offline_used')

def release_offline_stock(db,batch_id,user,expected_quantity):
    require_admin(user)
    db.query(PaperTicketBatch).filter_by(id=batch_id).update({PaperTicketBatch.quantity:PaperTicketBatch.quantity},synchronize_session=False)
    batch=db.get(PaperTicketBatch,batch_id)
    if not batch:raise HTTPException(404,'Batch not found')
    rows=db.query(PaperTicket).filter_by(batch_id=batch_id).populate_existing().all()
    if batch.quantity!=expected_quantity or len(rows)!=expected_quantity:raise HTTPException(409,'Batch quantity changed; review the stock before releasing')
    if any(t.status=='returned' for t in rows):raise HTTPException(409,'Returned stock cannot be released')
    if any(t.status not in (*UNRECORDED,'sold') for t in rows):raise HTTPException(409,'Ticket state requires review')
    changed=0
    for ticket in rows:
        if ticket.status=='allocated':ticket.status='released';changed+=1
    db.add(SecurityLog(user_id=user.id,action='PAPER_OFFLINE_STOCK_RELEASED',description=json.dumps({'batch_id':batch.id,'event_id':batch.event_id,'quantity_enabled':changed,'paid_sales_recorded':0,'reason':'Owner authorized admission before offline cash reconciliation'}),success=True))
    db.commit()
    return {'batch_id':batch.id,'newly_enabled':changed,'paid_sales_recorded':0}

def offline_admissions(db,event_id):
    return db.query(PaperTicket).join(PaperTicketBatch).filter(PaperTicketBatch.event_id==event_id,PaperTicket.status=='offline_used').count()
