"""Caller-requested existing membership registration/waiver link; no enrollment by phone."""
import os,re
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from sqlalchemy import Column,String,Text,DateTime,ForeignKey
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from app.database import Base,get_db
from app.ticketing.delivery import normalize_ticket_phone
from app.services.sms_service import ensure_stop_footer
from .routes import verified,config,get_call,gather,transfer_for,url,PhoneCall
from .tickets import sms_route,claim_rate
from .tracking import activity
router=APIRouter(prefix='/api/phone/signup',tags=['Phone membership signup'])
NOTICE='Caller pressed 1 to request one TNG Boxing registration and waiver link by SMS. Message and data rates may apply. Reply STOP to unsubscribe. This is not marketing consent.'
class PhoneSignupLink(Base):
    __tablename__='phone_signup_links'
    call_sid=Column(String(80),ForeignKey('phone_assistant_calls.call_sid'),primary_key=True)
    phone=Column(String(40),nullable=True)
    status=Column(String(30),nullable=True)
    provider_id=Column(String(80),nullable=True,unique=True)
    consent_notice=Column(Text,nullable=True)
    submitted_at=Column(DateTime,nullable=True)

def link():return os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/register?source=phone'
def context(db,call):
    row=db.get(PhoneSignupLink,call.call_sid)
    if not row:row=PhoneSignupLink(call_sid=call.call_sid);db.add(row);db.flush()
    return row

def prompt(db,call,cfg):
    ctx=context(db,call)
    if not ctx.phone:
        call.stage='signup_phone';db.commit()
        return gather('Please enter your ten digit mobile number to receive the TNG Boxing registration and waiver link. Press 0 for staff.','signup/phone',input='dtmf',digits=10,cfg=cfg)
    call.stage='signup_consent';db.commit()
    return gather(f'To sign up now, I can text our membership registration and waiver page to the number ending {" ".join(ctx.phone[-4:])}. Press 1 to request this one text, or press 2 to enter a different mobile number. Message and data rates may apply. Reply STOP to unsubscribe. Press 0 for staff.','signup/confirm',input='dtmf',cfg=cfg)

def offer_signup(db,call,cfg):
    if not cfg.enabled:return transfer_for(db,call,cfg)
    if not cfg.signup_links_enabled or not sms_route(db):
        db.commit();return gather('Signup texts are unavailable right now. You can register at tngos dot tngboxinggym dot com slash register, or press 0 for staff.','menu',cfg=cfg)
    ctx=context(db,call)
    if ctx.status:
        message='Your signup link was already requested during this call. Please check your texts or press 0 for staff.'
        if ctx.status in ('failed','undelivered','unknown'):message='We could not confirm delivery of your earlier signup text. Please use our registration website or press 0 for staff.'
        db.commit();return gather(message,'menu',cfg=cfg)
    ctx.phone=call.caller_phone if call.caller_phone not in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')) else None
    call.empty_attempts=0
    activity(db,call,'menu_choice','Sign up now');db.commit()
    return prompt(db,call,cfg)

