"""Explicit event grants for external investor and sponsor logins."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base, get_db
from app.core.dependencies import current_user
from app.models import User, SecurityLog
from app.matchmaker.models import BoxingEvent, BoxingBout
from .recap import CANCELLED, recap
router=APIRouter(prefix='/api/partners',tags=['Partner access'])

class PartnerGrant(Base):
    __tablename__='partner_event_grants'
    __table_args__=(UniqueConstraint('user_id','event_id',name='uq_partner_event_grant'),)
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False)
    update_text=Column(Text,default='',nullable=False)
    financials=Column(Boolean,default=False,nullable=False)
    updated_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class PartnerProfile(Base):
    __tablename__='partner_profiles'
    user_id=Column(Integer,ForeignKey('users.id'),primary_key=True)
    title=Column(Text,default='',nullable=False)
    phone=Column(Text,default='',nullable=False)

class GrantBody(BaseModel):
    user_id:int
    event_id:int
    update_text:str=Field(default='',max_length=8000)
    financials:bool=False

def admin(user=Depends(current_user)):
    if user.role!='admin':raise HTTPException(403,'Administrator access required')
    return user

@router.get('/access')
def access(response:Response,db=Depends(get_db),user=Depends(admin)):
    response.headers['Cache-Control']='private, no-store'
    profiles={p.user_id:p for p in db.query(PartnerProfile).all()}
    return {'users':[{'id':u.id,'name':u.name,'email':u.email,'role':u.role,'active':u.active,'title':profiles[u.id].title if u.id in profiles else '', 'phone':profiles[u.id].phone if u.id in profiles else ''} for u in db.query(User).filter(User.role.in_(['investor','sponsor','concessions'])).order_by(User.name)],'events':[{'id':e.id,'name':e.name} for e in db.query(BoxingEvent).order_by(BoxingEvent.id.desc())],'grants':[{'id':g.id,'user_id':g.user_id,'event_id':g.event_id,'update_text':g.update_text,'financials':g.financials} for g in db.query(PartnerGrant).all()]}

@router.put('/access')
def grant(body:GrantBody,db=Depends(get_db),user=Depends(admin)):
    partner=db.get(User,body.user_id)
    if not partner or partner.role not in ('investor','sponsor','concessions'):raise HTTPException(422,'Choose an investor, sponsor or concessions account')
    if not db.get(BoxingEvent,body.event_id):raise HTTPException(404,'Event not found')
    if body.financials and partner.role not in ('investor','sponsor'):raise HTTPException(422,'Cost statements are available for investor and sponsor grants')
    row=db.query(PartnerGrant).filter_by(user_id=body.user_id,event_id=body.event_id).first()
    if not row:row=PartnerGrant(user_id=body.user_id,event_id=body.event_id);db.add(row)
    row.update_text=body.update_text.strip();row.financials=body.financials;row.updated_at=datetime.utcnow()
    db.add(SecurityLog(user_id=user.id,action='PARTNER_ACCESS_UPDATED',description=f'Partner user {body.user_id}; event {body.event_id}; financials {body.financials}'))
    db.commit();return {'saved':True}

@router.delete('/access/{grant_id}')
def revoke(grant_id:int,db=Depends(get_db),user=Depends(admin)):
    row=db.get(PartnerGrant,grant_id)
    if not row:raise HTTPException(404,'Access grant not found')
    db.add(SecurityLog(user_id=user.id,action='PARTNER_ACCESS_REVOKED',description=f'Partner user {row.user_id}; event {row.event_id}'));db.delete(row);db.commit();return {'revoked':True}

@router.get('/portal')
def portal(response:Response,period:Literal['all','month','year']='all',db=Depends(get_db),user=Depends(current_user)):
    if user.role not in ('investor','sponsor','concessions'):raise HTTPException(403,'Partner login required')
    response.headers['Cache-Control']='private, no-store'
    events=[]
    for g in db.query(PartnerGrant).filter_by(user_id=user.id).all():
        e=db.get(BoxingEvent,g.event_id)
        if not e:continue
        bouts=db.query(BoxingBout).filter_by(event_id=e.id).all()
        item={'id':e.id,'name':e.name,'date':e.event_date,'venue':e.venue,'status':e.status,'current_bouts':sum(str(b.status or '').strip().lower() not in CANCELLED for b in bouts),'update_text':g.update_text,'updated_at':g.updated_at.isoformat()+'Z'}
        if user.role=='concessions':item.pop('current_bouts',None)
        if user.role=='investor' and g.financials:
            d=recap(db,e.id);summary=d['summary'];item['financials']={k:summary[k] for k in ['ticket_sales_cents','total_recorded_income_cents','total_cost_cents','recorded_result_cents']};item['financials_provisional']=d['provisional'];item['financials_basis']='Recorded event income and costs; not a bank balance. Incomplete records can change these totals.'
        if g.financials and user.role in ('investor','sponsor'):
            from .cost_statement import statement
            item['cost_statement']=statement(recap(db,e.id))
        events.append(item)
    profile=db.get(PartnerProfile,user.id)
    result={'name':user.name,'role':user.role,'title':profile.title if profile else '', 'events':events}
    if user.role=='investor':
        from .investors import InvestorBusinessAccess,overview,safe_event
        grant=db.get(InvestorBusinessAccess,user.id);result['business_access']=bool(grant and grant.enabled)
        result['business']=overview(db,period) if result['business_access'] else None
        for item in result['events']:
            if 'financials' in item:item['financial_detail']=safe_event(db,db.get(BoxingEvent,item['id']))
    return result


def cost_access(db,user,event_id):
    if user.role in ('admin','staff'):return
    if user.role=='investor':
        from .investors import InvestorBusinessAccess
        grant=db.get(InvestorBusinessAccess,user.id)
        if grant and grant.enabled:return
    grant=db.query(PartnerGrant).filter_by(user_id=user.id,event_id=event_id,financials=True).first()
    if user.role not in ('investor','sponsor') or not grant:raise HTTPException(403,'Event cost statement access required')

@router.get('/events/{event_id}/cost-statement')
def cost_statement(event_id:int,response:Response,db=Depends(get_db),user=Depends(current_user)):
    cost_access(db,user,event_id)
    from .cost_statement import statement
    response.headers['Cache-Control']='private, no-store'
    return statement(recap(db,event_id))

@router.get('/events/{event_id}/cost-statement.pdf')
def cost_statement_pdf(event_id:int,db=Depends(get_db),user=Depends(current_user)):
    cost_access(db,user,event_id)
    from .cost_statement import statement,pdf
    return Response(pdf(statement(recap(db,event_id))),media_type='application/pdf',headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="TNG-event-{event_id}-cost-statement.pdf"'})
