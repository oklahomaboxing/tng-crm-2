"""Read-only operations overview. Never contacts providers or runs follow-ups."""
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.dependencies import current_user
from app.core.permissions import require_admin
from app.database import get_db
from app.models import Member, Sale, MembershipProduct, SecurityLog, MarketingCampaign
from app.member_portal.models import MemberAccount, MemberInvite
from app.matchmaker.models import BoxingEvent, BoxingContract
from app.ticketing.models import TicketOrder, IssuedTicket, TicketDelivery, PaperTicket
from app.marketing.models import SmsDelivery
from app.account_security import AccountSecurity
from app.services.member_profiles import phone_key
from app.services.memberships import effective_membership_status

router = APIRouter(prefix='/api/operations', tags=['Operations overview'])


def expected_quantity(raw):
    try:
        items = json.loads(raw or '[]')
        if not isinstance(items, list) or not items:
            return None
        total = 0
        for item in items:
            quantity = item.get('quantity')
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                return None
            total += quantity
        return total
    except (ValueError, AttributeError, TypeError):
        return None


@router.get('/overview')
def operations_overview(response: Response, db: Session = Depends(get_db), user=Depends(current_user)):
    require_admin(user)
    response.headers['Cache-Control'] = 'private, no-store, max-age=0'
    now = datetime.utcnow()
    today = datetime.now(ZoneInfo('America/Chicago')).date().isoformat()
    members = db.query(Member).all()
    accounts = {a.member_id for a in db.query(MemberAccount).all()}
    invited = {a.member_id for a in db.query(MemberInvite).filter(MemberInvite.used_at.is_(None), MemberInvite.expires_at > now).all()}
    emails = Counter((m.email or '').strip().lower() for m in members if (m.email or '').strip())
    phones = Counter(phone_key(m.phone) for m in members if phone_key(m.phone))
    paid_members = {member_id for (member_id,) in db.query(Sale.member_id).join(MembershipProduct,
        MembershipProduct.id == Sale.product_id).filter(Sale.payment_status == 'paid', Sale.refunded.isnot(True),
        MembershipProduct.is_membership.is_(True), MembershipProduct.category == 'membership').distinct().all()}
    expiring = [m for m in members if m.id in paid_members and effective_membership_status(m) == 'active'
                and m.membership_end and now <= m.membership_end <= now + timedelta(days=7)]
    missing_email = sum(1 for m in members if not (m.email or '').strip())
    shared = sum(1 for m in members if emails.get((m.email or '').strip().lower(), 0) > 1 or phones.get(phone_key(m.phone), 0) > 1)
    needs_activation = sum(1 for m in members if m.id in paid_members and m.id not in accounts and m.id not in invited and (m.email or '').strip())
    issued = dict(db.query(IssuedTicket.order_id, func.count(IssuedTicket.id)).group_by(IssuedTicket.order_id).all())
    paid_orders = db.query(TicketOrder).filter_by(payment_status='paid').all()
    missing = []
    for order in paid_orders:
        expected = expected_quantity(order.items_json)
        actual = issued.get(order.id, 0)
        if expected is None or actual < expected:
            missing.append({'order_id': order.id, 'event_id': order.event_id, 'receipt_number': order.receipt_number,
                            'expected': expected, 'issued': actual})
    pending = db.query(TicketOrder).filter_by(payment_status='pending').count()
    delivery_failed = db.query(TicketDelivery).join(TicketOrder, TicketOrder.id == TicketDelivery.order_id).filter(
        TicketOrder.payment_status == 'paid', TicketDelivery.status.in_(['failed', 'undelivered'])).count()
    marketing_failed = db.query(SmsDelivery).filter(SmsDelivery.status.in_(['failed', 'undelivered'])).count()
    offline = db.query(PaperTicket).filter_by(status='offline_used').count()
    events = db.query(BoxingEvent).filter(BoxingEvent.event_date >= today,
        ~func.lower(BoxingEvent.status).in_(['completed', 'cancelled', 'canceled', 'archived'])).order_by(BoxingEvent.event_date, BoxingEvent.id).limit(6).all()
    contracts = db.query(BoxingContract).filter(func.lower(BoxingContract.docusign_status).in_(['sent', 'delivered'])).count()
    sync = db.query(SecurityLog).filter_by(action='CLOVER_PROFILE_SYNC', success=True).order_by(SecurityLog.created_at.desc()).first()
    security = db.get(AccountSecurity, user.id)
    definitions = [
        ('paid_ticket_issuance', 'Paid orders missing tickets', len(missing), 'TNG BOXING EVENTS', 'error', 'Verify payment and fulfillment before issuing or resending.'),
        ('ticket_delivery', 'Ticket delivery failures', delivery_failed, 'TNG BOXING EVENTS', 'warning', 'Review saved delivery status and the customer contact details.'),
        ('paper_reconciliation', 'Paper admissions awaiting cash records', offline, 'TNG BOXING EVENTS', 'warning', 'These admissions are separate from recorded paid sales.'),
        ('member_expiring', 'Memberships expiring in seven days', len(expiring), 'Members', 'warning', 'Review paid memberships and renewal options.'),
        ('member_activation', 'Paid member profiles awaiting activation email', needs_activation, 'Members', 'info', 'Review each profile before sending access; no emails are sent here.'),
        ('shared_contacts', 'Profiles with shared contact details', shared, 'Duplicate Review', 'info', 'Shared family contacts can be valid. Review before merging.'),
        ('marketing_delivery', 'Marketing text delivery failures', marketing_failed, 'Marketing Center', 'warning', 'Review campaign delivery details and sending approval.'),
        ('contracts_pending', 'DocuSign signatures outstanding', contracts, 'TNG BOXING EVENTS', 'info', 'Open the event contracts to check status or connection.'),
    ]
    work = [{'id': key, 'title': title, 'count': count, 'page': page, 'severity': level, 'description': description}
            for key, title, count, page, level, description in definitions if count]
    work.sort(key=lambda item: {'error': 0, 'warning': 1, 'info': 2}[item['severity']])
    integrations = []
    for name, keys, page in [
        ('Clover', ['CLOVER_API_TOKEN', 'CLOVER_MERCHANT_ID'], 'Clover'),
        ('Ticket email', ['RESEND_API_KEY'], 'TNG BOXING EVENTS'),
        ('Text messaging', ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'], 'Marketing Center'),
        ('DocuSign', ['DOCUSIGN_INTEGRATION_KEY', 'DOCUSIGN_USER_ID', 'DOCUSIGN_ACCOUNT_ID', 'DOCUSIGN_PRIVATE_KEY'], 'TNG BOXING EVENTS'),
        ('AI generation', ['OPENAI_API_KEY'], 'Marketing Center'),
    ]:
        configured = all(bool(os.getenv(key, '').strip()) for key in keys)
        integrations.append({'name': name, 'configured': configured, 'verified': False, 'page': page,
            'status': 'configured_unverified' if configured else 'not_configured'})
    return {'generated_at': now.isoformat() + 'Z', 'timezone': 'America/Chicago', 'read_only': True,
        'members': {'profiles': len(members), 'paid_profiles': len(paid_members), 'expiring_seven_days': len(expiring),
                    'missing_email': missing_email, 'shared_contact_profiles': shared, 'awaiting_activation': needs_activation},
        'tickets': {'paid_orders': len(paid_orders), 'pending_checkouts': pending, 'paid_orders_missing_tickets': len(missing),
                    'failed_deliveries': delivery_failed, 'unreconciled_paper_admissions': offline},
        'work_queue': work, 'paid_ticket_issues': missing[:25],
        'upcoming_events': [{'id': e.id, 'name': e.name, 'date': e.event_date, 'venue': e.venue, 'status': e.status} for e in events],
        'integrations': integrations, 'provider_checks_performed': False,
        'last_customer_sync_at': sync.created_at.isoformat() + 'Z' if sync else None,
        'customer_sync_enabled': os.getenv('CLOVER_PROFILE_SYNC_ENABLED', '1') == '1',
        'security': {'mfa_enabled': bool(security and security.mfa_enabled)},
        'marketing_drafts': db.query(MarketingCampaign).filter_by(status='draft').count()}
