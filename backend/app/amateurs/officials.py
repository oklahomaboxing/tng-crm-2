"""Staff-triggered official availability requests, private coverage and scoped public replies."""
import os,json,secrets,hashlib,html
from datetime import datetime,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response,Request
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,String,Text,JSON,DateTime,ForeignKey,UniqueConstraint
from app.database import Base,get_db
from app.models import SecurityLog
from app.kiosk.routes import throttle
from app.matchmaker.models import BoxingEvent
from .rosters import access,roster_for
from .directory import DirectoryContact,ROLES,serialize as contact_dict
from .tournaments import plan_for,session_list
router=APIRouter(prefix='/api/amateurs/officials',tags=['Amateur officials'])
class OfficialRequest(Base):
 __tablename__='amateur_official_requests'
 __table_args__=(UniqueConstraint('context_key','contact_id',name='uq_amateur_official_context'),)
 id=Column(Integer,primary_key=True)
 roster_id=Column(Integer,ForeignKey('amateur_rosters.id'),nullable=False,index=True)
 plan_id=Column(Integer,ForeignKey('amateur_tournament_plans.id'),nullable=True)
 context_key=Column(String(80),nullable=False)
 contact_id=Column(Integer,ForeignKey('amateur_directory_contacts.id'),nullable=False)
 token_hash=Column(String(64),unique=True,nullable=False)
 token_cipher=Column(Text,nullable=False)
 expires_at=Column(DateTime,nullable=False)
 context_hash=Column(String(64),nullable=False)
 availability=Column(JSON,default=dict,nullable=False)
 confirmed_roles=Column(JSON,default=dict,nullable=False)
 reply_note=Column(Text,default='',nullable=False)
 staff_note=Column(Text,default='',nullable=False)
 version=Column(Integer,default=1,nullable=False)
 replied_at=Column(DateTime,nullable=True)
class OfficialStaffing(Base):
 __tablename__='amateur_official_staffing'
 context_key=Column(String(80),primary_key=True)
 requirements=Column(JSON,default=dict,nullable=False)
 version=Column(Integer,default=1,nullable=False)
class OfficialMessage(Base):
 __tablename__='amateur_official_messages'
 __table_args__=(UniqueConstraint('request_id','request_key',name='uq_amateur_official_message'),)
 id=Column(Integer,primary_key=True)
 request_id=Column(Integer,ForeignKey('amateur_official_requests.id'),nullable=False,index=True)
 request_key=Column(String(80),nullable=False)
 channel=Column(String(10),nullable=False)
 recipient=Column(String(254),nullable=False)
 body=Column(Text,nullable=False)
 signature=Column(String(64),nullable=False)
 status=Column(String(20),nullable=False)
 provider_id=Column(String(120),nullable=True)
 error=Column(String(200),nullable=True)
 created_by=Column(Integer,ForeignKey('users.id'),nullable=True)
 created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def ctx(db,rid,pid=None):
 r=roster_for(db,rid);key=f'roster:{rid}:plan:{pid or 0}';event=db.get(BoxingEvent,r.event_id) if r.event_id else None
 if pid:
  p=plan_for(db,pid)
  if p.roster_id!=rid:raise HTTPException(422,'Tournament belongs to a different roster')
  include=p.sunday_am!='off';sessions=session_list(p,include);sessions=[s for s in sessions if s['enabled']]
  for s in sessions:s['optional']=s['key']=='sun_am' and p.sunday_am=='auto' and not (p.schedule and p.schedule.get('sunday_am_enabled'))
  name=p.name
 else:
  if not r.competition_date:raise HTTPException(409,'Set the event date or create a tournament plan before requesting availability')
  name=event.name if event else r.name;sessions=[{'key':'event','label':'Event day','date':r.competition_date.isoformat(),'start_local':None,'end_local':None,'optional':False}]
 venue=((event.venue or '')+' '+(event.venue_address or '')).strip() if event else 'Venue to be confirmed'
 canonical={'name':name,'venue':venue,'sessions':[{k:s.get(k) for k in ('key','label','date','start_local','end_local')} for s in sessions]}
 return {'key':key,'name':name,'venue':venue,'sessions':sessions,'hash':digest(json.dumps(canonical,sort_keys=True))}
