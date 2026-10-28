"""Profile creation/import cannot manufacture a paid membership or login."""
import os
import unittest
from unittest.mock import Mock, patch
import requests
import test_stabilization as support
from app.models import Member, User, Sale, Lead
from app.member_portal.models import MemberAccount, MemberInvite


def customer(cid='clover-new', **values):
    return {'id': cid, 'firstName': 'New', 'lastName': 'Customer',
            'emailAddresses': {'elements': [{'emailAddress': 'new@example.com'}]},
            'phoneNumbers': {'elements': [{'phoneNumber': '+1 (405) 555-0100'}]}, **values}


def response(rows, status=200):
    r = Mock(ok=status < 400, status_code=status)
    r.json.return_value = {'elements': rows}
    return r


class MemberProfilesTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers
    payment = support.StabilizationTests.payment

    def sync(self, rows):
        with patch.dict(os.environ, {'CLOVER_API_TOKEN': 'test-api', 'CLOVER_MERCHANT_ID': 'test-merchant',
                                     'CLOVER_ECOMMERCE_PRIVATE_KEY': 'wrong-hosted-key'}), \
             patch('requests.get', return_value=response(rows)) as get:
            result = self.client.post('/api/clover/sync-customers', headers=self.headers())
            self.assertEqual(get.call_args.kwargs['headers']['Authorization'], 'Bearer test-api')
        return result

    def test_admin_create_is_visible_pending_and_has_unique_card_without_sale_or_login(self):
        users = self.db.query(User).count(); sales = self.db.query(Sale).count()
        r = self.client.post('/api/members', headers=self.headers(), json={'first_name': 'Admin Added', 'email': ' NEW@EXAMPLE.COM '})
        self.assertEqual(r.status_code, 201, r.text)
        member = self.db.get(Member, r.json()['id'])
        self.assertEqual(member.email, 'new@example.com'); self.assertEqual(member.membership_status, 'pending')
        self.assertTrue(member.qr_code.startswith('member:TNG-')); self.assertNotEqual(member.member_number, self.member.member_number)
        listed = self.client.get('/api/members', headers=self.headers()).json()
        self.assertEqual(next(m['portal_status'] for m in listed if m['id'] == member.id), 'not_invited')
        self.assertEqual(self.db.query(User).count(), users); self.assertEqual(self.db.query(Sale).count(), sales)
        self.assertEqual(self.db.query(MemberInvite).count(), 0)

    def test_creation_is_admin_only_and_validates_details(self):
        for role in ('staff', 'rep', 'member', 'fighter'):
            self.assertEqual(self.client.post('/api/members', headers=self.headers(role), json={'first_name': 'No'}).status_code, 403)
        self.assertEqual(self.client.post('/api/members', json={'first_name': 'No'}).status_code, 401)
        for data in ({}, {'first_name': 'Name', 'email': 'invalid'}, {'first_name': 'Name', 'phone': '123'}):
            self.assertEqual(self.client.post('/api/members', headers=self.headers(), json=data).status_code, 422)

    def test_manual_duplicate_email_or_normalized_phone_rejected(self):
        self.member.phone = '(405) 555-0100'; self.db.commit()
        for data in ({'email': self.member.email.upper()}, {'phone': '+1 405 555 0100'}):
            r = self.client.post('/api/members', headers=self.headers(), json={'first_name': 'Duplicate', **data})
            self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.db.query(Member).count(), 1)

    def test_sync_creates_name_only_and_contact_profiles_once_without_activating(self):
        before_sales = self.db.query(Sale).count()
        rows = [customer(), customer('name-only', emailAddresses={}, phoneNumbers={})]
        for created in (2, 0):
            r = self.sync(rows); self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()['members_created'], created)
        people = self.db.query(Member).filter(Member.clover_customer_id.isnot(None)).all()
        self.assertEqual(len(people), 2)
        for person in people:
            self.assertEqual(person.member_type, 'CUSTOMER'); self.assertEqual(person.membership_status, 'pending')
            self.assertIsNone(person.membership_end); self.assertTrue(person.member_number)
        self.assertEqual(self.db.query(Sale).count(), before_sales); self.assertEqual(self.db.query(MemberAccount).count(), 1)
        listed = self.client.get('/api/members', headers=self.headers()).json()
        self.assertEqual(len(listed), 3)
        self.assertEqual(next(m['portal_status'] for m in listed if m['clover_customer_id'] == 'name-only'), 'needs_email')

    def test_link_preserves_paid_membership_existing_card_and_portal_contacts(self):
        self.member.qr_code = 'member:TNG-000001'; self.db.commit()
        end, card, email = self.member.membership_end, self.member.qr_code, self.member.email
        r = self.sync([customer(emailAddresses={'elements': [{'emailAddress': email.upper()}]})])
        self.assertEqual(r.json()['members_linked'], 1)
        self.db.refresh(self.member)
        self.assertEqual(self.member.clover_customer_id, 'clover-new'); self.assertEqual(self.member.membership_end, end)
        self.assertEqual(self.member.qr_code, card); self.assertEqual(self.member.email, email)
        r = self.sync([customer(emailAddresses={'elements': [{'emailAddress': 'changed@example.com'}]})])
        self.assertEqual(r.status_code, 200); self.db.refresh(self.member); self.assertEqual(self.member.email, email)

    def test_ambiguous_contacts_are_reported_without_arbitrary_linking(self):
        self.db.add(Member(first_name='Other', last_name='Person', email=self.member.email)); self.db.commit()
        r = self.sync([customer(emailAddresses={'elements': [{'emailAddress': self.member.email}]})])
        self.assertEqual(r.status_code, 200, r.text); self.assertEqual(r.json()['needs_review'], 1)
        self.assertEqual(r.json()['members_created'], 0); self.assertEqual(self.db.query(Member).count(), 2)
        self.db.refresh(self.member); self.assertFalse(self.member.clover_customer_id)

    def test_same_names_never_merge_and_other_clover_id_not_overwritten(self):
        r = self.sync([customer(firstName=self.member.first_name, lastName=self.member.last_name, emailAddresses={}, phoneNumbers={})])
        self.assertEqual(r.json()['members_created'], 1)
        self.member.clover_customer_id = 'original'; self.db.commit()
        r = self.sync([customer('different', emailAddresses={'elements': [{'emailAddress': self.member.email}]}, phoneNumbers={})])
        self.assertEqual(r.json()['needs_review'], 1); self.db.refresh(self.member); self.assertEqual(self.member.clover_customer_id, 'original')

    def test_pagination_reads_every_page_with_read_token(self):
        rows = [customer(f'id-{i}', emailAddresses={}, phoneNumbers={}) for i in range(100)]
        with patch.dict(os.environ, {'CLOVER_API_TOKEN': 'test-api', 'CLOVER_MERCHANT_ID': 'test'}), \
             patch('requests.get', side_effect=[response(rows), response([customer('last', emailAddresses={}, phoneNumbers={})])]) as get:
            r = self.client.post('/api/clover/sync-customers', headers=self.headers())
        self.assertEqual(r.status_code, 200, r.text); self.assertEqual(r.json()['members_created'], 101)
        self.assertEqual([c.kwargs['params']['offset'] for c in get.call_args_list], [0, 100])

    def test_failed_or_repeated_page_never_partially_imports_or_leaks_provider_body(self):
        from app.services.clover_customers import fetch_customers
        from fastapi import HTTPException
        rows = [customer(f'id-{i}') for i in range(100)]
        for second in (response([], 401), response(rows), requests.Timeout('PRIVATE_PROVIDER_DETAIL')):
            with patch.dict(os.environ, {'CLOVER_API_TOKEN': 'test', 'CLOVER_MERCHANT_ID': 'test'}), \
                 patch('requests.get', side_effect=[response(rows), second]):
                with self.assertRaises(HTTPException) as error: fetch_customers()
                self.assertNotIn('PRIVATE_PROVIDER_DETAIL', str(error.exception.detail))
        self.assertEqual(self.db.query(Member).count(), 1)

    def test_new_number_avoids_existing_printed_card_collision(self):
        self.member.member_number = 'TNG-000002'; self.member.barcode = 'TNG000002'; self.db.commit()
        r = self.client.post('/api/members', headers=self.headers(), json={'first_name': 'New'})
        self.assertEqual(r.status_code, 201); self.assertEqual(r.json()['member_number'], 'TNG-000003')

    def test_failed_checkout_invite_retries_without_duplicate_payment_or_second_email(self):
        self.db.add(Lead(first_name='New', last_name='Member', email='new@example.com',
                         product_id=self.product.id, clover_checkout_id='retry-email', status='started_checkout'))
        self.db.commit()
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-only'}), \
             patch('resend.Emails.send', side_effect=[RuntimeError('offline'), {'id': 'accepted'}]) as send:
            first = self.payment('retry-email'); self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()['portal_invite_status'], 'email_error')
            second = self.payment('retry-email'); self.assertEqual(second.status_code, 200)
            self.assertEqual(second.json()['portal_invite_status'], 'sent')
            third = self.payment('retry-email'); self.assertEqual(third.json()['portal_invite_status'], 'already_invited')
            self.assertEqual(send.call_count, 2)
        self.assertEqual(self.db.query(Sale).filter_by(clover_checkout_id='retry-email').count(), 1)
        self.assertEqual(self.db.query(MemberInvite).count(), 1)
        self.assertEqual(self.db.query(Member).count(), 2)

    def test_pos_membership_sale_upgrades_imported_profile_and_sends_one_activation(self):
        self.sync([customer()])
        order = {'id': 'pos-paid', 'total': 15000, 'state': 'locked', 'paymentState': 'PAID',
                 'payments': {'elements': [{'id': 'pos-payment', 'result': 'SUCCESS', 'amount': 15000}]},
                 'customers': {'elements': [customer()]},
                 'lineItems': {'elements': [{'name': self.product.name, 'price': 15000}]}}
        with patch.dict(os.environ, {'CLOVER_API_TOKEN': 'test', 'CLOVER_MERCHANT_ID': 'test', 'RESEND_API_KEY': 'test'}), \
             patch('requests.get', return_value=response([order])), \
             patch('resend.Emails.send', return_value={'id': 'accepted'}) as send:
            for expected in (1, 0):
                r = self.client.post('/api/clover/sync-sales', headers=self.headers())
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json()['portal_invitations_sent'], expected)
            self.assertEqual(send.call_count, 1)
        member = self.db.query(Member).filter_by(clover_customer_id='clover-new').one()
        self.db.refresh(member)
        self.assertEqual(member.member_type, 'MEMBER'); self.assertEqual(member.membership_status, 'active')
        self.assertEqual(self.db.query(Member).count(), 2)
        self.assertEqual(self.db.query(Sale).filter_by(clover_order_id='pos-paid').count(), 1)
        self.assertEqual(self.db.query(MemberInvite).filter_by(member_id=member.id).count(), 1)

    def test_customer_profile_with_legacy_active_default_cannot_check_in(self):
        legacy = Member(first_name='Retail', last_name='Customer', member_type='CUSTOMER',
                        membership_status='active', clover_customer_id='retail')
        self.db.add(legacy); self.db.commit()
        r = self.sync([customer('retail', emailAddresses={}, phoneNumbers={})])
        self.assertEqual(r.status_code, 200); self.db.refresh(legacy)
        r = self.client.post('/api/checkin', headers=self.headers(), json={'code': legacy.member_number})
        self.assertEqual(r.status_code, 403, r.text)

    def test_read_worker_never_sends_activation_or_modifies_paid_terms(self):
        from app.services.clover_customers import sync_profiles
        with patch('app.services.clover_customers.fetch_customers', return_value=[customer()]), \
             patch('resend.Emails.send') as send, patch('httpx.post') as post:
            result = sync_profiles()
            self.assertEqual(result['members_created'], 1); send.assert_not_called(); post.assert_not_called()
        self.db.refresh(self.member); self.assertEqual(self.member.membership_status, 'active')

if __name__ == '__main__': unittest.main()
