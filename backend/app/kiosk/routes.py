"""Restricted physical kiosk enrollment and minimal check-in responses. No profile API."""
import hashlib
import hmac
import os
import secrets
import time
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update,func,case
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import staff_user
from app.models import Attendance, Member, SecurityLog
from app.services.attendance import record_attendance
from app.services.memberships import effective_membership_status
from app.services.member_numbers import find_checkin_member
from app.services.business_time import reporting_periods
from .models import KioskDevice, KioskAttempt, KioskRateBucket

router = APIRouter(prefix='/api/kiosk', tags=['Check-In Kiosk'])

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def private(response: Response):
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Pragma'] = 'no-cache'

def throttle(db, key, limit):
    # Atomic database counters also apply across App Platform workers/restarts.
    key = hmac.new(os.environ.get('SECRET_KEY', 'kiosk-rate').encode(), key.encode(), hashlib.sha256).hexdigest()
    window = int(time.time() // 60)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert=pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert
    statement=insert(KioskRateBucket).values(key=key,window=window,count=1)
    statement=statement.on_conflict_do_update(index_elements=['key'],set_={'window':window,'count':case((KioskRateBucket.window==window,KioskRateBucket.count+1),else_=1)},where=(KioskRateBucket.window!=window)|(KioskRateBucket.count<limit)).returning(KioskRateBucket.count)
    accepted=db.execute(statement).scalar();db.commit()
    if accepted is None:
        raise HTTPException(429,'Too many attempts. Please wait one minute or visit the front desk.',headers={'Retry-After':'60'})

def device_auth(request: Request, response: Response, authorization: str = Header(default=''), db: Session = Depends(get_db)):
    private(response)
    # Use the socket peer, never a client-supplied forwarded-for header.
    throttle(db, 'ip:' + (request.client.host if request.client else 'unknown'), 180)
    token = authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
    device = db.query(KioskDevice).filter(KioskDevice.credential_hash == digest(token)).first() if 32 <= len(token) <= 256 else None
    if not device:
        raise HTTPException(401, 'This kiosk must be paired by gym staff.')
    request.state.kiosk_credential_hash = digest(token)
    return device

class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    confirmation_seconds: int = Field(default=8, ge=3, le=30)
    duplicate_seconds: int = Field(default=120, ge=30, le=3600)
    @field_validator('name')
    @classmethod
    def nonblank_name(cls,value):
        if not value.strip():raise ValueError('Enter a device name.')
        return value.strip()

class PairInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=8, max_length=32)

class CheckinInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    member_number: str = Field(min_length=1, max_length=32, pattern=r'^[0-9]+$')

def device_summary(db, device):
    periods = reporting_periods()
    attempts = db.query(KioskAttempt).filter(KioskAttempt.device_id == device.id,
        KioskAttempt.created_at >= periods['day_start'], KioskAttempt.created_at < periods['day_end']).all()
    return {'id': device.id, 'name': device.name, 'enabled': device.enabled,
        'confirmation_seconds': device.confirmation_seconds, 'duplicate_seconds': device.duplicate_seconds,
        'paired': bool(device.credential_hash), 'last_seen': device.last_seen,
        'online': bool(device.credential_hash and device.last_seen and device.last_seen > datetime.utcnow() - timedelta(seconds=90)),
        'pairing_pending': bool(device.pairing_hash and device.pairing_expires and device.pairing_expires>datetime.utcnow()),
        'pairing_expires_at':device.pairing_expires.isoformat()+'Z' if device.pairing_hash and device.pairing_expires else None,
        'today': {outcome: sum(a.outcome == outcome for a in attempts) for outcome in ('recorded', 'duplicate', 'invalid', 'inactive', 'ineligible', 'ambiguous', 'rate_limited')},
        'recent_attempts': [{'id': a.id, 'outcome': a.outcome, 'at': a.created_at,
            'member_id': a.member_id} for a in sorted(attempts, key=lambda a: a.id, reverse=True)[:50]]}

@router.get('/devices')
def devices(response: Response, db: Session = Depends(get_db), user=Depends(staff_user)):
    private(response)
    return {'devices': [device_summary(db, d) for d in db.query(KioskDevice).order_by(KioskDevice.id).all()], 'timezone': 'America/Chicago'}

@router.post('/devices', status_code=201)
def create_device(data: Settings, db: Session = Depends(get_db), user=Depends(staff_user)):
    from app.services.member_profiles import lock_profiles
    lock_profiles(db)
    if db.query(KioskDevice).filter(func.lower(func.trim(KioskDevice.name))==data.name.casefold()).first():raise HTTPException(409,'A kiosk with this name already exists. Select it instead, or use a different name.')
    device = KioskDevice(**data.model_dump()); db.add(device); db.flush()
    db.add(SecurityLog(user_id=user.id, action='KIOSK_CREATED', description=f'Created check-in device #{device.id}'))
    db.commit()
    return {'id': device.id}

@router.put('/devices/{device_id}')
def configure(device_id: int, data: Settings, db: Session = Depends(get_db), user=Depends(staff_user)):
    device = db.get(KioskDevice, device_id)
    if not device: raise HTTPException(404, 'Kiosk not found')
    for key, value in data.model_dump().items(): setattr(device, key, value)
    db.add(SecurityLog(user_id=user.id, action='KIOSK_SETTINGS_UPDATED', description=f'Updated check-in device #{device.id}'))
    db.commit(); return {'saved': True}

