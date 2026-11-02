"""One reporting definition for contacts, current memberships and expiration."""
from datetime import datetime, timedelta
import math
import re
from app.models import Member, Sale, MembershipProduct
from app.services.memberships import effective_membership_status,is_ticket_purchase_name


def has_member_identity(member):
    name=' '.join(((member.first_name or '')+' '+(member.last_name or '')).split())
    return bool(name and any(c.isalpha() for c in name) and name.casefold() not in ('unknown','customer','unknown customer','clover customer','guest','walk in','walk-in')
        and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',(member.email or '').strip()))


def membership_evidence(db):
    from app.services.memberships import is_membership_product
    rows=db.query(Sale,MembershipProduct,Member).join(MembershipProduct,MembershipProduct.id==Sale.product_id).join(Member,Member.id==Sale.member_id).filter(
        Sale.payment_status=='paid',Sale.refunded.isnot(True),MembershipProduct.is_membership.is_(True),
        MembershipProduct.category=='membership').all()
    return {member.id for sale,product,member in rows if is_membership_product(product) and (
        member.member_type=='MEMBER' or (member.membership_start and member.membership_end)
        or (sale.payment_method or '').strip().casefold() in ('cash','check','manual','offline')
        or re.fullmatch(r'[A-Z0-9]{13}',sale.clover_payment_id or ''))}



def membership_report(member, paid_ids, now=None):
    now = now or datetime.utcnow()
    end = member.membership_end
    status = effective_membership_status(member, now)
    # Directory imports and bare legacy active defaults do not prove a membership.
    recorded = has_member_identity(member) and (member.id in paid_ids or bool(member.member_type == 'MEMBER'
        and member.membership_start and (end or member.membership_type) and not is_ticket_purchase_name(member.membership_type)))
    if not recorded:
        category = 'contact'
    elif end and end <= now:
        category = 'expired'
    elif status == 'active':
        category = 'expiring' if end and end <= now + timedelta(days=7) else 'active'
    elif status in ('inactive', 'expired', 'cancelled', 'canceled', 'suspended'):
        category = 'inactive'
    else:
        category = 'review'
    delta = (end - now).total_seconds() / 86400 if end else None
    days = (math.ceil(delta) if delta >= 0 else math.floor(delta)) if delta is not None else None
    return {'membership_category': category, 'is_current_member': category in ('active','expiring'),
        'membership_days_remaining': days, 'membership_recorded': recorded,
        'member_identity_complete':has_member_identity(member)}


def membership_totals(members, paid_ids, now=None):
    now = now or datetime.utcnow()
    counts = {key:0 for key in ('active','expiring','expired','inactive','contact','review')}
    for member in members:
        counts[membership_report(member, paid_ids, now)['membership_category']] += 1
    counts['active'] += counts['expiring']
    counts['members'] = counts['active'] + counts['expired'] + counts['inactive'] + counts['review']
    counts['profiles'] = len(members)
    return counts
