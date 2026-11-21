"""Explicit staff work texts to identified officials; uses the existing private SMS inbox."""
import os,json,hashlib,re
from datetime import datetime,timedelta
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Response,Query
from pydantic import BaseModel,Field
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.core.dependencies import staff_user
from app.models import User,SecurityLog
from app.amateurs.directory import DirectoryContact,serialize as contact_dict,lock,key,words
from app.messaging.inbox import InboxMessage,serialize as message_dict,base
from app.marketing.sms import blocked_sms_numbers,number_blocked,approved_routes
from app.ticketing.delivery import normalize_ticket_phone
from app.services.sms_service import ensure_stop_footer
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
router=APIRouter(prefix='/api/amateurs/official-work-texts',tags=['Officials work communication'])

def official(c):return bool(c and c.kind=='person' and ('official' in c.details.get('categories',[])or(c.role_verified and c.roles)))
def phone(c):
 try:return normalize_ticket_phone(c.phones[0])if c.phones else None
 except ValueError:return None

def eligibility(c,blocked):
 if not official(c):return None,'Not an identified official contact'
 if not c.active:return None,'Inactive contact'
 p=phone(c)
 if not p:return None,'Phone number missing or invalid'
 if number_blocked(p,blocked):return p,'Opted out — official must text START to resume'
 if not c.sms_consent:return p,'Work-text permission not recorded'
 return p,None

@router.get('')
def workspace(response:Response,q:str=Query('',max_length=160),db=Depends(get_db),user=Depends(staff_user)):
 response.headers['Cache-Control']='private, no-store';blocked=blocked_sms_numbers(db);rows=[]
 for c in db.query(DirectoryContact).filter_by(kind='person').order_by(DirectoryContact.name):
  if not official(c):continue
  if q.strip()and q.casefold()not in json.dumps([c.name,c.emails,c.phones,c.details]).casefold():continue
  p,reason=eligibility(c,blocked);rows.append({**contact_dict(c),'sms_phone':p,'can_text':reason is None,'text_blocked_reason':reason})
 return {'contacts':rows,'sending_number':os.getenv('TWILIO_PHONE_NUMBER',''),'provider_status':'Verified on send; no provider health check performed','reply_workspace':'Text Inbox'}

class OfficialContact(BaseModel):
 name:str=Field(min_length=2,max_length=200)
 email:str=Field(default='',max_length=254)
 phone:str=Field(default='',max_length=40)
 group:str=Field(default='',max_length=120)
@router.post('/contacts')
def add_contact(body:OfficialContact,db=Depends(get_db),user=Depends(staff_user)):
 name=body.name.strip();email=body.email.strip().casefold();p=None
 if len(name)<2:raise HTTPException(422,'Enter the official name')
 if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise HTTPException(422,'Enter a valid email')
 if body.phone.strip():
  try:p=normalize_ticket_phone(body.phone)
  except ValueError:raise HTTPException(422,'Enter a valid phone number')
 if not email and not p:raise HTTPException(422,'Provide an email or phone number')
 lock(db);matches=[c for c in db.query(DirectoryContact).filter_by(kind='person')if words(name)in{words(x)for x in [c.name]+c.details.get('aliases',[])}and((email and email in c.emails)or(p and p in c.phones))]
 if len(matches)>1:raise HTTPException(409,'Multiple matching people need review in Contact details')
 created=not matches
 if matches:c=matches[0]
 else:
  c=DirectoryContact(identity_key=key('official-manual:'+words(name)+':'+(email or p)),kind='person',name=name,emails=[],phones=[],details={},observations=[],roles=[],role_verified=False,sms_consent=False,issues=[],active=True);db.add(c)
 d=dict(c.details);d['categories']=list(dict.fromkeys(d.get('categories',[])+['official']))
 if body.group.strip():d['official_affiliation']=body.group.strip()
 c.details=d;c.emails=list(dict.fromkeys(c.emails+([email]if email else[])));c.phones=list(dict.fromkeys(c.phones+([p]if p else[])));c.version=(c.version or 0)+1;db.flush();db.add(SecurityLog(user_id=user.id,action='OFFICIAL_WORK_CONTACT_IDENTIFIED',description=f'Contact {c.id}; created {created}; official contact identified by staff; no certification or SMS permission inferred.',success=True));db.commit();return {'saved':True,'created':created,'contact_id':c.id}

