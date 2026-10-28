"""Idempotent paid-checkout activation delivery; failed email never undoes payment."""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from html import escape
import resend
from sqlalchemy import func
from app.models import Member, User
from app.member_portal.models import MemberAccount, MemberInvite


def invite_paid_member(db, member_id):
    try:
        member = db.query(Member).filter_by(id=member_id).with_for_update().first()
        if not member or not (member.email or '').strip():
            db.rollback()
            return {'portal_invite_sent': False, 'portal_invite_status': 'member_has_no_email'}
        email = member.email.strip().lower()
        status = None
        if db.query(MemberAccount).filter_by(member_id=member.id).first():
            status = 'already_active'
        elif db.query(MemberInvite).filter(MemberInvite.member_id == member.id, MemberInvite.used_at.is_(None),
                                          MemberInvite.expires_at > datetime.utcnow()).first():
            status = 'already_invited'
        elif not os.getenv('RESEND_API_KEY'):
            status = 'email_not_configured'
        else:
            user = db.query(User).filter(func.lower(User.email) == email).first()
            if user and (user.role != 'member' or db.query(MemberAccount).filter_by(user_id=user.id).first()):
                status = 'email_in_use'
        if status:
            db.rollback()
            return {'portal_invite_sent': False, 'portal_invite_status': status}
        token = secrets.token_urlsafe(32)
        db.add(MemberInvite(member_id=member.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                            expires_at=datetime.utcnow() + timedelta(days=7)))
        db.flush()
        url = os.getenv('FRONTEND_URL', 'https://tngos.tngboxinggym.com').rstrip('/') + '/member/activate?token=' + token
        resend.api_key = os.environ['RESEND_API_KEY']
        resend.Emails.send({'from': os.getenv('RESEND_FROM_EMAIL', 'TNG Boxing <marketing@tngboxinggym.com>'),
            'to': [email], 'subject': 'Activate Your TNG Boxing Member Account',
            'html': '<h2>Welcome to TNG Boxing</h2><p>Your membership payment was received. Create your password to access your member portal.</p>'
                    f'<p><a href="{escape(url, quote=True)}">Set Up My Member Account</a></p><p>This link expires in 7 days.</p>'})
        db.commit()
        return {'portal_invite_sent': True, 'portal_invite_status': 'sent'}
    except Exception as exc:
        db.rollback()
        logging.getLogger(__name__).warning('Member activation delivery failed (%s)', type(exc).__name__)
        return {'portal_invite_sent': False, 'portal_invite_status': 'email_error'}
