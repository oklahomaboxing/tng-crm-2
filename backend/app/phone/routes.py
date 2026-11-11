"""NumberBarn-forwarded Twilio keypad receptionist; approved answers only."""
import json,os,re
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response,JSONResponse
from pydantic import BaseModel,Field,field_validator,model_validator
from sqlalchemy import Column,Integer,String,Text,Boolean,DateTime,ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse
from app.database import Base,get_db
from app.models import Lead,SecurityLog
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.ticketing.delivery import normalize_ticket_phone
from app.services.business_time import reporting_periods

router=APIRouter(prefix='/api/phone',tags=['Phone assistant'])
PUBLIC_NUMBER='+14058644496'
STAFF_NUMBER='+14059895823'
MENU='Press 1 for hours, 2 for memberships, 3 for events, 4 for a callback, 5 to buy tickets, 6 for marketing, 7 to sign up now, 8 for coaches, or 0 for staff. Press 9 to repeat the menu.'
FOLLOW_UP='For another option, use your keypad. Press 9 for the menu or 0 for staff.'


class PhoneSettings(Base):
    __tablename__='phone_assistant_settings'
    id=Column(Integer,primary_key=True)
    settings_json=Column(Text,nullable=False)
    connected=Column(Boolean,default=False,nullable=False)

class PhoneCall(Base):
    __tablename__='phone_assistant_calls'
    call_sid=Column(String(80),primary_key=True)
    caller_phone=Column(String(40),nullable=True)
    caller_name=Column(String(150),nullable=True)
    stage=Column(String(40),default='menu',nullable=False)
    turns=Column(Integer,default=0,nullable=False)
    empty_attempts=Column(Integer,default=0,nullable=False)
    status=Column(String(40),default='in-progress',nullable=False)
    lead_id=Column(Integer,ForeignKey('leads.id'),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class PhoneCallDepartment(Base):
    __tablename__='phone_call_departments'
    call_sid=Column(String(80),ForeignKey('phone_assistant_calls.call_sid'),primary_key=True)
    department=Column(String(30),nullable=False,default='staff')


class CoachPhone(BaseModel):
    digit:Literal['1','2','3','4','5','6','7','8','9']
    name:str=Field(min_length=3,max_length=80)
    phone:str
    enabled:bool=True

    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if len(value)<3:raise ValueError('Enter the coach name')
        return value

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls,value):
        number=normalize_ticket_phone(value)
        if not number:raise ValueError('Enter a coach phone number')
        return number

def default_coaches():
    return [CoachPhone(digit=digit,name=name,phone=phone) for digit,name,phone in [
        ('1','Rodney Porter','+14052090453'),('2','Maurice Williams','+16512390916'),
        ('3','Dora Williams','+14059895453'),('4','Jose Iturinno','+14057773615'),
        ('5','Marlon Geddis','+14056407542')]]

class PhoneConfig(BaseModel):
    enabled:bool=False
    public_number:str=PUBLIC_NUMBER
    staff_number:str=STAFF_NUMBER
    marketing_number:str='+14059895453'
    voice:Literal['Polly.Joanna','Polly.Matthew','woman']='Polly.Joanna'
    use_live_membership_prices:bool=True
    use_live_event_info:bool=True
    ticket_links_enabled:bool=True
    signup_links_enabled:bool=True
    coaches:list[CoachPhone]=Field(default_factory=default_coaches,max_length=9)
    greeting:str=Field(default='Thank you for calling TNG Boxing, The Next Generation.',min_length=5,max_length=500)
    hours_answer:str=Field(default='TNG Boxing is located at 8416 Northwest Expressway in Oklahoma City, Oklahoma, 73162. For current opening hours and class times, please speak with our staff.',min_length=5,max_length=2000)
    membership_answer:str=Field(default='Our staff can help you choose a boxing membership and discuss current rates. To arrange a visit or request membership information, press 4. To speak with staff, press 0.',min_length=5,max_length=2000)
    events_answer:str=Field(default='For current TNG Promotions boxing events, ticket availability and fight night details, visit tngos.tngboxinggym.com or speak with staff by pressing 0.',min_length=5,max_length=2000)

    @field_validator('public_number','staff_number','marketing_number')
    @classmethod
    def phone(cls,value):
        try:
            phone=normalize_ticket_phone(value)
            if not phone:raise ValueError()
            return phone
        except ValueError:raise ValueError('Enter a valid phone number including its area code')

    @model_validator(mode='after')
    def unique_coach_keys(self):
        if len({c.digit for c in self.coaches})!=len(self.coaches):raise ValueError('Each coach needs a unique menu number')
        return self