class Permission(BaseModel):
 opt_in:bool
 evidence:str=Field(default='',max_length=500)
 version:int=Field(ge=1)
@router.put('/contacts/{contact_id}/permission')
def permission(contact_id:int,body:Permission,db=Depends(get_db),user=Depends(staff_user)):
 lock(db);c=db.query(DirectoryContact).filter_by(id=contact_id).with_for_update().first()
 if not official(c):raise HTTPException(404,'Official contact not found')
 if c.version!=body.version:raise HTTPException(409,'Contact changed. Refresh before recording permission')
 if body.opt_in:
  p=phone(c)
  if not p or not c.active:raise HTTPException(422,'An active contact with a valid phone number is required')
  if number_blocked(p,blocked_sms_numbers(db)):raise HTTPException(409,'This number opted out. The official must text START before permission can be restored')
  if len(body.evidence.strip())<10:raise HTTPException(422,'Record when and how the official agreed to work-related texts')
 c.sms_consent=body.opt_in;c.consent_note=body.evidence.strip();c.consent_at=datetime.utcnow()if body.opt_in else None;c.version+=1
 db.add(SecurityLog(user_id=user.id,action='OFFICIAL_WORK_TEXT_PERMISSION',description=json.dumps({'contact_id':c.id,'opt_in':body.opt_in,'evidence':c.consent_note,'phone':phone(c)}),success=True));db.commit();return {'saved':True,'version':c.version}

class Draft(BaseModel):
 contact_ids:list[int]=Field(min_length=1,max_length=50)
 message:str=Field(min_length=1,max_length=1200)
class Send(Draft):
 preview_hash:str=Field(min_length=64,max_length=64)
 request_key:UUID
 work_related:bool=False

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def content(body):
 text=body.message.strip()
 if not text:raise HTTPException(422,'Enter a work-related message')
 text=ensure_stop_footer('TNG Boxing officials: '+text)
 if len(text)>1500:raise HTTPException(422,'Shorten the text to 1,500 characters including the footer')
 return text

def draft(db,body):
 ids=sorted(set(body.contact_ids));contacts={c.id:c for c in db.query(DirectoryContact).filter(DirectoryContact.id.in_(ids)).populate_existing()};blocked=blocked_sms_numbers(db);recipients=[];skipped=[];seen=set();state=[]
 for cid in ids:
  c=contacts.get(cid);p,reason=eligibility(c,blocked);state.append({'id':cid,'version':c.version if c else None,'phone':p,'reason':reason})
  if not reason and p in seen:reason='Duplicate phone in this selection'
  if reason:skipped.append({'contact_id':cid,'name':c.name if c else 'Contact not found','reason':reason});continue
  seen.add(p);recipients.append({'contact_id':cid,'name':c.name,'phone':p})
 text=content(body);return {'body':text,'recipients':recipients,'skipped':skipped,'preview_hash':digest({'state':state,'body':text}),'notice':'Review recipients and message. Provider acceptance does not confirm delivery. No text has been sent by this preview.'}

@router.post('/preview')
def preview(body:Draft,response:Response,db=Depends(get_db),user=Depends(staff_user)):
 response.headers['Cache-Control']='private, no-store';return draft(db,body)

def batch_result(db,manifest,existing):
 rows=db.query(InboxMessage).filter(InboxMessage.id.in_(manifest['message_ids'])).order_by(InboxMessage.id).all()
 return {'already_submitted':existing,'messages':[{'phone':r.phone,**message_dict(r)}for r in rows],'skipped':manifest['skipped'],'notice':'Accepted is not delivered. Unknown/submitting messages require provider review; repeating this submission does not resend them.'}

