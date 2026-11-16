"""Private event contact directory and manually logged matchmaking conversations."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base, get_db
from app.core.dependencies import current_user
from app.matchmaker.models import BoxingEvent

router = APIRouter(prefix='/api/matchmaker-desk', tags=['Matchmaker desk'])

class MatchmakerContact(Base):
    __tablename__ = 'matchmaker_desk_contacts'
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    company = Column(String(160), nullable=False, default='')
    phone = Column(String(40), nullable=False, default='')
    email = Column(String(254), nullable=False, default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class MatchmakerSlot(Base):
    __tablename__ = 'matchmaker_desk_slots'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('boxing_events.id'), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey('matchmaker_desk_contacts.id'), nullable=False)
    title = Column(String(200), nullable=False)
    terms = Column(Text, nullable=False, default='')
    status = Column(String(30), nullable=False, default='open')
    version = Column(Integer, nullable=False, default=0)

class MatchmakerNote(Base):
    __tablename__ = 'matchmaker_desk_notes'
    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey('matchmaker_desk_slots.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class ContactBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    company: str = Field(default='', max_length=160)
    phone: str = Field(default='', max_length=40)
    email: str = Field(default='', max_length=254)

class SlotBody(BaseModel):
    contact_id: int
    title: str = Field(min_length=1, max_length=200)
    terms: str = Field(default='', max_length=4000)

class SlotUpdate(BaseModel):
    status: Literal['open','contacted','negotiating','agreed','closed']
    version: int = Field(ge=0)

class NoteBody(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

def operator(user=Depends(current_user)):
    if user.role not in ('admin','staff','matchmaker'):
        raise HTTPException(403, 'Event staff access required')
    return user

def event_for(db, eid):
    if not db.get(BoxingEvent, eid):
        raise HTTPException(404, 'Event not found')

def clean_contact(body):
    values={key:value.strip() for key,value in body.model_dump().items()}
    if not values['name']:raise HTTPException(422,'Enter a contact name')
    if values['phone'] and (any(c not in '+0123456789 ()-.' for c in values['phone']) or not 10 <= len(''.join(c for c in values['phone'] if c.isdigit())) <= 15):
        raise HTTPException(422,'Enter a complete phone number or leave it blank')
    if values['email'] and ('@' not in values['email'] or any(c.isspace() for c in values['email'])):
        raise HTTPException(422,'Enter a valid email address or leave it blank')
    return values

def contact_dict(c):return {k:getattr(c,k) for k in ('id','name','company','phone','email')}

@router.get('/events/{event_id}')
def get_desk(event_id:int,response:Response,db=Depends(get_db),user=Depends(operator)):
    event_for(db,event_id);response.headers['Cache-Control']='private, no-store'
    contacts=db.query(MatchmakerContact).order_by(MatchmakerContact.name).all()
    slots=db.query(MatchmakerSlot).filter_by(event_id=event_id).order_by(MatchmakerSlot.id.desc()).all()
    notes=db.query(MatchmakerNote).filter(MatchmakerNote.slot_id.in_([s.id for s in slots])).order_by(MatchmakerNote.id).all() if slots else []
    return {'contacts':[contact_dict(c) for c in contacts],'slots':[{**{k:getattr(s,k) for k in ('id','contact_id','title','terms','status','version')},'notes':[{'id':n.id,'body':n.body,'created_at':n.created_at.isoformat()+'Z'} for n in notes if n.slot_id==s.id]} for s in slots]}

@router.post('/contacts')
def add_contact(body:ContactBody,db=Depends(get_db),user=Depends(operator)):
    c=MatchmakerContact(**clean_contact(body));db.add(c);db.commit();db.refresh(c);return contact_dict(c)

@router.put('/contacts/{contact_id}')
def edit_contact(contact_id:int,body:ContactBody,db=Depends(get_db),user=Depends(operator)):
    c=db.get(MatchmakerContact,contact_id)
    if not c:raise HTTPException(404,'Contact not found')
    for k,v in clean_contact(body).items():setattr(c,k,v)
    db.commit();return contact_dict(c)

@router.post('/events/{event_id}/slots')
def add_slot(event_id:int,body:SlotBody,db=Depends(get_db),user=Depends(operator)):
    event_for(db,event_id)
    if not db.get(MatchmakerContact,body.contact_id):raise HTTPException(404,'Contact not found')
    if not body.title.strip():raise HTTPException(422,'Enter a slot or matchup title')
    slot=MatchmakerSlot(event_id=event_id,contact_id=body.contact_id,title=body.title.strip(),terms=body.terms.strip());db.add(slot);db.commit();return {'id':slot.id}

@router.patch('/events/{event_id}/slots/{slot_id}')
def update_slot(event_id:int,slot_id:int,body:SlotUpdate,db=Depends(get_db),user=Depends(operator)):
    updated=db.query(MatchmakerSlot).filter_by(id=slot_id,event_id=event_id,version=body.version).update({'status':body.status,'version':body.version+1})
    if not updated:raise HTTPException(409,'This slot changed or is unavailable. Refresh before saving')
    db.commit();return {'saved':True}

@router.post('/events/{event_id}/slots/{slot_id}/notes')
def add_note(event_id:int,slot_id:int,body:NoteBody,db=Depends(get_db),user=Depends(operator)):
    if not db.query(MatchmakerSlot).filter_by(id=slot_id,event_id=event_id).first():raise HTTPException(404,'Slot not found for this event')
    if not body.body.strip():raise HTTPException(422,'Enter a conversation note')
    db.add(MatchmakerNote(slot_id=slot_id,user_id=user.id,body=body.body.strip()));db.commit();return {'saved':True}