class ConnectPhone(BaseModel):
    acknowledge_voice_charges:bool=False

def base():return os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
def url(path):return base()+'/api/phone/'+path
def config(db):
    row=db.get(PhoneSettings,1)
    return PhoneConfig(**json.loads(row.settings_json)) if row else PhoneConfig()
def xml(response):return Response(str(response),media_type='application/xml',headers={'Cache-Control':'no-store'})
def say(response,text,cfg=None):response.say(text,language='en-US',voice=cfg.voice if cfg else 'Polly.Joanna')
def gather(text,path,input='dtmf',digits=1,cfg=None):
    response=VoiceResponse()
    g=response.gather(input='dtmf',num_digits=digits,action=url(path),method='POST',timeout=8,action_on_empty_result=True)
    say(g,text,cfg)
    say(response,'Please call again if you need help. Goodbye.',cfg);response.hangup()
    return xml(response)
def coach_for(cfg,department):
    return next((c for c in cfg.coaches if 'coach_'+c.digit==department and c.enabled),None)

def department_name(cfg,department):
    coach=next((c for c in cfg.coaches if 'coach_'+c.digit==department),None)
    return 'Coach '+coach.name if coach else ('Marketing' if department=='marketing' else 'Staff')

def transfer(cfg,department='staff'):
    coach=coach_for(cfg,department)
    response=VoiceResponse()
    label='Coach '+coach.name if coach else ('TNG marketing' if department=='marketing' else 'the TNG Boxing team')
    say(response,'One moment while I connect you with '+label+'.',cfg)
    dial=response.dial(timeout=35,action=url('transfer-result'),method='POST')
    dial.number(coach.phone if coach else (cfg.marketing_number if department=='marketing' else cfg.staff_number))
    return xml(response)
def transfer_for(db,call,cfg,department='staff'):
    row=db.get(PhoneCallDepartment,call.call_sid)
    if not row:row=PhoneCallDepartment(call_sid=call.call_sid);db.add(row)
    from .tracking import activity
    coach=coach_for(cfg,department)
    activity(db,call,'transfer_requested',('Coach '+coach.name) if coach else department)
    row.department=department;call.stage='coach_transfer' if coach else ('marketing_transfer' if department=='marketing' else 'transfer');db.commit()
    return transfer(cfg,department)

def callback_prompt(call,cfg=None):
    if call.empty_attempts>=3:
        response=VoiceResponse();say(response,'We could not complete your request. Please call again or visit TNG Boxing. Goodbye.',cfg);response.hangup();return xml(response)
    if not call.caller_phone:return gather('Please enter a ten digit callback number, including the area code.','callback/phone',input='dtmf',digits=10,cfg=cfg)
    return gather('To request a callback to the number ending '+ ' '.join(call.caller_phone[-4:])+', press 1. Press 2 for a different callback number, 9 for the main menu, or 0 for staff.','callback/confirm',cfg=cfg)