@router.post('/phone')
async def choose_phone(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    if not cfg.enabled or form.get('Digits')=='0':return transfer_for(db,call,cfg)
    ctx=context(db,call)
    if not cfg.signup_links_enabled or call.stage!='signup_phone' or ctx.status:return offer_signup(db,call,cfg)
    try:
        phone=normalize_ticket_phone(form.get('Digits'))
        if not phone or phone in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')):raise ValueError()
    except ValueError:
        call.empty_attempts+=1
        if call.empty_attempts>=3:return transfer_for(db,call,cfg)
        db.commit();return prompt(db,call,cfg)
    ctx.phone=phone;call.empty_attempts=0;db.commit();return prompt(db,call,cfg)

@router.post('/confirm')
async def confirm(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form);ctx=context(db,call)
    if not cfg.enabled or form.get('Digits')=='0':return transfer_for(db,call,cfg)
    route=sms_route(db)
    if not cfg.signup_links_enabled or not route or ctx.status or call.stage!='signup_consent' or not ctx.phone:return offer_signup(db,call,cfg)
    if form.get('Digits')=='2':ctx.phone=None;call.empty_attempts=0;db.commit();return prompt(db,call,cfg)
    if form.get('Digits')!='1':
        call.empty_attempts+=1
        if call.empty_attempts>=3:return transfer_for(db,call,cfg)
        db.commit();return prompt(db,call,cfg)
    from app.marketing.sms import blocked_sms_numbers,number_blocked
    if number_blocked(ctx.phone,blocked_sms_numbers(db)):
        db.commit();return gather('This mobile number has opted out of texts. Please use our registration website, or press 0 for staff.','menu',cfg=cfg)
    if not claim_rate(db,ctx.phone):
        db.commit();return gather('Too many links have been requested for this number. Please use our registration website, or press 0 for staff.','menu',cfg=cfg)
    ctx.status='submitting';ctx.consent_notice=NOTICE;ctx.submitted_at=datetime.utcnow();call.stage='signup_link_submitting'
    activity(db,call,'signup_text','Requested');db.commit()
    text=ensure_stop_footer(f'TNG Boxing: Here is the membership signup link you requested: {link()} Complete your registration, participation waiver and signature, then continue to secure Clover checkout. Sending this link does not activate a membership.')
    try:
        client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=5))
        sent=client.messages.create(to=ctx.phone,from_=route.from_number,messaging_service_sid=route.service_sid,body=text,status_callback=url('signup/status')+'?call_sid='+call.call_sid)
        call=db.query(PhoneCall).filter_by(call_sid=call.call_sid).with_for_update().populate_existing().one()
        ctx=db.query(PhoneSignupLink).filter_by(call_sid=call.call_sid).with_for_update().populate_existing().one();ctx.provider_id=ctx.provider_id or sent.sid
        if ctx.status not in ('delivered','failed','undelivered'):ctx.status='accepted'
        call.stage='signup_link_submitted';activity(db,call,'signup_text','Provider accepted');db.commit()
        return gather('Your signup link is on its way. Open it to choose a membership and complete the registration, waiver and secure checkout. Your membership is activated after payment is confirmed. For anything else, say a topic or press 0 for staff.','menu',cfg=cfg)
    except Exception as exc:
        sid=call.call_sid;db.rollback();call=db.query(PhoneCall).filter_by(call_sid=sid).with_for_update().populate_existing().one();ctx=db.query(PhoneSignupLink).filter_by(call_sid=sid).with_for_update().populate_existing().one()
        if ctx.status not in ('delivered','failed','undelivered'):ctx.status='failed' if getattr(exc,'code',None) else 'unknown'
        if str(getattr(exc,'code',''))=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,ctx.phone)
        call.stage='signup_link_'+ctx.status;activity(db,call,'signup_text','Submission '+ctx.status);db.commit()
        return gather('We could not confirm your signup text submission. Please use our registration website or press 0 for staff.','menu',cfg=cfg)

@router.post('/status')
async def status(request:Request,call_sid:str,db:Session=Depends(get_db)):
    from app.marketing.sms import validate_webhook
    form=await validate_webhook(request)
    call=db.query(PhoneCall).filter_by(call_sid=call_sid).with_for_update().one_or_none()
    if not call:raise HTTPException(404,'Call not found')
    ctx=db.query(PhoneSignupLink).filter_by(call_sid=call_sid).with_for_update().one_or_none()
    if not ctx:raise HTTPException(404,'Signup text not found')
    sid=str(form.get('MessageSid') or '')
    if not re.fullmatch(r'SM[0-9a-fA-F]{32}',sid):raise HTTPException(400,'Invalid message reference')
    if not ctx.provider_id and ctx.status in ('submitting','unknown') and form.get('To')==ctx.phone and form.get('From')==os.getenv('TWILIO_PHONE_NUMBER'):ctx.provider_id=sid
    if sid!=ctx.provider_id:raise HTTPException(403,'Message reference does not match')
    state=str(form.get('MessageStatus') or '')
    if state in ('queued','sent','delivered','failed','undelivered') and ctx.status not in ('delivered','failed','undelivered'):
        ctx.status=state;activity(db,call,'signup_text',state)
        if str(form.get('ErrorCode',''))=='21610':
            from app.operations.renewal_reminders import suppress_sms
            suppress_sms(db,ctx.phone)
    db.commit();return Response(status_code=204)
