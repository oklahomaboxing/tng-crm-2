"""Limited planning-event edits from the facility calendar; live event obligations stay protected."""
import hashlib,json,secrets
from datetime import date,datetime,time,timedelta
from fastapi import Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import or_
from app.database import get_db
from app.models import SecurityLog
from app.matchmaker.models import BoxingEvent,BoxingBout,BoxingContract
from app.ticketing.models import TicketOrder,PaperTicketBatch,EventTicketType,EventSeller
from .venue import router,staff,lock_calendar,VenueBooking,BLOCKING,VenueBookingPromotion,reserved_events,utc_local

class PlanningEventBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 name:str=Field(min_length=2,max_length=160)
 event_date:date
 venue:str=Field(default='',max_length=250)
 venue_address:str=Field(default='',max_length=500)
 @model_validator(mode='after')
 def normalize(self):
  self.name=self.name.strip();self.venue=self.venue.strip();self.venue_address=self.venue_address.strip()
  if len(self.name)<2:raise ValueError('Enter a complete event name')
  if not 2000<=self.event_date.year<=2100:raise ValueError('Choose a year between 2000 and 2100')
  return self
class PlanningEventEdit(PlanningEventBody):
 schedule_version:str=Field(min_length=64,max_length=64)

def schedule_version(e):return hashlib.sha256(json.dumps([e.id,e.name,e.event_date,e.venue,e.venue_address,e.status]).encode()).hexdigest()
def protected_event(db,e,ignore_link=False,allow_cancelled=False):
 if not ignore_link and db.query(VenueBookingPromotion).filter_by(event_id=e.id).first():return True
 if e.status not in ('planning','draft') and not (allow_cancelled and e.status=='cancelled'):return True
 return any(db.query(model.id).filter(model.event_id==e.id).first() for model in (BoxingBout,BoxingContract,TicketOrder,PaperTicketBatch,EventTicketType,EventSeller))
def conflicts_for_event(db,body,exclude=None,exclude_booking=None):
 if '8416' not in (body.venue+' '+body.venue_address).lower() and 'tng boxing' not in (body.venue+' '+body.venue_address).lower():return
 start=utc_local(datetime.combine(body.event_date,time.min));end=utc_local(datetime.combine(body.event_date+timedelta(days=1),time.min))
 if db.query(VenueBooking.id).filter(VenueBooking.status.in_(BLOCKING),VenueBooking.starts_at<end,VenueBooking.ends_at>start,VenueBooking.id!=(exclude_booking or -1)).first() or any(e.id!=exclude and a<end and b>start for e,a,b in reserved_events(db)):
  raise HTTPException(409,'This date overlaps a facility hold, booking or TNG event. Resolve the calendar conflict first')

def event_result(db,e):return {'id':e.id,'name':e.name,'date':e.event_date,'venue':e.venue,'venue_address':e.venue_address,'status':e.status,'schedule_version':schedule_version(e),'schedule_editable':not protected_event(db,e)}

@router.post('/planning-events')
def add_event(body:PlanningEventBody,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);conflicts_for_event(db,body)
 e=BoxingEvent(slug='tng-event-'+secrets.token_hex(8),name=body.name,event_date=body.event_date.isoformat(),venue=body.venue,venue_address=body.venue_address,status='planning');db.add(e);db.flush();db.add(SecurityLog(user_id=user.id,action='VENUE_PLANNING_EVENT_CREATED',description=f'Created planning event {e.id} for {e.event_date}'));db.commit();return event_result(db,e)

@router.patch('/planning-events/{event_id}')
def edit_event(event_id:int,body:PlanningEventEdit,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);e=db.query(BoxingEvent).filter_by(id=event_id).with_for_update().first()
 if not e:raise HTTPException(404,'Event not found')
 if schedule_version(e)!=body.schedule_version:raise HTTPException(409,'Event changed. Refresh the yearly list before editing')
 if protected_event(db,e):raise HTTPException(409,'This event has live status, bouts, contracts or ticket records. Use the event workspace for coordinated changes')
 conflicts_for_event(db,body,e.id)
 e.name=body.name;e.event_date=body.event_date.isoformat();e.venue=body.venue;e.venue_address=body.venue_address
 db.add(SecurityLog(user_id=user.id,action='VENUE_PLANNING_EVENT_UPDATED',description=f'Updated planning event {e.id} for {e.event_date}'));db.commit();return event_result(db,e)
