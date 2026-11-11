"""Staff inbox for verified inbound texts and explicit one-to-one service replies."""
import os,re
from datetime import datetime,timedelta
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from fastapi.responses import JSONResponse,Response
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,String,Text,DateTime,ForeignKey,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import Base,get_db
from app.core.dependencies import staff_user
from app.models import User
from app.marketing.sms import validate_webhook,blocked_sms_numbers,number_blocked,approved_routes
from app.ticketing.delivery import normalize_ticket_phone
from app.services.sms_service import ensure_stop_footer
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient

router=APIRouter(prefix='/api/messages',tags=['Text Inbox'])
CONTROL={'STOP','STOPALL','UNSUBSCRIBE','CANCEL','END','QUIT','START','UNSTOP','HELP'}
class InboxMessage(Base):
    __tablename__='sms_inbox_messages'
    id=Column(Integer,primary_key=True)
    provider_id=Column(String(80),nullable=True,unique=True)
    request_key=Column(String(80),nullable=True,unique=True)
    phone=Column(String(40),nullable=False,index=True)
    line=Column(String(40),nullable=False)
    direction=Column(String(12),nullable=False)
    body=Column(Text,nullable=False)
    command=Column(String(30),nullable=True)
    media_count=Column(Integer,default=0,nullable=False)
    status=Column(String(30),nullable=False)
    error_code=Column(String(40),nullable=True)
    staff_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
    read_at=Column(DateTime,nullable=True)

def base():return os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
def stamp(value):return value.isoformat()+'Z' if value else None
def response(data):return JSONResponse(data,headers={'Cache-Control':'private, no-store'})
def phone_value(value):
    try:
        phone=normalize_ticket_phone(value)
        if not phone:raise ValueError()
        return phone
    except ValueError:raise HTTPException(400,'Enter a valid mobile number')

def capture(db,form):
    phone=phone_value(form.get('From'));line=phone_value(form.get('To'))
    if line!=os.getenv('TWILIO_PHONE_NUMBER'):raise HTTPException(403,'Text was not sent to the assigned inbox number')
    sid=str(form.get('MessageSid') or '')
    if not re.fullmatch(r'(?:SM|MM)[0-9a-fA-F]{32}',sid):raise HTTPException(400,'Invalid message reference')
    command=str(form.get('OptOutType') or form.get('Body') or '').strip().upper()
    try:media=max(0,min(int(form.get('NumMedia','0')),10))
    except (ValueError,TypeError):media=0
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=pg_insert if db.bind.dialect.name=='postgresql' else sqlite_insert
    db.execute(insert(InboxMessage.__table__).values(provider_id=sid,phone=phone,line=line,direction='inbound',body=str(form.get('Body') or '')[:4000],command=command if command in CONTROL else None,media_count=media,status='received',created_at=datetime.utcnow()).on_conflict_do_nothing(index_elements=['provider_id']))

def allowed(db,phone):
    if number_blocked(phone,blocked_sms_numbers(db)):return False,'This number opted out. The customer must text START before replies can resume.'
    latest=db.query(InboxMessage).filter_by(phone=phone,direction='inbound').order_by(InboxMessage.id.desc()).first()
    if not latest or latest.line!=os.getenv('TWILIO_PHONE_NUMBER') or latest.command or latest.created_at<datetime.utcnow()-timedelta(days=7):return False,'A recent customer message is required for a service reply. Ask the customer to text their question.'
    return True,None

def serialize(row):return {'id':row.id,'direction':row.direction,'body':row.body,'command':row.command,'media_count':row.media_count,'status':row.status,'error_code':row.error_code,'created_at':stamp(row.created_at),'read_at':stamp(row.read_at)}

@router.get('')
def inbox(q:str=Query('',max_length=40),unread_only:bool=False,page:int=Query(1,ge=1),db:Session=Depends(get_db),user=Depends(staff_user)):
    grouped=db.query(InboxMessage.phone.label('phone'),func.max(InboxMessage.id).label('latest')).group_by(InboxMessage.phone).subquery()
    query=db.query(InboxMessage).join(grouped,InboxMessage.id==grouped.c.latest)
    unread=db.query(InboxMessage.phone).filter(InboxMessage.direction=='inbound',InboxMessage.read_at.is_(None))
    if q.strip():query=query.filter(InboxMessage.phone.contains(re.sub(r'[^0-9+]','',q) or 'INVALID'))
    if unread_only:query=query.filter(InboxMessage.phone.in_(unread))
    total=query.count();rows=query.order_by(InboxMessage.id.desc()).offset((page-1)*25).limit(25).all()
    counts=dict(db.query(InboxMessage.phone,func.count(InboxMessage.id)).filter(InboxMessage.direction=='inbound',InboxMessage.read_at.is_(None),InboxMessage.phone.in_([r.phone for r in rows])).group_by(InboxMessage.phone).all()) if rows else {}
    return response({'number':os.getenv('TWILIO_PHONE_NUMBER',''),'total':total,'page_size':25,'unread_messages':unread.count(),'conversations':[{'phone':r.phone,'latest':serialize(r),'unread':counts.get(r.phone,0)} for r in rows]})

