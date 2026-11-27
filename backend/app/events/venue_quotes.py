"""Versioned facility quotes, restricted customer links, and recorded deposit receipts."""
import os,secrets,html
from datetime import datetime,timedelta,date
from typing import Literal
from fastapi import Depends,HTTPException,Request,Response
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import func,Column,Integer,String,Text,DateTime,ForeignKey,UniqueConstraint
from app.database import Base,get_db
from .venue import router,staff,VenueBooking,lock_calendar,audit,conflicts,ADDRESS,TZ

class VenueQuote(Base):
 __tablename__='venue_quotes'
 id=Column(Integer,primary_key=True)
 booking_id=Column(Integer,ForeignKey('venue_bookings.id'),nullable=False,index=True)
 revision=Column(Integer,nullable=False)
 token=Column(String(96),unique=True,nullable=False)
 rental_cents=Column(Integer,nullable=False)
 services_cents=Column(Integer,nullable=False)
 deposit_cents=Column(Integer,nullable=False)
 services=Column(Text,nullable=False,default='')
 inclusions=Column(Text,nullable=False,default='')
 terms=Column(Text,nullable=False)
 starts_at=Column(DateTime,nullable=False)
 ends_at=Column(DateTime,nullable=False)
 expires_at=Column(DateTime,nullable=False)
 superseded_at=Column(DateTime)
 accepted_at=Column(DateTime)
 accepted_name=Column(String(160))
 email_status=Column(String(30),nullable=False,default='not_sent')
 created_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 created_at=Column(DateTime,nullable=False,default=datetime.utcnow)

class VenueQuoteMessage(Base):
 __tablename__='venue_quote_messages'
 __table_args__=(UniqueConstraint('quote_id','request_key',name='uq_venue_quote_message_request'),)
 id=Column(Integer,primary_key=True)
 quote_id=Column(Integer,ForeignKey('venue_quotes.id'),nullable=False,index=True)
 author=Column(String(20),nullable=False)
 body=Column(Text,nullable=False)
 request_key=Column(String(80),nullable=False)
 created_at=Column(DateTime,nullable=False,default=datetime.utcnow)

class VenueQuoteReceipt(Base):
 __tablename__='venue_quote_receipts'
 __table_args__=(UniqueConstraint('request_key',name='uq_venue_quote_receipt_request'),)
 id=Column(Integer,primary_key=True)
 quote_id=Column(Integer,ForeignKey('venue_quotes.id'),nullable=False,index=True)
 amount_cents=Column(Integer,nullable=False)
 reference=Column(String(200),nullable=False)
 paid_on=Column(String(10),nullable=False)
 request_key=Column(String(80),nullable=False)
 created_by=Column(Integer,ForeignKey('users.id'),nullable=False)
 created_at=Column(DateTime,nullable=False,default=datetime.utcnow)

class QuoteBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 booking_version:int=Field(ge=1)
 rental_cents:int=Field(ge=0,le=100000000,strict=True)
 services_cents:int=Field(default=0,ge=0,le=100000000,strict=True)
 deposit_cents:int=Field(ge=0,le=100000000,strict=True)
 services:str=Field(default='',max_length=2000)
 inclusions:str=Field(default='',max_length=3000)
 terms:str=Field(min_length=10,max_length=6000)
 valid_days:int=Field(default=7,ge=1,le=60)
class TokenBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 token:str=Field(min_length=40,max_length=96)
class AcceptBody(TokenBody):
 name:str=Field(min_length=2,max_length=160)
 agree:bool
class MessageBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 message:str=Field(min_length=1,max_length=2000)
 request_key:str=Field(min_length=16,max_length=80)
class PublicMessageBody(TokenBody):
 message:str=Field(min_length=1,max_length=2000)
 request_key:str=Field(min_length=16,max_length=80)
class ReceiptBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 amount_cents:int=Field(gt=0,le=100000000,strict=True)
 reference:str=Field(min_length=3,max_length=200)
 paid_on:date
 request_key:str=Field(min_length=16,max_length=80)

def booking(db,booking_id):
 row=db.query(VenueBooking).filter_by(id=booking_id).with_for_update().first()
 if not row:raise HTTPException(404,'Booking not found')
 return row

