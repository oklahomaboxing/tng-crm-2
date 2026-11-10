"""Event welcome letter draft, PDF, and explicit staff-triggered individual emails."""
import base64
import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timedelta
from html import escape
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from app.database import Base, get_db
from app.core.dependencies import current_user
from app.core.permissions import require_matchmaker_access
from .models import BoxingEvent, BoxingBout, BoxingFighter, BoxingEventPublication

router=APIRouter(prefix='/api/boxing/events',tags=['fighter-welcome'])

class FighterWelcomeSettings(Base):
    __tablename__='boxing_fighter_welcome_settings'
    event_id=Column(Integer,ForeignKey('boxing_events.id'),primary_key=True)
    settings_json=Column(Text,nullable=False,default='{}')

class FighterWelcomeDelivery(Base):
    __tablename__='boxing_fighter_welcome_deliveries'
    __table_args__=(UniqueConstraint('event_id','content_hash','recipient',name='uq_fighter_welcome_delivery'),)
    id=Column(Integer,primary_key=True)
    event_id=Column(Integer,ForeignKey('boxing_events.id'),nullable=False,index=True)
    content_hash=Column(String(64),nullable=False)
    recipient=Column(String(255),nullable=False)
    status=Column(String(30),nullable=False,default='submitting')
    provider_id=Column(String(255),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow)

class FighterWelcomeSubmission(Base):
    """Exact provider payload retained for safe, explicitly requested idempotent retries."""
    __tablename__='boxing_fighter_welcome_submissions'
    delivery_id=Column(Integer,ForeignKey('boxing_fighter_welcome_deliveries.id'),primary_key=True)
    payload_json=Column(Text,nullable=False)
    error_code=Column(String(60),nullable=True)


class FighterWelcomeProviderHistory(Base):
    __tablename__='boxing_fighter_welcome_provider_history'
    id=Column(Integer,primary_key=True)
    delivery_id=Column(Integer,ForeignKey('boxing_fighter_welcome_deliveries.id'),nullable=False,index=True)
    previous_payload_json=Column(Text,nullable=False)
    previous_error_code=Column(String(60),nullable=True)
    changed_by=Column(Integer,ForeignKey('users.id'),nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)


def submission_provider(db,delivery_id):
    snapshot=db.get(FighterWelcomeSubmission,delivery_id)
    return json.loads(snapshot.payload_json).get('_tng_provider','resend') if snapshot else 'resend'


class LetterSettings(BaseModel):
    weigh_in_datetime: str=Field(default='',max_length=120)
    weigh_in_location: str=Field(default='',max_length=500)
    fighter_arrival: str=Field(default='',max_length=200)
    contact_name: str=Field(default='TNG Promotions',max_length=120)
    contact_phone: str=Field(default='405-959-5823',max_length=80)
    contact_email: str=Field(default='marketing@tngboxinggym.com',max_length=255)
    additional_notes: str=Field(default='',max_length=6000)
    additional_emails: list[str]=Field(default_factory=list,max_length=100)

    @field_validator('additional_emails',mode='before')
    @classmethod
    def validate_additional_emails(cls,value):
        if isinstance(value,str):value=re.split(r'[;,\s]+',value)
        if not isinstance(value,list):raise ValueError('Enter email addresses separated by commas or new lines')
        normalized=[]
        for item in value:
            if not isinstance(item,str):raise ValueError('Each additional recipient must be an email address')
            if not item.strip():continue
            try:email=validate_email(item.strip(),check_deliverability=False).normalized.lower()
            except EmailNotValidError:raise ValueError('An additional email address is invalid. Correct it before saving.')
            if email not in normalized:normalized.append(email)
        return normalized

class SendLetter(BaseModel):
    preview_hash: str=Field(min_length=64,max_length=64)
    retry_unconfirmed: bool=False
    use_microsoft_for_rejected: bool=False


def access(user):
    require_matchmaker_access(user)


def clock(value):
    if not value:
        return 'TO BE CONFIRMED'
    try:
        return datetime.strptime(value,'%H:%M').strftime('%I:%M %p').lstrip('0')
    except ValueError:
        return value