async def verified(request):
    form=dict(await request.form())
    token=os.getenv('TWILIO_AUTH_TOKEN','')
    if not token:raise HTTPException(503,'Voice provider is not configured')
    signature=request.headers.get('X-Twilio-Signature','')
    callback_url=base()+request.url.path+('?' + request.url.query if request.url.query else '')
    if not RequestValidator(token).validate(callback_url,form,signature):raise HTTPException(401,'Invalid voice provider signature')
    if form.get('AccountSid')!=os.getenv('TWILIO_ACCOUNT_SID'):raise HTTPException(401,'Voice account does not match')
    try:to=normalize_ticket_phone(form.get('To'))
    except ValueError:raise HTTPException(400,'Invalid called number')
    if to!=normalize_ticket_phone(os.getenv('TWILIO_PHONE_NUMBER','')):raise HTTPException(403,'Called number is not assigned to this assistant')
    if not re.fullmatch(r'CA[0-9a-fA-F]{32}',str(form.get('CallSid',''))):raise HTTPException(400,'Invalid call reference')
    return form

def get_call(db,form):
    call=db.get(PhoneCall,form['CallSid'])
    if not call:
        try:phone=normalize_ticket_phone(form.get('From')) or None
        except ValueError:phone=None
        call=PhoneCall(call_sid=form['CallSid'],caller_phone=phone,stage='menu')
        db.add(call)
        try:db.commit()
        except IntegrityError:db.rollback()
    return db.query(PhoneCall).filter_by(call_sid=form['CallSid']).with_for_update().populate_existing().one()

