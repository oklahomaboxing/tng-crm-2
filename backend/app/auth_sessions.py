"""Revocable remembered device sessions; existing credential/MFA revocation still applies."""
import hashlib
import secrets
from datetime import datetime
from fastapi import APIRouter,Depends,Header
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

router=APIRouter(prefix='/api/auth',tags=['Device sessions'])

def persistent_token(db,user,*,credential=None):
    sid=secrets.token_urlsafe(32)
    db.add(RememberedDevice(user_id=user.id,token_hash=hashlib.sha256(sid.encode()).hexdigest(),revoked=False));db.commit()
    return create_token({'sub':str(user.id),'role':user.role,'persistent':True,'sid':sid},minutes=60*24*365*100,credential=credential)

def revoke_current(db,user,authorization):
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    sid=payload.get('sid')
    if sid:db.query(RememberedDevice).filter_by(user_id=user.id,token_hash=hashlib.sha256(sid.encode()).hexdigest()).update({'revoked':True})
    db.commit()

@router.post('/remember-device')
def remember_device(db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    # Rotate the old device token when enabling this setting again.
    revoke_current(db,user,authorization)
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    return {'token':persistent_token(db,user,credential=str(payload.get('credential') or '')),'persistent':True}

@router.post('/forget-device')
def forget_device(db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    revoke_current(db,user,authorization)
    payload=decode_token(authorization.removeprefix('Bearer ')) or {}
    return {'token':create_token({'sub':str(user.id),'role':user.role},credential=str(payload.get('credential') or '')),'persistent':False}

@router.post('/logout')
def logout_device(db=Depends(get_db),user=Depends(current_user),authorization:str=Header(default='')):
    revoke_current(db,user,authorization)
    return {'logged_out':True}