def draft(db,event_id):
    event=db.get(BoxingEvent,event_id)
    if not event:
        raise HTTPException(404,'Event not found')
    row=db.get(FighterWelcomeSettings,event_id)
    settings=LetterSettings(**json.loads(row.settings_json)) if row else LetterSettings()
    pub=db.query(BoxingEventPublication).filter_by(event_id=event_id).first()
    bouts=db.query(BoxingBout).filter_by(event_id=event_id).all()
    ids={fid for b in bouts if str(b.status or '').lower() not in ('cancelled','canceled','void','withdrawn','deleted') for fid in (b.red_fighter_id,b.blue_fighter_id) if fid}
    fighters=db.query(BoxingFighter).filter(BoxingFighter.id.in_(ids)).order_by(BoxingFighter.legal_name).all() if ids else []
    recipients={};missing=[]
    for f in fighters:
        try:
            email=validate_email((f.email or '').strip(),check_deliverability=False).normalized.lower()
            recipients.setdefault(email,[]).append(f.legal_name or f'Fighter {f.id}')
        except EmailNotValidError:
            missing.append(f.legal_name or f'Fighter {f.id}')
    for email in settings.additional_emails:
        recipients.setdefault(email,["Additional recipient"])
    missing_fields=[]
    for key,label in [('weigh_in_datetime','Weigh-in date and time'),('weigh_in_location','Weigh-in location'),('fighter_arrival','Fight-day fighter arrival')]:
        if not getattr(settings,key).strip():missing_fields.append(label)
    if not event.venue_address:missing_fields.append('Event venue address')
    if not event.event_date:missing_fields.append('Event date')
    if not pub or not pub.doors_time or not pub.first_bout_time:missing_fields.append('Doors / first bout times')
    paragraphs=[
        f'FIGHTER WELCOME LETTER | {event.name}',
        'Dear Fighters, Coaches and Teams,',
        f'Welcome to {event.name}. Thank you for being part of the TNG Promotions fight card. Please review the event information below and share it with your team.',
        f'EVENT: {event.name}\nDATE: {event.event_date or "TO BE CONFIRMED"}\nVENUE: {event.venue or "TO BE CONFIRMED"}\nADDRESS: {event.venue_address or "TO BE CONFIRMED"}',
        f'OFFICIAL WEIGH-INS\nDate and time: {settings.weigh_in_datetime or "TO BE CONFIRMED"}\nLocation: {settings.weigh_in_location or "TO BE CONFIRMED"}\nAll listed times are Oklahoma local time (America/Chicago). Please be ready to weigh in at your contracted weight and follow instructions from the commission and promoter.',
        f'FIGHT DAY\nFighter / team arrival: {settings.fighter_arrival or "TO BE CONFIRMED"}\nDoors open: {clock(pub.doors_time if pub else "")}\nFirst bout: {clock(pub.first_bout_time if pub else "")}\nCheck in with TNG Promotions on arrival. Bout order and ring-walk times may change; remain available for staff instructions.',
        'BEFORE YOU ARRIVE\nConfirm your opponent, contracted weight and rounds with your team and TNG Promotions. Review and complete your bout agreement. Confirm your licensing, medical and bloodwork requirements with the Oklahoma State Athletic Commission and submit any outstanding documents through the required process. Bring government-issued photo identification and the equipment and corner credentials required for your bout.',
        'TEAM & EVENT COORDINATION\nTell TNG Promotions promptly about travel delays, opponent or weight concerns, missing documents or changes to your team. Ticket sales and commissions follow your agreement and the event ticket-sales settings. Contact the promoter for your personal ticket link, paper-ticket reconciliation or any outstanding questions.',
    ]
    window=None
    from app.ticketing.models import EventSalesWindow
    window=db.get(EventSalesWindow,event_id)
    if window and window.cutoff_at:
        from datetime import timezone
        from zoneinfo import ZoneInfo
        local=window.cutoff_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/Chicago'))
        paragraphs.append(f'FIGHTER TICKET-SALES CUTOFF\n{local.strftime("%A, %B %d, %Y at %I:%M %p %Z")}. After the cutoff, online purchases follow the event\'s promoter sales policy. Already-purchased tickets remain valid.')
    if settings.additional_notes.strip():paragraphs.append('ADDITIONAL EVENT INFORMATION\n'+settings.additional_notes.strip())
    paragraphs.extend([f'PROMOTER CONTACT\n{settings.contact_name}\n{settings.contact_phone}\n{settings.contact_email}', 'We appreciate your preparation, professionalism and support. We look forward to seeing you and your team.\n\nTNG Promotions\nTHE NEXT GENERATION — EARNED NOT GIVEN'])
    text='\n\n'.join(paragraphs)
    content_hash=hashlib.sha256(text.encode()).hexdigest()
    preview_hash=hashlib.sha256((content_hash+'|'+json.dumps(sorted(recipients))).encode()).hexdigest()
    return event,settings,paragraphs,text,content_hash,preview_hash,recipients,missing,missing_fields


