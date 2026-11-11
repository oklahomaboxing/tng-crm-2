"""Administrator call ledger and structured, non-transcribed interaction history."""
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import JSONResponse
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,or_
from sqlalchemy.orm import Session
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.models import Lead
from .routes import PhoneCall,PhoneCallDepartment,config

router=APIRouter(prefix='/api/phone/admin/calls',tags=['Call Center'])
class PhoneCallActivity(Base):
    __tablename__='phone_call_activities'
    id=Column(Integer,primary_key=True)
    call_sid=Column(String(80),ForeignKey('phone_assistant_calls.call_sid'),nullable=False,index=True)
    action=Column(String(50),nullable=False)
    detail=Column(String(100),nullable=False)
    duration_seconds=Column(Integer,nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

def activity(db,call,action,detail,duration=None):
    db.add(PhoneCallActivity(call_sid=call.call_sid,action=action,detail=detail,duration_seconds=duration))

def stamp(value):return value.isoformat()+'Z' if value else None

def bounds(day):
    local=ZoneInfo('America/Chicago')
    return datetime.combine(day,time.min,tzinfo=local).astimezone(timezone.utc).replace(tzinfo=None)

@router.get('')
def calls(start:date|None=None,end:date|None=None,q:str=Query('',max_length=100),outcome:str='all',page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    if start and end and start>end:raise HTTPException(400,'Start date must be before end date')
    query=db.query(PhoneCall)
    if start:query=query.filter(PhoneCall.created_at>=bounds(start))
    if end:query=query.filter(PhoneCall.created_at<bounds(end+timedelta(days=1)))
    if q.strip():
        escaped=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        term='%'+escaped+'%'
        query=query.filter(or_(PhoneCall.caller_phone.ilike(term,escape='\\'),PhoneCall.caller_name.ilike(term,escape='\\')))
    # Summary uses the date/search scope before the outcome filter.
    summary={'total':query.count(),'callbacks':query.filter(PhoneCall.lead_id.isnot(None)).count(),'transferred':query.filter(PhoneCall.stage.in_(['staff_connected','marketing_connected'])).count(),'in_progress':query.filter(PhoneCall.status.in_(['queued','ringing','in-progress'])).count()}
    if outcome=='callbacks':query=query.filter(PhoneCall.lead_id.isnot(None))
    elif outcome=='transferred':query=query.filter(PhoneCall.stage.in_(['staff_connected','marketing_connected']))
    elif outcome=='in_progress':query=query.filter(PhoneCall.status.in_(['queued','ringing','in-progress']))
    elif outcome!='all':raise HTTPException(400,'Unknown call filter')
    total=query.count();rows=query.order_by(PhoneCall.created_at.desc(),PhoneCall.call_sid.desc()).offset((page-1)*page_size).limit(page_size).all()
    departments={r.call_sid:r.department for r in db.query(PhoneCallDepartment).filter(PhoneCallDepartment.call_sid.in_([c.call_sid for c in rows]))} if rows else {}
    cfg=config(db)
    return JSONResponse({'calls':[{'call_sid':c.call_sid,'caller_phone':c.caller_phone,'caller_name':c.caller_name,'status':c.status,'stage':c.stage,'department':departments.get(c.call_sid),'lead_id':c.lead_id,'created_at':stamp(c.created_at)} for c in rows],'total':total,'page':page,'page_size':page_size,'summary':summary,'public_number':cfg.public_number},headers={'Cache-Control':'private, no-store'})

@router.get('/{call_sid}')
def detail(call_sid:str,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    call=db.get(PhoneCall,call_sid)
    if not call:raise HTTPException(404,'Call not found')
    from .tickets import PhoneTicketDelivery
    events=db.query(PhoneCallActivity).filter_by(call_sid=call_sid).order_by(PhoneCallActivity.created_at,PhoneCallActivity.id).all()
    lead=db.get(Lead,call.lead_id) if call.lead_id else None
    duration=next((e.duration_seconds for e in reversed(events) if e.duration_seconds is not None),None)
    return JSONResponse({'call_sid':call.call_sid,'caller_phone':call.caller_phone,'caller_name':call.caller_name,'status':call.status,'stage':call.stage,'created_at':stamp(call.created_at),'duration_seconds':duration,'lead_id':call.lead_id,'callback_notes':lead.notes if lead else None,'timeline':[{'id':e.id,'action':e.action,'detail':e.detail,'created_at':stamp(e.created_at)} for e in events],'ticket_links':[{'status':t.status,'created_at':stamp(t.created_at)} for t in db.query(PhoneTicketDelivery).filter_by(call_sid=call_sid).order_by(PhoneTicketDelivery.id)]},headers={'Cache-Control':'private, no-store'})