def view(db):
    cfg=config(db);row=db.get(PhoneSettings,1)
    periods=reporting_periods()
    from .tickets import sms_route
    from .facts import membership_answer,event_answer
    return {'settings':cfg.model_dump(),'connected':bool(row and row.connected),'forwarding_number':os.getenv('TWILIO_PHONE_NUMBER',''),
            'voice_url':url('incoming'),'voice_status_url':url('status'),
            'ticket_links_ready':bool(sms_route(db)),
            'membership_preview':membership_answer(db,cfg.membership_answer) if cfg.use_live_membership_prices else cfg.membership_answer,
            'events_preview':event_answer(db,cfg.events_answer) if cfg.use_live_event_info else cfg.events_answer,
            'twilio_configured':all(os.getenv(k) for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_PHONE_NUMBER')),
            'today_calls':db.query(PhoneCall).filter(PhoneCall.created_at>=periods['day_start'],PhoneCall.created_at<periods['day_end']).count()}

@router.get('/admin')
def admin_status(db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    data=view(db)
    calls=db.query(PhoneCall).order_by(PhoneCall.created_at.desc()).limit(50).all()
    from .tickets import PhoneTicketDelivery
    link_status={}
    if calls:
        for delivery in db.query(PhoneTicketDelivery).filter(PhoneTicketDelivery.call_sid.in_([c.call_sid for c in calls])).order_by(PhoneTicketDelivery.id.desc()):
            link_status.setdefault(delivery.call_sid,delivery.status)
    data['calls']=[{'call_sid':c.call_sid,'caller_last_four':(c.caller_phone or '')[-4:],'status':c.status,'stage':c.stage,'lead_id':c.lead_id,'ticket_link_status':link_status.get(c.call_sid),'created_at':c.created_at.isoformat()+'Z'} for c in calls]
    return JSONResponse(data,headers={'Cache-Control':'private, no-store'})

@router.put('/admin')
def save_config(body:PhoneConfig,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    assigned=normalize_ticket_phone(os.getenv('TWILIO_PHONE_NUMBER',''))
    if any(c.phone in (body.public_number,assigned) for c in body.coaches):raise HTTPException(400,'Coach numbers must not route back to the NumberBarn or Twilio line')
    if body.staff_number in (body.public_number,assigned) or body.marketing_number in (body.public_number,assigned):raise HTTPException(400,'Transfer numbers must not route back to the NumberBarn or Twilio line')
    row=db.get(PhoneSettings,1)
    if not row:row=PhoneSettings(id=1);db.add(row)
    row.settings_json=json.dumps(body.model_dump())
    db.add(SecurityLog(user_id=user.id,action='PHONE_ASSISTANT_SETTINGS_SAVED',description='Approved phone answers and transfer settings saved; no calls placed.',success=True));db.commit()
    return view(db)

@router.post('/admin/connect')
def connect_voice(body:ConnectPhone,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    if not body.acknowledge_voice_charges:raise HTTPException(400,'Acknowledge voice-call charges before connecting')
    cfg=config(db)
    if any(number in (cfg.public_number,normalize_ticket_phone(os.getenv('TWILIO_PHONE_NUMBER',''))) for number in (cfg.staff_number,cfg.marketing_number,*[c.phone for c in cfg.coaches if c.enabled])):raise HTTPException(400,'Staff transfer would create a routing loop')
    if not all(os.getenv(k) for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_PHONE_NUMBER')):raise HTTPException(503,'Configure the existing Twilio account and phone number first')
    try:
        client=Client(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN'],http_client=TwilioHttpClient(timeout=10))
        numbers=client.incoming_phone_numbers.list(phone_number=os.environ['TWILIO_PHONE_NUMBER'],limit=5)
        if not numbers or not numbers[0].capabilities.get('voice'):raise HTTPException(409,'The assigned Twilio number is not voice capable')
        number=numbers[0]
        if getattr(number,'voice_application_sid',None) or number.voice_url not in (None,'',url('incoming')):raise HTTPException(409,'This Twilio number already has another voice application. Review that route before replacing it.')
        number.update(voice_url=url('incoming'),voice_method='POST',status_callback=url('status'),status_callback_method='POST')
    except HTTPException:raise
    except Exception:raise HTTPException(502,'Could not connect the Twilio voice number. Verify provider access and retry.')
    cfg.enabled=True
    row=db.get(PhoneSettings,1)
    if not row:row=PhoneSettings(id=1);db.add(row)
    row.settings_json=json.dumps(cfg.model_dump());row.connected=True
    db.add(SecurityLog(user_id=user.id,action='PHONE_ASSISTANT_CONNECTED',description='Voice webhooks connected on the assigned Twilio number. SMS settings unchanged; no calls placed.',success=True));db.commit()
    return view(db)

@router.post('/incoming')
async def incoming(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    call=get_call(db,form)
    from .tracking import activity,PhoneCallActivity
    if not db.query(PhoneCallActivity).filter_by(call_sid=call.call_sid,action='received').first():activity(db,call,'received','Call reached TNGOS')
    if not cfg.enabled:
        call.stage='staff_direct';db.commit();return transfer(cfg)
    db.commit()
    return gather(cfg.greeting+' '+MENU,'menu',cfg=cfg)

@router.post('/menu')
async def menu(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    if not cfg.enabled:return transfer(cfg)
    call=get_call(db,form);call.turns+=1
    digit=str(form.get('Digits',''))
    if not digit:call.empty_attempts+=1
    else:call.empty_attempts=0
    if call.turns>=12 or call.empty_attempts>=3:db.commit();return transfer_for(db,call,cfg)
    if digit=='9':db.commit();return gather(MENU,'menu',cfg=cfg)
    if digit=='8':
        from .coaches import offer_coaches
        return offer_coaches(db,call,cfg)
    if digit=='6':return transfer_for(db,call,cfg,'marketing')
    if digit=='0':return transfer_for(db,call,cfg)
    if digit=='7':
        from .signup import offer_signup
        return offer_signup(db,call,cfg)
    if digit=='4':
        from .tracking import activity
        activity(db,call,'menu_choice','Callback request')
        if call.caller_phone in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')):call.caller_phone=None
        call.stage='callback_confirm' if call.caller_phone else 'callback_phone';db.commit();return callback_prompt(call,cfg)
    if digit=='5':
        db.commit()
        from .tickets import offer_events
        return offer_events(db,call,cfg)
    from .facts import membership_answer,event_answer
    answer=None;topic=None
    if digit=='3':answer=event_answer(db,cfg.events_answer) if cfg.use_live_event_info else cfg.events_answer;topic='Events'
    elif digit=='1':answer=cfg.hours_answer;topic='Hours and location'
    elif digit=='2':answer=membership_answer(db,cfg.membership_answer) if cfg.use_live_membership_prices else cfg.membership_answer;topic='Memberships'
    if answer:
        from .tracking import activity
        activity(db,call,'menu_choice',topic)
    db.commit()
    return gather((answer+' '+FOLLOW_UP if answer else 'Please choose using your phone keypad. '+MENU),'menu',cfg=cfg)

@router.post('/callback/phone')
async def callback_phone(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    call=get_call(db,form)
    if form.get('Digits')=='0':
        return transfer_for(db,call,cfg)
    if call.stage!='callback_phone':db.commit();return callback_prompt(call,cfg)
    try:
        phone=normalize_ticket_phone(form.get('Digits'))
        if not phone or phone in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')):raise ValueError()
    except ValueError:
        call.empty_attempts+=1;db.commit();return callback_prompt(call,cfg)
    call.empty_attempts=0
    call.caller_phone=phone;call.stage='callback_confirm';db.commit();return callback_prompt(call,cfg)

@router.post('/callback/name')
@router.post('/callback/details')
@router.post('/callback/confirm')
async def callback_confirm(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    digit=str(form.get('Digits') or '')
    if digit=='0':return transfer_for(db,call,cfg)
    if digit=='9':call.stage='menu';db.commit();return gather(MENU,'menu',cfg=cfg)
    if call.lead_id:
        db.commit();response=VoiceResponse();say(response,'Your callback request is already saved. Thank you for calling TNG Boxing.',cfg);response.hangup();return xml(response)
    if call.stage not in ('callback_confirm','callback_name','callback_details') or not call.caller_phone:
        call.stage='callback_confirm' if call.caller_phone else 'callback_phone';db.commit();return callback_prompt(call,cfg)
    if digit=='2':call.caller_phone=None;call.empty_attempts=0;call.stage='callback_phone';db.commit();return callback_prompt(call,cfg)
    if digit!='1':call.empty_attempts+=1;db.commit();return callback_prompt(call,cfg)
    department=db.get(PhoneCallDepartment,call.call_sid)
    prefix=(department_name(cfg,department.department)+' inquiry. ') if department and (department.department=='marketing' or department.department.startswith('coach_')) else ''
    lead=Lead(first_name='Phone caller',last_name='',email='',phone=call.caller_phone,status='new',conversion_source='phone_assistant',notes=prefix+'Caller requested a callback by pressing 1. Name and spoken message were not collected.')
    db.add(lead);db.flush();call.lead_id=lead.id;call.stage='callback_saved'
    from .tracking import activity
    activity(db,call,'callback_saved','Keypad-confirmed callback');db.commit()
    response=VoiceResponse();say(response,'Thank you. Your callback request has been saved for the TNG Boxing team. Goodbye.',cfg);response.hangup();return xml(response)

@router.post('/transfer-result')
async def transfer_result(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    from .tracking import activity
    transfer_status=str(form.get('DialCallStatus',''))
    if transfer_status in ('completed','busy','failed','no-answer','canceled'):activity(db,call,'transfer_result',transfer_status)
    if form.get('DialCallStatus')=='completed':
        department=db.get(PhoneCallDepartment,call.call_sid)
        call.stage='coach_connected' if department and department.department.startswith('coach_') else ('marketing_connected' if department and department.department=='marketing' else 'staff_connected');db.commit();response=VoiceResponse();response.hangup();return xml(response)
    if call.caller_phone in (cfg.public_number,os.getenv('TWILIO_PHONE_NUMBER')):call.caller_phone=None
    call.stage='callback_confirm' if call.caller_phone else 'callback_phone';db.commit()
    return callback_prompt(call,cfg)

@router.post('/status')
async def status_callback(request:Request,db:Session=Depends(get_db)):
    form=await verified(request)
    call=get_call(db,form)
    if call:
        status=str(form.get('CallStatus',''))
        if status in ('queued','ringing','in-progress','completed','busy','failed','no-answer','canceled') and call.status not in ('completed','busy','failed','no-answer','canceled'):
            from .tracking import activity
            try:duration=max(0,min(int(form.get('CallDuration','')),86400))
            except (ValueError,TypeError):duration=None
            activity(db,call,'call_status',status,duration)
            call.status=status;db.commit()
    return Response(status_code=204)