def pdf_bytes(paragraphs,incomplete):
    out=io.BytesIO();styles=getSampleStyleSheet()
    styles['Title'].textColor=colors.HexColor('#c91c28')
    styles['BodyText'].fontSize=9.5;styles['BodyText'].leading=12
    story=[Paragraph('TNG PROMOTIONS',styles['Title']),Paragraph('THE NEXT GENERATION',styles['Heading2'])]
    if incomplete:story.append(Paragraph('DRAFT — SCHEDULE DETAILS TO BE CONFIRMED',styles['Heading2']))
    for p in paragraphs:
        story.extend([Spacer(1,8),Paragraph(escape(p).replace('\n','<br/>'),styles['BodyText'])])
    SimpleDocTemplate(out,leftMargin=48,rightMargin=48,topMargin=36,bottomMargin=36,title='TNG Fighter Welcome Letter',invariant=1).build(story)
    return out.getvalue()


@router.get('/{event_id}/fighter-welcome')
def get_letter(event_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    access(user)
    event,settings,paragraphs,text,ch,ph,recipients,missing,required=draft(db,event_id)
    deliveries=db.query(FighterWelcomeDelivery).filter_by(event_id=event_id,content_hash=ch).all()
    from app.mail.microsoft365 import selected_provider
    return JSONResponse({'email_provider':selected_provider(db),'event_id':event_id,'settings':settings.model_dump(),'text':text,'preview_hash':ph,'content_hash':ch,
            'recipients':[{'email':e,'fighters':names} for e,names in recipients.items()],
            'missing_email_fighters':missing,'missing_fields':required,
            'rejected_resend':sum(r.status=='rejected' and not r.provider_id and r.recipient in recipients and submission_provider(db,r.id)=='resend' for r in deliveries),
            'accepted':sum(r.status=='accepted' and r.recipient in recipients for r in deliveries),
            'needs_review':sum(r.status in ('submitting','unknown','rejected') and r.recipient in recipients for r in deliveries)},headers={'Cache-Control':'private, no-store'})


@router.put('/{event_id}/fighter-welcome')
def save_letter(event_id:int,body:LetterSettings,db:Session=Depends(get_db),user=Depends(current_user)):
    access(user)
    if not db.get(BoxingEvent,event_id):raise HTTPException(404,'Event not found')
    row=db.get(FighterWelcomeSettings,event_id)
    if not row:
        row=FighterWelcomeSettings(event_id=event_id);db.add(row)
    row.settings_json=json.dumps(body.model_dump())
    db.commit()
    return get_letter(event_id,db,user)


@router.get('/{event_id}/fighter-welcome.pdf')
def download_letter(event_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    access(user)
    data=draft(db,event_id)
    return Response(pdf_bytes(data[2],bool(data[8])),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="tng_event_{event_id}_fighter_welcome.pdf"','Cache-Control':'private, no-store'})


@router.post('/{event_id}/fighter-welcome/send')
def send_letter(event_id:int,body:SendLetter,db:Session=Depends(get_db),user=Depends(current_user)):
    access(user)
    event,settings,paragraphs,text,ch,ph,recipients,missing,required=draft(db,event_id)
    if body.preview_hash!=ph:raise HTTPException(409,'Event details or recipients changed. Refresh and review the letter before sending.')
    if required:raise HTTPException(409,'Complete these details before sending: '+', '.join(required))
    if not recipients:raise HTTPException(409,'No booked fighters have a valid email address')
    from app.mail.microsoft365 import selected_provider, send_welcome, MailSubmissionError
    provider=selected_provider(db)
    if body.use_microsoft_for_rejected and provider!='microsoft365':raise HTTPException(409,'Connect Microsoft 365 before moving rejected emails')
    if provider=='resend' and not os.getenv('RESEND_API_KEY'):raise HTTPException(503,'Email service is not configured')
    import resend
    resend.api_key=os.getenv('RESEND_API_KEY')
    attachment=base64.b64encode(pdf_bytes(paragraphs,False)).decode()
    result={'accepted':0,'already_submitted':0,'needs_review':0,'missing_email_fighters':missing,'issues':[]}
    for email in recipients:
        legacy_retry=False
        previous_status=None
        if body.use_microsoft_for_rejected and not db.query(FighterWelcomeDelivery).filter_by(event_id=event_id,content_hash=ch,recipient=email).first():
            continue
        row=FighterWelcomeDelivery(event_id=event_id,content_hash=ch,recipient=email,status='submitting')
        db.add(row)
        try:db.commit()
        except IntegrityError:
            db.rollback()
            legacy_retry=True
            row=db.query(FighterWelcomeDelivery).filter_by(event_id=event_id,content_hash=ch,recipient=email).one()
            if row.status=='accepted':
                result['already_submitted']+=1;continue
            previous_status=row.status
            if body.use_microsoft_for_rejected and (previous_status!='rejected' or row.provider_id or submission_provider(db,row.id)!='resend'):
                result['needs_review']+=1;continue
            # Provider idempotency keys expire after 24h. Never replay after that window.
            if not (body.retry_unconfirmed or body.use_microsoft_for_rejected) or row.status not in ('unknown','rejected') or (not body.use_microsoft_for_rejected and row.created_at < datetime.utcnow()-timedelta(hours=23)):
                result['needs_review']+=1;continue
            claimed=db.query(FighterWelcomeDelivery).filter_by(id=row.id,status=row.status).update({'status':'submitting'},synchronize_session=False)
            db.commit()
            if not claimed:
                result['needs_review']+=1;continue
            db.refresh(row)
        snapshot=db.get(FighterWelcomeSubmission,row.id)
        if not snapshot:
            payload={'from':os.getenv('FIGHTER_WELCOME_FROM_EMAIL','TNG Promotions <marketing@tngboxinggym.com>'),
                'reply_to':'marketing@tngboxinggym.com','to':[email],
                'subject':f'{event.name} — Fighter Welcome & Event Information','text':text,
                'html':'<div style="font-family:Arial,sans-serif;max-width:680px;margin:auto">'+''.join('<p>'+escape(p).replace('\n','<br/>')+'</p>' for p in paragraphs)+'</div>',
                'attachments':[{'filename':f'TNG_{event_id}_Fighter_Welcome.pdf','content':attachment}]}
            payload['_tng_provider']='resend' if legacy_retry else provider
            snapshot=FighterWelcomeSubmission(delivery_id=row.id,payload_json=json.dumps(payload))
            db.add(snapshot);db.commit()
        payload=json.loads(snapshot.payload_json)
        route=payload.pop('_tng_provider','resend')
        if body.use_microsoft_for_rejected and previous_status=='rejected' and route=='resend' and not row.provider_id:
            # Explicit staff action only. Retain the old payload and failure for audit.
            db.add(FighterWelcomeProviderHistory(delivery_id=row.id,previous_payload_json=snapshot.payload_json,
                previous_error_code=snapshot.error_code,changed_by=user.id))
            payload['_tng_provider']='microsoft365'
            snapshot.payload_json=json.dumps(payload);snapshot.error_code=None
            db.commit()
            payload.pop('_tng_provider');route='microsoft365'
        # Resend's default API rate is two requests/second; pace the individual emails.
        time.sleep(0.65)
        try:
            sent=(send_welcome(db,payload,f'tng-fighter-welcome-{row.id}') if route=='microsoft365' else resend.Emails.send(payload,options={'idempotency_key':f'tng-fighter-welcome-{row.id}'}))
            provider_id=sent.get('id') if isinstance(sent,dict) else None
            if not provider_id:raise RuntimeError('Missing provider acknowledgment')
            row.status='accepted';row.provider_id=str(provider_id);snapshot.error_code=None;result['accepted']+=1
        except Exception as exc:
            code=str(getattr(exc,'code',''))
            snapshot.error_code=code if code.isdigit() else type(exc).__name__[:60]
            row.status='rejected' if code in ('400','401','403','422','429') else 'unknown'
            result['needs_review']+=1
            issue=(str(exc) if isinstance(exc,MailSubmissionError) else 'Email provider rate limit: retry the unconfirmed emails shortly.' if code=='429' else
                   'Email provider rejected the request. Check the configured sending address and provider settings.' if row.status=='rejected' else
                   'An email submission is unconfirmed. Accepted emails are skipped on retry; conflicting or expired submissions need review.')
            if issue not in result['issues']:result['issues'].append(issue)
        db.commit()
    return result