def audit(db,u,action,request_id):db.add(SecurityLog(user_id=u.id if u else None,action='AMATEUR_OFFICIAL_'+action,description=f'Official availability request {request_id} updated'))
def request_for(db,rid,lock=False):
 q=db.query(OfficialRequest).filter_by(id=rid);r=q.with_for_update().first() if lock else q.first()
 if not r:raise HTTPException(404,'Availability request not found')
 return r
def fresh(db,row):
 c=ctx(db,row.roster_id,row.plan_id)
 if c['hash']!=row.context_hash:raise HTTPException(409,'Event details changed. Staff must update this availability request before it can be used')
 return c

def token_values():
 from app.mail.microsoft365 import encrypt
 token=secrets.token_urlsafe(32);return digest(token),encrypt(token)
def request_dict(db,r,c):
 contact=db.get(DirectoryContact,r.contact_id)
 messages=db.query(OfficialMessage).filter_by(request_id=r.id).order_by(OfficialMessage.id.desc()).limit(20).all()
 return {'id':r.id,'contact':contact_dict(contact),'availability':r.availability,'confirmed_roles':r.confirmed_roles,'reply_note':r.reply_note,'staff_note':r.staff_note,'version':r.version,'stale':c['hash']!=r.context_hash,'expired':r.expires_at<datetime.utcnow(),'replied_at':r.replied_at.isoformat()+'Z' if r.replied_at else None,'messages':[{'id':m.id,'channel':m.channel,'status':m.status,'recipient':m.recipient,'body':m.body,'error':m.error,'created_at':m.created_at.isoformat()+'Z'} for m in messages]}
@router.get('/events/{roster_id}')
def workspace(roster_id:int,response:Response,plan_id:int|None=None,db=Depends(get_db),user=Depends(access)):
 c=ctx(db,roster_id,plan_id);response.headers['Cache-Control']='private, no-store';requests=db.query(OfficialRequest).filter_by(context_key=c['key']).order_by(OfficialRequest.id).all();cfg=db.get(OfficialStaffing,c['key']);requirements=cfg.requirements if cfg else {};rows=[request_dict(db,r,c) for r in requests];coverage=[]
 for s in c['sessions']:
  for role,needed in requirements.get(s['key'],{}).items():
   confirmed=sum(not r['stale'] and r['contact']['active'] and r['contact']['role_verified'] and role in r['contact']['roles'] and r['availability'].get(s['key'])=='available' and r['confirmed_roles'].get(s['key'])==role for r in rows)
   coverage.append({'session':s['key'],'role':role,'required':needed,'confirmed':confirmed,'shortfall':max(0,needed-confirmed),'optional':s['optional']})
 return {'context':c,'requests':rows,'requirements':requirements,'requirements_version':cfg.version if cfg else 1,'coverage':coverage,'roles':ROLES,'notice':'Non-Athlete source membership is not official certification. Verify roles/current credentials before assigning. Availability and confirmed assignments are separate. Staffing targets are entered by TNG; no official minimum is invented.'}
class AddRequest(BaseModel):contact_id:int;plan_id:int|None=None
@router.post('/events/{roster_id}/requests')
def add(roster_id:int,body:AddRequest,db=Depends(get_db),user=Depends(access)):
 c=ctx(db,roster_id,body.plan_id);contact=db.get(DirectoryContact,body.contact_id)
 if not contact or contact.kind!='person' or not contact.active or not contact.role_verified or not contact.roles:raise HTTPException(422,'Choose an active official whose role and credentials have been verified by staff')
 # Roster row serializes first-request creation across workers.
 from .rosters import AmateurRoster
 db.query(AmateurRoster).filter_by(id=roster_id).with_for_update().first();prior=db.query(OfficialRequest).filter_by(context_key=c['key'],contact_id=contact.id).first()
 if prior:return {'request_id':prior.id,'existing':True}
 h,cipher=token_values();r=OfficialRequest(roster_id=roster_id,plan_id=body.plan_id,context_key=c['key'],contact_id=contact.id,token_hash=h,token_cipher=cipher,expires_at=datetime.utcnow()+timedelta(days=30),context_hash=c['hash'],availability={},confirmed_roles={});db.add(r);db.flush();audit(db,user,'REQUEST_CREATED',r.id);db.commit();return {'request_id':r.id,'existing':False}
