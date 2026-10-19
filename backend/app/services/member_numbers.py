"""Short member-number aliases preserve existing printed cards and QR values."""
import re
from fastapi import HTTPException
from sqlalchemy import func, or_, and_
from app.models import Member


def normalize_code(value):
    code = str(value or '').strip().upper().replace('-', '').replace(' ', '')
    return code[7:] if code.startswith('MEMBER:') else code


def find_checkin_member(db, value):
    code = normalize_code(value)
    if len(code) > 256:
        raise HTTPException(status_code=400, detail='Member code is too long')
    if not code:
        raise HTTPException(status_code=400, detail='Member code is required')
    def normalized(column):
        raw = func.upper(func.replace(func.replace(func.trim(column), '-', ''), ' ', ''))
        # Existing QR values may include the member: prefix.
        return func.replace(raw, 'MEMBER:', '')
    matches = [normalized(column) == code for column in (Member.member_number, Member.barcode, Member.qr_code)]
    if re.fullmatch(r'[0-9]+', code):
        short = str(int(code))
        number = normalized(Member.member_number)
        matches.extend([
            func.ltrim(number, '0') == short,
            and_(number.like('TNG%'), func.ltrim(func.substr(number, 4), '0') == short),
        ])
    members = db.query(Member).filter(or_(*matches)).limit(2).all()
    if len(members) > 1:
        raise HTTPException(status_code=409, detail='This number matches more than one member. Please ask the front desk to verify your full member number.')
    return members[0] if members else None
