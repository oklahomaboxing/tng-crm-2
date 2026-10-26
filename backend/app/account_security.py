"""Account-bound sessions and authenticator verification. Never log secrets."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base, get_db


class AccountSecurity(Base):
    __tablename__ = 'account_security'
    user_id = Column(Integer, primary_key=True)
    generation = Column(String, nullable=False, default=lambda: secrets.token_hex(24))
    mfa_secret = Column(Text, nullable=True)
    pending_secret = Column(Text, nullable=True)
    pending_until = Column(Integer, nullable=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    last_step = Column(Integer, nullable=False, default=-1)
    recovery_hashes = Column(Text, nullable=False, default='[]')


def cipher():
    key = hashlib.sha256(('tng-mfa-v1:' + os.environ['SECRET_KEY']).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def session_marker(user, state=None):
    value = f'{user.id}:{user.password_hash}:{user.role}:{state.generation if state else "initial"}'
    return hmac.new(os.environ['SECRET_KEY'].encode(), value.encode(), hashlib.sha256).hexdigest()


def valid_session(payload, user, db):
    state = db.get(AccountSecurity, user.id)
    return hmac.compare_digest(str(payload.get('credential', '')), session_marker(user, state))


def totp(secret, step):
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f'{(struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % 1000000:06d}'


def recovery_hash(code):
    return hmac.new(os.environ['SECRET_KEY'].encode(), code.strip().encode(), hashlib.sha256).hexdigest()


def verify_second_factor(db, state, code):
    if not state or not state.mfa_enabled:
        return False
    step = int(time.time()) // 30
    secret = cipher().decrypt(state.mfa_secret.encode()).decode()
    for candidate in [step-1, step, step+1]:
        if hmac.compare_digest(totp(secret, candidate), str(code)):
            changed = db.query(AccountSecurity).filter(AccountSecurity.user_id == state.user_id,
                AccountSecurity.last_step < candidate).update({AccountSecurity.last_step: candidate})
            return bool(changed)
    hashes = json.loads(state.recovery_hashes or '[]')
    target = recovery_hash(code)
    if target not in hashes:
        return False
    old = state.recovery_hashes
    hashes.remove(target)
    return bool(db.query(AccountSecurity).filter(AccountSecurity.user_id == state.user_id,
        AccountSecurity.recovery_hashes == old).update({AccountSecurity.recovery_hashes: json.dumps(hashes)}))


class SecurityInput(BaseModel):
    password: str
    code: str = Field(default='', max_length=100)


def build_security_router():
    from app.core.dependencies import current_user
    from app.auth import verify_password
    from app.models import SecurityLog
    router = APIRouter(prefix='/api/auth/security', tags=['Account security'])

    def authenticate(data, user, db, second=False):
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if user.locked_until and user.locked_until > now:
            raise HTTPException(423, 'Account temporarily locked. Try again later.')
        state = db.get(AccountSecurity, user.id)
        if not verify_password(data.password, user.password_hash) or (second and state and state.mfa_enabled and not verify_second_factor(db, state, data.code)):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.add(SecurityLog(user_id=user.id, action='SECURITY_VERIFY_FAILED', success=False))
            db.commit()
            raise HTTPException(401, 'Password or verification code is incorrect.')
        return state

    @router.get('/status')
    def status(user=Depends(current_user), db=Depends(get_db)):
        state = db.get(AccountSecurity, user.id)
        return {'mfa_enabled': bool(state and state.mfa_enabled)}

    @router.post('/revoke-sessions')
    def revoke(data: SecurityInput, user=Depends(current_user), db=Depends(get_db)):
        state = authenticate(data, user, db, second=True)
        if not state:
            state = AccountSecurity(user_id=user.id)
            db.add(state)
        state.generation = secrets.token_hex(24)
        db.add(SecurityLog(user_id=user.id, action='SESSIONS_REVOKED', success=True))
        db.commit()
        return {'message': 'All sessions signed out. Sign in again.'}

    @router.post('/mfa/setup')
    def setup(data: SecurityInput, user=Depends(current_user), db=Depends(get_db)):
        state = authenticate(data, user, db)
        if state and state.mfa_enabled:
            raise HTTPException(409, 'Authenticator protection is already enabled.')
        if not state:
            # Creating security settings must not revoke the enrollment session.
            state = AccountSecurity(user_id=user.id, generation='initial')
            db.add(state)
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        state.pending_secret = cipher().encrypt(secret.encode()).decode()
        state.pending_until = int(time.time()) + 600
        db.commit()
        return {'secret': secret, 'uri': f'otpauth://totp/{quote("TNGOS:"+user.email)}?secret={secret}&issuer=TNGOS', 'expires_in': 600}

    @router.post('/mfa/confirm')
    def confirm(data: SecurityInput, user=Depends(current_user), db=Depends(get_db)):
        state = authenticate(data, user, db)
        if not state or not state.pending_secret or (state.pending_until or 0) < time.time():
            raise HTTPException(400, 'Setup expired. Start authenticator setup again.')
        step = int(time.time()) // 30
        secret = cipher().decrypt(state.pending_secret.encode()).decode()
        match = next((i for i in [step-1, step, step+1] if hmac.compare_digest(totp(secret, i), data.code)), None)
        if match is None:
            from datetime import datetime, timedelta
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow()+timedelta(minutes=15)
            db.commit()
            raise HTTPException(401, 'Authenticator code is incorrect.')
        codes = [secrets.token_hex(8) for _ in range(10)]
        state.mfa_secret = state.pending_secret
        state.pending_secret = None
        state.pending_until = None
        state.mfa_enabled = True
        state.last_step = match
        state.recovery_hashes = json.dumps([recovery_hash(c) for c in codes])
        state.generation = secrets.token_hex(24)
        db.add(SecurityLog(user_id=user.id, action='MFA_ENABLED', success=True))
        db.commit()
        return {'recovery_codes': codes, 'message': 'Save these codes privately. All sessions are signed out. Sign in with your next authenticator code or a recovery code.'}

    return router