def latest(db,booking_id):return db.query(VenueQuote).filter_by(booking_id=booking_id).order_by(VenueQuote.revision.desc()).first()
def paid(db,q):return sum(r.amount_cents for r in db.query(VenueQuoteReceipt).filter_by(quote_id=q.id).all())
def link(q):return os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/venue/quote#'+q.token

def valid(q,row):
 if q.superseded_at:raise HTTPException(409,'This quote was replaced. Ask TNG for the latest link')
 if row.status in ('cancelled','declined'):raise HTTPException(409,'This booking is no longer available')
 if (row.starts_at,row.ends_at)!=(q.starts_at,q.ends_at):raise HTTPException(409,'Booking times changed. Ask TNG for an updated quote')
 if not q.accepted_at and datetime.utcnow()>q.expires_at:raise HTTPException(410,'This quote expired. Ask TNG for an updated quote')

def payload(db,q,row,private=False):
 received=paid(db,q);total=q.rental_cents+q.services_cents
 stage=quote_stage(q,row,received)
 messages=db.query(VenueQuoteMessage).filter_by(quote_id=q.id).order_by(VenueQuoteMessage.created_at.desc(),VenueQuoteMessage.id.desc()).limit(100).all()
 d={'id':q.id,'reference':row.reference,'title':row.title,'venue':'TNG Boxing','address':ADDRESS,'revision':q.revision,'rental_cents':q.rental_cents,'services_cents':q.services_cents,'deposit_cents':q.deposit_cents,'total_cents':total,'received_cents':received,'balance_cents':max(0,total-received),'deposit_remaining_cents':max(0,q.deposit_cents-received),'services':q.services,'inclusions':q.inclusions,'terms':q.terms,'starts_at':q.starts_at.isoformat()+'Z','ends_at':q.ends_at.isoformat()+'Z','expires_at':q.expires_at.isoformat()+'Z','accepted_at':q.accepted_at.isoformat()+'Z' if q.accepted_at else None,'accepted_name':q.accepted_name,'booking_status':row.status,'stage':stage,'email_status':q.email_status,'expired':not q.accepted_at and datetime.utcnow()>q.expires_at,'schedule_changed':(row.starts_at,row.ends_at)!=(q.starts_at,q.ends_at),'messages':[{'id':m.id,'author':m.author,'message':m.body,'created_at':m.created_at.isoformat()+'Z'} for m in reversed(messages)]}
 if private:d.update({'url':link(q),'email':row.email,'receipts':[{'id':r.id,'amount_cents':r.amount_cents,'reference':r.reference,'paid_on':r.paid_on} for r in db.query(VenueQuoteReceipt).filter_by(quote_id=q.id).order_by(VenueQuoteReceipt.id).all()]})
 return d

def public_quote(db,body,request,response):
 from app.kiosk.routes import throttle
 throttle(db,'venue-quote:ip:'+(request.client.host if request.client else 'unknown'),60)
 response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='no-referrer'
 lock_calendar(db)
 q=db.query(VenueQuote).filter_by(token=body.token).first()
 if not q:raise HTTPException(404,'Quote link unavailable')
 row=booking(db,q.booking_id);valid(q,row);return q,row

@router.get('/bookings/{booking_id}/quote')
def get_quote(booking_id:int,response:Response,db=Depends(get_db),user=Depends(staff)):
 response.headers['Cache-Control']='private, no-store';row=booking(db,booking_id);q=latest(db,row.id)
 return {'quote':payload(db,q,row,True) if q else None,'booking_version':row.version}

@router.post('/bookings/{booking_id}/quote')
def create_quote(booking_id:int,body:QuoteBody,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);row=booking(db,booking_id)
 if row.version!=body.booking_version:raise HTTPException(409,'Booking changed. Close and reopen the booking before quoting')
 if row.status in ('confirmed','cancelled','declined'):raise HTTPException(409,'Quotes require an open booking request or hold')
 if row.starts_at<=datetime.utcnow():raise HTTPException(422,'Choose a future booking time')
 if body.deposit_cents>body.rental_cents+body.services_cents:raise HTTPException(422,'Deposit cannot exceed the quote total')
 if not body.terms.strip() or len(body.terms.strip())<10:raise HTTPException(422,'Enter the customer terms before issuing a quote')
 if body.services_cents and not body.services.strip():raise HTTPException(422,'Describe the extra services being charged')
 old=latest(db,row.id)
 if old and paid(db,old):raise HTTPException(409,'A receipt is recorded on this quote. Resolve the payment with staff before replacing pricing')
 if old:old.superseded_at=datetime.utcnow()
 q=VenueQuote(booking_id=row.id,revision=old.revision+1 if old else 1,token=secrets.token_urlsafe(36),rental_cents=body.rental_cents,services_cents=body.services_cents,deposit_cents=body.deposit_cents,services=body.services.strip(),inclusions=body.inclusions.strip(),terms=body.terms.strip(),starts_at=row.starts_at,ends_at=row.ends_at,expires_at=min(datetime.utcnow()+timedelta(days=body.valid_days),row.starts_at),created_by=user.id)
 db.add(q);row.version+=1;row.updated_by=user.id;row.updated_at=datetime.utcnow();db.flush();audit(db,user,row,'QUOTE_CREATED');db.commit();return {'quote':payload(db,q,row,True),'booking_version':row.version}