@router.get('/thread')
def thread(phone:str,before:int|None=Query(None,ge=1),db:Session=Depends(get_db),user=Depends(staff_user)):
    phone=phone_value(phone);query=db.query(InboxMessage).filter_by(phone=phone)
    if before:query=query.filter(InboxMessage.id<before)
    rows=query.order_by(InboxMessage.id.desc()).limit(101).all();more=len(rows)>100;rows=list(reversed(rows[:100]))
    can_reply,reason=allowed(db,phone)
    return response({'phone':phone,'messages':[serialize(r) for r in rows],'has_more':more,'can_reply':can_reply,'reply_blocked_reason':reason})

class ReadMessages(BaseModel):
    phone:str
    through_id:int=Field(ge=1)
@router.post('/read')
def mark_read(body:ReadMessages,db:Session=Depends(get_db),user=Depends(staff_user)):
    phone=phone_value(body.phone)
    db.query(InboxMessage).filter(InboxMessage.phone==phone,InboxMessage.id<=body.through_id,InboxMessage.direction=='inbound',InboxMessage.read_at.is_(None)).update({'read_at':datetime.utcnow()},synchronize_session=False);db.commit()
    return {'marked_read':True}

class Reply(BaseModel):
    phone:str
    message:str=Field(min_length=1,max_length=1200)
    request_key:UUID
    service_reply:bool=False
@router.post('/reply')
def reply(body:Reply,db:Session=Depends(get_db),user=Depends(staff_user)):
    if not body.service_reply:raise HTTPException(400,'Confirm this answers their account, membership or ticket question and is not a promotion')
    phone=phone_value(body.phone);text=body.message.strip()
    if not text:raise HTTPException(400,'Enter a reply')
    text=ensure_stop_footer('TNG Boxing: '+text)
    # Serialize staff submissions to enforce limits and durable idempotency.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    previous=db.query(InboxMessage).filter_by(request_key=str(body.request_key)).first()
    if previous:
        if previous.phone!=phone or previous.body!=text or previous.staff_id!=user.id:raise HTTPException(409,'Reply key already belongs to a different submission')
        return response({'message':serialize(previous),'already_submitted':True})
    can_reply,reason=allowed(db,phone)
    if not can_reply:raise HTTPException(409,reason)
    count=db.query(InboxMessage).filter(InboxMessage.staff_id==user.id,InboxMessage.created_at>=datetime.utcnow()-timedelta(hours=1)).count()
    if count>=30:raise HTTPException(429,'Reply limit reached. Try again later.')
    service=approved_routes().get('notification')
    if not service:raise HTTPException(409,'An approved account-notification SMS service is required')
    row=InboxMessage(request_key=str(body.request_key),phone=phone,line=os.environ['TWILIO_PHONE_NUMBER'],direction='outbound',body=text,status='submitting',staff_id=user.id)
    db.add(row)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'This reply was already submitted. Refresh the conversation.')
    try:
        client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=8))
        sent=client.messages.create(to=phone,from_=row.line,messaging_service_sid=service,body=text,status_callback=base()+f'/api/messages/status?message_id={row.id}')
        row=db.query(InboxMessage).filter_by(id=row.id).with_for_update().populate_existing().one();row.provider_id=row.provider_id or sent.sid
        if row.status not in ('delivered','failed','undelivered'):row.status='accepted'
        db.commit()
    except Exception as exc:
        message_id=row.id;db.rollback()
        row=db.query(InboxMessage).filter_by(id=message_id).with_for_update().populate_existing().one()
        if row.status not in ('delivered','failed','undelivered'):
            row.status='failed' if getattr(exc,'code',None) else 'unknown';row.error_code=str(getattr(exc,'code',''))[:40] or 'submission_unknown'
        if str(getattr(exc,'code',''))=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,phone)
        db.commit()
    return response({'message':serialize(row),'already_submitted':False})

@router.post('/status')
async def status(request:Request,message_id:int,db:Session=Depends(get_db)):
    form=await validate_webhook(request)
    row=db.query(InboxMessage).filter_by(id=message_id,direction='outbound').with_for_update().one_or_none()
    if not row:raise HTTPException(404,'Reply not found')
    sid=str(form.get('MessageSid') or '')
    if not re.fullmatch(r'SM[0-9a-fA-F]{32}',sid):raise HTTPException(400,'Invalid message reference')
    if not row.provider_id and row.status in ('submitting','unknown') and form.get('To')==row.phone and form.get('From')==row.line:row.provider_id=sid
    if row.provider_id!=sid:raise HTTPException(403,'Message reference does not match')
    state=str(form.get('MessageStatus',''))
    if state in ('queued','sent','delivered','failed','undelivered') and row.status not in ('delivered','failed','undelivered'):
        row.status=state;row.error_code=str(form.get('ErrorCode') or '')[:40] or None
        if row.error_code=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,row.phone)
    db.commit();return Response(status_code=204)