class Requirements(BaseModel):requirements:dict[str,dict[str,int]];version:int=Field(ge=1);plan_id:int|None=None
@router.put('/events/{roster_id}/requirements')
def requirements(roster_id:int,body:Requirements,db=Depends(get_db),user=Depends(access)):
 c=ctx(db,roster_id,body.plan_id);from .rosters import AmateurRoster
 db.query(AmateurRoster).filter_by(id=roster_id).with_for_update().first();keys={s['key'] for s in c['sessions']}
 if set(body.requirements)-keys or any(set(v)-set(ROLES) or any(isinstance(n,bool) or n<0 or n>50 for n in v.values()) for v in body.requirements.values()):raise HTTPException(422,'Set known session/role targets from 0 to 50')
 row=db.get(OfficialStaffing,c['key'])
 if row and row.version!=body.version:raise HTTPException(409,'Staffing targets changed. Refresh before saving')
 if not row:
  if body.version!=1:raise HTTPException(409,'Refresh staffing targets')
  row=OfficialStaffing(context_key=c['key'],version=1);db.add(row)
 row.requirements=body.requirements;row.version+=1;audit(db,user,'TARGETS_UPDATED',0);db.commit();return {'saved':True}
class AvailabilityUpdate(BaseModel):
 availability:dict[str,Literal['available','tentative','unavailable','no_response']]
 confirmed_roles:dict[str,str]=Field(default_factory=dict)
 staff_note:str=Field(default='',max_length=4000)
 version:int=Field(ge=1)
@router.put('/requests/{request_id}')
def update(request_id:int,body:AvailabilityUpdate,db=Depends(get_db),user=Depends(access)):
 r=request_for(db,request_id,True);c=fresh(db,r);contact=db.get(DirectoryContact,r.contact_id);keys={s['key'] for s in c['sessions']}
 if r.version!=body.version:raise HTTPException(409,'Official response changed. Refresh before saving')
 if set(body.availability)-keys or set(body.confirmed_roles)-keys:raise HTTPException(422,'Unknown session')
 for k,role in body.confirmed_roles.items():
  if role and (role not in contact.roles or not contact.role_verified or not contact.active or body.availability.get(k)!='available'):raise HTTPException(422,'Confirm only an available official in a verified role')

 if body.staff_note.strip() and body.staff_note!=r.staff_note:db.add(OfficialMessage(request_id=r.id,request_key='note:'+secrets.token_hex(16),channel='note',recipient='',body=body.staff_note.strip(),signature=digest(body.staff_note),status='logged',created_by=user.id))
 r.availability=body.availability;r.confirmed_roles={k:v for k,v in body.confirmed_roles.items() if v};r.staff_note=body.staff_note;r.version+=1;audit(db,user,'AVAILABILITY_RECORDED',r.id);db.commit();return {'saved':True}
class RefreshRequest(BaseModel):version:int=Field(ge=1)
@router.post('/requests/{request_id}/refresh')
def refresh(request_id:int,body:RefreshRequest,db=Depends(get_db),user=Depends(access)):
 r=request_for(db,request_id,True)
 if r.version!=body.version:raise HTTPException(409,'Request changed. Refresh first')
 c=ctx(db,r.roster_id,r.plan_id);r.token_hash,r.token_cipher=token_values();r.context_hash=c['hash'];r.expires_at=datetime.utcnow()+timedelta(days=30);r.availability={};r.confirmed_roles={};r.replied_at=None;r.reply_note='';r.version+=1;audit(db,user,'REQUEST_REISSUED',r.id);db.commit();return {'saved':True}

