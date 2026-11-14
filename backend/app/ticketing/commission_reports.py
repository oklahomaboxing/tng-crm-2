"""Explicit commission report submissions, immutable snapshots and deadline alerts."""
import base64,hashlib,io,json,zipfile
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
from html import escape
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field,field_validator
from email_validator import validate_email,EmailNotValidError
from sqlalchemy import Column,Integer,String,Text,DateTime,Boolean,ForeignKey
from sqlalchemy.orm import Session
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent
from .sales_reports import report_data,export_pdf,export_csv
router=APIRouter(prefix='/api/ticketing',tags=['Commission report submission'])
CT=ZoneInfo('America/Chicago')
TO='Heather.Turner@osac.ok.gov';CC='Diana.Fletcher@osac.ok.gov'
class CommissionReportSettings(Base):
 __tablename__='commission_report_settings'
 event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
 to_email=Column(String(255),nullable=False)
 cc_email=Column(String(255),nullable=False)
 confirmed=Column(Boolean,nullable=False,default=False)
 deadline=Column(DateTime,nullable=False)
 closes_at=Column(DateTime,nullable=False)
 enabled=Column(Boolean,nullable=False,default=True)
class CommissionReportSubmission(Base):
 __tablename__='commission_report_submissions'
 id=Column(Integer,primary_key=True)
 event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
 signature=Column(String(64),nullable=False,unique=True)
 report_hash=Column(String(64),nullable=False)
 payload_json=Column(Text,nullable=False)
 status=Column(String(30),nullable=False,default='submitting')
 provider_id=Column(String(255),nullable=True)
 error=Column(String(255),nullable=True)
 created_at=Column(DateTime,nullable=False,default=datetime.utcnow)
 accepted_at=Column(DateTime,nullable=True)

def utc(value):return value.replace(tzinfo=timezone.utc)
def iso(value):return utc(value).isoformat() if value else None
def local(value):return utc(value).astimezone(CT).strftime('%Y-%m-%dT%H:%M')
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
def event_for(db,eid):
 e=db.get(BoxingEvent,eid)
 if not e:raise HTTPException(404,'Event not found')
 return e
def defaults(event):
 try:day=date.fromisoformat(event.event_date)
 except (ValueError,TypeError):raise HTTPException(400,'Set a valid event date before configuring reports')
 return datetime.combine(day+timedelta(days=1),time.min,CT).astimezone(timezone.utc).replace(tzinfo=None),datetime.combine(day+timedelta(days=2),time(1),CT).astimezone(timezone.utc).replace(tzinfo=None)
def fingerprint(data):return digest({'event':{'id':data[0].id,'name':data[0].name,'date':data[0].event_date},'records':data[1:]})
def state(db,eid,now=None):
 event=event_for(db,eid);data=report_data(db,eid);key=fingerprint(data);cfg=db.get(CommissionReportSettings,eid)
 deadline,closes=defaults(event) if not cfg else (cfg.deadline,cfg.closes_at)
 accepted=db.query(CommissionReportSubmission).filter_by(signature=digest([eid,key,cfg.to_email.lower(),cfg.cc_email.lower()]),status='accepted').first() if cfg else None
 rows=db.query(CommissionReportSubmission).filter_by(event_id=eid).order_by(CommissionReportSubmission.id.desc()).limit(10).all();now=now or datetime.utcnow()
 return {'event_id':eid,'event_name':event.name,'report_hash':key,'summary':data[1],'to':cfg.to_email if cfg else TO,'cc':cfg.cc_email if cfg else CC,'confirmed':bool(cfg and cfg.confirmed),'enabled':bool(cfg and cfg.enabled),'deadline':iso(deadline),'closes_at':iso(closes),'deadline_local':local(deadline),'closes_local':local(closes),'submitted_current_report':bool(accepted),'overdue':bool(cfg and cfg.enabled and now>=deadline and not accepted),'window_closed':now>=closes,'server_now':iso(now),'history':[{'id':r.id,'status':r.status,'created_at':iso(r.created_at),'accepted_at':iso(r.accepted_at),'error':r.error,'current_snapshot':r.report_hash==key} for r in rows]}