@router.post('/devices/{device_id}/pairing')
def pairing(device_id: int, response: Response, db: Session = Depends(get_db), user=Depends(staff_user)):
    private(response)
    device = db.get(KioskDevice, device_id)
    if not device: raise HTTPException(404, 'Kiosk not found')
    if not device.enabled:raise HTTPException(409,'Enable this kiosk in its settings before creating a pairing code.')
    code = secrets.token_hex(6).upper()
    device.pairing_hash = digest(code); device.pairing_expires = datetime.utcnow() + timedelta(minutes=10)
    db.add(SecurityLog(user_id=user.id, action='KIOSK_PAIRING_ISSUED', description=f'Issued ten-minute pairing for device #{device.id}'))
    db.commit()
    return {'code': code, 'device_id':device.id,'device_name':device.name,'expires_at':device.pairing_expires.isoformat()+'Z','expires_in_seconds': 600}

@router.post('/devices/{device_id}/revoke')
def revoke(device_id: int, db: Session = Depends(get_db), user=Depends(staff_user)):
    device = db.get(KioskDevice, device_id)
    if not device: raise HTTPException(404, 'Kiosk not found')
    device.credential_hash = None; device.pairing_hash = None; device.pairing_expires = None
    db.add(SecurityLog(user_id=user.id, action='KIOSK_ACCESS_REVOKED', description=f'Revoked check-in device #{device.id}'))
    db.commit(); return {'revoked': True}

@router.post('/pair')
def pair(data: PairInput, request: Request, response: Response, db: Session = Depends(get_db)):
    private(response)
    throttle(db, 'pair:' + (request.client.host if request.client else 'unknown'), 10)
    normalized=re.sub(r'[\s-]','',data.code).upper()
    device = db.execute(select(KioskDevice).where(KioskDevice.pairing_hash == digest(normalized)).with_for_update()).scalar_one_or_none()
    if not device or not device.pairing_expires or device.pairing_expires < datetime.utcnow() or not device.enabled:
        raise HTTPException(401, 'Invalid or expired pairing code. Ask staff for a new code.')
    token = secrets.token_urlsafe(48)
    device.credential_hash = digest(token); device.pairing_hash = None; device.pairing_expires = None
    device.last_seen = datetime.utcnow(); db.commit()
    return {'credential': token}

@router.post('/heartbeat')
def heartbeat(response: Response, device=Depends(device_auth), db: Session = Depends(get_db)):
    private(response)
    device.last_seen = datetime.utcnow(); db.commit()
    return {'enabled': device.enabled, 'confirmation_seconds': device.confirmation_seconds,
        'name': device.name, 'online': True}

@router.post('/checkin')
def checkin(data: CheckinInput, request: Request, response: Response, device=Depends(device_auth), db: Session = Depends(get_db)):
    private(response)
    try:
        throttle(db, 'device:' + str(device.id), 30)
    except HTTPException:
        db.add(KioskAttempt(device_id=device.id, outcome='rate_limited')); db.commit()
        raise
    # Re-read under lock so disabling/revoking and concurrent submissions serialize.
    device = db.execute(select(KioskDevice).where(KioskDevice.id == device.id).with_for_update().execution_options(populate_existing=True)).scalar_one()
    if not device.enabled or not device.credential_hash or not hmac.compare_digest(device.credential_hash, request.state.kiosk_credential_hash):
        raise HTTPException(403, 'Kiosk unavailable. Please visit the front desk.')
    device.last_seen = datetime.utcnow()
    outcome, member, recorded = 'invalid', None, False
    try:
        member = find_checkin_member(db, data.member_number)
        if member:
            recorded, member = record_attendance(db, member, method='kiosk_number', location=f'Kiosk #{device.id}: {device.name}', duplicate_seconds=device.duplicate_seconds)
            outcome = 'recorded' if recorded else 'duplicate'
    except HTTPException as exc:
        if exc.status_code == 403:
            outcome = 'inactive' if member and effective_membership_status(member) in ('inactive', 'expired') else 'ineligible'
        elif exc.status_code == 409: outcome = 'ambiguous'
        else: raise
    attendance = db.query(Attendance).filter(Attendance.member_id == member.id).order_by(Attendance.id.desc()).first() if recorded else None
    db.add(KioskAttempt(device_id=device.id, member_id=member.id if member else None,
        attendance_id=attendance.id if attendance else None, outcome=outcome))
    db.commit()
    if outcome in ('recorded', 'duplicate'):
        return {'success': True, 'recorded': recorded, 'duplicate': not recorded,
            'first_name': (member.first_name or 'Member')[:60], 'status': 'active',
            'confirmation_seconds': device.confirmation_seconds,
            'message': 'Attendance recorded.' if recorded else 'You are already checked in. No duplicate attendance recorded.'}
    messages = {
        'invalid': 'Member number not recognized. Check your number or visit the front desk.',
        'inactive': 'Membership inactive. Please visit the front desk.',
        'ineligible': 'Please visit the front desk to verify your membership.',
        'ambiguous': 'This number needs staff verification. Please visit the front desk.',
    }
    return {'success': False, 'code': 'membership_inactive' if outcome == 'inactive' else outcome,
        'message': messages[outcome], 'reset_seconds': 5}