@router.post('/send')
def send(body:Send,response:Response,db=Depends(get_db),user=Depends(staff_user)):
 response.headers['Cache-Control']='private, no-store'
 if not body.work_related:raise HTTPException(422,'Confirm this concerns official work, not advertising or promotions')
 text=content(body);endpoint=f'/api/amateurs/official-work-texts/batches/{user.id}/{body.request_key}';fingerprint=digest({'staff_id':user.id,'ids':sorted(set(body.contact_ids)),'body':text})
 # One durable batch per staff/key; the no-op write serializes SQLite and PostgreSQL submissions alike.
 db.query(User).filter_by(id=user.id).update({User.id:User.id},synchronize_session=False)
 old=db.query(SecurityLog).filter_by(action='OFFICIAL_WORK_SMS_BATCH',endpoint=endpoint).first()
 if old:
  manifest=json.loads(old.description)
  if manifest['fingerprint']!=fingerprint:raise HTTPException(409,'Submission key belongs to a different message or selection')
  return batch_result(db,manifest,True)
 lock(db);d=draft(db,body)
 if d['preview_hash']!=body.preview_hash:raise HTTPException(409,'Contacts, permission or message changed. Review a new preview')
 if not d['recipients']:raise HTTPException(422,'No eligible recipients. Review phone numbers, permission and opt-out status')
 recent=db.query(InboxMessage).filter(InboxMessage.staff_id==user.id,InboxMessage.direction=='outbound',InboxMessage.created_at>=datetime.utcnow()-timedelta(hours=1)).count()
 if recent+len(d['recipients'])>50:raise HTTPException(429,'Work-text limit reached. Try again later')
 service=approved_routes().get('notification');line=os.getenv('TWILIO_PHONE_NUMBER','')
 if not service or not line:raise HTTPException(409,'An approved notification sending service and assigned phone line are required')
 rows=[]
 for r in d['recipients']:
  row=InboxMessage(request_key=f'official:{user.id}:{body.request_key}:{r["contact_id"]}',phone=r['phone'],line=line,direction='outbound',body=text,status='submitting',staff_id=user.id);db.add(row);db.flush();rows.append((row.id,r['contact_id']))
 manifest={'fingerprint':fingerprint,'message_ids':[mid for mid,_ in rows],'skipped':d['skipped']}
 db.add(SecurityLog(user_id=user.id,action='OFFICIAL_WORK_SMS_BATCH',endpoint=endpoint,description=json.dumps(manifest),success=True))
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'Submission was already recorded. Refresh the conversation')
 halted=False
 for mid,cid in rows:
  row=db.get(InboxMessage,mid)
  if halted:
   row.status='failed';row.error_code='not_submitted_after_provider_error';db.commit();continue
  c=db.query(DirectoryContact).filter_by(id=cid).populate_existing().first();p,reason=eligibility(c,blocked_sms_numbers(db))
  if reason or p!=row.phone:
   row.status='failed';row.error_code='recipient_changed_or_suppressed';db.commit();continue
  try:
   client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=8));sent=client.messages.create(to=row.phone,from_=line,messaging_service_sid=service,body=text,status_callback=base()+f'/api/messages/status?message_id={mid}')
   if not sent.sid:raise RuntimeError('Provider reference unavailable')
   row=db.query(InboxMessage).filter_by(id=mid).with_for_update().populate_existing().one();row.provider_id=row.provider_id or sent.sid
   if row.status not in ('delivered','failed','undelivered'):row.status='accepted'
   db.commit()
  except Exception as exc:
   if not getattr(exc,'code',None)or str(getattr(exc,'code',''))in ('20003','20429'):halted=True
   db.rollback();row=db.query(InboxMessage).filter_by(id=mid).with_for_update().populate_existing().one()
   if row.status not in ('delivered','failed','undelivered'):row.status='failed'if getattr(exc,'code',None)else'unknown';row.error_code=str(getattr(exc,'code',''))[:40]or'submission_unknown'
   if str(getattr(exc,'code',''))=='21610':
    from app.operations.renewal_reminders import suppress_sms
    suppress_sms(db,row.phone)
   db.commit()
 return batch_result(db,manifest,False)

@router.get('/contacts/{contact_id}/history')
def history(contact_id:int,response:Response,db=Depends(get_db),user=Depends(staff_user)):
 c=db.get(DirectoryContact,contact_id)
 if not official(c):raise HTTPException(404,'Official contact not found')
 response.headers['Cache-Control']='private, no-store';p=phone(c)
 rows=db.query(InboxMessage).filter_by(phone=p).order_by(InboxMessage.id.desc()).limit(100).all()if p else[]
 return {'name':c.name,'phone':p,'messages':[message_dict(r)for r in reversed(rows)]}
