"""Facility booking requests and a restricted coordinator calendar (America/Chicago)."""
import os, secrets
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, EmailStr, model_validator
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, text
from app.database import Base, get_db
from app.core.dependencies import current_user
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent
from app.kiosk.routes import throttle
from app.ticketing.delivery import normalize_ticket_phone

router=APIRouter(prefix='/api/venue', tags=['Venue bookings'])
TZ=ZoneInfo('America/Chicago')
BLOCKING={'on_hold','confirmed'}
ADDRESS='8416 NW Expressway, Oklahoma City, OK 73162'

class VenueSettings(Base):
    __tablename__='venue_booking_settings'
    id=Column(Integer,primary_key=True)
    enabled=Column(Boolean,default=True,nullable=False)
    version=Column(Integer,default=1,nullable=False)

class VenueBooking(Base):
    __tablename__='venue_bookings'
    __table_args__=(UniqueConstraint('request_key',name='uq_venue_request_key'),)
    id=Column(Integer,primary_key=True)
    reference=Column(String(40),unique=True,nullable=False)
    request_key=Column(String(100),nullable=False)
    title=Column(String(160),nullable=False)
    event_type=Column(String(80),nullable=False)
    contact_name=Column(String(160),nullable=False)
    email=Column(String(254),nullable=False)
    phone=Column(String(40),nullable=False)
    starts_at=Column(DateTime,nullable=False,index=True)
    ends_at=Column(DateTime,nullable=False,index=True)
    guests=Column(Integer,default=1,nullable=False)
    details=Column(Text,default='',nullable=False)
    staff_notes=Column(Text,default='',nullable=False)
    status=Column(String(20),default='requested',nullable=False)
    source=Column(String(20),default='public',nullable=False)
    created_by=Column(Integer,ForeignKey('users.id'),nullable=True)
    updated_by=Column(Integer,ForeignKey('users.id'),nullable=True)
    version=Column(Integer,default=1,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)
    updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class BookingBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=2,max_length=160)
    event_type:str=Field(min_length=2,max_length=80)
    contact_name:str=Field(min_length=2,max_length=160)
    email:EmailStr=Field(max_length=254)
    phone:str=Field(min_length=10,max_length=40)
    starts_local:datetime
    ends_local:datetime
    guests:int=Field(default=1,ge=1,le=10000)
    details:str=Field(default='',max_length=4000)
    request_key:str=Field(min_length=16,max_length=80)
    acknowledge:bool
    website_confirmation:str=Field(default='',max_length=300)
    @model_validator(mode='after')
    def validate_booking(self):
        for k in ('title','event_type','contact_name'):
            setattr(self,k,getattr(self,k).strip())
            if len(getattr(self,k))<2:raise ValueError('Enter complete event and contact names')
        self.phone=normalize_ticket_phone(self.phone)
        if not self.phone:raise ValueError('Enter a complete contact phone number')
        if not self.acknowledge:raise ValueError('Acknowledge that a request is not a confirmed booking')
        start=utc_local(self.starts_local);end=utc_local(self.ends_local)
        if end<=start or end-start>timedelta(days=7):raise ValueError('End time must follow start time, with a maximum seven-day booking')
        if start<datetime.utcnow()-timedelta(minutes=5):raise ValueError('Choose a future start time')
        if start>datetime.utcnow()+timedelta(days=730):raise ValueError('Choose a date within the next two years')
        return self

class ReviewBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:Literal['requested','on_hold','confirmed','declined','cancelled']
    staff_notes:str=Field(default='',max_length=8000)
    version:int=Field(ge=1)
    starts_local:datetime|None=None
    ends_local:datetime|None=None
    @model_validator(mode='after')
    def validate_times(self):
        if bool(self.starts_local)!=bool(self.ends_local):raise ValueError('Provide both start and end times')
        if self.starts_local:
            start=utc_local(self.starts_local);end=utc_local(self.ends_local)
            if end<=start or end-start>timedelta(days=7):raise ValueError('End time must follow start time, within seven days')
        return self

class SettingsBody(BaseModel):
    enabled:bool
    version:int=Field(ge=1)

def utc_local(value):
    if value.tzinfo is not None:raise ValueError('Use local Oklahoma City time without a timezone suffix')
    a=value.replace(tzinfo=TZ,fold=0);b=value.replace(tzinfo=TZ,fold=1)
    if a.utcoffset()!=b.utcoffset() or a.astimezone(timezone.utc).astimezone(TZ).replace(tzinfo=None)!=value:raise ValueError('Choose an unambiguous Oklahoma City time outside the daylight-saving change')
    return a.astimezone(timezone.utc).replace(tzinfo=None)

