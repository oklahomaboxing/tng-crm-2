"""Administrator-authorized Microsoft 365 mailbox for transactional welcome letters."""
import base64,hashlib,hmac,json,os,re,secrets,uuid
from datetime import datetime,timedelta
from urllib.parse import urlencode,quote
import requests
from cryptography.fernet import Fernet
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from fastapi.responses import JSONResponse,RedirectResponse
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,String,Text,Boolean,DateTime,ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import Base,get_db
from app.models import User
from app.auth import SECRET_KEY
from app.account_security import AccountSecurity,session_marker
from app.core.dependencies import current_user
from app.core.permissions import require_admin

router=APIRouter(prefix='/api/mail/microsoft365',tags=['Microsoft 365 email'])
MAILBOX='marketing@tngboxinggym.com'
GRAPH='https://graph.microsoft.com/v1.0'
SCOPES='offline_access https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Send'
COOKIE='tng_microsoft_mail_oauth'
GUID=re.compile(r'^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')

class MicrosoftMailbox(Base):
    __tablename__='microsoft_mailbox_connections'
    id=Column(Integer,primary_key=True)
    tenant_id=Column(String(40),nullable=False)
    client_id=Column(String(40),nullable=False)
    client_secret=Column(Text,nullable=False)
    refresh_token=Column(Text,nullable=True)
    access_token=Column(Text,nullable=True)
    expires_at=Column(DateTime,nullable=True)
    mailbox=Column(String(255),nullable=True)
    enabled=Column(Boolean,default=False,nullable=False)
    generation=Column(Integer,default=1,nullable=False)

class MicrosoftMailOAuthState(Base):
    __tablename__='microsoft_mail_oauth_states'
    state_hash=Column(String(64),primary_key=True)
    cookie_hash=Column(String(64),nullable=False)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    session_marker=Column(String(128),nullable=False)
    generation=Column(Integer,nullable=False)
    verifier=Column(Text,nullable=False)
    expires_at=Column(DateTime,nullable=False)
    used=Column(Boolean,default=False,nullable=False)
    started=Column(Boolean,default=False,nullable=False)

class MicrosoftMailAttempt(Base):
    __tablename__='microsoft_mail_attempts'
    key=Column(String(150),primary_key=True)
    payload_hash=Column(String(64),nullable=False)
    request_id=Column(String(50),nullable=False)
    status=Column(String(30),nullable=False,default='submitting')
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class MicrosoftConfig(BaseModel):
    tenant_id:str=Field(min_length=36,max_length=36)
    client_id:str=Field(min_length=36,max_length=36)
    client_secret:str|None=Field(default=None,max_length=5000)

class MailSubmissionError(Exception):
    def __init__(self,message,code=''):
        super().__init__(message);self.code=code


def cipher():
    key=hashlib.sha256(b'tng-microsoft-mail-v1:'+SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))
def encrypt(value):return cipher().encrypt(value.encode()).decode()
def decrypt(value):return cipher().decrypt(value.encode()).decode()
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def redirect_uri():return os.getenv('TNG_BACKEND_URL','https://sea-lion-app-2-gxyfr.ondigitalocean.app').rstrip('/')+'/api/mail/microsoft365/callback'
def token_url(cfg):return 'https://login.microsoftonline.com/'+cfg.tenant_id+'/oauth2/v2.0/token'
def selected_provider(db):
    cfg=db.get(MicrosoftMailbox,1)
    return 'microsoft365' if cfg and cfg.enabled else 'resend'

def safe_status(db):
    cfg=db.get(MicrosoftMailbox,1)
    return {'configured':bool(cfg),'connected':bool(cfg and cfg.refresh_token and cfg.mailbox==MAILBOX),
            'provider':selected_provider(db),'mailbox':MAILBOX,'tenant_id':cfg.tenant_id if cfg else '',
            'client_id':cfg.client_id if cfg else '', 'has_client_secret':bool(cfg and cfg.client_secret),
            'redirect_uri':redirect_uri()}

