"""One public sales-portal URL across fighter shares, QR codes and phone texts."""
import os,re
from urllib.parse import quote,urlencode
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy import func
from app.database import get_db
from .models import EventSeller
from app.matchmaker.models import BoxingEvent
from .sales_access import sales_access
router=APIRouter(prefix='/api/ticketing',tags=['Public ticket portals'])
def public_sales_url(event_id,seller_code=None,source=None):
    base=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')
    path='/tickets/'+quote(seller_code,safe='') if seller_code else f'/events/{event_id}/tickets'
    return base+path+('?' + urlencode({'source':source}) if source else '')
@router.get('/public/sellers/{seller_code}/portal')
def resolve_portal(seller_code:str,response:Response,db=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',seller_code):raise HTTPException(404,'Ticket sales link not found')
    seller=db.query(EventSeller).filter(func.lower(EventSeller.public_code)==seller_code.lower()).first()
    if not seller:raise HTTPException(404,'Ticket sales link not found')
    # Resolve paused/cut-off links too; the existing event sales API enforces the current policy.
    return {'event_id':seller.event_id,'seller_code':seller.public_code,'seller_name':seller.display_name,'public_url':public_sales_url(seller.event_id,seller.public_code)}

def company_sellers(db,event_id):
    return db.query(EventSeller).filter(EventSeller.event_id==event_id,func.lower(func.trim(EventSeller.display_name))=='tng promotions').order_by(EventSeller.id).all()

@router.get('/public/events/{event_id}/phone-portal')
def resolve_phone_portal(event_id:int,response:Response,db=Depends(get_db)):
    if not db.get(BoxingEvent,event_id):raise HTTPException(404,'Event not found')
    companies=company_sellers(db,event_id)
    seller=next((s for s in companies if sales_access(db,event_id,s)['sales_open']),companies[0] if companies else None)
    response.headers['Cache-Control']='no-store'
    return {'event_id':event_id,'seller_code':seller.public_code if seller else None,'seller_name':seller.display_name if seller else None,'public_url':public_sales_url(event_id,seller.public_code if seller else None,source='phone')}
