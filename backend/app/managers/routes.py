"""Manager-owned roster creation, profile maintenance and reviewed pool links."""
from datetime import datetime
import hashlib,re,time
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response,Header
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import Column,Integer,String,Text,DateTime,ForeignKey,UniqueConstraint,func,or_,text
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.models import User,SecurityLog
from app.matchmaker.models import BoxingFighter,BoxingManagerAccount,BoxingManagerFighter
from app.auth import create_token,decode_token
from .access import manager_for,represented_fighter
router=APIRouter(prefix='/api/manager-workspace',tags=['Manager workspace'])

class ManagerRosterSubmission(Base):
    __tablename__='manager_roster_submissions'
    __table_args__=(UniqueConstraint('manager_id','request_key',name='uq_manager_roster_request'),)
    id=Column(Integer,primary_key=True)
    manager_id=Column(Integer,ForeignKey('boxing_manager_accounts.id'),nullable=False,index=True)
    fighter_id=Column(Integer,ForeignKey('boxing_fighters.id'),nullable=True)
    request_key=Column(String(80),nullable=False)
    boxer_name=Column(String(160),nullable=False)
    boxrec_id=Column(String(40),default='',nullable=False)
    email=Column(String(254),default='',nullable=False)
    phone=Column(String(40),default='',nullable=False)
    status=Column(String(30),nullable=False)
    notes=Column(Text,default='',nullable=False)
    reviewed_by=Column(Integer,ForeignKey('users.id'),nullable=True)
    reviewed_at=Column(DateTime,nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

class ProfileBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    legal_name:str=Field(min_length=1,max_length=160)
    email:str=Field(default='',max_length=254)
    phone:str=Field(default='',max_length=40)
    city:str=Field(default='',max_length=100)
    state:str=Field(default='',max_length=100)
    country:str=Field(default='',max_length=100)
    gym:str=Field(default='',max_length=160)
    coach:str=Field(default='',max_length=160)
    stance:str=Field(default='',max_length=40)
    sex:str=Field(default='',max_length=30)
    nationality:str=Field(default='',max_length=100)
    fight_weight:float|None=Field(default=None,gt=0,le=1000)
    available_weight_min:float|None=Field(default=None,gt=0,le=1000)
    available_weight_max:float|None=Field(default=None,gt=0,le=1000)
    instagram:str=Field(default='',max_length=500)
    facebook:str=Field(default='',max_length=500)
    tiktok:str=Field(default='',max_length=500)
    twitter:str=Field(default='',max_length=500)
    @model_validator(mode='after')
    def validate_profile(self):
        if not self.legal_name.strip():raise ValueError('Enter the boxer’s legal name')
        if self.email and ('@' not in self.email or any(c.isspace() for c in self.email)):raise ValueError('Enter a valid email or leave it blank')
        digits=''.join(c for c in self.phone if c.isdigit())
        if self.phone and (not 10<=len(digits)<=15 or any(c not in '+0123456789 ()-.' for c in self.phone)):raise ValueError('Enter a complete phone number')
        if self.available_weight_min and self.available_weight_max and self.available_weight_min>self.available_weight_max:raise ValueError('Minimum weight cannot exceed maximum weight')
        return self

class NewBoxerBody(ProfileBody):
    boxrec_id:str=Field(default='',max_length=250)
    pro_record:str=Field(default='',max_length=30)
    request_key:str=Field(min_length=8,max_length=80)
    @model_validator(mode='after')
    def validate_identity(self):
        if not (self.boxrec_id.strip() or self.email.strip() or self.phone.strip()):raise ValueError('Provide BoxRec ID, email or phone to avoid duplicate boxer profiles')
        if self.pro_record and not re.fullmatch(r'\d{1,3}-\d{1,3}(?:-\d{1,3})?',self.pro_record.strip()):raise ValueError('Use a record such as 2-1 or 2-1-0, or leave it blank')
        return self

class ProfileUpdate(ProfileBody):
    expected_updated_at:str

class ReviewBody(BaseModel):
    decision:Literal['approve','decline']
    note:str=Field(default='',max_length=1000)

def admin(user=Depends(current_user)):
    if user.role not in ('admin','staff'):raise HTTPException(403,'Roster review requires event staff')
    return user

def serialize(f):
    return {'id':f.id,**{k:getattr(f,k) for k in ProfileBody.model_fields},'pro_record':f.pro_record or '', 'boxrec_id':f.boxrec_id or '', 'updated_at':f.updated_at.isoformat() if f.updated_at else ''}

def audit(db,user,action,fid):db.add(SecurityLog(user_id=user.id,action=action,description=f'Manager roster/profile action for fighter {fid}'))

@router.get('/roster')
def roster(response:Response,db=Depends(get_db),user=Depends(current_user)):
    manager=manager_for(db,user);response.headers['Cache-Control']='private, no-store'
    fighters=db.query(BoxingFighter).join(BoxingManagerFighter,BoxingManagerFighter.fighter_id==BoxingFighter.id).filter(BoxingManagerFighter.manager_account_id==manager.id,BoxingManagerFighter.active.is_(True)).order_by(BoxingFighter.legal_name).all()
    requests=db.query(ManagerRosterSubmission).filter_by(manager_id=manager.id).order_by(ManagerRosterSubmission.id.desc()).limit(50).all()
    return {'manager':{'name':manager.display_name or user.name,'company':manager.company_name},'fighters':[serialize(f) for f in fighters],'requests':[{'id':r.id,'boxer_name':r.boxer_name,'status':r.status,'notes':r.notes} for r in requests if r.status!='added']}

@router.post('/fighters/{fighter_id}/token')
def workspace_token(fighter_id:int,response:Response,authorization:str=Header(default=''),db=Depends(get_db),user=Depends(current_user)):
    represented_fighter(db,user,fighter_id);response.headers['Cache-Control']='private, no-store'
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    seconds=min(1800,max(1,int(payload.get('exp',time.time())-time.time())))
    claims={'sub':str(user.id),'managed_fighter_id':fighter_id}
    if payload.get('sid'):claims.update(sid=payload['sid'],persistent=bool(payload.get('persistent')))
    return {'token':create_token(claims,minutes=seconds/60,credential=payload.get('credential')),'fighter_id':fighter_id,'expires_in':seconds}

@router.post('/fighters')
def add_boxer(body:NewBoxerBody,db=Depends(get_db),user=Depends(current_user)):
    manager=manager_for(db,user,True)
    prior=db.query(ManagerRosterSubmission).filter_by(manager_id=manager.id,request_key=body.request_key).first()
    boxrec=body.boxrec_id.strip()
    if boxrec:
        match=re.fullmatch(r'(?:https?://(?:www\.)?boxrec\.com/(?:en/)?(?:box-pro|box-am|boxer)/)?(\d+)/?',boxrec)
        if not match:raise HTTPException(422,'Enter a numeric BoxRec ID or a BoxRec boxer profile URL')
        boxrec=match[1]
    name=body.legal_name.strip();email=body.email.strip().lower();phone=body.phone.strip()
    if prior:
        if (prior.boxer_name,prior.boxrec_id,prior.email,prior.phone)!=(name,boxrec,email,phone):raise HTTPException(409,'This save key belongs to a different boxer submission. Reopen Add boxer to start a new submission')
        return {'status':prior.status,'request_id':prior.id,'fighter_id':prior.fighter_id if prior.status=='added' else None}
    if db.get_bind().dialect.name=='postgresql':
        identity=boxrec or (email+'|'+name.casefold()) or (phone+'|'+name.casefold())
        key=int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8],'big',signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':key})
    tests=[]
    if boxrec:tests.append(BoxingFighter.boxrec_id==boxrec)
    if email:tests.append((func.lower(func.trim(BoxingFighter.email))==email)&(func.lower(func.trim(BoxingFighter.legal_name))==name.lower()))
    if phone:
        normalized=BoxingFighter.phone
        for char in ('+',' ','-','(',')','.') :normalized=func.replace(normalized,char,'')
        digits=''.join(c for c in phone if c.isdigit());variants={digits}
        if len(digits)==10:variants.add('1'+digits)
        if len(digits)==11 and digits.startswith('1'):variants.add(digits[1:])
        tests.append(normalized.in_(variants)&(func.lower(func.trim(BoxingFighter.legal_name))==name.lower()))
    matches=db.query(BoxingFighter).filter(or_(*tests)).all()
    existing=matches[0] if len(matches)==1 else None
    request=ManagerRosterSubmission(manager_id=manager.id,request_key=body.request_key,boxer_name=name,boxrec_id=boxrec,email=email,phone=phone,status='needs_review')
    if matches:
        request.fighter_id=existing.id if existing else None
        if existing and db.query(BoxingManagerFighter).filter_by(manager_account_id=manager.id,fighter_id=existing.id,active=True).first():request.status='added'
        else:request.notes='Existing or ambiguous fighter record found. TNG must verify the representation link.'
    else:
        values=body.model_dump(exclude={'boxrec_id','pro_record','request_key'})
        values={k:v.strip() if isinstance(v,str) else v for k,v in values.items()};values.update(email=email,phone=phone)
        boxer=BoxingFighter(**values,boxrec_id=boxrec,pro_record=body.pro_record.strip(),source='manager_portal',source_id=manager.id,manager_name=manager.display_name or user.name,manager_email=manager.email or user.email,manager_phone=manager.phone or '',submitted_by_name=user.name,submitted_by_role='manager',submitted_by_email=user.email)
        db.add(boxer);db.flush();db.add(BoxingManagerFighter(manager_account_id=manager.id,fighter_id=boxer.id,active=True,notes='Manager submitted a new boxer to the TNG fighter pool.'));request.fighter_id=boxer.id;request.status='added';audit(db,user,'MANAGER_BOXER_ADDED_TO_POOL',boxer.id)
    db.add(request);db.commit();return {'status':request.status,'request_id':request.id,'fighter_id':request.fighter_id if request.status=='added' else None}

