"""Public media applications and staff review, separate from tickets and memberships."""
import csv,io,os
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel,Field,EmailStr,field_validator
from sqlalchemy import Column,Integer,String,Text,Boolean,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.exc import IntegrityError
from app.database import Base,get_db
from app.core.dependencies import staff_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent
from app.ticketing.delivery import normalize_ticket_phone
router=APIRouter(prefix='/api/events',tags=['Media applications'])
class MediaSettings(Base):
    __tablename__='event_media_settings'
    event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
    enabled=Column(Boolean,nullable=False,default=False)
class MediaApplication(Base):
    __tablename__='event_media_applications'
    __table_args__=(UniqueConstraint('event_id','email',name='uq_event_media_email'),)
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    name=Column(String(160),nullable=False)
    email=Column(String(255),nullable=False)
    phone=Column(String(40),nullable=False,default='')
    outlet=Column(String(200),nullable=False)
    role=Column(String(30),nullable=False)
    website=Column(String(500),nullable=False,default='')
    team_size=Column(Integer,nullable=False,default=1)
    coverage=Column(Text,nullable=False,default='')
    referred_by=Column(String(160),nullable=False,default='')
    status=Column(String(20),nullable=False,default='pending')
    staff_notes=Column(Text,nullable=False,default='')
    created_at=Column(DateTime,nullable=False,default=datetime.utcnow)
    reviewed_at=Column(DateTime,nullable=True)
    reviewed_by=Column(Integer,ForeignKey('users.id'),nullable=True)
def event_for(db,event_id):
    event=db.get(BoxingEvent,event_id)
    if not event:raise HTTPException(404,'Event not found')
    return event
def link(event_id):return os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+f'/events/{event_id}/media'
class Application(BaseModel):
    name:str=Field(min_length=2,max_length=160)
    email:EmailStr=Field(max_length=255)
    phone:str=Field(default='',max_length=40)
    outlet:str=Field(min_length=2,max_length=200)
    role:Literal['photographer','videographer','journalist','broadcaster','content_creator','other']
    website:str=Field(default='',max_length=500)
    team_size:int=Field(default=1,ge=1,le=10)
    coverage:str=Field(default='',max_length=2000)
    referred_by:str=Field(default='',max_length=160)
    acknowledge:bool
    website_confirmation:str=Field(default='',max_length=500)
    @field_validator('name','outlet')
    @classmethod
    def text(cls,v):
        v=v.strip()
        if len(v)<2:raise ValueError('Enter at least two characters')
        return v
    @field_validator('website')
    @classmethod
    def website_url(cls,v):
        v=v.strip()
        if v and (urlsplit(v).scheme not in ('https','http') or not urlsplit(v).hostname):raise ValueError('Use an https:// or http:// website or social profile link')
        return v
    @field_validator('phone')
    @classmethod
    def phone_number(cls,v):return normalize_ticket_phone(v)
    @field_validator('acknowledge')
    @classmethod
    def acknowledged(cls,v):
        if not v:raise ValueError('Acknowledge that a request does not grant admission')
        return v
@router.get('/{event_id}/media/public')
def public_event(event_id:int,response:Response,db=Depends(get_db)):
    event=event_for(db,event_id);cfg=db.get(MediaSettings,event_id);response.headers['Cache-Control']='no-store'
    opened=bool(cfg and cfg.enabled)
    return {'event_id':event.id,'event_name':event.name if opened else 'TNG Boxing Event','event_date':event.event_date if opened else None,'venue':event.venue if opened else None,'open':opened}
