"""Account renewal notifications: persistent claims, consent checks and no billing mutations."""
import asyncio,hashlib,json,os,re
from datetime import datetime,timedelta,timezone
from html import escape
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel
from sqlalchemy import Boolean,Column,DateTime,ForeignKey,Integer,String,Text,UniqueConstraint,select,or_
from sqlalchemy.exc import IntegrityError
from app.database import Base,SessionLocal,get_db
from app.models import Member,MarketingContact,WaiverSubmission,Lead,SecurityLog
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.services.member_reporting import membership_evidence,membership_report
from app.ticketing.delivery import normalize_ticket_phone

CT=ZoneInfo('America/Chicago')
router=APIRouter(prefix='/api/renewal-reminders',tags=['Renewal reminders'])
class ReminderSettings(Base):
    __tablename__='renewal_reminder_settings'
    id=Column(Integer,primary_key=True)
    enabled=Column(Boolean,default=True,nullable=False)
    email_enabled=Column(Boolean,default=True,nullable=False)
    sms_enabled=Column(Boolean,default=True,nullable=False)
    five_day=Column(Boolean,default=True,nullable=False)
    one_day=Column(Boolean,default=False,nullable=False)

class ExpiryNoticeSettings(Base):
    __tablename__='membership_expiry_notice_settings'
    id=Column(Integer,primary_key=True)
    enabled=Column(Boolean,default=True,nullable=False)

class RenewalReminder(Base):
    __tablename__='renewal_reminders'
    __table_args__=(UniqueConstraint('recipient','expiry_date','lead_days','channel',name='uq_renewal_recipient_term_channel'),)
    id=Column(Integer,primary_key=True)
    member_id=Column(Integer,ForeignKey('members.id',ondelete='CASCADE'),nullable=False,index=True)
    expiry_date=Column(String(10),nullable=False)
    lead_days=Column(Integer,nullable=False)
    channel=Column(String(10),nullable=False)
    recipient=Column(String(255),nullable=False)
    status=Column(String(30),default='queued',nullable=False,index=True)
    reason=Column(String(100),nullable=True)
    provider_id=Column(String(100),nullable=True,index=True)
    attempts=Column(Integer,default=0,nullable=False)
    next_attempt=Column(DateTime,default=datetime.utcnow)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
    submitted_at=Column(DateTime,nullable=True)
    sent_date=Column(String(10),nullable=True)

class ReminderSmsSuppression(Base):
    __tablename__='renewal_sms_suppressions'
    phone_hash=Column(String(64),primary_key=True)

class ReminderWorkerState(Base):
    __tablename__='renewal_reminder_worker_state'
    id=Column(Integer,primary_key=True)
    last_completed_at=Column(DateTime,nullable=False)

def utcnow():return datetime.utcnow()
def localnow(now):return now.replace(tzinfo=timezone.utc).astimezone(CT)
def expiry(member):return localnow(member.membership_end).date().isoformat() if member.membership_end else None
def settings(db):
    cfg=db.get(ReminderSettings,1) or ReminderSettings(id=1,enabled=True,email_enabled=True,sms_enabled=True,five_day=True,one_day=False)
    expired=db.get(ExpiryNoticeSettings,1)
    cfg.expired_sms=expired.enabled if expired else True
    return cfg
def phone(value):
    try:return normalize_ticket_phone(value)
    except ValueError:return ''
def suppress_sms(db,number,stop=True):
    key=hashlib.sha256(number.encode()).hexdigest();row=db.get(ReminderSmsSuppression,key)
    if stop and not row:db.add(ReminderSmsSuppression(phone_hash=key))
    elif not stop and row:db.delete(row)

def eligibility(db,member,channel,members,contacts):
    email=(member.email or '').strip().casefold();number=phone(member.phone)
    if channel=='email':
        if any(m.id!=member.id and (m.email or '').strip().casefold()==email for m in members):return None,'shared_email_review'
        if any((c.email or '').strip().casefold()==email and c.email_unsubscribed for c in contacts):return None,'email_opted_out'
        return email,None
    if not number:return None,'invalid_phone'
    if any(m.id!=member.id and phone(m.phone)==number for m in members):return None,'shared_phone_review'
    matched=[c for c in contacts if phone(c.phone)==number]
    if db.get(ReminderSmsSuppression,hashlib.sha256(number.encode()).hexdigest()) or any(c.sms_unsubscribed for c in matched):return None,'sms_opted_out'
    # Waiver consent must belong to the same lead/contact and participant, not a ticket buyer.
    candidates=db.query(WaiverSubmission,Lead).join(Lead,Lead.id==WaiverSubmission.lead_id).order_by(WaiverSubmission.submitted_at.desc()).all()
    for waiver,lead in candidates:
        name=' '.join(f'{waiver.participant_first_name} {waiver.participant_last_name}'.casefold().split())
        member_name=' '.join(f'{member.first_name or ""} {member.last_name or ""}'.casefold().split())
        if (lead.email or '').strip().casefold()==email and phone(lead.phone)==number and name==member_name:
            return (number,None) if waiver.sms_consent and waiver.sms_consent_at and waiver.sms_disclosure_version else (None,'no_sms_consent')
    if any(c.active and c.sms_opt_in and (c.email or '').strip().casefold()==email for c in matched):return number,None
    return None,'no_sms_consent'

