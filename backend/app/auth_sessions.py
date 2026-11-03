"""Revocable remembered device sessions; existing credential/MFA revocation still applies."""
import hashlib
import secrets
from datetime import datetime
from fastapi import APIRouter,Depends,Header,Request,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,Boolean
from app.database import Base,get_db
from app.core.dependencies import current_user
from app.auth import create_token,decode_token

class RememberedDevice(Base):
    __tablename__='remembered_devices'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    token_hash=Column(String(64),nullable=False,unique=True)
    revoked=Column(Boolean,default=False,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow)

class RememberedDeviceDetails(Base):
    __tablename__='remembered_device_details'
    device_id=Column(Integer,ForeignKey('remembered_devices.id',ondelete='CASCADE'),primary_key=True)
    label=Column(String(80),nullable=False)
    credential_fingerprint=Column(String(64),nullable=False)

def browser_label(agent):
    browser='Edge' if 'Edg/' in agent else 'Chrome' if 'Chrome/' in agent else 'Firefox' if 'Firefox/' in agent else 'Safari' if 'Safari/' in agent else 'Browser'
    device='Android' if 'Android' in agent else 'iPad' if 'iPad' in agent else 'iPhone' if 'iPhone' in agent else 'Windows' if 'Windows' in agent else 'Mac' if 'Macintosh' in agent else 'device'
    return f'{browser} · {device}'

router=APIRouter(prefix='/api/auth',tags=['Device sessions'])

def persistent_token(db,user,*,credential=None,agent=''):
    sid=secrets.token_urlsafe(32)
    device=RememberedDevice(user_id=user.id,token_hash=hashlib.sha256(sid.encode()).hexdigest(),revoked=False);db.add(device);db.commit()
    token=create_token({'sub':str(user.id),'role':user.role,'persistent':True,'sid':sid},minutes=60*24*365*100,credential=credential)
    binding=(decode_token(token) or {}).get('credential','')
    db.add(RememberedDeviceDetails(device_id=device.id,label=browser_label(agent),credential_fingerprint=hashlib.sha256(binding.encode()).hexdigest()));db.commit()
    return token

def revoke_current(db,user,authorization):
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    sid=payload.get('sid')
    if sid:db.query(RememberedDevice).filter_by(user_id=user.id,token_hash=hashlib.sha256(sid.encode()).hexdigest()).update({'revoked':True})
    db.commit()

@router.post('/remember-device')
def remember_device(request:Request,db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    # Rotate the old device token when enabling this setting again.
    revoke_current(db,user,authorization)
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    return {'token':persistent_token(db,user,credential=str(payload.get('credential') or ''),agent=request.headers.get('user-agent','')),'persistent':True}

@router.post('/forget-device')
def forget_device(db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    revoke_current(db,user,authorization)
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    return {'token':create_token({'sub':str(user.id),'role':user.role},credential=str(payload.get('credential') or '')),'persistent':False}

@router.post('/logout')
def logout_device(db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    revoke_current(db,user,authorization)
    return {'logged_out':True}

@router.get('/devices')
def devices(response:Response,db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    from app.account_security import AccountSecurity,session_marker
    response.headers['Cache-Control']='private, no-store'
    sid=(decode_token(authorization.removeprefix('Bearer ')) or {}).get('sid','')
    current_hash=hashlib.sha256(sid.encode()).hexdigest()
    fingerprint=hashlib.sha256(session_marker(user,db.get(AccountSecurity,user.id)).encode()).hexdigest()
    rows=db.query(RememberedDevice).filter_by(user_id=user.id).order_by(RememberedDevice.created_at.desc(),RememberedDevice.id.desc()).limit(100).all()
    details={d.device_id:d for d in db.query(RememberedDeviceDetails).filter(RememberedDeviceDetails.device_id.in_([r.id for r in rows])).all()}
    result=[]
    for row in rows:
        detail=details.get(row.id);current=row.token_hash==current_hash
        status='revoked' if row.revoked else 'invalidated' if detail and detail.credential_fingerprint!=fingerprint else 'current' if current else 'remembered' if detail else 'unverified'
        result.append({'id':row.id,'label':detail.label if detail else f'Earlier device · session #{row.id}','created_at':row.created_at,'current':current,'status':status,'renamable':detail is not None or current})
    return {'devices':result,'total':db.query(RememberedDevice).filter_by(user_id=user.id).count(),'limit':100}

class DeviceLabel(BaseModel):
    label:str=Field(min_length=1,max_length=80)

@router.patch('/devices/{device_id}')
def rename_device(device_id:int,data:DeviceLabel,db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    row=db.query(RememberedDevice).filter_by(user_id=user.id,id=device_id).first()
    if not row:raise HTTPException(404,'Device session not found.')
    detail=db.get(RememberedDeviceDetails,row.id)
    if not detail:
        payload=decode_token(authorization.removeprefix('Bearer ')) or {}
        if hashlib.sha256(str(payload.get('sid') or '').encode()).hexdigest()!=row.token_hash:raise HTTPException(409,'Earlier sessions can be revoked, but only the current device can establish its details.')
        detail=RememberedDeviceDetails(device_id=row.id,label=data.label,credential_fingerprint=hashlib.sha256(str(payload.get('credential') or '').encode()).hexdigest());db.add(detail)
    if not data.label.strip():raise HTTPException(422,'Enter a device name.')
    detail.label=data.label.strip();db.commit();return {'saved':True}

@router.post('/devices/{device_id}/revoke')
def revoke_device(device_id:int,db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    row=db.query(RememberedDevice).filter_by(user_id=user.id,id=device_id).first()
    if not row:raise HTTPException(404,'Device session not found.')
    sid=(decode_token(authorization.removeprefix('Bearer ')) or {}).get('sid','')
    current=row.token_hash==hashlib.sha256(sid.encode()).hexdigest()
    row.revoked=True;db.commit();return {'revoked':True,'current':current}
