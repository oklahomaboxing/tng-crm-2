"""NumberBarn-forwarded Twilio speech/keypad receptionist; approved answers only."""
import json,os,re
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response,JSONResponse
from pydantic import BaseModel,Field,field_validator
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
STAFF_NUMBER='+14059895843'
MENU='For hours and location, say location or press 1. For memberships, say membership or press 2. For boxing events and tickets, say events or press 3. To request a callback or gym visit, say callback or press 4. To speak to staff, say staff or press 0.'

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

class PhoneConfig(BaseModel):
    enabled:bool=False
    public_number:str=PUBLIC_NUMBER
    staff_number:str=STAFF_NUMBER
    greeting:str=Field(default='Thank you for calling TNG Boxing, The Next Generation.',min_length=5,max_length=500)
    hours_answer:str=Field(default='TNG Boxing is located at 8416 Northwest Expressway in Oklahoma City, Oklahoma, 73162. For current opening hours and class times, please speak with our staff.',min_length=5,max_length=2000)
    membership_answer:str=Field(default='Our staff can help you choose a boxing membership and discuss current rates. To arrange a visit or request membership information, press 4. To speak with staff, press 0.',min_length=5,max_length=2000)
    events_answer:str=Field(default='For current TNG Promotions boxing events, ticket availability and fight night details, visit tngos.tngboxinggym.com or speak with staff by pressing 0.',min_length=5,max_length=2000)

    @field_validator('public_number','staff_number')
    @classmethod
    def phone(cls,value):
        try:
            phone=normalize_ticket_phone(value)
            if not phone:raise ValueError()
            return phone
        except ValueError:raise ValueError('Enter a valid phone number including its area code')

class ConnectPhone(BaseModel):
    acknowledge_voice_charges:bool=False

def base():return os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')
def url(path):return base()+'/api/phone/'+path
def config(db):
    row=db.get(PhoneSettings,1)
    return PhoneConfig(**json.loads(row.settings_json)) if row else PhoneConfig()
def xml(response):return Response(str(response),media_type='application/xml',headers={'Cache-Control':'no-store'})
def say(response,text):response.say(text,language='en-US')
def gather(text,path,input='speech dtmf',digits=1):
    response=VoiceResponse()
    g=response.gather(input=input,num_digits=digits,action=url(path),method='POST',timeout=6,speech_timeout='auto',action_on_empty_result=True,language='en-US')
    say(g,text)
    say(response,'Please call again if you need help. Goodbye.');response.hangup()
    return xml(response)
def transfer(cfg):
    response=VoiceResponse();say(response,'Please hold while I connect you with TNG Boxing staff.')
    dial=response.dial(timeout=20,action=url('transfer-result'),method='POST')
    dial.number(cfg.staff_number)
    return xml(response)
def callback_prompt(call):
    if call.empty_attempts>=3:
        response=VoiceResponse();say(response,'We could not complete your request. Please call again or visit TNG Boxing. Goodbye.');response.hangup();return xml(response)
    if not call.caller_phone:return gather('Please enter a ten digit callback number, including the area code.','callback/phone',input='dtmf',digits=10)
    return gather('To request a callback from our team, please say your first and last name now, or press zero to speak with staff.','callback/name')

