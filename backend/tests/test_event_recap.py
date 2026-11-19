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
        self.assertEqual(s['state_assessment_cents'], 45000)
        self.assertEqual(s['recorded_result_cents'], -55300)
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

    def test_cancelled_bout_excludes_paid_fighter_without_deleting_history(self):
        self.fixture()
        self.client.put(self.url + f'/purses/{self.a.id}', headers=self.headers(), json={'amount_paid': '150', 'version': 0})
        self.bout.status = 'cancelled'
        self.db.commit()
        s = self.get()['summary']
        self.assertEqual(s['net_purse_obligation_cents'], 0)
        self.assertEqual(s['purse_cost_cents'], 0)
        self.assertEqual(s['excluded_off_card_purse_paid_cents'], 15000)
        self.assertEqual(self.get()['fighters'], [])
        self.assertEqual(self.db.query(EventPursePayment).one().amount_paid_cents, 15000)
        response=self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'160','version':1})
        self.assertEqual(response.status_code,409)
        self.bout.status='completed';self.db.commit()
        self.assertEqual(self.get()['summary']['purse_payments_recorded_cents'],15000)
        self.assertEqual(self.get()['summary']['purse_cost_cents'],20000)

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
        self.db.add(BoxingEventFee(event_id=self.event.id,fee_key='assessment',name='State assessment',actual_amount=1000))
        self.db.commit()
        self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'0','version':0})
        data=self.get()
        self.assertEqual(data['summary']['state_assessment_cents'],100000)
        self.assertEqual(data['summary']['assessment_basis'],'recorded_actual')
        self.assertEqual(data['summary']['purse_payment_status_unknown'],1)
        self.assertEqual(next(r for r in data['fighters'] if r['fighter_id']==self.a.id)['purse_paid_cents'],0)
        self.assertEqual(self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'5','paid_date':'2099-01-01','version':1}).status_code,422)

    def test_replaced_fighter_and_old_contract_do_not_reappear_from_payment(self):
        self.fixture()
        self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'125','version':0})
        replacement=BoxingFighter(legal_name='Current Replacement')
        self.db.add(replacement);self.db.flush()
        self.bout.red_fighter_id=replacement.id;self.db.commit()
        data=self.get()
        self.assertEqual({r['fighter_id'] for r in data['fighters']},{replacement.id,self.b.id})
        self.assertEqual(data['summary']['net_purse_obligation_cents'],15000)
        self.assertEqual(data['summary']['purse_payments_recorded_cents'],0)
        self.assertEqual(data['summary']['excluded_off_card_purse_paid_cents'],12500)
        self.assertEqual(data['summary']['ticket_sales_cents'],8000)
        self.assertEqual(data['summary']['commission_cost_cents'],800)
        self.assertEqual(self.db.query(EventPursePayment).count(),1)
        self.assertEqual(data['roster_scope'],'current_bout_card')
        csv=self.client.get(self.url+'.csv',headers=self.headers()).text
        fighter_section=csv.split('Fighters\r\n',1)[1].split('Ticket commissions',1)[0]
        self.assertNotIn('Red Fighter',fighter_section)
        self.assertIn('Current Replacement',fighter_section)

    def test_all_off_card_statuses_exclude_fighters_but_completed_remains(self):
        self.fixture()
        for status in ['cancelled','canceled','void','withdrawn','declined','rejected','removed','deleted',' VOID ']:
            self.bout.status=status;self.db.commit()
            self.assertEqual(self.get()['fighters'],[],status)
        self.bout.status='completed';self.db.commit()
        self.assertEqual(len(self.get()['fighters']),2)

    def test_purse_hold_is_separate_from_paid_amount_and_commission(self):
        self.fixture();before=self.get()['summary']['recorded_result_cents'];url=self.url+f'/purses/{self.a.id}/hold'
        r=self.client.put(url,headers=self.headers(),json={'active':True,'reason':'Pending commission approval','version':0});self.assertEqual(r.status_code,200,r.text)
        d=self.get();a=next(f for f in d['fighters'] if f['fighter_id']==self.a.id);self.assertEqual(a['purse_status'],'on_hold');self.assertIsNone(a['purse_paid_cents']);self.assertEqual(d['summary']['purses_on_hold'],1);self.assertEqual(d['summary']['recorded_result_cents'],before)
        self.assertEqual(self.client.put(url,headers=self.headers(),json={'active':False,'version':0}).status_code,409)
        r=self.client.put(url,headers=self.headers(),json={'active':False,'reason':'Approval received','version':1});self.assertEqual(r.status_code,200);a=next(f for f in self.get()['fighters'] if f['fighter_id']==self.a.id);self.assertEqual(a['purse_status'],'not_recorded');self.assertIsNone(a['purse_paid_cents'])

    def test_history_preserves_cumulative_totals_dates_actor_and_hold_revisions(self):
        self.fixture();url=self.url+f'/purses/{self.a.id}'
        self.client.put(url,headers=self.headers(),json={'amount_paid':'50','version':0,'paid_date':'2026-11-14','notes':'Cash partial'})
        self.client.put(url,headers=self.headers(),json={'amount_paid':'125','version':1,'notes':'Owner confirmed balance paid; date unknown'})
        self.client.put(url+'/hold',headers=self.headers(),json={'active':True,'reason':'Review approval','version':0})
        response=self.client.get(self.url+f'/payment-history?kind=purse&target_id={self.a.id}',headers=self.headers());self.assertEqual(response.status_code,200,response.text);self.assertIn('no-store',response.headers['cache-control'])
        changes=response.json()['records'];payments=[r for r in changes if r['kind']=='purse'];self.assertEqual([r['paid_to_date_cents'] for r in payments],[12500,5000]);self.assertIsNone(payments[0]['paid_date']);self.assertEqual(payments[1]['paid_date'],'2026-11-14');self.assertEqual(payments[0]['recorded_by'],'admin');self.assertEqual(changes[0]['kind'],'hold');self.assertEqual(self.get()['summary']['purse_payments_recorded_cents'],12500)

    def test_legacy_purse_is_preserved_as_baseline_before_correction(self):
        self.fixture();old=EventPursePayment(event_id=self.event.id,fighter_id=self.a.id,amount_paid_cents=7500,paid_date='2026-11-14',notes='Legacy receipt',updated_by=self.users['admin'].id,version=1);self.db.add(old);self.db.commit()
        legacy=self.client.get(self.url+f'/payment-history?kind=purse&target_id={self.a.id}',headers=self.headers()).json()['records'];self.assertTrue(legacy[0]['baseline']);self.assertEqual(legacy[0]['paid_to_date_cents'],7500)
        self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'125','version':1})
        changes=self.client.get(self.url+f'/payment-history?kind=purse&target_id={self.a.id}',headers=self.headers()).json()['records'];self.assertEqual([r['paid_to_date_cents'] for r in changes],[12500,7500]);self.assertTrue(changes[1]['baseline']);self.assertEqual(changes[1]['notes'],'Legacy receipt')

    def test_commission_paid_status_and_history_do_not_pay_purse(self):
        self.fixture();d=self.get();seller=next(s for s in d['sellers'] if s['seller_id']==self.seller.id);due=seller['commission_earned_cents'];r=self.client.put(self.url+f'/commissions/{self.seller.id}',headers=self.headers(),json={'amount_paid':format(due/100,'.2f'),'previous_id':None,'notes':'Owner confirmed fully paid'})
        self.assertEqual(r.status_code,200,r.text);d=self.get();a=next(f for f in d['fighters'] if f['fighter_id']==self.a.id);self.assertEqual(a['commission_status'],'paid');self.assertEqual(a['commission_paid_cents'],due);self.assertIsNone(a['purse_paid_cents']);self.assertEqual(a['purse_status'],'not_recorded')
        h=self.client.get(self.url+f'/payment-history?kind=commission&target_id={self.seller.id}',headers=self.headers()).json()['records'];self.assertEqual(len(h),1);self.assertEqual(h[0]['paid_to_date_cents'],due);self.assertIsNone(h[0]['paid_date']);self.assertEqual(h[0]['recorded_by'],'admin')

    def test_statuses_and_exports_include_hold_without_changing_signed_contract(self):
        self.fixture();self.client.put(self.url+f'/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'0','version':0});self.client.put(self.url+f'/purses/{self.a.id}/hold',headers=self.headers(),json={'active':True,'reason':'Pending commission approval','version':0})
        data=self.get();a=next(f for f in data['fighters'] if f['fighter_id']==self.a.id);self.assertEqual(a['purse_status'],'on_hold');self.assertEqual(a['purse_paid_cents'],0);self.db.refresh(self.contract);self.assertEqual(self.contract.boxer_paid,125)
        csv=self.client.get(self.url+'.csv',headers=self.headers()).text;self.assertIn('Payment status',csv);self.assertIn('Pending commission approval',csv);pdf=self.client.get(self.url+'.pdf',headers=self.headers());self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_hold_and_history_require_staff_and_current_card_for_updates(self):
        self.fixture();path=self.url+f'/purses/{self.a.id}/hold'
        for role in ('member','fighter','rep'):
            self.assertEqual(self.client.put(path,headers=self.headers(role),json={'active':True,'reason':'test','version':0}).status_code,403)
            self.assertEqual(self.client.get(self.url+f'/payment-history?kind=purse&target_id={self.a.id}',headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.get(self.url+f'/payment-history?kind=purse&target_id={self.a.id}').status_code,401)
        self.assertEqual(self.client.put(path,headers=self.headers(),json={'active':True,'reason':' ','version':0}).status_code,422)
        self.bout.status='cancelled';self.db.commit();self.assertEqual(self.client.put(path,headers=self.headers(),json={'active':True,'reason':'test','version':0}).status_code,409)

    @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
    def test_simultaneous_commission_updates_create_one_snapshot(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from app.main import app
        from app.database import SessionLocal,get_db
        from app.events.recap import EventPaymentChange
        self.fixture();headers=self.headers();gate=Barrier(2)
        def separate_db():
            with SessionLocal() as db:yield db
        app.dependency_overrides[get_db]=separate_db
        def run(_):gate.wait();return self.client.put(self.url+f'/commissions/{self.seller.id}',headers=headers,json={'amount_paid':'5','previous_id':None}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
        self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.db.query(SellerPayout).count(),1);self.assertEqual(self.db.query(EventPaymentChange).filter_by(kind='commission').count(),1)

    @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
    def test_simultaneous_hold_updates_preserve_one_version_and_no_payment(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from app.main import app
        from app.database import SessionLocal,get_db
        from app.events.recap import EventPurseHold,EventPaymentChange
        self.fixture();headers=self.headers();gate=Barrier(2);fid=self.a.id
        def separate_db():
            with SessionLocal() as db:yield db
        app.dependency_overrides[get_db]=separate_db
        def run(_):gate.wait();return self.client.put(self.url+f'/purses/{fid}/hold',headers=headers,json={'active':True,'reason':'Pending commission approval','version':0}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
        self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.db.query(EventPurseHold).count(),1);self.assertEqual(self.db.query(EventPaymentChange).filter_by(kind='hold').count(),1);self.assertEqual(self.db.query(EventPursePayment).count(),0)

    def test_recorded_assessment_below_minimum_does_not_understate_liability(self):
        self.fixture();self.db.add(BoxingEventFee(event_id=self.event.id,fee_key='assessment',name='Assessment partial record',actual_amount=10));self.db.commit();d=self.get();self.assertEqual(d['summary']['state_assessment_cents'],45000);self.assertEqual(d['summary']['state_assessment_recorded_cents'],1000);self.assertEqual(d['summary']['assessment_basis'],'required_exceeds_recorded');self.assertTrue(any('below the required' in w for w in d['warnings']))