def draft(db,r):
 from app.mail.microsoft365 import decrypt
 c=fresh(db,r);contact=db.get(DirectoryContact,r.contact_id)
 if r.expires_at<datetime.utcnow():raise HTTPException(409,'Reply link expired. Reissue the request first')
 if not contact.active or not contact.role_verified or not contact.roles:raise HTTPException(409,'Verify this official’s role/current credentials first')
 link=os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/officials/respond#'+decrypt(r.token_cipher)
 lines=[f"Hello {contact.name},",f"TNG is checking your availability for {c['name']}.",c['venue']]
 for s in c['sessions']:lines.append(s['label']+' · '+s['date']+' · '+((s['start_local'] or '')[11:]+'–'+(s['end_local'] or '')[11:] if s['start_local'] else 'times to be confirmed')+(' (if needed)' if s['optional'] else '')+' · Oklahoma City time')
 lines+=['Please tell us which sessions you can work: '+link,'This is an availability request, not a confirmed assignment. TNG will confirm your role separately.']
 body='\n'.join(lines);signature=digest(json.dumps({'body':body,'contact_version':contact.version,'context':r.context_hash},sort_keys=True));return contact,body,signature,link
@router.get('/requests/{request_id}/preview')
def preview(request_id:int,response:Response,db=Depends(get_db),user=Depends(access)):
 r=request_for(db,request_id);contact,body,signature,link=draft(db,r);response.headers['Cache-Control']='private, no-store';return {'body':body,'preview_hash':signature,'reply_link':link,'emails':contact.emails,'phones':contact.phones,'sms_permission':contact.sms_consent}
class SendBody(BaseModel):
 channel:Literal['email','sms']
 preview_hash:str
 request_key:str=Field(min_length=16,max_length=80)
 note:str=Field(default='',max_length=2000)
@router.post('/requests/{request_id}/send')
def send(request_id:int,body:SendBody,db=Depends(get_db),user=Depends(access)):
 r=request_for(db,request_id,True);contact,message,signature,link=draft(db,r)
 if signature!=body.preview_hash:raise HTTPException(409,'Event or contact details changed. Review a fresh preview before sending')
 submission_signature=digest(signature+'|'+body.note.strip())
 if body.note.strip():message+='\n\nMessage from TNG:\n'+body.note.strip()
 existing=db.query(OfficialMessage).filter_by(request_id=r.id,request_key=body.request_key).first()
 if existing:
  if existing.signature!=submission_signature or existing.channel!=body.channel:raise HTTPException(409,'Send key was used for a different message')
  return {'status':existing.status,'error':existing.error,'existing':True}
 if body.channel=='sms':
  from app.marketing.sms import blocked_sms_numbers,number_blocked,approved_routes
  if not contact.phones or not contact.sms_consent:raise HTTPException(422,'Record the official’s permission to receive availability texts first')
  if number_blocked(contact.phones[0],blocked_sms_numbers(db)):raise HTTPException(422,'This phone opted out; it must text START before messages resume')
  service=approved_routes().get('notification')
  if not service:raise HTTPException(409,'An approved notification SMS sending service is required')
  from app.services.sms_service import ensure_stop_footer
  message=ensure_stop_footer(message)
  if len(message)>1500:raise HTTPException(422,'Text is too long. Shorten the added message or use email')
  recipient=contact.phones[0]
 else:
  if not contact.emails:raise HTTPException(422,'Add an email address first')
  from app.mail.microsoft365 import selected_provider
  if selected_provider(db)!='microsoft365' and not os.getenv('RESEND_API_KEY'):raise HTTPException(503,'Email is not configured. Connect Microsoft 365 or Resend before sending')
  recipient=contact.emails[0]
 m=OfficialMessage(request_id=r.id,request_key=body.request_key,channel=body.channel,recipient=recipient,body=message,signature=submission_signature,status='submitting',created_by=user.id);db.add(m);db.flush();mid=m.id;audit(db,user,'MESSAGE_SUBMITTED',r.id);db.commit()
 try:
  if body.channel=='email':
   from app.mail.microsoft365 import selected_provider,send_welcome
   payload={'from':os.getenv('RESEND_FROM_EMAIL','TNG Boxing <marketing@tngboxinggym.com>'),'to':[recipient],'subject':'TNG official availability request','text':message,'html':'<div style="font-family:Arial;white-space:pre-wrap">'+html.escape(message).replace(html.escape(link),'<a href="'+html.escape(link,quote=True)+'">Reply with availability</a>')+'</div>'}
   if selected_provider(db)=='microsoft365':result=send_welcome(db,payload,f'tng-official-message-{mid}')
   else:
    import resend
    if not os.getenv('RESEND_API_KEY'):raise RuntimeError('Email is not configured')
    resend.api_key=os.environ['RESEND_API_KEY'];result=resend.Emails.send(payload,options={'idempotency_key':f'tng-official-message-{mid}'})
   provider_id=result.get('id') if isinstance(result,dict) else None
   if not provider_id:raise RuntimeError('Provider did not return a submission reference')
  else:
   from twilio.rest import Client
   from twilio.http.http_client import TwilioHttpClient
   from app.services.sms_service import ensure_stop_footer
   client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=15));provider_id=client.messages.create(to=recipient,messaging_service_sid=service,body=ensure_stop_footer(message)).sid
  m=db.get(OfficialMessage,mid);m.status='accepted';m.provider_id=str(provider_id)[:120];db.commit();return {'status':'accepted','notice':'Accepted by provider; delivery is not confirmed'}
 except Exception:
  db.rollback();m=db.get(OfficialMessage,mid);m.status='unknown';m.error='Submission could not be confirmed. Check the email/SMS provider before sending again.';db.commit();return {'status':'unknown','error':m.error}