@router.put('/fighters/{fighter_id}')
def update_profile(fighter_id:int,body:ProfileUpdate,db=Depends(get_db),user=Depends(current_user)):
    manager=manager_for(db,user,True);represented_fighter(db,user,fighter_id)
    f=db.query(BoxingFighter).filter_by(id=fighter_id).with_for_update().first()
    if not f:raise HTTPException(404,'Boxer not found')
    if (f.updated_at.isoformat() if f.updated_at else '')!=body.expected_updated_at:raise HTTPException(409,'This profile changed. Refresh before saving')
    for k,v in body.model_dump(exclude={'expected_updated_at'}).items():setattr(f,k,v.strip() if isinstance(v,str) else v)
    f.email=f.email.lower();f.updated_at=datetime.utcnow();audit(db,user,'MANAGER_BOXER_PROFILE_UPDATED',f.id);db.commit();return serialize(f)

@router.delete('/fighters/{fighter_id}')
def remove_boxer(fighter_id:int,db=Depends(get_db),user=Depends(current_user)):
    manager=manager_for(db,user,True)
    db.query(BoxingFighter).filter_by(id=fighter_id).with_for_update().first()
    links=db.query(BoxingManagerFighter).filter_by(manager_account_id=manager.id,fighter_id=fighter_id,active=True).all()
    if not links:raise HTTPException(404,'This boxer is not on your active roster')
    for link in links:link.active=False;link.released_at=datetime.utcnow()
    f=db.get(BoxingFighter,fighter_id)
    if f and f.manager_email==(manager.email or user.email) and f.manager_name==(manager.display_name or user.name):f.manager_name='';f.manager_email='';f.manager_phone=''
    audit(db,user,'MANAGER_BOXER_RELEASED',fighter_id);db.commit();return {'released':True,'fighter_pool_record_preserved':True}