@router.get('/status')
def status(db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    return JSONResponse(safe_status(db),headers={'Cache-Control':'private, no-store'})

@router.put('/config')
def configure(body:MicrosoftConfig,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    if not GUID.fullmatch(body.tenant_id) or not GUID.fullmatch(body.client_id):raise HTTPException(400,'Tenant and application IDs must be Microsoft GUIDs')
    cfg=db.get(MicrosoftMailbox,1)
    if not body.client_secret and (not cfg or cfg.tenant_id!=body.tenant_id or cfg.client_id!=body.client_id):raise HTTPException(400,'Enter the application client secret in this secure form')
    if not cfg:
        cfg=MicrosoftMailbox(id=1,tenant_id=body.tenant_id,client_id=body.client_id,client_secret=encrypt(body.client_secret));db.add(cfg)
    else:
        cfg.tenant_id=body.tenant_id;cfg.client_id=body.client_id
        if body.client_secret:cfg.client_secret=encrypt(body.client_secret)
        cfg.refresh_token=None;cfg.access_token=None;cfg.mailbox=None;cfg.enabled=False;cfg.generation+=1
    db.commit()
    return JSONResponse(safe_status(db),headers={'Cache-Control':'private, no-store'})

@router.post('/connect')
def connect(response:Response,db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    cfg=db.get(MicrosoftMailbox,1)
    if not cfg:raise HTTPException(409,'Save the Microsoft application registration first')
    state=secrets.token_urlsafe(32);cookie=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    db.query(MicrosoftMailOAuthState).filter(MicrosoftMailOAuthState.expires_at<datetime.utcnow()).delete(synchronize_session=False)
    db.add(MicrosoftMailOAuthState(state_hash=digest(state),cookie_hash=digest(cookie),user_id=user.id,
        session_marker=session_marker(user,db.get(AccountSecurity,user.id)),generation=cfg.generation,
        verifier=encrypt(verifier),expires_at=datetime.utcnow()+timedelta(minutes=10)))
    db.commit()
    response.headers['Cache-Control']='no-store'
    return {'authorization_url':redirect_uri().replace('/callback','/begin')+'?'+urlencode({'state':state,'handoff':cookie})}

@router.get('/begin')
def begin(state:str='',handoff:str='',db:Session=Depends(get_db)):
    row=db.get(MicrosoftMailOAuthState,digest(state)) if state else None
    cfg=db.get(MicrosoftMailbox,1)
    if not row or row.used or row.started or row.expires_at<datetime.utcnow() or not handoff or not hmac.compare_digest(row.cookie_hash,digest(handoff)) or not cfg or cfg.generation!=row.generation:
        raise HTTPException(400,'Microsoft connection link expired. Start again from TNGOS.')
    claimed=db.query(MicrosoftMailOAuthState).filter_by(state_hash=row.state_hash,started=False,used=False).update({'started':True},synchronize_session=False)
    db.commit()
    if not claimed:raise HTTPException(400,'Microsoft connection link already used')
    verifier=decrypt(row.verifier)
    params={'client_id':cfg.client_id,'response_type':'code','redirect_uri':redirect_uri(),'response_mode':'query',
            'scope':SCOPES,'state':state,'code_challenge':base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='),
            'code_challenge_method':'S256','prompt':'select_account','login_hint':MAILBOX}
    response=RedirectResponse('https://login.microsoftonline.com/'+cfg.tenant_id+'/oauth2/v2.0/authorize?'+urlencode(params),status_code=303)
    response.set_cookie(COOKIE,handoff,max_age=600,secure=True,httponly=True,samesite='lax',path='/api/mail/microsoft365')
    response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='no-referrer'
    return response

@router.get('/callback')
def callback(request:Request,state:str='',code:str='',error:str='',db:Session=Depends(get_db)):
    row=db.get(MicrosoftMailOAuthState,digest(state)) if state else None
    cfg=db.get(MicrosoftMailbox,1)
    user=db.get(User,row.user_id) if row else None
    cookie=request.cookies.get(COOKIE,'')
    if not row or not row.started or row.used or row.expires_at<datetime.utcnow() or not cookie or not hmac.compare_digest(row.cookie_hash,digest(cookie)):
        raise HTTPException(400,'Microsoft connection expired or invalid. Start again from TNGOS.')
    if not cfg or cfg.generation!=row.generation or not user or not user.active or user.role!='admin' or not hmac.compare_digest(row.session_marker,session_marker(user,db.get(AccountSecurity,user.id))):
        raise HTTPException(403,'Administrator authorization changed. Start a new connection.')
    claimed=db.query(MicrosoftMailOAuthState).filter_by(state_hash=row.state_hash,used=False).update({'used':True},synchronize_session=False)
    db.commit()
    if not claimed:raise HTTPException(400,'Microsoft connection link already used')
    if error or not code:raise HTTPException(400,'Microsoft sign-in was cancelled or denied. Return to TNGOS and connect again.')
    try:
        r=requests.post(token_url(cfg),data={'client_id':cfg.client_id,'client_secret':decrypt(cfg.client_secret),'grant_type':'authorization_code',
            'code':code,'redirect_uri':redirect_uri(),'code_verifier':decrypt(row.verifier),'scope':SCOPES},timeout=15)
        if r.status_code!=200:raise ValueError()
        tokens=r.json()
        if not tokens.get('access_token') or not tokens.get('refresh_token'):raise ValueError()
        scopes={s.rsplit('/',1)[-1].lower() for s in tokens.get('scope','').split()}
        if 'mail.send' not in scopes:raise ValueError()
        profile=requests.get(GRAPH+'/me',params={'$select':'id,mail,userPrincipalName'},headers={'Authorization':'Bearer '+tokens['access_token']},timeout=15)
        if profile.status_code!=200:raise ValueError()
        identity=profile.json()
        mailbox=(identity.get('mail') or identity.get('userPrincipalName') or '').casefold()
        if mailbox!=MAILBOX:raise HTTPException(400,'Sign in to the marketing@tngboxinggym.com mailbox. Shared mailboxes need a separate Send As configuration.')
    except HTTPException:raise
    except Exception:raise HTTPException(502,'Microsoft did not complete the connection. Check app credentials and delegated permissions, then reconnect.')
    # Config/disconnect may change while Microsoft responds. Never restore a superseded connection.
    db.expire_all()
    cfg=db.get(MicrosoftMailbox,1);user=db.get(User,row.user_id)
    if not cfg or cfg.generation!=row.generation or not user or not user.active or user.role!='admin' or not hmac.compare_digest(row.session_marker,session_marker(user,db.get(AccountSecurity,user.id))):raise HTTPException(409,'Email settings changed. Connect again.')
    cfg.refresh_token=encrypt(tokens['refresh_token']);cfg.access_token=encrypt(tokens['access_token'])
    cfg.expires_at=datetime.utcnow()+timedelta(seconds=int(tokens.get('expires_in',3600)));cfg.mailbox=MAILBOX;cfg.enabled=True;db.commit()
    response=RedirectResponse(os.getenv('TNG_APP_URL','https://tngos.tngboxinggym.com').rstrip('/')+'/#/system-overview',status_code=303)
    response.delete_cookie(COOKIE,path='/api/mail/microsoft365',secure=True,httponly=True,samesite='lax')
    response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='no-referrer'
    return response

@router.post('/disconnect')
def disconnect(db:Session=Depends(get_db),user=Depends(current_user)):
    require_admin(user)
    cfg=db.get(MicrosoftMailbox,1)
    if cfg:
        cfg.enabled=False;cfg.refresh_token=None;cfg.access_token=None;cfg.expires_at=None;cfg.mailbox=None;cfg.generation+=1;db.commit()
    return safe_status(db)


def access_token(db):
    cfg=db.query(MicrosoftMailbox).filter_by(id=1).with_for_update().one_or_none()
    if not cfg or not cfg.enabled or not cfg.refresh_token:raise MailSubmissionError('Reconnect the Microsoft mailbox in System Overview','403')
    if cfg.access_token and cfg.expires_at and cfg.expires_at>datetime.utcnow()+timedelta(seconds=60):
        token=decrypt(cfg.access_token);db.commit();return token
    try:
        r=requests.post(token_url(cfg),data={'client_id':cfg.client_id,'client_secret':decrypt(cfg.client_secret),'grant_type':'refresh_token',
             'refresh_token':decrypt(cfg.refresh_token),'scope':SCOPES},timeout=15)
        if r.status_code!=200:raise ValueError()
        data=r.json();token=data['access_token']
        cfg.access_token=encrypt(token);cfg.expires_at=datetime.utcnow()+timedelta(seconds=int(data.get('expires_in',3600)))
        if data.get('refresh_token'):cfg.refresh_token=encrypt(data['refresh_token'])
        db.commit();return token
    except Exception:
        db.rollback();raise MailSubmissionError('Microsoft authorization needs reconnection','403')


def send_welcome(db,payload,key):
    """Mail.Send only. Unknown Graph submissions are never replayed or sent via a fallback."""
    signature=digest(json.dumps(payload,sort_keys=True))
    attempt=db.get(MicrosoftMailAttempt,key)
    if attempt:
        if attempt.payload_hash!=signature:raise MailSubmissionError('Microsoft email payload changed; review required','409')
        if attempt.status=='accepted':return {'id':'microsoft365:'+attempt.request_id}
        if attempt.status!='rejected':raise MailSubmissionError('Check Outlook Sent Items: this Microsoft submission is unconfirmed and will not be sent again automatically.')
    token=access_token(db)
    if not attempt:
        attempt=MicrosoftMailAttempt(key=key,payload_hash=signature,request_id=str(uuid.uuid4()),status='submitting');db.add(attempt)
        try:db.commit()
        except IntegrityError:
            db.rollback();raise MailSubmissionError('Email is already being processed','409')
    else:
        claimed=db.query(MicrosoftMailAttempt).filter_by(key=key,status='rejected').update({'status':'submitting'},synchronize_session=False)
        db.commit()
        if not claimed:raise MailSubmissionError('Email is already being processed','409')
    headers={'Authorization':'Bearer '+token,'client-request-id':attempt.request_id,'return-client-request-id':'true'}
    message={'subject':payload['subject'],'body':{'contentType':'HTML','content':payload['html']},
             'toRecipients':[{'emailAddress':{'address':email}} for email in payload['to']],
             'replyTo':[{'emailAddress':{'address':MAILBOX}}],
             'attachments':[{'@odata.type':'#microsoft.graph.fileAttachment','name':a['filename'],'contentType':'application/pdf','contentBytes':a['content']} for a in payload.get('attachments',[])]}
    try:
        r=requests.post(GRAPH+'/me/sendMail',headers=headers,json={'message':message,'saveToSentItems':True},timeout=20,allow_redirects=False)
        if r.status_code!=202:
            attempt.status='rejected' if r.status_code in (400,401,403,404,413,422,429) else 'unknown';db.commit()
            raise MailSubmissionError('Microsoft rejected the email. Check the mailbox connection and delegated Mail.Send permission.' if attempt.status=='rejected' else 'Microsoft email submission needs review.',str(r.status_code))
        attempt.status='accepted';db.commit();return {'id':'microsoft365:'+attempt.request_id}
    except requests.RequestException:
        attempt.status='unknown';db.commit();raise MailSubmissionError('Check Outlook Sent Items: Microsoft email submission is unconfirmed and will not be sent again automatically.')
