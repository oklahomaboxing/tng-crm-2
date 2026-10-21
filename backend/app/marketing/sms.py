import os,json,time,re
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.request_validator import RequestValidator
from app.database import get_db
from app.core.dependencies import staff_user
from app.models import MarketingCampaign,MarketingContact,SecurityLog
from app.ticketing.delivery import normalize_ticket_phone
from .models import SmsCampaignConfig,SmsDelivery

router=APIRouter(prefix='/api/marketing/sms',tags=['Member SMS'])
_cache={'at':0,'routes':{}}

def approved_routes():
    if time.monotonic()-_cache['at']<60:return _cache['routes']
    try:
        account=os.environ['TWILIO_ACCOUNT_SID'];token=os.environ['TWILIO_AUTH_TOKEN'];sender=os.environ['TWILIO_PHONE_NUMBER']
        client=Client(account,token,http_client=TwilioHttpClient(timeout=8));routes={}
        for service in client.messaging.v1.services.list(limit=100):
            phones=client.messaging.v1.services(service.sid).phone_numbers.list(limit=100)
            if not any(p.phone_number==sender for p in phones):continue
            for c in client.messaging.v1.services(service.sid).us_app_to_person.list(limit=100):
                if str(c.campaign_status).upper()!='VERIFIED':continue
                kind=str(c.us_app_to_person_usecase).upper()
                if kind in {'ACCOUNT_NOTIFICATION','MIXED','LOW_VOLUME'}:routes['notification']=service.sid
                if kind in {'MARKETING','MIXED','LOW_VOLUME'}:routes['promotion']=service.sid
        _cache.update(at=time.monotonic(),routes=routes);return routes
    except Exception:
        raise HTTPException(503,'Could not verify the approved Twilio sending service. Check provider access before sending.')

@router.get('/readiness')
def readiness(user=Depends(staff_user)):
    routes=approved_routes()
    return {'notification_ready':'notification' in routes,'promotion_ready':'promotion' in routes,
            'notice':'Member notifications use the approved account-notification campaign. Promotions require a verified marketing or mixed campaign with an assigned sending number.'}

def eligible_contacts(db,ids):
    selected=db.query(MarketingContact).filter(MarketingContact.id.in_(ids)).all();good=[];skips={'no_consent':0,'unsubscribed':0,'invalid_phone':0,'inactive':0,'duplicate_phone':0};seen=set()
    for c in selected:
        if not c.active:skips['inactive']+=1;continue
        if c.sms_unsubscribed:skips['unsubscribed']+=1;continue
        if not c.sms_opt_in:skips['no_consent']+=1;continue
        try:
            phone=normalize_ticket_phone(c.phone)
            if not phone:raise ValueError()
        except ValueError:skips['invalid_phone']+=1;continue
        if phone in seen:skips['duplicate_phone']+=1;continue
        seen.add(phone);good.append((c,phone))
    return good,skips

def preview_campaign(db,campaign):
    config=db.get(SmsCampaignConfig,campaign.id)
    purpose=config.purpose if config else 'promotion'
    ids=json.loads(campaign.selected_contact_ids or '[]');eligible,skips=eligible_contacts(db,ids)
    routes=approved_routes();ready=purpose in routes
    return {'purpose':purpose,'selected_count':len(set(ids)),'eligible_count':len(eligible),'skipped':skips,'sending_ready':ready,
            'notice':None if ready else 'This message type needs an approved Twilio campaign and assigned sending number.'}

@router.get('/campaigns/{campaign_id}/preview')
def preview(campaign_id:int,db:Session=Depends(get_db),user=Depends(staff_user)):
    campaign=db.get(MarketingCampaign,campaign_id)
    if not campaign or campaign.campaign_type!='sms':raise HTTPException(404,'SMS campaign not found')
    return preview_campaign(db,campaign)

