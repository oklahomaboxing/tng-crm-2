import unittest
import test_stabilization as support
import test_ticketing as tickets
import test_event_recap as recaps
from app.fighter_portal.models import FighterAccount
from app.events.recap import EventPursePayment
from app.ticketing.models import TicketOrder, SellerPayout

class FighterContributionTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    order=tickets.TicketingTests.order
    fixture=recaps.RecapTests.fixture
    def setup_fighter(self):
        self.fixture()
        self.db.add(FighterAccount(user_id=self.users['fighter'].id,fighter_id=self.a.id));self.db.commit()
        self.path=f'/api/events/fighters/{self.a.id}/contribution'
    def get(self,role='fighter'):
        r=self.client.get(self.path,headers=self.headers(role));self.assertEqual(r.status_code,200,r.text);return r.json()
    def test_own_contribution_matches_recap_without_exposing_opponent_costs(self):
        self.setup_fighter();d=self.get();r=d['events'][0]
        self.assertEqual(r['ticket_sales_cents'],8000)
        self.assertEqual(r['total_fighter_cost_cents'],13300)
        self.assertEqual(r['opponent_direct_cost_cents'],5000)
        self.assertEqual(r['combined_bout_cost_cents'],18300)
        self.assertEqual(r['combined_bout_contribution_cents'],-10300)
        self.assertEqual(r['outcome'],'below_direct_costs')
        self.assertEqual(r['travel_cents'],2000);self.assertEqual(r['per_diem_cents'],1000);self.assertEqual(r['deductions_cents'],500)
        self.assertIsNone(r['purse_paid_cents']);self.assertTrue(r['provisional'])
        body=self.client.get(self.path,headers=self.headers('fighter')).text
        self.assertNotIn('Blue Fighter',body);self.assertNotIn('buyer_email',body);self.assertNotIn('qr_token',body);self.assertNotIn('purse_notes',body)
        self.assertEqual(d['roster_scope'],'current_bout_card')
        self.assertEqual(self.get('admin')['events'],d['events'])
    def test_access_is_own_fighter_or_staff_only(self):
        self.setup_fighter()
        self.assertEqual(self.client.get(f'/api/events/fighters/{self.b.id}/contribution',headers=self.headers('fighter')).status_code,403)
        for role in ['member','rep']:
            self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.get(self.path).status_code,401)
        self.assertEqual(self.client.get(self.path,headers=self.headers('staff')).status_code,200)
        self.assertEqual(self.client.get('/api/events/fighters/999999/contribution',headers=self.headers('admin')).status_code,404)
    def test_current_card_only_and_payment_corrections_reflect_immediately(self):
        self.setup_fighter()
        self.client.put(f'/api/events/{self.event.id}/recap/purses/{self.a.id}',headers=self.headers(),json={'amount_paid':'150','version':0})
        d=self.get();self.assertEqual(d['events'][0]['purse_cost_cents'],15000)
        self.assertEqual(d['events'][0]['combined_bout_contribution_cents'],-12800)
        self.bout.status='cancelled';self.db.commit();self.assertEqual(self.get()['events'],[])
        self.assertEqual(self.db.query(EventPursePayment).count(),1)
        self.bout.status='completed';self.db.commit();self.assertEqual(len(self.get()['events']),1)
    def test_paid_sales_only_and_commission_overpayments_count_as_cost(self):
        self.setup_fighter()
        self.db.add(SellerPayout(event_id=self.event.id,seller_id=self.seller.id,amount_paid_cents=1200))
        self.db.commit();self.assertEqual(self.get()['events'][0]['commission_cost_cents'],1200)
        order=self.db.query(TicketOrder).filter_by(event_id=self.event.id).one();order.payment_status='pending';self.db.commit()
        d=self.get()['events'][0];self.assertEqual(d['ticket_sales_cents'],0);self.assertEqual(d['ticket_quantity'],0);self.assertEqual(d['commission_cost_cents'],1200)
    def test_pagination_and_partial_refund_warning(self):
        self.setup_fighter();self.assertEqual(self.client.get(self.path+'?limit=51',headers=self.headers()).status_code,422)
        self.assertEqual(self.client.get(self.path+'?offset=1',headers=self.headers()).json()['events'],[])
        order=self.db.query(TicketOrder).filter_by(event_id=self.event.id).one();order.payment_status='partial_refund';self.db.commit()
        r=self.get()['events'][0];self.assertEqual(r['ticket_sales_cents'],0);self.assertTrue(any('refunded' in n for n in r['notes']))

    def test_unrecorded_paper_stock_is_disclosed_without_inventing_revenue(self):
        from uuid import uuid4
        self.setup_fighter()
        r=self.client.post(f'/api/ticketing/events/{self.event.id}/paper-batches',headers=self.headers(),json={'seller_id':self.seller.id,'ticket_type_id':self.kind.id,'quantity':3,'request_key':str(uuid4())})
        self.assertEqual(r.status_code,200,r.text)
        data=self.get()['events'][0]
        self.assertEqual(data['ticket_sales_cents'],8000)
        self.assertTrue(any('3 paper ticket(s)' in n for n in data['notes']))

    def test_positive_and_break_even_outcomes_use_direct_costs_not_legacy_paid_field(self):
        self.setup_fighter()
        self.contract.gross_purse=10;self.contract.travel_expense=0;self.contract.per_diem_total=0;self.contract.deductions=0;self.db.commit()
        data=self.get()['events'][0]
        self.assertEqual(data['total_fighter_cost_cents'],1800)
        self.assertEqual(data['combined_bout_contribution_cents'],1200)
        self.assertEqual(data['combined_bout_outcome'],'above_direct_costs')
        self.assertIsNone(data['purse_paid_cents'])
        self.contract.gross_purse=22;self.db.commit()
        data=self.get()['events'][0]
        self.assertEqual(data['combined_bout_contribution_cents'],0)
        self.assertEqual(data['combined_bout_outcome'],'break_even')

    def test_opponent_unrelated_bout_requires_allocation_instead_of_overcounting(self):
        from app.matchmaker.models import BoxingBout,BoxingFighter
        self.setup_fighter();other=BoxingFighter(legal_name='Third fighter');self.db.add(other);self.db.flush()
        self.db.add(BoxingBout(event_id=self.event.id,red_fighter_id=self.b.id,blue_fighter_id=other.id,red_purse=100));self.db.commit()
        row=self.get()['events'][0]
        self.assertIsNone(row['combined_bout_cost_cents']);self.assertIsNone(row['combined_bout_contribution_cents']);self.assertEqual(row['combined_bout_outcome'],'needs_allocation')
