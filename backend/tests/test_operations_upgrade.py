"""Read-only system overview, reporting correctness and scoped follow-up regression tests."""
import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import test_stabilization as support
from app.models import Sale, Member, SecurityLog
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import TicketOrder, IssuedTicket, EventTicketType, TicketDelivery
from app.operations.overview import expected_quantity
from app.services.business_time import reporting_periods
from app.revenue.models import RevenueOrganization, EventRevenueProspect
from app.revenue.followups import run_due_followups

class OperationsUpgradeTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers

    def event(self, slug='future', date='2099-11-14'):
        event = BoxingEvent(name='Fixture Event', slug=slug, event_date=date, venue='Test Venue')
        self.db.add(event); self.db.flush(); return event

    def test_overview_is_admin_only_and_private(self):
        for role in ('staff', 'rep', 'fighter', 'member'):
            self.assertEqual(self.client.get('/api/operations/overview', headers=self.headers(role)).status_code, 403)
        self.assertEqual(self.client.get('/api/operations/overview').status_code, 401)
        result = self.client.get('/api/operations/overview', headers=self.headers())
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn('no-store', result.headers['cache-control'])
        self.assertTrue(result.json()['read_only'])

    def test_overview_does_not_contact_providers_or_write_records(self):
        self.event(); self.db.commit()
        before = (self.db.query(Sale).count(), self.db.query(Member).count(), self.db.query(SecurityLog).count())
        with patch.dict(os.environ, {'CLOVER_API_TOKEN': 'PRIVATE_SENTINEL', 'CLOVER_MERCHANT_ID': 'PRIVATE_MERCHANT', 'OPENAI_API_KEY': 'PRIVATE_AI'}), \
             patch('requests.get') as get, patch('httpx.post') as post, patch('resend.Emails.send') as send:
            r = self.client.get('/api/operations/overview', headers=self.headers())
            self.assertEqual(r.status_code, 200, r.text)
            get.assert_not_called(); post.assert_not_called(); send.assert_not_called()
        self.assertNotIn('PRIVATE_SENTINEL', r.text); self.assertNotIn('PRIVATE_MERCHANT', r.text); self.assertNotIn('PRIVATE_AI', r.text)
        self.assertFalse(r.json()['provider_checks_performed'])
        self.assertTrue(all(not i['verified'] for i in r.json()['integrations']))
        self.assertEqual(before, (self.db.query(Sale).count(), self.db.query(Member).count(), self.db.query(SecurityLog).count()))

    def test_paid_partial_fulfillment_flagged_while_pending_orders_stay_separate(self):
        event = self.event(); kind = EventTicketType(event_id=event.id, name='GA', price_cents=4000)
        self.db.add(kind); self.db.flush()
        for number, status in [(1, 'paid'), (2, 'pending')]:
            order = TicketOrder(event_id=event.id, buyer_name='Fixture Buyer', buyer_email='test@example.com',
                receipt_number=f'FIXTURE-{number}', payment_status=status, total_cents=8000,
                items_json=json.dumps([{'ticket_type_id': kind.id, 'quantity': 2}]))
            self.db.add(order); self.db.flush()
            self.db.add(TicketDelivery(order_id=order.id, channel='email', status='failed'))
            if status == 'paid':
                self.db.add(IssuedTicket(order_id=order.id, event_id=event.id, ticket_type_id=kind.id,
                    ticket_number='FIXTURE-TICKET', qr_token_hash='fixture-hash', price_cents=4000))
        self.db.commit()
        r = self.client.get('/api/operations/overview', headers=self.headers()); self.assertEqual(r.status_code, 200, r.text)
        data = r.json(); self.assertEqual(data['tickets']['paid_orders_missing_tickets'], 1)
        self.assertEqual(data['tickets']['pending_checkouts'], 1); self.assertEqual(data['tickets']['failed_deliveries'], 1)
        self.assertEqual(data['paid_ticket_issues'][0]['expected'], 2); self.assertEqual(data['paid_ticket_issues'][0]['issued'], 1)
        self.assertNotIn('buyer_email', r.text)

    def test_expiring_memberships_require_paid_sale_and_upcoming_events_exclude_past(self):
        self.member.membership_end = datetime.utcnow() + timedelta(days=2)
        unpaid = Member(first_name='Unpaid', last_name='Profile', membership_status='active', member_type='MEMBER',
                        membership_end=datetime.utcnow() + timedelta(days=2))
        self.db.add(unpaid); self.event(); self.event('past', '2001-01-01'); self.db.commit()
        data = self.client.get('/api/operations/overview', headers=self.headers()).json()
        self.assertEqual(data['members']['expiring_seven_days'], 1)
        self.assertEqual(len(data['upcoming_events']), 1)

    def test_reporting_periods_respect_central_midnight_month_and_daylight_saving(self):
        period = reporting_periods(datetime(2026, 11, 1, 2))
        self.assertEqual(period['local_day'], '2026-10-31')
        self.assertEqual(period['month_start'], datetime(2026, 10, 1, 5))
        spring = reporting_periods(datetime(2026, 3, 8, 12)); fall = reporting_periods(datetime(2026, 11, 1, 12))
        self.assertEqual(spring['day_end'] - spring['day_start'], timedelta(hours=23))
        self.assertEqual(fall['day_end'] - fall['day_start'], timedelta(hours=25))

    def test_dashboard_counts_paid_sales_and_nets_refunds_consistently(self):
        existing = self.db.query(Sale).one(); existing.sale_date = datetime.utcnow(); existing.amount = 100; existing.refund_amount = 20; existing.sale_type = 'nexgen_nutrition'
        for status, refunded, amount in [('pending', False, 999), ('paid', True, 500)]:
            self.db.add(Sale(member_id=self.member.id, sales_rep_id=self.rep.id, product_id=self.product.id,
                             amount=amount, payment_status=status, refunded=refunded, sale_type='nexgen_nutrition'))
        self.db.commit()
        result = self.client.get('/api/dashboard', headers=self.headers()).json()
        self.assertEqual(result['revenue_this_month'], 80)
        self.assertEqual(result['nutrition_club_sales_this_month'], 80)
        self.assertEqual(result['active_member_revenue_this_month'], 80)
        self.assertEqual(result['sales_this_month'], 1); self.assertEqual(result['transactions_this_month'], 3)
        self.assertEqual(result['timezone'], 'America/Chicago')

    def test_event_followup_processing_never_touches_another_event(self):
        one, two = self.event(), self.event('other')
        org = RevenueOrganization(business_name='Fixture', email='fixture@example.com'); self.db.add(org); self.db.flush()
        due = datetime.utcnow() - timedelta(days=1)
        for event in (one, two):
            self.db.add(EventRevenueProspect(event_id=event.id, organization_id=org.id, prospect_type='SPONSOR',
                         status='PAID', next_follow_up_at=due, do_not_contact=False))
        self.db.commit()
        with patch.dict(os.environ, {'AUTO_SPONSOR_FOLLOWUPS': 'false'}), patch('resend.Emails.send') as send:
            result = run_due_followups(self.db, event_id=one.id); send.assert_not_called()
        self.assertEqual(result['checked'], 1)
        self.db.expire_all()
        self.assertIsNone(self.db.query(EventRevenueProspect).filter_by(event_id=one.id).one().next_follow_up_at)
        self.assertIsNotNone(self.db.query(EventRevenueProspect).filter_by(event_id=two.id).one().next_follow_up_at)
        self.assertEqual(self.client.post('/api/events/999/revenue/process-followups', headers=self.headers()).status_code, 404)

    def test_expected_quantity_rejects_invalid_items_without_fabricating_ticket_count(self):
        for value in [None, 'bad json', '{}', '[]', '[{"quantity":true}]', '[{"quantity":-1}]', '[{"quantity":1.5}]']:
            self.assertIsNone(expected_quantity(value))
        self.assertEqual(expected_quantity('[{"quantity":2},{"quantity":3}]'), 5)

    def test_legacy_hs256_sessions_remain_valid_after_jwt_library_upgrade(self):
        import base64, hashlib, hmac
        from app.auth import create_token, decode_token, SECRET_KEY
        payload = decode_token(create_token({'sub': str(self.users['admin'].id)}))
        def encoded(value):
            return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=')
        unsigned = encoded({'alg': 'HS256', 'typ': 'JWT'}) + b'.' + encoded(payload)
        signature = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), unsigned, hashlib.sha256).digest()).rstrip(b'=')
        legacy = (unsigned + b'.' + signature).decode()
        result = self.client.get('/api/members', headers={'Authorization': 'Bearer ' + legacy})
        self.assertEqual(result.status_code, 200, result.text)

    def test_jwt_requires_expiration_subject_and_explicit_hs256(self):
        import jwt
        from app.auth import decode_token, SECRET_KEY
        valid = {'sub': '1', 'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp())}
        for payload in ({'sub': '1'}, {'exp': valid['exp']}):
            self.assertIsNone(decode_token(jwt.encode(payload, SECRET_KEY, algorithm='HS256')))
        self.assertIsNone(decode_token(jwt.encode(valid, None, algorithm='none')))
        self.assertIsNone(decode_token(jwt.encode(valid, SECRET_KEY, algorithm='HS384')))
        self.assertIsNone(decode_token('x' * 8193))

    def test_application_startup_and_worker_shutdown_on_patched_framework(self):
        import asyncio
        from fastapi.testclient import TestClient
        async def idle_worker():
            await asyncio.sleep(86400)
        with patch.dict(os.environ, {'TICKET_DELIVERY_WORKER_ENABLED': '1', 'CLOVER_PROFILE_SYNC_ENABLED': '1'}), \
             patch('app.ticketing.worker.delivery_loop', idle_worker), \
             patch('app.services.clover_customers.profile_sync_loop', idle_worker):
            with TestClient(support.app) as client:
                self.assertEqual(client.get('/api/health').status_code, 200)
                tickets = support.app.state.ticket_delivery_task
                profiles = support.app.state.clover_profile_task
                self.assertFalse(tickets.done()); self.assertFalse(profiles.done())
            self.assertTrue(tickets.cancelled()); self.assertTrue(profiles.cancelled())

if __name__ == '__main__': unittest.main()
