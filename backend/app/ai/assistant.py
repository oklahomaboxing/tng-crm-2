"""Owner's read-only voice assistant. Models select topics, never invent business figures."""
import json
import os
import re
import time
from datetime import datetime,time as day_time,timedelta,timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,ForeignKey,func,case
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.models import Member,Attendance
from app.services.member_reporting import membership_evidence,membership_totals
from app.matchmaker.models import BoxingEvent,BoxingBout,BoxingContract,BoxingEventChecklist
from app.ticketing.models import TicketOrder,IssuedTicket,PaperTicket,PaperTicketBatch
from app.operations.overview import operations_overview,expected_quantity
from app.ai.client import client

router=APIRouter(prefix='/api/assistant',tags=['TNG Assistant'])
Topic=Literal['overview','members','tickets','card','updates','help']

class AssistantUsage(Base):
    __tablename__='assistant_usage_windows'
    user_id=Column(Integer,ForeignKey('users.id'),primary_key=True)
    window=Column(Integer,nullable=False)
    requests=Column(Integer,nullable=False)

class Question(BaseModel):
    question:str=Field(min_length=1,max_length=1600)
    event_id:int|None=Field(default=None,gt=0)
    previous_topic:Topic|None=None

def limit_requests(db,user):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert
    window=int(time.time()//60)
    stmt=insert(AssistantUsage).values(user_id=user.id,window=window,requests=1)
    stmt=stmt.on_conflict_do_update(index_elements=['user_id'],set_={'window':window,'requests':case((AssistantUsage.window==window,AssistantUsage.requests+1),else_=1)},where=(AssistantUsage.window!=window)|(AssistantUsage.requests<20)).returning(AssistantUsage.requests)
    count=db.execute(stmt).scalar();db.commit()
    if count is None:raise HTTPException(429,'Please wait a minute before asking more questions.')

def event_list(db):
    return db.query(BoxingEvent).filter(~func.lower(BoxingEvent.status).in_(['cancelled','canceled','archived'])).order_by(BoxingEvent.event_date.desc(),BoxingEvent.id.desc()).limit(40).all()

def snapshot(db,user,event_id=None):
    now=datetime.now(timezone.utc);local=now.astimezone(ZoneInfo('America/Chicago'))
    events=event_list(db)
    event=db.get(BoxingEvent,event_id) if event_id else next(iter(sorted([e for e in events if e.event_date>=local.date().isoformat() and (e.status or '').casefold()!='completed'],key=lambda e:(e.event_date,e.id))),events[0] if events else None)
    if event_id and not event:raise HTTPException(404,'Event not found.')
    members=membership_totals(db.query(Member).all(),membership_evidence(db))
    start=datetime.combine(local.date(),day_time.min,tzinfo=local.tzinfo).astimezone(timezone.utc).replace(tzinfo=None)
    end=datetime.combine(local.date()+timedelta(days=1),day_time.min,tzinfo=local.tzinfo).astimezone(timezone.utc).replace(tzinfo=None)
    members['people_checked_in_today']=db.query(func.count(func.distinct(Attendance.member_id))).filter(Attendance.checkin_time>=start,Attendance.checkin_time<end).scalar()
    overview=operations_overview(Response(),db,user)
    result={'generated_at':now.isoformat(),'timezone':'America/Chicago','read_only':True,'members':members,
        'events':[{'id':e.id,'name':e.name,'date':e.event_date} for e in events],
        'event':{'id':event.id,'name':event.name,'date':event.event_date,'venue':event.venue,'status':event.status} if event else None,
        'updates':[{'title':w['title'],'count':w['count'],'page':w['page'],'severity':w['severity']} for w in overview['work_queue']],
        'last_customer_sync_at':overview['last_customer_sync_at'],'tickets':None,'card':None}
    if not event:return result
    orders=db.query(TicketOrder).filter_by(event_id=event.id,payment_status='paid').all()
    quantities=[expected_quantity(o.items_json) for o in orders]
    issued=db.query(IssuedTicket).join(TicketOrder,TicketOrder.id==IssuedTicket.order_id).filter(TicketOrder.event_id==event.id,TicketOrder.payment_status=='paid',IssuedTicket.status.in_(['valid','used'])).count()
    paper=dict(db.query(PaperTicket.status,func.count(PaperTicket.id)).join(PaperTicketBatch,PaperTicketBatch.id==PaperTicket.batch_id).filter(PaperTicketBatch.event_id==event.id).group_by(PaperTicket.status).all())
    result['tickets']={'paid_orders':len(orders),'paid_quantity':sum(q for q in quantities if q is not None),'unknown_quantity_orders':quantities.count(None),'valid_or_used_issued':issued,'gross_paid_cents':sum(o.total_cents for o in orders),
        'pending_checkouts':db.query(TicketOrder).filter_by(event_id=event.id,payment_status='pending').count(),
        'partially_refunded_orders':db.query(TicketOrder).filter_by(event_id=event.id,payment_status='partial_refund').count(),
        'released_paper':paper.get('released',0),'offline_admissions':paper.get('offline_used',0)}
    bouts=db.query(BoxingBout).filter(BoxingBout.event_id==event.id,~func.lower(BoxingBout.status).in_(['cancelled','canceled','removed'])).order_by(BoxingBout.bout_order,BoxingBout.id).all()
    result['card']={'bouts':[{'order':b.bout_order,'red':b.red_fighter.legal_name if b.red_fighter else 'TBD','blue':b.blue_fighter.legal_name if b.blue_fighter else 'TBD','rounds':b.rounds,'status':b.status} for b in bouts],
        'signatures_outstanding':db.query(BoxingContract).filter(BoxingContract.event_id==event.id,func.lower(BoxingContract.docusign_status).in_(['sent','delivered'])).count(),
        'checklist_open':db.query(BoxingEventChecklist).filter(BoxingEventChecklist.event_id==event.id,~func.lower(BoxingEventChecklist.status).in_(['complete','completed','done','waived','not_applicable'])).count()}
    return result

def choose_topic(question,previous=None):
    text=question.casefold()
    if re.search(r'\b(send|delete|merge|charge|refund|activate|cancel|change|update\s+the)\b',text):return 'help'
    hits=[bool(re.search(pattern,text)) for pattern in (r'\b(members?|memberships?|gym|attendance)\b',r'\b(tickets?|sold|sales|revenue)\b',r'\b(card|bouts?|fighters?|contracts?)\b')]
    if sum(hits)>1:return 'overview'
    if re.search(r'\b(member|members|membership|memberships|gym|attendance|check.?ins?)\b',text):return 'members'
    if re.search(r'\b(tickets?|sold|sales|revenue|checkout|checkouts)\b',text):return 'tickets'
    if re.search(r'\b(card|bout|bouts|fighters?|contracts?|signatures?)\b',text):return 'card'
    if re.search(r'\b(updates?|latest|prioriti\w*|issues?|attention|tasks?)\b',text):return 'updates'
    if re.search(r'\b(today|briefing|morning|doing|how are we|how.s everything)\b',text):return 'overview'
    if previous and re.search(r'\b(that|those|them|it|more|again)\b',text):return previous
    return None

def resolve_topic(question,previous=None):
    known=choose_topic(question,previous)
    if known:return known,'live_reports'
    if client:
        try:
            reply=client.with_options(timeout=8,max_retries=0).chat.completions.create(model=os.getenv('OPENAI_ASSISTANT_MODEL','gpt-4.1-mini'),temperature=0,max_tokens=100,response_format={'type':'json_object'},messages=[{'role':'system','content':'Classify a gym owner question. Return only {"topic":"overview|members|tickets|card|updates|help"}. Questions about unrelated subjects, personal customer details or requests to perform actions must be help. You have no tools and must never supply business numbers.'},{'role':'user','content':question}])
            topic=json.loads(reply.choices[0].message.content).get('topic')
            if topic in ('overview','members','tickets','card','updates','help'):return topic,'ai_routed_live_reports'
        except Exception:pass
    return 'help','live_reports'

def answer(topic,data):
    m=data['members'];event=data['event'];tickets=data['tickets'];card=data['card']
    member_text=f"We have {m['active']} active gym memberships, including {m['expiring']} expiring within seven days, and {m['expired']} expired memberships. {m['people_checked_in_today']} people have checked in today. Ticket-only customers are excluded from gym membership counts."
    if event:
        quantity=f"at least {tickets['paid_quantity']}" if tickets['unknown_quantity_orders'] else str(tickets['paid_quantity'])
        ticket_text=f"For {event['name']}, {quantity} tickets have recorded paid orders across {tickets['paid_orders']} orders, totaling ${tickets['gross_paid_cents']/100:,.2f} including any fees. {tickets['valid_or_used_issued']} tickets are issued and valid or used. {tickets['pending_checkouts']} unfinished checkouts are not counted as sold. {tickets['released_paper']} released paper tickets and {tickets['offline_admissions']} offline admissions are separate from recorded paid sales."
        if tickets['unknown_quantity_orders']:ticket_text+=f" Quantities need review for {tickets['unknown_quantity_orders']} paid orders."
        if tickets['partially_refunded_orders']:ticket_text+=f" {tickets['partially_refunded_orders']} partially refunded orders are excluded from this fully paid total; review their remaining tickets separately."
        card_text=f"{event['name']} is scheduled for {event['date'] or 'a date to be set'}. There are {len(card['bouts'])} bouts on the saved card, {card['signatures_outstanding']} contracts awaiting signatures, and {card['checklist_open']} open checklist items."
        if topic=='card':card_text+=' '+' '.join(f"Bout {b['order'] or i+1}: {b['red']} versus {b['blue']}, {b['rounds']} rounds, {b['status']}." for i,b in enumerate(card['bouts'][:12]))
    else:ticket_text=card_text='There is no saved event to report on yet.'
    updates=' '.join(f"{w['title']}: {w['count']}." for w in data['updates'][:6]) or 'No items are currently flagged in the operations work queue. This does not verify external providers or guarantee every task is complete.'
    if topic=='members':return member_text
    if topic=='tickets':return ticket_text
    if topic=='card':return card_text
    if topic=='updates':return updates
    if topic=='overview':return 'Here is your TNG briefing. '+member_text+' '+ticket_text+' '+card_text+' Priorities: '+updates
    return 'I can give you a live TNG briefing, gym membership counts, attendance today, recorded ticket sales, fight-card progress, and outstanding operational tasks. Try “How are we today?” or select an event. I report saved data; use the relevant workspace to make changes.'

@router.get('/snapshot')
def get_snapshot(response:Response,event_id:int|None=None,db=Depends(get_db),user=Depends(current_user)):
    require_admin(user);response.headers['Cache-Control']='private, no-store'
    facts=snapshot(db,user,event_id)
    return {**facts,'briefing':answer('overview',facts)}

@router.post('/ask')
def ask(data:Question,response:Response,db=Depends(get_db),user=Depends(current_user)):
    require_admin(user);response.headers['Cache-Control']='private, no-store'
    if not data.question.strip():raise HTTPException(422,'Ask a question.')
    limit_requests(db,user)
    event_id=data.event_id
    # Only exact saved event names select an event; model output never selects records.
    named=[e for e in event_list(db) if len(e.name.strip())>=3 and e.name.casefold() in data.question.casefold()]
    if named:event_id=max(named,key=lambda e:len(e.name)).id
    topic,engine=resolve_topic(data.question,data.previous_topic)
    facts=snapshot(db,user,event_id)
    return {'answer':answer(topic,facts),'topic':topic,'engine':engine,'facts':facts,'sources':['TNGOS membership report','Recorded ticket orders','Saved fight card','Operations work queue']}