def plan(db,now=None):
    now=now or utcnow();cfg=settings(db);members=db.query(Member).all();contacts=db.query(MarketingContact).all();paid=membership_evidence(db);today=localnow(now).date();rows=[]
    if not cfg.enabled:return []
    for member in members:
        report=membership_report(member,paid,now)
        if str(member.membership_status or '').lower() in ('inactive','cancelled','canceled','suspended'):continue
        if not member.membership_end or not (report['is_current_member'] or report['membership_category']=='expired'):continue
        end=expiry(member);days=(datetime.fromisoformat(end).date()-today).days
        stage=0 if cfg.expired_sms and report['membership_category']=='expired' and -3<=days<=0 else 1 if report['is_current_member'] and cfg.one_day and days==1 else 5 if report['is_current_member'] and cfg.five_day and 1<=days<=5 else None
        if stage is None:continue
        for channel,enabled in [('email',cfg.email_enabled),('sms',cfg.sms_enabled)]:
            if not enabled or (stage==0 and channel!='sms'):continue
            recipient,reason=eligibility(db,member,channel,members,contacts)
            existing=db.query(RenewalReminder).filter_by(member_id=member.id,expiry_date=end,lead_days=stage,channel=channel).order_by(RenewalReminder.id.desc()).first()
            resume=bool(existing and existing.status=='cancelled' and existing.reason in ('contact_changed','renewed_inactive_or_settings_changed') and not existing.provider_id and existing.attempts<3)
            rows.append({'member_id':member.id,'name':f'{member.first_name} {member.last_name}'.strip(),'expiry_date':end,'days_remaining':days,'lead_days':stage,'channel':channel,'recipient':recipient,'reason':reason,'status':'skipped' if reason else 'ready' if resume else existing.status if existing else 'ready'})
    return rows

def enqueue(db,now=None):
    count=0
    for item in plan(db,now):
        if item['status']!='ready':continue
        try:
            changed=False
            with db.begin_nested():
                previous=db.query(RenewalReminder).filter_by(member_id=item['member_id'],expiry_date=item['expiry_date'],lead_days=item['lead_days'],channel=item['channel'],recipient=item['recipient']).with_for_update().first()
                if previous:
                    if previous.status=='cancelled':
                        previous.status='queued';previous.reason=None;previous.next_attempt=now or utcnow();changed=True
                else:
                    db.add(RenewalReminder(member_id=item['member_id'],expiry_date=item['expiry_date'],lead_days=item['lead_days'],channel=item['channel'],recipient=item['recipient'],status='queued',next_attempt=now or utcnow()));changed=True
                db.flush()
            db.commit();count+=int(changed)
        except IntegrityError:db.rollback()
    return count

def content(member,date,expired=False):
    end=datetime.fromisoformat(date).strftime('%B %d, %Y')
    url=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/'
    text=f"TNG Boxing: Hi {member.first_name or 'member'}, your current membership period ends {end}. View membership details and renewal options: {url} If renewal is already arranged, check with the front desk. Help: 405-959-5823."
    if expired:text=f"TNG Boxing: Hi {member.first_name or 'member'}, your membership period ended {end}. View your account and renewal options: {url} If you have already renewed, please contact the front desk at 405-959-5823 so we can update your record."
    return text,text+' Reply STOP to opt out.'