@router.post('/{event_id}/media/apply')
def apply(event_id:int,body:Application,request:Request,response:Response,db=Depends(get_db)):
    event_for(db,event_id);cfg=db.get(MediaSettings,event_id)
    if not cfg or not cfg.enabled:raise HTTPException(409,'Media applications are closed. Contact marketing@tngboxinggym.com.')
    from app.kiosk.routes import throttle
    try:throttle(db,f'media:{event_id}:ip:'+(request.client.host if request.client else 'unknown'),10)
    except HTTPException as exc:
        if exc.status_code==429:raise HTTPException(429,'Too many requests. Please wait a minute and try again.',headers={'Retry-After':'60'})
        raise
    cfg=db.query(MediaSettings).filter_by(event_id=event_id).with_for_update().first()
    if not cfg or not cfg.enabled:raise HTTPException(409,'Media applications are closed. Contact marketing@tngboxinggym.com.')
    response.headers['Cache-Control']='no-store'
    if body.website_confirmation:return {'received':True}
    email=str(body.email).strip().casefold()
    if db.query(MediaApplication.id).filter_by(event_id=event_id,email=email).first():return {'received':True}
    row=MediaApplication(event_id=event_id,name=body.name,email=email,phone=body.phone,outlet=body.outlet,role=body.role,website=body.website,team_size=body.team_size,coverage=body.coverage.strip(),referred_by=body.referred_by.strip())
    db.add(row)
    try:db.commit()
    except IntegrityError:
        db.rollback()
        if not db.query(MediaApplication.id).filter_by(event_id=event_id,email=email).first():raise
    return {'received':True}
class SettingsBody(BaseModel):enabled:bool
@router.put('/{event_id}/media/settings')
def settings(event_id:int,body:SettingsBody,db=Depends(get_db),user=Depends(staff_user)):
    event_for(db,event_id);row=db.get(MediaSettings,event_id)
    if not row:row=MediaSettings(event_id=event_id);db.add(row)
    row.enabled=body.enabled
    db.add(SecurityLog(user_id=user.id,action='MEDIA_APPLICATION_SETTINGS',description=f'Event {event_id}; enabled={body.enabled}',success=True));db.commit()
    return {'enabled':row.enabled,'public_url':link(event_id)}
@router.get('/{event_id}/media/requests')
def requests(event_id:int,response:Response,db=Depends(get_db),user=Depends(staff_user)):
    event_for(db,event_id);cfg=db.get(MediaSettings,event_id);response.headers['Cache-Control']='private, no-store'
    rows=db.query(MediaApplication).filter_by(event_id=event_id).order_by(MediaApplication.id.desc()).all()
    return {'enabled':bool(cfg and cfg.enabled),'public_url':link(event_id),'requests':[{'id':r.id,'name':r.name,'email':r.email,'phone':r.phone,'outlet':r.outlet,'role':r.role,'website':r.website,'team_size':r.team_size,'coverage':r.coverage,'referred_by':r.referred_by,'status':r.status,'staff_notes':r.staff_notes,'created_at':r.created_at.isoformat()+'Z','reviewed_at':r.reviewed_at.isoformat()+'Z' if r.reviewed_at else None} for r in rows]}
class Review(BaseModel):
    status:Literal['pending','approved','declined']
    staff_notes:str=Field(default='',max_length=2000)
@router.put('/{event_id}/media/requests/{request_id}')
def review(event_id:int,request_id:int,body:Review,db=Depends(get_db),user=Depends(staff_user)):
    row=db.query(MediaApplication).filter_by(id=request_id,event_id=event_id).with_for_update().first()
    if not row:raise HTTPException(404,'Media request not found')
    row.status=body.status;row.staff_notes=body.staff_notes.strip();row.reviewed_at=datetime.utcnow();row.reviewed_by=user.id
    db.add(SecurityLog(user_id=user.id,action='MEDIA_REQUEST_REVIEWED',description=f'Event {event_id}; request {request_id}; status={body.status}',success=True));db.commit()
    return {'status':row.status,'notification_sent':False}
@router.get('/{event_id}/media/requests.csv')
def export(event_id:int,db=Depends(get_db),user=Depends(staff_user)):
    event_for(db,event_id);out=io.StringIO();w=csv.writer(out);w.writerow(['Name','Email','Phone','Outlet','Role','People','Website / social','Referred by','Status','Coverage','Staff notes'])
    def safe(v):
        s=str(v or '');return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    for r in db.query(MediaApplication).filter_by(event_id=event_id).order_by(MediaApplication.id):w.writerow([safe(v) for v in [r.name,r.email,r.phone,r.outlet,r.role,r.team_size,r.website,r.referred_by,r.status,r.coverage,r.staff_notes]])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="tng_event_{event_id}_media_requests.csv"'})