@router.post('/quotes/public/view')
def view_quote(body:TokenBody,request:Request,response:Response,db=Depends(get_db)):
 q,row=public_quote(db,body,request,response);return payload(db,q,row)

@router.post('/quotes/public/accept')
def accept_quote(body:AcceptBody,request:Request,response:Response,db=Depends(get_db)):
 lock_calendar(db);q,row=public_quote(db,body,request,response)
 if not body.agree or len(body.name.strip())<2:raise HTTPException(422,'Enter your name and agree to the quote terms')
 if not q.accepted_at:
  if conflicts(db,row.starts_at,row.ends_at,row.id):raise HTTPException(409,'This time is no longer available. Contact TNG before paying')
  q.accepted_at=datetime.utcnow();q.accepted_name=body.name.strip();db.commit()
 return payload(db,q,row)

@router.post('/quotes/public/messages')
def public_message(body:PublicMessageBody,request:Request,response:Response,db=Depends(get_db)):
 from app.kiosk.routes import throttle
 throttle(db,'venue-quote-message:'+body.token,8)
 q,row=public_quote(db,body,request,response)
 return save_message(db,q,row,body,'customer')

def save_message(db,q,row,body,author):
 message=body.message.strip()
 if not message:raise HTTPException(422,'Enter a message')
 old=db.query(VenueQuoteMessage).filter_by(quote_id=q.id,request_key=body.request_key).first()
 if old and (old.body!=message or old.author!=author):raise HTTPException(409,'Message key already used')
 if not old:db.add(VenueQuoteMessage(quote_id=q.id,author=author,body=message,request_key=body.request_key));db.commit()
 return payload(db,q,row,author=='staff')

@router.post('/bookings/{booking_id}/quote/messages')
def staff_message(booking_id:int,body:MessageBody,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);row=booking(db,booking_id);q=latest(db,row.id)
 if not q:raise HTTPException(404,'Create a quote first')
 valid(q,row);return save_message(db,q,row,body,'staff')

@router.post('/bookings/{booking_id}/quote/receipts')
def receipt(booking_id:int,body:ReceiptBody,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);row=booking(db,booking_id);q=latest(db,row.id)
 if not q:raise HTTPException(404,'Quote not found')
 valid(q,row)
 if not q.accepted_at:raise HTTPException(409,'Customer must accept the current quote first')
 if body.paid_on>datetime.now(TZ).date() or len(body.reference.strip())<3:raise HTTPException(422,'Enter a valid payment date and receipt reference')
 old=db.query(VenueQuoteReceipt).filter_by(request_key=body.request_key).first()
 if old:
  if (old.quote_id,old.amount_cents,old.reference,old.paid_on)!=(q.id,body.amount_cents,body.reference.strip(),body.paid_on.isoformat()):raise HTTPException(409,'Payment key already used')
 else:
  if paid(db,q)+body.amount_cents>q.rental_cents+q.services_cents:raise HTTPException(422,'Recorded receipts cannot exceed the quote total')
  db.add(VenueQuoteReceipt(quote_id=q.id,amount_cents=body.amount_cents,reference=body.reference.strip(),paid_on=body.paid_on.isoformat(),request_key=body.request_key,created_by=user.id));audit(db,user,row,'QUOTE_RECEIPT_RECORDED');db.commit()
 return payload(db,q,row,True)

