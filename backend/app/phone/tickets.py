"""Caller-requested secure ticket purchase links; no card collection or payment assertions."""
import hashlib,os,json
from datetime import datetime,timedelta
from urllib.parse import urlencode
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from sqlalchemy import Column,Integer,String,Text,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.ticketing.delivery import normalize_ticket_phone
from app.services.sms_service import ensure_stop_footer
from .routes import verified,config,get_call,gather,transfer,transfer_for,xml,say,PhoneCall,url
from .facts import ticket_events

router=APIRouter(prefix='/api/phone',tags=['Phone ticket checkout'])
NOTICE='Caller pressed 1 to request one TNG Boxing ticket checkout link by SMS. Message and data rates may apply. Reply STOP to unsubscribe. This is not marketing consent.'

class PhoneTicketContext(Base):
    __tablename__='phone_ticket_contexts'
    call_sid=Column(String(80),ForeignKey('phone_assistant_calls.call_sid'),primary_key=True)
    options_json=Column(Text,default='[]',nullable=False)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=True)
    phone=Column(String(40),nullable=True)

class PhoneTicketSmsRoute(Base):
    __tablename__='phone_ticket_sms_routes'
    id=Column(Integer,primary_key=True)
    account_sid=Column(String(80),nullable=False)
    from_number=Column(String(40),nullable=False)
    service_sid=Column(String(80),nullable=False)