def no_private_lookup(text):
    return bool(re.search(r'\b(my account|my membership|my balance|payment status|refund|cancel|billing|password)\b',text))

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
    return {'settings':cfg.model_dump(),'connected':bool(row and row.connected),'forwarding_number':os.getenv('TWILIO_PHONE_NUMBER',''),
            'voice_url':url('incoming'),'voice_status_url':url('status'),
            'twilio_configured':all(os.getenv(k) for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_PHONE_NUMBER')),
            'today_calls':db.query(PhoneCall).filter(PhoneCall.created_at>=periods['day_start'],PhoneCall.created_at<periods['day_end']).count()}

@router.get('/admin')
def admin_status(db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    data=view(db)
    data['calls']=[{'call_sid':c.call_sid,'caller_last_four':(c.caller_phone or '')[-4:],'status':c.status,'stage':c.stage,'lead_id':c.lead_id,'created_at':c.created_at.isoformat()+'Z'} for c in db.query(PhoneCall).order_by(PhoneCall.created_at.desc()).limit(50)]
    return JSONResponse(data,headers={'Cache-Control':'private, no-store'})

@router.put('/admin')
def save_config(body:PhoneConfig,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    assigned=normalize_ticket_phone(os.getenv('TWILIO_PHONE_NUMBER',''))
    if body.staff_number in (body.public_number,assigned):raise HTTPException(400,'Staff transfer number must not forward back to the NumberBarn or Twilio line')
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
    if cfg.staff_number in (cfg.public_number,normalize_ticket_phone(os.getenv('TWILIO_PHONE_NUMBER',''))):raise HTTPException(400,'Staff transfer would create a routing loop')
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
    if not cfg.enabled:
        call.stage='staff_direct';db.commit();return transfer(cfg)
    db.commit()
    return gather(cfg.greeting+' '+MENU,'menu')

@router.post('/menu')
async def menu(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    if not cfg.enabled:return transfer(cfg)
    call=get_call(db,form);call.turns+=1
    text=str(form.get('SpeechResult',''))[:500].lower();digit=str(form.get('Digits',''))
    if not text and not digit:call.empty_attempts+=1
    else:call.empty_attempts=0
    if call.turns>=12 or call.empty_attempts>=3:db.commit();return transfer(cfg)
    if digit=='0' or no_private_lookup(text) or re.search(r'\b(staff|person|operator|human|front desk|transfer|agent)\b',text):
        call.stage='transfer';db.commit();return transfer(cfg)
    if digit=='4' or re.search(r'\b(callback|call back|call me|tour|visit|join|sign up)\b',text):
        call.stage='callback_name' if call.caller_phone else 'callback_phone';db.commit();return callback_prompt(call)
    answer=None
    if digit=='1' or re.search(r'\b(hours|location|address|directions|where|open|close|closing|schedule)\b',text):answer=cfg.hours_answer
    elif digit=='2' or re.search(r'\b(membership|memberships|price|prices|cost|rates|training|classes)\b',text):answer=cfg.membership_answer
    elif digit=='3' or re.search(r'\b(events|event|fight|tickets|ticket|weigh)\b',text):answer=cfg.events_answer
    db.commit()
    return gather((answer+' ' if answer else 'Please choose an option. ')+MENU,'menu')

@router.post('/callback/phone')
async def callback_phone(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    call=get_call(db,form)
    if form.get('Digits')=='0':
        call.stage='transfer';db.commit();return transfer(cfg)
    if call.stage!='callback_phone':db.commit();return callback_prompt(call)
    try:
        phone=normalize_ticket_phone(form.get('Digits'))
        if not phone:raise ValueError()
    except ValueError:
        call.empty_attempts+=1;db.commit();return callback_prompt(call)
    call.empty_attempts=0
    call.caller_phone=phone;call.stage='callback_name';db.commit();return callback_prompt(call)

@router.post('/callback/name')
async def callback_name(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    call=get_call(db,form)
    if form.get('Digits')=='0':
        call.stage='transfer';db.commit();return transfer(cfg)
    if call.stage not in ('callback_name','callback_details'):db.commit();return callback_prompt(call)
    if call.stage=='callback_name':
        name=re.sub(r'[\x00-\x1f]','',str(form.get('SpeechResult','')))[:150].strip()
        if not name:
            call.empty_attempts+=1;db.commit();return callback_prompt(call)
        call.empty_attempts=0
        call.caller_name=name;call.stage='callback_details';db.commit()
    else:db.commit()
    return gather('Thank you. Briefly tell us what you would like to know, or what kind of gym visit you are interested in.','callback/details')

@router.post('/callback/details')
async def callback_details(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db)
    call=get_call(db,form)
    if form.get('Digits')=='0':
        call.stage='transfer';db.commit();return transfer(cfg)
    if call.lead_id:
        db.commit();response=VoiceResponse();say(response,'Your callback request is already saved. Thank you for calling TNG Boxing.');response.hangup();return xml(response)
    if call.stage!='callback_details' or not call.caller_name or not call.caller_phone:db.commit();return callback_prompt(call)
    details=re.sub(r'[\x00-\x1f]',' ',str(form.get('SpeechResult','')))[:1500].strip()
    if not details:
        call.empty_attempts+=1;db.commit()
        if call.empty_attempts>=3:return callback_prompt(call)
        return gather('Please briefly tell us what you would like staff to call you about.','callback/details')
    names=call.caller_name.split(maxsplit=1)
    lead=Lead(first_name=names[0],last_name=names[1] if len(names)>1 else '',email='',phone=call.caller_phone,status='new',conversion_source='phone_assistant',notes='Caller requested a staff callback. '+details)
    db.add(lead);db.flush();call.lead_id=lead.id;call.stage='callback_saved';db.commit()
    response=VoiceResponse();say(response,'Thank you. Your request has been saved for the TNG Boxing team. Staff will follow up with you. Goodbye.');response.hangup();return xml(response)

@router.post('/transfer-result')
async def transfer_result(request:Request,db:Session=Depends(get_db)):
    form=await verified(request);cfg=config(db);call=get_call(db,form)
    if form.get('DialCallStatus')=='completed':
        call.stage='staff_connected';db.commit();response=VoiceResponse();response.hangup();return xml(response)
    call.stage='callback_name' if call.caller_phone else 'callback_phone';db.commit()
    return callback_prompt(call)

@router.post('/status')
async def status_callback(request:Request,db:Session=Depends(get_db)):
    form=await verified(request)
    call=get_call(db,form)
    if call:
        status=str(form.get('CallStatus',''))
        if status in ('queued','ringing','in-progress','completed','busy','failed','no-answer','canceled') and call.status not in ('completed','busy','failed','no-answer','canceled'):
            call.status=status;db.commit()
    return Response(status_code=204)