@router.post('/contacts/{contact_id}/consent')
def consent(contact_id:int,data:dict,db:Session=Depends(get_db),user=Depends(staff_user)):
    contact=db.get(MarketingContact,contact_id)
    if not contact:raise HTTPException(404,'Contact not found')
    note=str(data.get('evidence') or '').strip()
    if data.get('opt_in') is not True or not 10<=len(note)<=500:raise HTTPException(400,'Document the member’s existing SMS permission (10–500 characters). Do not opt in contacts merely because they are members.')
    if contact.sms_unsubscribed:raise HTTPException(409,'This contact opted out. They must text START to the gym number before staff can record new consent.')
    try:
        if not normalize_ticket_phone(contact.phone):raise ValueError()
    except ValueError:raise HTTPException(400,'A valid mobile number is required')
    contact.sms_opt_in=True;contact.updated_at=datetime.utcnow()
    db.add(SecurityLog(user_id=user.id,action='SMS_CONSENT_RECORDED',description=f'Contact #{contact.id}; staff-supplied evidence: {note}',endpoint='/api/marketing/sms/contacts/consent',success=True));db.commit()
    return {'recorded':True}

def send_campaign(db,campaign):
    config=db.get(SmsCampaignConfig,campaign.id);purpose=config.purpose if config else 'promotion'
    routes=approved_routes()
    if purpose not in routes:raise HTTPException(409,'The approved Twilio campaign does not cover this message type. Save the draft until the matching campaign and sender are approved.')
    eligible,skips=eligible_contacts(db,json.loads(campaign.selected_contact_ids or '[]'))
    if not eligible:raise HTTPException(400,'No eligible SMS recipients. Select contacts with valid mobile numbers and documented SMS consent who have not opted out.')
    if len(eligible)>500:raise HTTPException(400,'Send to at most 500 recipients per campaign.')
    # Reserve the campaign once; repeat clicks cannot resend it or replay uncertain submissions.
    reserved=db.query(MarketingCampaign).filter(MarketingCampaign.id==campaign.id,MarketingCampaign.status=='draft').update({'status':'sending'},synchronize_session=False)
    if not reserved:db.rollback();raise HTTPException(409,'This campaign has already been submitted. Review its delivery results instead of sending it again.')
    db.commit()
    client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=10))
    for contact,phone in eligible:
        db.refresh(contact)
        if not contact.sms_opt_in or contact.sms_unsubscribed or not contact.active:continue
        record=SmsDelivery(campaign_id=campaign.id,contact_id=contact.id,phone=phone,status='submitting');db.add(record);db.commit()
        db.query(SmsDelivery).filter_by(id=record.id).update({SmsDelivery.status:SmsDelivery.status},synchronize_session=False)
        body=campaign.message.replace('{{first_name}}',contact.first_name or 'member').strip()
        if not body.lower().startswith('tng'):body='TNG Boxing: '+body
        if 'reply stop' not in body.lower():body+=' Reply STOP to opt out.'
        callback=os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')+f'/api/marketing/sms/status?delivery_id={record.id}'
        try:
            sent=client.messages.create(to=phone,from_=os.environ['TWILIO_PHONE_NUMBER'],messaging_service_sid=routes[purpose],body=body,status_callback=callback)
            record.provider_id=sent.sid;record.status='accepted'
        except Exception as exc:
            code=getattr(exc,'code',None);record.status='failed' if code else 'unknown';record.error_code=str(code) if code else type(exc).__name__
            if code==21610:contact.sms_unsubscribed=True;contact.sms_opt_in=False
        db.commit()
        if record.status=='unknown':break
    refresh_counts(db,campaign.id)
    db.refresh(campaign)
    return {'campaign_id':campaign.id,'status':campaign.status,'sent_count':campaign.sent_count,'failed_count':campaign.failed_count,'delivered_count':campaign.delivered_count,'skipped':skips,'unattempted_count':len(eligible)-campaign.recipient_count,'message':'Submitted messages are not automatically retried. Accepted means Twilio accepted the message; delivered means carrier-confirmed.'}

def refresh_counts(db,campaign_id):
    rows=db.query(SmsDelivery).filter_by(campaign_id=campaign_id).all();campaign=db.get(MarketingCampaign,campaign_id)
    campaign.recipient_count=len(rows);campaign.sent_count=sum(r.status in ('accepted','sent','delivered') for r in rows);campaign.delivered_count=sum(r.status=='delivered' for r in rows);campaign.failed_count=sum(r.status in ('failed','unknown') for r in rows)
    campaign.status='partially_sent' if campaign.sent_count and campaign.failed_count else 'sent' if campaign.sent_count else 'failed';campaign.sent_at=campaign.sent_at or datetime.utcnow();db.commit()