class PhoneTicketDelivery(Base):
    __tablename__='phone_ticket_deliveries'
    __table_args__=(UniqueConstraint('call_sid','event_id',name='uq_phone_ticket_link_call_event'),)
    id=Column(Integer,primary_key=True)
    call_sid=Column(String(80),ForeignKey('phone_assistant_calls.call_sid'),nullable=False)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False)
    phone=Column(String(40),nullable=False)
    consent_notice=Column(Text,nullable=False)
    status=Column(String(30),default='submitting',nullable=False)
    provider_id=Column(String(100),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class PhoneTicketRate(Base):
    __tablename__='phone_ticket_rate_limits'
    phone_hash=Column(String(64),primary_key=True)
    window_start=Column(DateTime,nullable=False)
    count=Column(Integer,default=0,nullable=False)


def sms_route(db):
    row=db.get(PhoneTicketSmsRoute,1)
    return row if row and row.account_sid==os.getenv('TWILIO_ACCOUNT_SID') and row.from_number==os.getenv('TWILIO_PHONE_NUMBER') else None

@router.post('/admin/ticket-links/connect')
def connect_links(db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    from app.marketing.sms import approved_routes
    service=approved_routes().get('notification')
    if not service:raise HTTPException(409,'An approved ticket/account-notification SMS service is required')
    row=db.get(PhoneTicketSmsRoute,1)
    if not row:row=PhoneTicketSmsRoute(id=1);db.add(row)
    row.account_sid=os.environ['TWILIO_ACCOUNT_SID'];row.from_number=os.environ['TWILIO_PHONE_NUMBER'];row.service_sid=service;db.commit()
    return {'ticket_links_ready':True}


def context(db,call):
    row=db.get(PhoneTicketContext,call.call_sid)
    if not row:row=PhoneTicketContext(call_sid=call.call_sid,options_json='[]');db.add(row);db.flush()
    return row


def consent_prompt(db,call,cfg):
    ctx=context(db,call)
    if not ctx.phone:
        call.stage='ticket_phone';db.commit()
        return gather('Please enter the ten digit mobile number where you want the secure ticket checkout link.','tickets/phone',input='dtmf',digits=10,cfg=cfg)
    call.stage='ticket_consent';db.commit()
    return gather(f'I can text a secure ticket checkout link to the number ending {" ".join(ctx.phone[-4:])}. Press 1 to request this one text, or press 2 to enter a different mobile number. Message and data rates may apply. Reply STOP to unsubscribe. Press 0 for staff.','tickets/confirm',input='dtmf',cfg=cfg)


def offer_events(db,call,cfg):
    events=ticket_events(db)
    if not cfg.ticket_links_enabled or not sms_route(db) or not events:
        return gather('Phone ticket links are not available right now. Please press 0 for staff.','menu',cfg=cfg)
    ctx=context(db,call);ctx.options_json=json.dumps([e.id for e,p,s in events])
    if len(events)==1:
        ctx.event_id=events[0][0].id
        ctx.phone=call.caller_phone if call.caller_phone not in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')) else None
        db.commit();return consent_prompt(db,call,cfg)
    call.stage='ticket_choice';db.commit()
    text='Choose your event. '+' '.join(f'Press {i} for {p.public_title or e.name} on {e.event_date}.' for i,(e,p,s) in enumerate(events,1))+' Press 0 for staff.'
    return gather(text,'tickets/event',input='dtmf',cfg=cfg)

@router.post('/tickets/event')
async def choose_event(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    if form.get('Digits')=='0':return transfer_for(db,call,cfg)
    ctx=context(db,call)
    if call.stage!='ticket_choice':db.commit();return offer_events(db,call,cfg)
    try:event_id=json.loads(ctx.options_json)[int(form.get('Digits',''))-1];assert int(form['Digits'])>0
    except (ValueError,IndexError,AssertionError):db.commit();return offer_events(db,call,cfg)
    if event_id not in {e.id for e,p,s in ticket_events(db)}:db.commit();return offer_events(db,call,cfg)
    ctx.event_id=event_id;ctx.phone=call.caller_phone if call.caller_phone not in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')) else None
    db.commit();return consent_prompt(db,call,cfg)

@router.post('/tickets/phone')
async def choose_phone(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    if form.get('Digits')=='0':return transfer_for(db,call,cfg)
    ctx=context(db,call)
    if call.stage!='ticket_phone' or not ctx.event_id:db.commit();return offer_events(db,call,cfg)
    try:
        phone=normalize_ticket_phone(form.get('Digits'))
        if not phone or phone in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')):raise ValueError()
    except ValueError:
        call.empty_attempts+=1;db.commit()
        if call.empty_attempts>=3:return transfer(cfg)
        return consent_prompt(db,call,cfg)
    ctx.phone=phone;call.empty_attempts=0;db.commit();return consent_prompt(db,call,cfg)


def claim_rate(db,phone):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    key=hashlib.sha256(phone.encode()).hexdigest();now=datetime.utcnow()
    insert=pg_insert if db.bind.dialect.name=='postgresql' else sqlite_insert
    db.execute(insert(PhoneTicketRate.__table__).values(phone_hash=key,window_start=now,count=0).on_conflict_do_nothing(index_elements=['phone_hash']))
    rate=db.query(PhoneTicketRate).filter_by(phone_hash=key).with_for_update().one()
    if rate.window_start<now-timedelta(hours=1):rate.window_start=now;rate.count=0
    if rate.count>=3:return False
    rate.count+=1;return True

@router.post('/tickets/confirm')
async def confirm_link(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form);ctx=context(db,call)
    if form.get('Digits')=='0':return transfer_for(db,call,cfg)
    if call.stage!='ticket_consent' or not ctx.event_id or not ctx.phone:db.commit();return offer_events(db,call,cfg)
    if form.get('Digits')=='2':ctx.phone=None;db.commit();return consent_prompt(db,call,cfg)
    if form.get('Digits')!='1':
        call.empty_attempts+=1;db.commit()
        return transfer(cfg) if call.empty_attempts>=3 else consent_prompt(db,call,cfg)
    route=sms_route(db)
    event=next(((e,p,s) for e,p,s in ticket_events(db) if e.id==ctx.event_id),None)
    if not cfg.ticket_links_enabled or not route or not event:db.commit();return gather('That ticket link is not currently available. Press 0 for staff.','menu',cfg=cfg)
    from app.marketing.sms import blocked_sms_numbers,number_blocked
    if number_blocked(ctx.phone,blocked_sms_numbers(db)):
        db.commit();return gather('This mobile number has opted out of text messages. Please visit the TNGOS ticket website or press 0 for staff.','menu',cfg=cfg)
    existing=db.query(PhoneTicketDelivery).filter_by(call_sid=call.call_sid,event_id=ctx.event_id).first()
    if existing:
        db.commit()
        message=('The earlier text could not be delivered. Please use the website or press 0 for staff.' if existing.status in ('failed','undelivered') else 'A link was already requested during this call. Please check your messages or press 0 for staff.')
        return gather(message,'menu',cfg=cfg)
    if not claim_rate(db,ctx.phone):db.commit();return gather('Too many ticket links have been requested for this number. Please use the website or press 0 for staff.','menu',cfg=cfg)
    delivery=PhoneTicketDelivery(call_sid=call.call_sid,event_id=ctx.event_id,phone=ctx.phone,consent_notice=NOTICE,status='submitting')
    db.add(delivery)
    try:db.commit()
    except IntegrityError:db.rollback();return gather('A link was already requested. Please check your messages.','menu',cfg=cfg)
    e,p,s=event
    query={'source':'phone'}
    if s:query['seller']=s.public_code
    link=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+f'/events/{e.id}/tickets?'+urlencode(query)
    text=ensure_stop_footer(f'TNG Boxing: You requested tickets for {e.name}. Choose your tickets and pay securely through Clover here: {link} Tickets are issued after payment confirmation.')
    try:
        client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=5))
        sent=client.messages.create(to=delivery.phone,from_=route.from_number,messaging_service_sid=route.service_sid,body=text,status_callback=url('tickets/sms-status')+'?'+urlencode({'delivery_id':delivery.id}))
        db.refresh(delivery)
        delivery.provider_id=delivery.provider_id or sent.sid
        if delivery.status not in ('delivered','failed','undelivered'):delivery.status='accepted'
        call.stage='ticket_link_submitted';db.commit()
        return gather('Your ticket checkout link is on its way. Open it to choose your tickets and pay securely through Clover. Your tickets are issued after payment is confirmed. '+ 'For another option, press 9 for the menu or 0 for staff.','menu',cfg=cfg)
    except Exception as exc:
        delivery.status='failed' if getattr(exc,'code',None) else 'unknown'
        if str(getattr(exc,'code',''))=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,delivery.phone)
        db.commit()
        return gather('We could not confirm the text submission. Please use the TNGOS ticket website or press 0 for staff.','menu',cfg=cfg)

@router.post('/tickets/sms-status')
async def sms_status(request:Request,delivery_id:int,db:Session=Depends(get_db)):
    from app.marketing.sms import validate_webhook
    form=await validate_webhook(request)
    delivery=db.query(PhoneTicketDelivery).filter_by(id=delivery_id).with_for_update().one_or_none()
    if not delivery:raise HTTPException(404,'Ticket link delivery not found')
    if not delivery.provider_id and delivery.status in ('submitting','unknown') and form.get('To')==delivery.phone and form.get('From')==os.getenv('TWILIO_PHONE_NUMBER'):
        delivery.provider_id=form.get('MessageSid')
    if form.get('MessageSid')!=delivery.provider_id:raise HTTPException(403,'Message reference does not match')
    status=str(form.get('MessageStatus',''))
    if status in ('queued','sent','delivered','failed','undelivered') and delivery.status not in ('delivered','failed','undelivered'):
        delivery.status=status
        if str(form.get('ErrorCode',''))=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,delivery.phone)
        db.commit()
    return Response(status_code=204)