class Settings(BaseModel):
 to:str=Field(max_length=255)
 cc:str=Field(max_length=255)
 confirmed:bool=False
 enabled:bool=True
 deadline_local:str
 closes_local:str
 @field_validator('to','cc')
 @classmethod
 def email(cls,value):
  try:return validate_email(value.strip(),check_deliverability=False).normalized
  except EmailNotValidError:raise ValueError('Enter a valid email address')
def parse_local(value):
 try:
  d=datetime.fromisoformat(value)
  if d.tzinfo:raise ValueError()
  return d.replace(tzinfo=CT).astimezone(timezone.utc).replace(tzinfo=None)
 except ValueError:raise HTTPException(400,'Enter a valid Oklahoma City date and time')
@router.get('/events/{event_id}/commission-submission')
def status(event_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 require_admin(user);return JSONResponse(state(db,event_id),headers={'Cache-Control':'private, no-store'})
@router.put('/events/{event_id}/commission-submission')
def settings(event_id:int,body:Settings,db:Session=Depends(get_db),user=Depends(current_user)):
 require_admin(user);event_for(db,event_id);deadline=parse_local(body.deadline_local);closes=parse_local(body.closes_local)
 if closes<=deadline:raise HTTPException(400,'Report window must close after the alert deadline')
 cfg=db.query(CommissionReportSettings).filter_by(event_id=event_id).with_for_update().first()
 if not cfg:cfg=CommissionReportSettings(event_id=event_id);db.add(cfg)
 cfg.to_email=body.to;cfg.cc_email=body.cc;cfg.confirmed=body.confirmed;cfg.enabled=body.enabled;cfg.deadline=deadline;cfg.closes_at=closes
 db.add(SecurityLog(user_id=user.id,action='COMMISSION_REPORT_SETTINGS',description=f'Event {event_id}; recipients and Oklahoma City schedule saved; confirmed={body.confirmed}',success=True));db.commit()
 return JSONResponse(state(db,event_id),headers={'Cache-Control':'private, no-store'})
@router.get('/commission-report-alerts')
def alerts(db:Session=Depends(get_db),user=Depends(current_user)):
 require_admin(user);rows=db.query(CommissionReportSettings).filter_by(enabled=True).all()
 return JSONResponse({'events':[state(db,r.event_id) for r in rows],'server_now':iso(datetime.utcnow())},headers={'Cache-Control':'private, no-store'})
async def content(response):
 if hasattr(response,'body'):return response.body
 chunks=[]
 async for chunk in response.body_iterator:chunks.append(chunk.encode() if isinstance(chunk,str) else chunk)
 return b''.join(chunks)
async def packet(db,eid,user):
 from .routes import download_seller_report_csv,download_seller_report_pdf
 from .models import EventSeller
 files={f'TNG_{eid}_Master_Ticket_Report.pdf':await content(export_pdf(db,eid)),f'TNG_{eid}_Master_Ticket_Report.csv':await content(export_csv(db,eid))}
 for seller in db.query(EventSeller).filter_by(event_id=eid).order_by(EventSeller.id):
  files[f'Seller_{seller.id}_Report.pdf']=await content(download_seller_report_pdf(eid,seller.id,db,user))
  files[f'Seller_{seller.id}_Report.csv']=await content(download_seller_report_csv(eid,seller.id,db,user))
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
  for name,body in files.items():archive.writestr(name,body)
 master=f'TNG_{eid}_Master_Ticket_Report.pdf'
 return [{'filename':master,'content':base64.b64encode(files[master]).decode(),'content_type':'application/pdf'},{'filename':f'TNG_{eid}_All_Ticket_Reports.zip','content':base64.b64encode(out.getvalue()).decode(),'content_type':'application/zip'}],len(files)
class Send(BaseModel):
 report_hash:str=Field(min_length=64,max_length=64)
 acknowledge_late:bool=False
@router.post('/events/{event_id}/commission-submission/send')
async def send(event_id:int,body:Send,db:Session=Depends(get_db),user=Depends(current_user)):
 require_admin(user)
 cfg=db.query(CommissionReportSettings).filter_by(event_id=event_id).with_for_update().one_or_none()
 if not cfg or not cfg.confirmed:raise HTTPException(409,'Verify and save the commission recipients first')
 current=state(db,event_id)
 if not cfg.enabled:raise HTTPException(409,'Commission report submission is disabled')
 if body.report_hash!=current['report_hash']:raise HTTPException(409,'Ticket records changed. Refresh and review the latest report before sending.')
 if current['window_closed'] and not body.acknowledge_late:raise HTTPException(409,'Report window closed. Acknowledge a late submission to continue.')
 signature=digest([event_id,body.report_hash,cfg.to_email.lower(),cfg.cc_email.lower()]);row=db.query(CommissionReportSubmission).filter_by(signature=signature).first()
 if row and row.status=='accepted':db.commit();return {'status':'accepted','already_submitted':True}
 if row and row.status in ('unknown','submitting'):raise HTTPException(409,'Check Outlook Sent Items. This submission is uncertain and will not be sent again automatically.')
 pending=db.query(CommissionReportSubmission).filter(CommissionReportSubmission.event_id==event_id,CommissionReportSubmission.status.in_(['unknown','submitting'])).first()
 if pending:raise HTTPException(409,'An earlier commission submission needs review in Outlook Sent Items before another email can be sent.')
 if not row:
  attachments,file_count=await packet(db,event_id,user)
  # Verify that the financial snapshot stayed stable while rendering all reports.
  db.expire_all()
  if state(db,event_id)['report_hash']!=body.report_hash:raise HTTPException(409,'Ticket records changed while preparing reports. Refresh and try again.')
  payload={'to':[cfg.to_email],'cc':[cfg.cc_email],'subject':f'{current["event_name"]} — All Ticket Sales Reports','html':f'<p>TNG Promotions ticket sales reports for {escape(current["event_name"])}.</p><p>Attached: master report PDF and ZIP containing all event and seller PDF/CSV reports ({file_count} files). The report includes recorded paid sales, the 5% state commission calculation, and reconciliation notes for unpaid orders, refunds and paper stock. Submission does not remit payment.</p>','attachments':attachments}
  encoded=json.dumps(payload)
  if len(encoded.encode())>3_000_000:raise HTTPException(413,'The complete report package exceeds the email attachment limit. Download the reports and submit through Outlook.')
  row=CommissionReportSubmission(event_id=event_id,signature=signature,report_hash=body.report_hash,payload_json=encoded,status='submitting');db.add(row)
 else:row.status='submitting'
 db.commit()
 from app.mail.microsoft365 import send_welcome,MicrosoftMailAttempt
 try:
  result=send_welcome(db,json.loads(row.payload_json),f'tng-commission-report-{row.id}')
  if not result.get('id'):raise RuntimeError('Missing provider acknowledgment')
  row.status='accepted';row.provider_id=result['id'];row.accepted_at=datetime.utcnow();row.error=None
 except Exception as exc:
  attempt=db.get(MicrosoftMailAttempt,f'tng-commission-report-{row.id}')
  row.status='unknown' if attempt and attempt.status in ('unknown','submitting') else 'rejected'
  row.error='Microsoft submission uncertain; check Outlook Sent Items.' if row.status=='unknown' else 'Email was not accepted. Review the Microsoft 365 connection before retrying.'
 db.add(SecurityLog(user_id=user.id,action='COMMISSION_REPORT_SUBMITTED',description=f'Event {event_id}; report snapshot {row.report_hash}; status {row.status}; submission {row.id}',success=row.status=='accepted'));db.commit()
 return {'status':row.status,'already_submitted':False,'submission_id':row.id,'message':'Microsoft accepted the report email. This does not confirm inbox delivery.' if row.status=='accepted' else row.error}