def staff(user=Depends(current_user)):
    if user.role not in ('admin','event_coordinator'):raise HTTPException(403,'Event coordinator or administrator access required')
    return user

def lock_calendar(db):
    if db.get_bind().dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(8426202601)'))

def config(db):
    c=db.get(VenueSettings,1)
    if not c:c=VenueSettings(id=1,enabled=True,version=1);db.add(c);db.flush()
    return c

def reserved_events(db):
    result=[]
    for e in db.query(BoxingEvent).filter(~BoxingEvent.status.in_(['cancelled','canceled','archived'])).all():
        v=((e.venue or '')+' '+(e.venue_address or '')).lower()
        if not ('8416' in v or 'tng boxing' in v):continue
        try:day=date.fromisoformat((e.event_date or '')[:10])
        except ValueError:continue
        result.append((e,utc_local(datetime.combine(day,time.min)),utc_local(datetime.combine(day+timedelta(days=1),time.min))))
    return result

def conflicts(db,start,end,exclude=None):
    q=db.query(VenueBooking).filter(VenueBooking.status.in_(BLOCKING),VenueBooking.starts_at<end,VenueBooking.ends_at>start)
    if exclude:q=q.filter(VenueBooking.id!=exclude)
    return bool(q.first()) or any(s<end and e>start for _,s,e in reserved_events(db))

def serialize(row):
    fields=('id','reference','title','event_type','contact_name','email','phone','guests','details','staff_notes','status','source','version','created_by','updated_by')
    return {**{k:getattr(row,k) for k in fields},'starts_at':row.starts_at.isoformat()+'Z','ends_at':row.ends_at.isoformat()+'Z','created_at':row.created_at.isoformat()+'Z','updated_at':row.updated_at.isoformat()+'Z'}

def audit(db,user,row,action):db.add(SecurityLog(user_id=user.id,action='VENUE_'+action,description=f'Facility booking {row.id} ({row.reference}); status {row.status}'))