@router.post('/bookings/{booking_id}/quote/send')
def send_quote(booking_id:int,db=Depends(get_db),user=Depends(staff)):
 lock_calendar(db);row=booking(db,booking_id);q=latest(db,row.id)
 if not q:raise HTTPException(404,'Create a quote first')
 valid(q,row)
 if q.email_status in ('accepted','submitting','unknown'):raise HTTPException(409,'Email already submitted or uncertain. Review the mailbox; use Copy quote link to share again')
 from app.mail.microsoft365 import selected_provider,send_welcome
 provider=selected_provider(db)
 if provider!='microsoft365' and not os.getenv('RESEND_API_KEY'):raise HTTPException(503,'Connect Microsoft 365 or Resend, or copy the quote link to share it')
 payload_mail={'from':os.getenv('RESEND_FROM_EMAIL','TNG Boxing <marketing@tngboxinggym.com>'),'to':[row.email],'subject':f'TNG Boxing facility quote — {row.reference} — revision {q.revision}','text':f'Hello {row.contact_name},\n\nReview your facility quote, ask questions and accept the terms here:\n{link(q)}\n\nTotal: ${(q.rental_cents+q.services_cents)/100:,.2f}\nRequired deposit: ${q.deposit_cents/100:,.2f}\n\nAcceptance does not confirm a reservation or collect payment. TNG will confirm availability and receipt of the required deposit.\n\nTNG Boxing'}
 payload_mail['html']='<div style="font-family:Arial;white-space:pre-wrap">'+html.escape(payload_mail['text']).replace(html.escape(link(q)),'<a href="'+html.escape(link(q),quote=True)+'">Review your facility quote</a>')+'</div>'
 q.email_status='submitting';db.commit()
 try:
  if provider=='microsoft365':send_welcome(db,payload_mail,f'tng-venue-quote-{q.id}')
  else:
   import resend
   resend.api_key=os.environ['RESEND_API_KEY'];resend.Emails.send(payload_mail,options={'idempotency_key':f'tng-venue-quote-{q.id}'})
 except Exception:
  q.email_status='unknown';db.commit();raise HTTPException(502,'Email submission could not be confirmed. Check the mailbox before sharing the link again')
 q.email_status='accepted';audit(db,user,row,'QUOTE_EMAIL_ACCEPTED');db.commit();return {'quote':payload(db,q,row,True),'notice':'Email accepted by the provider. Inbox delivery is not confirmed.'}

def check_quote_confirmation(db,row,start,end):
 q=latest(db,row.id)
 if not q:return # Preserve existing blockouts and previously managed bookings.
 if (start,end)!=(q.starts_at,q.ends_at):raise HTTPException(409,'Issue a revised quote for the new booking times before confirming')
 valid(q,row)
 if not q.accepted_at:raise HTTPException(409,'Customer must accept the current quote before confirmation')
 if paid(db,q)<q.deposit_cents:raise HTTPException(409,'Record receipt of the required deposit before confirming')


def calendar_quote_states(db,rows):
 ids=list({r.id for r in rows})
 if not ids:return {}
 quotes=db.query(VenueQuote).filter(VenueQuote.booking_id.in_(ids)).order_by(VenueQuote.revision.desc()).all();latest_rows={}
 for q in quotes:latest_rows.setdefault(q.booking_id,q)
 received=dict(db.query(VenueQuoteReceipt.quote_id,func.sum(VenueQuoteReceipt.amount_cents)).filter(VenueQuoteReceipt.quote_id.in_([q.id for q in latest_rows.values()])).group_by(VenueQuoteReceipt.quote_id).all())
 bookings={r.id:r for r in rows};result={}
 for bid,q in latest_rows.items():
  row=bookings[bid];amount=received.get(q.id,0)
  status=quote_stage(q,row,amount)
  result[str(bid)]={'stage':status,'total_cents':q.rental_cents+q.services_cents,'received_cents':amount}
 return result


def quote_stage(q,row,received):
 if row.status in ('confirmed','cancelled','declined'):return row.status
 if (row.starts_at,row.ends_at)!=(q.starts_at,q.ends_at):return 'revision_required'
 if not q.accepted_at and datetime.utcnow()>q.expires_at:return 'quote_expired'
 if q.accepted_at:
  if received>=q.deposit_cents:return 'deposit_paid' if q.deposit_cents else 'ready_to_confirm'
  return 'accepted'
 return 'quote_sent' if q.email_status=='accepted' else 'quote_ready'
