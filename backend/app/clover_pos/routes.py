"""Member-only API for the gym's Clover Android application.

POS tokens have a JWT audience that ordinary CRM authentication rejects.
Clover OAuth/merchant app installation will be connected after app registration.
"""
import os
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
import jwt
from jwt import InvalidTokenError as JWTError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from app.auth import ALGORITHM, SECRET_KEY, create_token
from app.database import get_db
from app.models import Member, User, Attendance, SecurityLog
from app.schemas import LoginIn
from app.services.memberships import effective_membership_status

AUDIENCE = 'tng-clover-members'
router = APIRouter(prefix='/api/clover-pos', tags=['Clover member app'])


def pos_user(authorization: str = Header(default=''), db: Session = Depends(get_db)):
    try:
        if not authorization.startswith('Bearer '):
            raise ValueError()
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=[ALGORITHM], audience=AUDIENCE)
        if payload.get('aud') != AUDIENCE:
            raise ValueError()
        user_id = int(payload['sub'])
        merchant = os.getenv('CLOVER_MERCHANT_ID', '').strip()
        if payload.get('merchant') != merchant:
            raise ValueError()
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail='Sign in to TNG Members again.')
    user = db.get(User, user_id)
    if not user or not user.active or user.role not in {'admin', 'staff'}:
        raise HTTPException(status_code=403, detail='An active TNG admin or staff account is required.')
    from app.account_security import valid_session
    if not valid_session(payload, user, db):
        raise HTTPException(status_code=401, detail='Sign in to TNG Members again.')
    return user


def simple_number(value):
    value = str(value or '').strip()
    match = re.fullmatch(r'(?:TNG[- ]?)?(\d+)', value, re.I)
    return str(int(match[1])) if match else value


def summary(member):
    return {
        'id': member.id, 'first_name': member.first_name, 'last_name': member.last_name,
        'name': f'{member.first_name} {member.last_name}'.strip(),
        'member_number': simple_number(member.member_number),
        'status': effective_membership_status(member),
        'membership': member.membership_type or 'Membership',
        'membership_end': member.membership_end.isoformat() if member.membership_end else None,
        'total_checkins': member.total_checkins or 0,
        'waiver_signed': bool(member.waiver_signed),
    }


def get_member(db, member_id):
    member = db.query(Member).filter(Member.id == member_id, Member.member_type == 'MEMBER').first()
    if not member:
        raise HTTPException(status_code=404, detail='Member not found')
    return member


@router.post('/login')
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    # Reuse account lockout, password verification and security auditing.
    from app.main import login as staff_login
    authenticated = staff_login(data, request, db)
    if authenticated.get('mfa_required'):
        raise HTTPException(status_code=403, detail='Authenticator verification is required. Use TNGOS web login with your authenticator code.')
    if authenticated['user']['role'] not in {'admin', 'staff'}:
        raise HTTPException(status_code=403, detail='Use a TNG admin or staff account.')
    user = authenticated['user']
    return {
        'token': create_token({'sub': str(user['id']), 'aud': AUDIENCE,
                               'merchant': os.getenv('CLOVER_MERCHANT_ID', '').strip()}, minutes=480),
        'expires_in': 480 * 60,
        'user': {'name': user['name'], 'role': user['role']},
        'app': 'TNG Members',
    }


@router.get('/session')
def session(user: User = Depends(pos_user)):
    return {'name': user.name, 'role': user.role, 'app': 'TNG Members'}


@router.get('/members')
def members(q: str = Query(default='', max_length=80), page: int = Query(default=1, ge=1),
            db: Session = Depends(get_db), user: User = Depends(pos_user)):
    query = db.query(Member).filter(Member.member_type == 'MEMBER', Member.member_number.isnot(None))
    term = q.strip()
    if term:
        # Escape SQL LIKE wildcards so user text is always a literal search.
        pattern = '%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        filters = [column.ilike(pattern, escape='\\') for column in
                   (Member.first_name, Member.last_name, Member.member_number,
                    func.trim(func.coalesce(Member.first_name, '') + ' ' + func.coalesce(Member.last_name, '')))]
        if re.fullmatch(r'[0-9]{1,12}', term):
            filters.extend([Member.member_number == f'TNG-{int(term):06d}', Member.member_number == str(int(term))])
        query = query.filter(or_(*filters))
    total = query.count()
    rows = query.order_by(Member.last_name, Member.first_name, Member.id).offset((page-1)*30).limit(30).all()
    return {'items': [summary(row) for row in rows], 'total': total, 'page': page, 'page_size': 30}


@router.get('/members/{member_id}')
def profile(member_id: int, db: Session = Depends(get_db), user: User = Depends(pos_user)):
    member = get_member(db, member_id)
    result = summary(member)
    result.update({'email': member.email or '', 'phone': member.phone or '',
                   'qr_value': member.barcode or member.member_number or member.qr_code or '',
                   'attendance': [row.checkin_time.isoformat() for row in db.query(Attendance)
                                  .filter(Attendance.member_id == member.id)
                                  .order_by(Attendance.checkin_time.desc(), Attendance.id.desc()).limit(10)]})
    return result


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=30)


@router.patch('/members/{member_id}')
def update_contact(member_id: int, data: ContactUpdate, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(pos_user)):
    member = get_member(db, member_id)
    values = {key: value.strip() for key, value in data.model_dump().items()}
    if not values['first_name'] or not values['last_name']:
        raise HTTPException(status_code=400, detail='First and last name are required.')
    if values['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
        raise HTTPException(status_code=400, detail='Enter a valid email address.')
    for key, value in values.items():
        setattr(member, key, value)
    db.add(SecurityLog(user_id=user.id, action='CLOVER_MEMBER_CONTACT_UPDATED',
                       description=f'Clover POS updated member contact #{member.id}',
                       endpoint='/api/clover-pos/members', success=True,
                       ip_address=request.client.host if request.client else 'unknown'))
    db.commit()
    return summary(member)


class CheckinInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=1, max_length=256)
    location: Optional[dict] = None


@router.post('/checkin')
def checkin(data: CheckinInput, db: Session = Depends(get_db), user: User = Depends(pos_user)):
    # Same membership eligibility and number/QR matching as the existing tablet.
    # Calling the shared route also preserves any future location enforcement.
    from app.main import checkin as member_checkin
    result = member_checkin(data.model_dump(), db, user)
    member = db.get(Member, result['member']['id'])
    return {'success': True, 'member': summary(member)}
