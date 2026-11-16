import unittest
import test_stabilization as support
import test_ticketing as tickets
from app.matchmaker.models import BoxingFighter, BoxingBout, BoxingContract, BoxingEventFee
from app.matchmaker.deductions import ContractDeductions
from app.ticketing.models import SellerPayout
from app.ticketing.service import issue_paid_order
from app.events.recap import EventPursePayment

class RecapTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers
    order = tickets.TicketingTests.order

    def fixture(self):
        o = self.order()
        o.payment_status = 'paid'
        self.db.commit()
        issue_paid_order(self.db, o, [{'ticket_type_id': self.kind.id, 'quantity': 2}])
        self.db.commit()
        a = BoxingFighter(id=100, legal_name='Red Fighter')
        b = BoxingFighter(id=101, legal_name='Blue Fighter')
        self.db.add_all([a, b])
        self.db.flush()
        self.seller.seller_ref_id = a.id
        self.db.commit()
        bout = BoxingBout(event_id=self.event.id, red_fighter_id=a.id, blue_fighter_id=b.id, red_purse=100, blue_purse=50)
        self.db.add(bout)
        self.db.flush()
        c = BoxingContract(event_id=self.event.id, bout_id=bout.id, fighter_id=a.id, opponent_id=b.id, corner='red', gross_purse=100, travel_expense=20, per_diem_total=10, deductions=5, boxer_paid=125, status='signed')
        self.db.add(c)
        self.db.commit()
        self.a = a
        self.b = b
        self.bout = bout
        self.contract = c
        self.url = f'/api/events/{self.event.id}/recap'

    def get(self):
        r = self.client.get(self.url, headers=self.headers())
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_obligations_not_mistaken_for_actual_paid_and_revenue_excludes_fees(self):
        self.fixture()
        d = self.get()
        s = d['summary']
        self.assertEqual(s['ticket_sales_cents'], 8000)
        self.assertEqual(s['purse_cost_cents'], 17500)
        self.assertEqual(s['commission_cost_cents'], 800)
        self.assertEqual(s['state_assessment_cents'], 400)
        self.assertEqual(s['recorded_result_cents'], -10700)
        self.assertEqual(s['purse_payment_status_unknown'], 2)
        self.assertIsNone(d['fighters'][1]['purse_paid_cents'])
        self.assertEqual(self.db.query(EventPursePayment).count(), 0)

    def test_purse_record_is_cumulative_versioned_and_never_edits_contract(self):
        self.fixture()
        url = self.url + f'/purses/{self.a.id}'
        r = self.client.put(url, headers=self.headers(), json={'amount_paid': '50.00', 'version': 0, 'notes': 'Cash receipt'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()['no_money_transferred'])
        self.assertEqual(self.client.put(url, headers=self.headers(), json={'amount_paid': '75', 'version': 0}).status_code, 409)
        self.assertEqual(self.client.put(url, headers=self.headers(), json={'amount_paid': '75', 'version': 1}).status_code, 200)
        d = self.get()
        self.assertEqual(d['summary']['purse_payments_recorded_cents'], 7500)
        self.assertEqual(d['summary']['remaining_recorded_purses_cents'], 5000)
        self.db.refresh(self.contract)
        self.assertEqual(self.contract.boxer_paid, 125)
        self.assertEqual(self.contract.status, 'signed')
        self.assertEqual(self.client.put(url, headers=self.headers(), json={'amount_paid': '-1', 'version': 2}).status_code, 422)

    def test_signed_revision_and_itemized_deductions_count_once(self):
        self.fixture()
        self.db.add(BoxingContract(event_id=self.event.id, bout_id=self.bout.id, fighter_id=self.a.id, opponent_id=self.b.id, corner='red', gross_purse=999, status='draft'))
        self.db.add(ContractDeductions(updated_by=self.users['admin'].id, contract_id=self.contract.id, base_deductions_cents=500, items_json='[{"label":"Medical","amount_cents":1000}]'))
        self.db.commit()
        d = self.get()
        r = next((r for r in d['fighters'] if r['fighter_id'] == self.a.id))
        self.assertEqual(r['net_obligation_cents'], 11500)
        self.assertEqual(r['contract_ids'], [self.contract.id])
        self.assertTrue(any(('newer unsigned' in w for w in d['warnings'])))

    def test_commission_snapshots_are_cumulative_and_separate(self):
        self.fixture()
        url = self.url + f'/commissions/{self.seller.id}'
        r = self.client.put(url, headers=self.headers(), json={'amount_paid': '3', 'previous_id': None})
        self.assertEqual(r.status_code, 200, r.text)
        pid = r.json()['payout_id']
        r = self.client.put(url, headers=self.headers(), json={'amount_paid': '5', 'previous_id': pid})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.put(url, headers=self.headers(), json={'amount_paid': '8', 'previous_id': pid}).status_code, 409)
        d = self.get()
        self.assertEqual(d['summary']['commission_payments_recorded_cents'], 500)
        self.assertEqual(d['summary']['remaining_commissions_cents'], 300)
        self.assertEqual(d['summary']['purse_payments_recorded_cents'], 0)
        self.assertEqual(self.db.query(SellerPayout).count(), 2)

    def test_actual_expense_classification_prevents_double_count(self):
        self.fixture()
        f = BoxingEventFee(event_id=self.event.id, fee_key='venue', name='Venue', actual_amount=100, estimate='$900')
        self.db.add(f)
        self.db.commit()
        self.assertEqual(self.get()['summary']['other_expenses_cents'], 10000)
        r = self.client.put(self.url + f'/expenses/{f.id}', headers=self.headers(), json={'treatment': 'fighter_pay', 'version': 0})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.get()['summary']['other_expenses_cents'], 0)
        self.db.refresh(f)
        self.assertEqual(f.actual_amount, 100)

    def test_auth_exports_and_event_comparison(self):
        self.fixture()
        for suffix in ['', '.pdf', '.csv']:
            self.assertIn(self.client.get(self.url + suffix).status_code, [401, 403])
            self.assertEqual(self.client.get(self.url + suffix, headers=self.headers('member')).status_code, 403)
        p = self.client.get(self.url + '.pdf', headers=self.headers())
        self.assertEqual(p.status_code, 200, p.text[:200])
        self.assertTrue(p.content.startswith(b'%PDF'))
        c = self.client.get(self.url + '.csv', headers=self.headers())
        self.assertEqual(c.status_code, 200)
        self.assertIn('Ticket commissions', c.text)
        self.assertNotIn('qr_token', c.text)
        r = self.client.get('/api/events/recaps', headers=self.headers())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['total'], 1)

    def test_cancelled_bout_keeps_actual_payment_and_overpayment_cost(self):
        self.fixture()
        self.client.put(self.url + f'/purses/{self.a.id}', headers=self.headers(), json={'amount_paid': '150', 'version': 0})
        self.bout.status = 'cancelled'
        self.db.commit()
        s = self.get()['summary']
        self.assertEqual(s['net_purse_obligation_cents'], 0)
        self.assertEqual(s['purse_cost_cents'], 15000)

    def test_collected_other_income_deduplicates_references_and_ignores_pending(self):
        from app.revenue.models import RevenueOrganization, EventRevenuePayment
        self.fixture()
        org = RevenueOrganization(business_name='Example sponsor')
        self.db.add(org)
        self.db.flush()
        for status, reference, amount in [('PAID','SPONSOR-1',100),('PAID','SPONSOR-1',100),('PENDING','SPONSOR-2',500),('PARTIAL','SPONSOR-3',200)]:
            self.db.add(EventRevenuePayment(event_id=self.event.id,organization_id=org.id,status=status,provider='CLOVER',provider_payment_id=reference,amount=amount))
        self.db.commit()
        data=self.get()
        self.assertEqual(data['summary']['other_income_cents'],10000)
        self.assertTrue(any('duplicate payment reference' in w for w in data['warnings']))
        self.assertTrue(any('Partial sponsor' in w for w in data['warnings']))

    def test_actual_assessment_replaces_estimate_and_zero_payment_is_known(self):
        self.fixture()
        self.db.add(BoxingEventFee(event_id=self.event.id,fee_key='assessment',name='State assessment',actual_amount=10))
        self.db.commit()
        self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'0','version':0})
        data=self.get()
        self.assertEqual(data['summary']['state_assessment_cents'],1000)
        self.assertEqual(data['summary']['assessment_basis'],'recorded_actual')
        self.assertEqual(data['summary']['purse_payment_status_unknown'],1)
        self.assertEqual(next(r for r in data['fighters'] if r['fighter_id']==self.a.id)['purse_paid_cents'],0)
        self.assertEqual(self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'5','paid_date':'2099-01-01','version':1}).status_code,422)