def process(db,now=None,limit=25):
    fixed_now=now
    now=now or utcnow();local=localnow(now);cfg=settings(db)
    if not cfg.enabled:return {'queued':0,'submitted':0,'quiet_hours':False}
    db.query(RenewalReminder).filter(RenewalReminder.status=='submitting',RenewalReminder.next_attempt<now-timedelta(minutes=30)).update({'status':'unknown','reason':'submission_state_uncertain'},synchronize_session=False);db.commit()
    queued=enqueue(db,now)
    if not 10<=local.hour<18:return {'queued':queued,'submitted':0,'quiet_hours':True}
    ids=[i for (i,) in db.query(RenewalReminder.id).filter(RenewalReminder.status.in_(['queued','blocked']),RenewalReminder.next_attempt<=now).order_by(RenewalReminder.id).limit(limit).all()]
    notification_service=None
    if cfg.sms_enabled and db.query(RenewalReminder.id).filter(RenewalReminder.id.in_(ids),RenewalReminder.channel=='sms').first():
        try:
            from app.marketing.sms import approved_routes
            notification_service=approved_routes().get('notification')
        except Exception:pass
    submitted=0
    for identity in ids:
        if fixed_now is None:now=utcnow();local=localnow(now)
        if not 10<=local.hour<18:break
        # Commit the submission claim before provider I/O. Uncertain submissions are never replayed.
        hint=db.get(RenewalReminder,identity)
        if not hint:continue
        member_id=hint.member_id
        member=db.query(Member).filter_by(id=member_id).with_for_update().first()
        row=db.execute(select(RenewalReminder).where(RenewalReminder.id==identity).with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
        if not row or row.member_id!=member_id:db.rollback();continue
        if row.status not in ('queued','blocked') or row.next_attempt>now:db.rollback();continue
        cfg=settings(db)
        paid=membership_evidence(db)
        valid=bool(member and member.membership_end and expiry(member)==row.expiry_date and (membership_report(member,paid,now)['membership_category']=='expired' if row.lead_days==0 else membership_report(member,paid,now)['is_current_member']))
        if row.lead_days==0 and member:
            days=(datetime.fromisoformat(row.expiry_date).date()-local.date()).days
            valid=valid and -3<=days<=0 and str(member.membership_status or '').lower() not in ('inactive','cancelled','canceled','suspended')
        allowed=cfg.enabled and (cfg.email_enabled if row.channel=='email' else cfg.sms_enabled) and (cfg.expired_sms if row.lead_days==0 else cfg.five_day if row.lead_days==5 else cfg.one_day)
        if not valid or not allowed:row.status='cancelled';row.reason='renewed_inactive_or_settings_changed';db.commit();continue
        recipient,reason=eligibility(db,member,row.channel,db.query(Member).all(),db.query(MarketingContact).all())
        if reason or recipient!=row.recipient:row.status='cancelled';row.reason=reason or 'contact_changed';db.commit();continue
        same_day=db.query(RenewalReminder).filter(RenewalReminder.member_id==member.id,RenewalReminder.expiry_date==row.expiry_date,RenewalReminder.channel==row.channel,RenewalReminder.sent_date==local.date().isoformat(),RenewalReminder.status.in_(['submitting','accepted','sent','delivered','unknown'])).first()
        if same_day:row.status='cancelled';row.reason='already_notified_today';db.commit();continue
        try:
            if row.channel=='email':
                if not os.getenv('RESEND_API_KEY'):raise RuntimeError('email_not_configured')
                service=None
            else:
                service=notification_service
                if not service:raise RuntimeError('sms_notification_route_unavailable')
        except Exception:
            row.status='blocked';row.reason='provider_configuration_unavailable';row.next_attempt=now+timedelta(minutes=30);db.commit();continue
        text,sms=content(member,row.expiry_date,expired=row.lead_days==0)
        claimed=db.query(RenewalReminder).filter(RenewalReminder.id==identity,RenewalReminder.status.in_(['queued','blocked'])).update({'status':'submitting','reason':None,'attempts':RenewalReminder.attempts+1,'sent_date':local.date().isoformat(),'next_attempt':now},synchronize_session=False)
        db.commit()
        if not claimed:continue
        db.refresh(row)
        try:
            if row.channel=='email':
                import resend
                resend.api_key=os.environ['RESEND_API_KEY']
                renewal_link=escape(os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/',quote=True)
                result=resend.Emails.send({'from':os.getenv('RESEND_FROM_EMAIL','TNG Boxing <marketing@tngboxinggym.com>'),'to':[row.recipient],'subject':'Your TNG Boxing membership period is ending','text':text,'html':f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px"><h2 style="color:#d71932">TNG BOXING</h2><p>{escape(text)}</p><p><a href="{renewal_link}">View membership and renewal options</a></p><p>No payment is charged by this reminder.</p></div>'},options={'idempotency_key':f'tng-renewal-{row.id}'})
                provider_id=result.get('id') if isinstance(result,dict) else None
            else:
                from twilio.rest import Client
                from twilio.http.http_client import TwilioHttpClient
                callback=os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')+f'/api/renewal-reminders/sms-status?delivery_id={row.id}'
                response=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=10)).messages.create(to=row.recipient,from_=os.environ['TWILIO_PHONE_NUMBER'],messaging_service_sid=service,body=sms,status_callback=callback)
                provider_id=response.sid
            if not provider_id:raise RuntimeError('provider_acknowledgment_missing')
            row=db.query(RenewalReminder).filter_by(id=identity).with_for_update().populate_existing().one()
            if row.status in ('submitting','unknown'):row.status='accepted'
            row.provider_id=str(provider_id);row.submitted_at=now;submitted+=1
        except Exception as exc:
            row=db.query(RenewalReminder).filter_by(id=identity).with_for_update().populate_existing().one()
            if row.status not in ('delivered','sent','failed'):
                row.status='unknown';row.reason='submission_requires_review'
                status=getattr(exc,'status',None) or getattr(exc,'status_code',None)
                if status in (400,401,403,404,422,429):
                    row.status='blocked' if row.attempts<3 else 'failed';row.reason='provider_rejected_submission';row.next_attempt=now+timedelta(minutes=30)
            if getattr(exc,'code',None)==21610:
                suppress_sms(db,row.recipient);row.status='failed';row.reason='sms_opted_out'
        db.commit()
    return {'queued':queued,'submitted':submitted,'quiet_hours':not 10<=local.hour<18}

async def reminder_loop():
    while True:
        try:
            def run():
                with SessionLocal() as db:
                    process(db)
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
                    insert=pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert
                    stmt=insert(ReminderWorkerState).values(id=1,last_completed_at=utcnow())
                    db.execute(stmt.on_conflict_do_update(index_elements=['id'],set_={'last_completed_at':utcnow()}));db.commit()
            await asyncio.to_thread(run)
        except Exception:
            import logging
            logging.getLogger(__name__).warning('Renewal reminder worker failed; saved claims prevent resubmission.')
        await asyncio.sleep(300)

class SettingsInput(BaseModel):
    enabled:bool=True
    email_enabled:bool=True
    sms_enabled:bool=True
    five_day:bool=True
    one_day:bool=False
    expired_sms:bool=True

@router.get('')
def overview(response:Response,db=Depends(get_db),user=Depends(current_user)):
    require_admin(user);response.headers['Cache-Control']='private, no-store'
    cfg=settings(db);preview=plan(db);worker=db.get(ReminderWorkerState,1)
    recent=db.query(RenewalReminder).order_by(RenewalReminder.id.desc()).limit(100).all()
    return {'settings':{key:getattr(cfg,key) for key in SettingsInput.model_fields},'timezone':'America/Chicago','sending_hours':'10 AM–6 PM Central','worker_configured':os.getenv('MEMBERSHIP_REMINDERS_WORKER_ENABLED','1')=='1','last_worker_check':worker.last_completed_at.isoformat()+'Z' if worker else None,'preview':[{k:v for k,v in item.items() if k!='recipient'} for item in preview],
        'recent':[{'id':r.id,'member_id':r.member_id,'expiry_date':r.expiry_date,'lead_days':r.lead_days,'channel':r.channel,'status':r.status,'reason':r.reason,'submitted_at':r.submitted_at} for r in recent],
        'email_configured':bool(os.getenv('RESEND_API_KEY')),'sms_configured':all(bool(os.getenv(k)) for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_PHONE_NUMBER')),
        'notice':'Accepted means the provider accepted submission, not inbox/handset delivery. Uncertain submissions are not automatically replayed.'}

@router.put('')
def configure(data:SettingsInput,db=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert
    values=data.model_dump()
    expired=values.pop('expired_sms')
    db.execute(insert(ExpiryNoticeSettings).values(id=1,enabled=expired).on_conflict_do_update(index_elements=['id'],set_={'enabled':expired}))
    db.execute(insert(ReminderSettings).values(id=1,**values).on_conflict_do_update(index_elements=['id'],set_=values))
    db.add(SecurityLog(user_id=user.id,action='RENEWAL_REMINDERS_CONFIGURED',description='Updated membership reminder channels and timing.'))
    db.commit();return {'saved':True}

@router.post('/sms-status')
async def sms_status(delivery_id:int,request:Request,db=Depends(get_db)):
    from app.marketing.sms import validate_webhook
    form=await validate_webhook(request);row=db.query(RenewalReminder).filter_by(id=delivery_id,channel='sms').with_for_update().first()
    if not row:raise HTTPException(404,'Reminder not found')
    if form.get('To')!=row.recipient or form.get('From')!=os.getenv('TWILIO_PHONE_NUMBER'):raise HTTPException(409,'Reminder address does not match')
    if row.provider_id and row.provider_id!=form.get('MessageSid'):raise HTTPException(409,'Message does not match')
    if not row.provider_id and row.status in ('submitting','unknown'):row.provider_id=form.get('MessageSid')
    if row.provider_id!=form.get('MessageSid'):raise HTTPException(409,'Message does not match')
    state=form.get('MessageStatus')
    if row.status!='delivered':
        if state=='delivered':row.status='delivered';row.reason=None
        elif state in ('failed','undelivered','canceled'):row.status='failed';row.reason='provider_delivery_failed'
        elif state=='sent' and row.status not in ('failed','unknown'):row.status='sent'
    if str(form.get('ErrorCode') or '')=='21610':suppress_sms(db,row.recipient);row.reason='sms_opted_out'
    db.commit();return {'received':True}