async def validate_webhook(request):
    form=await request.form();token=os.getenv('TWILIO_AUTH_TOKEN');base=os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
    url=base+request.url.path+('?' + request.url.query if request.url.query else '')
    if not token or not RequestValidator(token).validate(url,form,request.headers.get('X-Twilio-Signature','')) or form.get('AccountSid')!=os.getenv('TWILIO_ACCOUNT_SID'):raise HTTPException(401,'Invalid Twilio webhook')
    return form

@router.post('/status')
async def status(delivery_id:int,request:Request,db:Session=Depends(get_db)):
    form=await validate_webhook(request);row=db.query(SmsDelivery).filter_by(id=delivery_id).with_for_update().first()
    if not row:raise HTTPException(404,'Delivery not found')
    if not row.provider_id and row.status in ('unknown','submitting') and form.get('To')==row.phone and form.get('From')==os.getenv('TWILIO_PHONE_NUMBER'):
        row.provider_id=form.get('MessageSid')
    if row.provider_id!=form.get('MessageSid'):raise HTTPException(409,'Message attempt does not match')
    state=form.get('MessageStatus','')
    if row.status!='delivered':
        if state=='delivered':row.status='delivered';row.error_code=None
        elif state in ('failed','undelivered','canceled'):row.status='failed';row.error_code=str(form.get('ErrorCode') or '')
        elif state=='sent' and row.status not in ('failed','unknown'):row.status='sent'
    if str(form.get('ErrorCode') or '')=='21610':
        c=db.get(MarketingContact,row.contact_id)
        if c:c.sms_unsubscribed=True;c.sms_opt_in=False
    db.commit();refresh_counts(db,row.campaign_id);return {'received':True}

@router.post('/inbound')
async def inbound(request:Request,db:Session=Depends(get_db)):
    form=await validate_webhook(request)
    try:phone=normalize_ticket_phone(form.get('From'))
    except ValueError:raise HTTPException(400,'Invalid sender')
    command=str(form.get('OptOutType') or form.get('Body') or '').strip().upper()
    if command in ('STOP','STOPALL','UNSUBSCRIBE','CANCEL','END','QUIT','START','UNSTOP'):
        for contact in db.query(MarketingContact).all():
            try:match=normalize_ticket_phone(contact.phone)==phone
            except ValueError:match=False
            if match:
                if command in ('START','UNSTOP'):contact.sms_unsubscribed=False  # Never infer promotional consent from START alone.
                else:contact.sms_unsubscribed=True;contact.sms_opt_in=False
                contact.updated_at=datetime.utcnow()
        db.commit()
    if command=='HELP':
        return Response('<Response><Message>TNG Boxing member texts. Help: 405-959-5823 or marketing@tngboxinggym.com. Reply STOP to opt out.</Message></Response>',media_type='application/xml')
    return Response('<Response/>',media_type='application/xml')

@router.get('/member-audience')
def member_audience(active_only:bool=True,db:Session=Depends(get_db),user=Depends(staff_user)):
    from app.models import Member
    from app.services.memberships import effective_membership_status
    phones=set()
    for member in db.query(Member).filter(Member.member_type=='MEMBER').all():
        if active_only and effective_membership_status(member)!='active':continue
        try:
            phone=normalize_ticket_phone(member.phone)
            if phone:phones.add(phone)
        except ValueError:continue
    ids=[]
    for contact in db.query(MarketingContact).filter(MarketingContact.active.is_(True)).all():
        try:
            if normalize_ticket_phone(contact.phone) in phones:ids.append(contact.id)
        except ValueError:continue
    return {'contact_ids':ids,'active_members_only':active_only}

@router.get('/campaigns/{campaign_id}/deliveries')
def deliveries(campaign_id:int,db:Session=Depends(get_db),user=Depends(staff_user)):
    return [{'contact_id':r.contact_id,'phone_last4':r.phone[-4:],'status':r.status,'error_code':r.error_code} for r in db.query(SmsDelivery).filter_by(campaign_id=campaign_id).order_by(SmsDelivery.id)]
