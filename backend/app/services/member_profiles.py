"""Create discoverable profiles without granting paid membership or login access."""
import re
import uuid
from fastapi import HTTPException
from sqlalchemy import func, text
from app.models import Member, SecurityLog


def lock_profiles(db):
    # All import workers/manual creation share this transaction-scoped lock.
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(72460318)'))


def phone_key(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) >= 10 else ''


def matching_profile(db, *, clover_id='', email='', phone=''):
    if clover_id:
        direct = db.query(Member).filter_by(clover_customer_id=clover_id).limit(2).all()
        if len(direct) > 1:
            raise HTTPException(409, 'Multiple profiles share this Clover customer ID. Review duplicates before linking.')
        if direct:
            return direct[0]
    emails = db.query(Member).filter(func.lower(func.trim(Member.email)) == email).all() if email else []
    key = phone_key(phone)
    phones = [m for m in db.query(Member).filter(Member.phone.isnot(None)).all() if phone_key(m.phone) == key] if key else []
    candidates = {m.id: m for m in emails + phones}
    if len(candidates) > 1:
        raise HTTPException(409, 'Email or phone matches multiple profiles. Review existing profiles before linking.')
    member = next(iter(candidates.values()), None)
    if member and clover_id and member.clover_customer_id and member.clover_customer_id != clover_id:
        raise HTTPException(409, 'Contact information is already linked to another Clover customer. Review before linking.')
    return member


def ensure_profile_identity(db, member):
    db.flush()
    if not member.member_number:
        number = member.id
        occupied = set()
        for row in db.query(Member.member_number, Member.barcode).all():
            for value in row:
                digits = re.sub(r'^TNG-?', '', (value or '').upper())
                if digits.isdigit():
                    occupied.add(int(digits))
        while number in occupied:
            number += 1
        member.member_number = f'TNG-{number:06d}'
    if not member.digital_member_id:
        member.digital_member_id = f'TNG-{uuid.uuid4().hex[:8].upper()}'
    if not member.barcode:
        member.barcode = member.member_number.replace('-', '')
    if not member.qr_code:
        member.qr_code = f'member:{member.member_number}'


def import_customer(db, customer):
    clover_id = str(customer.get('id') or '').strip()
    if not clover_id:
        return 'skipped', None
    email_rows = (customer.get('emailAddresses') or {}).get('elements', [])
    phone_rows = (customer.get('phoneNumbers') or {}).get('elements', [])
    email = next((str(r.get('emailAddress') or '').strip().lower() for r in email_rows if r.get('emailAddress')), '')
    phone = next((str(r.get('phoneNumber') or '').strip() for r in phone_rows if r.get('phoneNumber')), '')
    first = str(customer.get('firstName') or '').strip()
    last = str(customer.get('lastName') or '').strip()
    # Owner policy: only import customers with both usable contact fields.
    # Existing profiles are retained; this never deletes or deactivates them.
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or not 10 <= len(re.sub(r'\D', '', phone)) <= 15:
        return 'skipped', None
    needs_review = False
    try:
        member = matching_profile(db, clover_id=clover_id, email=email, phone=phone)
    except HTTPException as exc:
        if exc.status_code != 409 or db.query(Member).filter_by(clover_customer_id=clover_id).first():
            raise
        # Keep the distinct Clover identity visible (e.g. family members sharing a phone),
        # without assigning it to an existing person's profile or portal login.
        member = None
        needs_review = True
    if member and member.clover_customer_id != clover_id:
        saved_name = ' '.join(((member.first_name or '') + ' ' + (member.last_name or '')).split()).casefold()
        clover_name = ' '.join((first + ' ' + last).split()).casefold()
        if saved_name and clover_name and saved_name != clover_name:
            member = None
            needs_review = True
    outcome = 'linked'
    if not member:
        member = Member(first_name=first, last_name=last, email=email, phone=phone,
                        clover_customer_id=clover_id, member_type='CUSTOMER', status='customer',
                        membership_status='pending', membership_type=None, waiver_signed=False)
        db.add(member)
        outcome = 'created_review' if needs_review else 'created'
    else:
        member.clover_customer_id = clover_id
        # Preserve populated contact details and portal ownership; admin can review changes.
        for field, value in [('first_name', first), ('last_name', last), ('email', email), ('phone', phone)]:
            if not getattr(member, field):
                setattr(member, field, value)
    ensure_profile_identity(db, member)
    return outcome, member


def audit_profile(db, user_id, action, description):
    db.add(SecurityLog(user_id=user_id, action=action, description=description,
                       endpoint='/api/members', success=True))