class PublicToken(BaseModel):token:str=Field(min_length=32,max_length=100)
class PublicReply(PublicToken):
 availability:dict[str,Literal['available','tentative','unavailable']]
 note:str=Field(default='',max_length=2000)
 version:int=Field(ge=1)
def public_request(db,token):
 r=db.query(OfficialRequest).filter_by(token_hash=digest(token)).with_for_update().first()
 if not r or r.expires_at<datetime.utcnow():raise HTTPException(404,'This availability link is invalid or expired. Ask TNG for a new request')
 contact=db.get(DirectoryContact,r.contact_id)
 if not contact or not contact.active or not contact.role_verified:raise HTTPException(404,'This request is no longer available')
 return r,fresh(db,r),contact
@router.post('/public/view')
def public_view(body:PublicToken,request:Request,response:Response,db=Depends(get_db)):
 throttle(db,'official-view:'+str(request.client.host if request.client else 'unknown'),30);r,c,contact=public_request(db,body.token);response.headers['Cache-Control']='no-store';return {'official_name':contact.name,'event_name':c['name'],'venue':c['venue'],'sessions':[{k:s.get(k) for k in ('key','label','date','start_local','end_local','optional')} for s in c['sessions']],'availability':r.availability,'note':r.reply_note,'version':r.version}
@router.post('/public/reply')
def public_reply(body:PublicReply,request:Request,response:Response,db=Depends(get_db)):
 throttle(db,'official-reply:'+str(request.client.host if request.client else 'unknown'),10);r,c,_=public_request(db,body.token);keys={s['key'] for s in c['sessions']}
 if r.version!=body.version:raise HTTPException(409,'Response changed. Reopen your link before submitting')
 if set(body.availability)!=keys:raise HTTPException(422,'Choose availability for every listed session')
 r.confirmed_roles={k:v for k,v in r.confirmed_roles.items() if r.availability.get(k)==body.availability.get(k)};r.availability=body.availability;r.reply_note=body.note;r.replied_at=datetime.utcnow();r.version+=1;db.add(OfficialMessage(request_id=r.id,request_key='reply:'+secrets.token_hex(16),channel='reply',recipient='',body=json.dumps({'availability':body.availability,'note':body.note}),signature=digest(json.dumps(body.availability,sort_keys=True)+body.note),status='received',created_by=None));audit(db,None,'PUBLIC_REPLY',r.id);db.commit();response.headers['Cache-Control']='no-store';return {'saved':True,'version':r.version,'notice':'Availability received. TNG will confirm assignments separately.'}