@router.get('/public')
def public(response:Response,db=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    c=db.get(VenueSettings,1)
    return {'enabled':c.enabled if c else True,'venue':'TNG Boxing','address':ADDRESS,'timezone':'America/Chicago','notice':'Submit a facility request. Your date is reserved only after TNG confirms the booking. Rental pricing and terms are arranged with our team.'}

@router.get('/public/availability')
def availability(start:date,end:date,response:Response,db=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    c=db.get(VenueSettings,1)
    if c and not c.enabled:raise HTTPException(409,'Facility requests are currently closed')
    if end<=start or (end-start).days>62:raise HTTPException(422,'Select a date range of up to 62 days')
    s=utc_local(datetime.combine(start,time.min));e=utc_local(datetime.combine(end,time.min))
    rows=db.query(VenueBooking).filter(VenueBooking.status.in_(BLOCKING),VenueBooking.starts_at<e,VenueBooking.ends_at>s).all()
    intervals=[{'starts_at':r.starts_at.isoformat()+'Z','ends_at':r.ends_at.isoformat()+'Z'} for r in rows]
    intervals += [{'starts_at':a.isoformat()+'Z','ends_at':b.isoformat()+'Z'} for _,a,b in reserved_events(db) if a<e and b>s]
    return {'timezone':'America/Chicago','unavailable':intervals}

@router.post('/public/requests')
def public_request(body:BookingBody,request:Request,response:Response,db=Depends(get_db)):
    throttle(db,'venue:ip:'+(request.client.host if request.client else 'unknown'),5)
    response.headers['Cache-Control']='no-store'
    lock_calendar(db);c=config(db)
    if not c.enabled:raise HTTPException(409,'Facility requests are currently closed')
    if body.website_confirmation:return {'received':True,'status':'requested'}
    return save_request(db,body,request_key='public:'+body.request_key)

def save_request(db,body,user=None,request_key=None):
    key=request_key or 'staff:'+str(user.id)+':'+body.request_key
    start=utc_local(body.starts_local);end=utc_local(body.ends_local);email=str(body.email).lower()
    prior=db.query(VenueBooking).filter_by(request_key=key).first()
    if prior:
        if (prior.email,prior.title,prior.starts_at,prior.ends_at)!=(email,body.title,start,end):raise HTTPException(409,'This request key was already used. Start a new request')
        return {'received':True,'reference':prior.reference,'status':prior.status}
    if conflicts(db,start,end):raise HTTPException(409,'That time overlaps a confirmed booking, hold or TNG event at this facility. Choose another time or contact TNG')
    row=VenueBooking(reference='TNG-V-'+secrets.token_hex(5).upper(),request_key=key,title=body.title,event_type=body.event_type,contact_name=body.contact_name,email=email,phone=body.phone,starts_at=start,ends_at=end,guests=body.guests,details=body.details.strip(),status='requested',source='staff' if user else 'public',created_by=user.id if user else None)
    db.add(row);db.flush()
    if user:audit(db,user,row,'CREATED')
    db.commit();return {'received':True,'reference':row.reference,'status':'requested'}

@router.get('/calendar')
def calendar(response:Response,start:date,end:date,db=Depends(get_db),user=Depends(staff)):
    response.headers['Cache-Control']='private, no-store'
    if end<=start or (end-start).days>366:raise HTTPException(422,'Select up to one year')
    s=utc_local(datetime.combine(start,time.min));e=utc_local(datetime.combine(end,time.min))
    rows=db.query(VenueBooking).filter(VenueBooking.starts_at<e,VenueBooking.ends_at>s).order_by(VenueBooking.starts_at).all()
    inbox=db.query(VenueBooking).filter_by(status='requested').order_by(VenueBooking.created_at).limit(200).all()
    events=db.query(BoxingEvent).filter(BoxingEvent.event_date>=start.isoformat(),BoxingEvent.event_date<end.isoformat()).order_by(BoxingEvent.event_date).all()
    cfg=db.get(VenueSettings,1);blocking_ids={ev.id for ev,_,_ in reserved_events(db)}
    from .venue_quotes import calendar_quote_states
    return {'quote_statuses':calendar_quote_states(db,rows+inbox),'bookings':[serialize(r) for r in rows],'requests':[serialize(r) for r in inbox],'events':[{'id':x.id,'name':x.name,'date':x.event_date,'venue':x.venue,'status':x.status,'blocks_facility':x.id in blocking_ids} for x in events],'settings':{'enabled':cfg.enabled if cfg else True,'version':cfg.version if cfg else 1},'timezone':'America/Chicago','public_url':os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/venue/book'}

@router.post('/bookings')
def internal_request(body:BookingBody,db=Depends(get_db),user=Depends(staff)):
    lock_calendar(db);return save_request(db,body,user)

@router.patch('/bookings/{booking_id}')
def review(booking_id:int,body:ReviewBody,db=Depends(get_db),user=Depends(staff)):
    lock_calendar(db)
    row=db.query(VenueBooking).filter_by(id=booking_id).with_for_update().first()
    if not row:raise HTTPException(404,'Booking not found')
    if row.version!=body.version:raise HTTPException(409,'This booking changed. Refresh before updating')
    start=utc_local(body.starts_local) if body.starts_local else row.starts_at
    end=utc_local(body.ends_local) if body.ends_local else row.ends_at
    if (start,end)!=(row.starts_at,row.ends_at) and start<datetime.utcnow():raise HTTPException(422,'Choose a future start time when rescheduling')
    if body.status in BLOCKING and conflicts(db,start,end,row.id):raise HTTPException(409,'This overlaps another reserved booking or an event at TNG. Resolve the conflict before reserving')
    if (start,end)!=(row.starts_at,row.ends_at):
        from .venue_quotes import latest,paid
        q=latest(db,row.id)
        if q and paid(db,q):raise HTTPException(409,'A receipt is recorded. Resolve the payment before rescheduling this quoted booking')
    if body.status=='confirmed':
        from .venue_quotes import check_quote_confirmation
        check_quote_confirmation(db,row,start,end)
    row.starts_at=start;row.ends_at=end
    row.status=body.status;row.staff_notes=body.staff_notes.strip();row.updated_by=user.id;row.updated_at=datetime.utcnow();row.version+=1;audit(db,user,row,'UPDATED');db.commit();return serialize(row)

@router.put('/settings')
def settings(body:SettingsBody,db=Depends(get_db),user=Depends(staff)):
    lock_calendar(db);row=config(db)
    if row.version!=body.version:raise HTTPException(409,'Settings changed. Refresh before updating')
    row.enabled=body.enabled;row.version+=1;db.add(SecurityLog(user_id=user.id,action='VENUE_REQUESTS_TOGGLED',description=f'Facility request form enabled: {row.enabled}'));db.commit();return {'enabled':row.enabled,'version':row.version}

# Register quote models before the application's metadata initialization.
from . import venue_quotes