@router.get('/roster-requests')
def roster_requests(response:Response,db=Depends(get_db),user=Depends(admin)):
    response.headers['Cache-Control']='private, no-store'
    rows=db.query(ManagerRosterSubmission).filter_by(status='needs_review').order_by(ManagerRosterSubmission.id).all()
    managers={m.id:m for m in db.query(BoxingManagerAccount)}
    return [{'id':r.id,'manager_id':r.manager_id,'manager_name':managers[r.manager_id].display_name,'boxer_name':r.boxer_name,'boxrec_id':r.boxrec_id,'email':r.email,'phone':r.phone,'fighter_id':r.fighter_id,'notes':r.notes} for r in rows]

@router.post('/roster-requests/{request_id}/review')
def review_link(request_id:int,body:ReviewBody,db=Depends(get_db),user=Depends(admin)):
    row=db.query(ManagerRosterSubmission).filter_by(id=request_id).with_for_update().first()
    if not row:raise HTTPException(404,'Roster request not found')
    if row.status!='needs_review':raise HTTPException(409,'This roster request has already been reviewed')
    manager=db.query(BoxingManagerAccount).filter_by(id=row.manager_id).with_for_update().first()
    manager_user=db.get(User,manager.user_id) if manager else None
    if not manager or not manager.active or not manager_user or not manager_user.active or manager_user.role!='manager':raise HTTPException(409,'Manager access is inactive')
    if body.decision=='approve':
        if not row.fighter_id:raise HTTPException(409,'Resolve the ambiguous boxer match in the fighter pool before linking')
        fighter=db.query(BoxingFighter).filter_by(id=row.fighter_id).with_for_update().first()
        if not fighter:raise HTTPException(404,'Boxer no longer exists')
        other=db.query(BoxingManagerFighter).filter(BoxingManagerFighter.fighter_id==row.fighter_id,BoxingManagerFighter.active.is_(True),BoxingManagerFighter.manager_account_id!=manager.id).first()
        if other:raise HTTPException(409,'Another manager currently represents this boxer. Review and release the existing assignment before transferring access')
        own=db.query(BoxingManagerFighter).filter_by(fighter_id=row.fighter_id,manager_account_id=manager.id,active=True).first()
        if not own:db.add(BoxingManagerFighter(fighter_id=row.fighter_id,manager_account_id=manager.id,active=True,notes='TNG approved roster link request '+str(row.id)))
        fighter.manager_name=manager.display_name or manager_user.name;fighter.manager_email=manager.email or manager_user.email;fighter.manager_phone=manager.phone or ''
        row.status='approved';audit(db,user,'MANAGER_ROSTER_LINK_APPROVED',row.fighter_id)
    else:
        row.status='declined';audit(db,user,'MANAGER_ROSTER_LINK_DECLINED',row.fighter_id)
    row.reviewed_by=user.id;row.reviewed_at=datetime.utcnow();row.notes=body.note.strip() or row.notes;db.commit();return {'status':row.status}
