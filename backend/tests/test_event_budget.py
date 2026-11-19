import unittest,json
from datetime import datetime
import test_stabilization as support
from app.events.budget import BudgetBody,calculate,EventBudget
from app.events.concessions_finance import EventPosSnapshot
from app.events.recap import RecapFeeTreatment
from app.matchmaker.models import BoxingEvent,BoxingFighter,BoxingBout,BoxingEventFee
from app.ticketing.models import TicketOrder
from app.models import Sale,User
class BudgetTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self);self.past=BoxingEvent(slug='budget-past',name='Past event',event_date='2026-11-14',status='completed');self.event=BoxingEvent(slug='budget-next',name='Next event',event_date='2027-01-30');self.red=BoxingFighter(legal_name='Example Red');self.blue=BoxingFighter(legal_name='Example Blue');self.db.add_all([self.past,self.event,self.red,self.blue]);self.db.flush();self.db.add_all([BoxingBout(event_id=self.past.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,status='booked',red_purse=500,blue_purse=500),BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,status='booked',red_purse=700,blue_purse=900),TicketOrder(event_id=self.past.id,buyer_name='Private buyer',buyer_email='private-budget@example.com',subtotal_cents=40000,total_cents=40000,payment_status='paid',receipt_number='BUDGET-PAID',items_json='[{"quantity":10}]'),BoxingEventFee(event_id=self.past.id,fee_key='venue',name='Venue',actual_amount=500),BoxingEventFee(event_id=self.past.id,fee_key='beer',name='Beer',actual_amount=200)]);self.db.commit();self.path=f'/api/events/{self.event.id}/budget'
 def assumptions(self,**extra):return BudgetBody(expected_paid_tickets=100,average_ticket_cents=4000,concessions_per_ticket_cents=500,bar_per_ticket_cents=500,sponsor_vendor_cents=10000,purse_allowance_cents=100000,commission_percent=20,assessment_percent=5,processing_fee_percent=0,operating_costs=[{'name':'Venue','amount_cents':50000}],**extra)
 def current(self):return {'summary':{'current_card_fighters':2,'commission_cost_cents':0,'paid_ticket_quantity':0}}
 def test_scenarios_and_break_even_count_all_revenue_and_cost_categories(self):
  f=calculate(self.assumptions(),self.current());self.assertEqual(f['break_even_paid_tickets'],45);self.assertEqual(f['scenarios'][1]['income_cents'],510000);self.assertEqual(f['scenarios'][1]['cost_cents'],275000);self.assertEqual(f['scenarios'][1]['projected_result_cents'],235000);self.assertEqual([s['paid_tickets']for s in f['scenarios']],[80,100,120])
 def test_assessment_floor_and_negative_unit_margin(self):
  body=self.assumptions();body.assessment_minimum_cents=45000;self.assertEqual(calculate(body,self.current())['break_even_paid_tickets'],45);body.commission_percent=100;body.assessment_percent=100;body.sponsor_vendor_cents=0;self.assertIsNone(calculate(body,self.current())['break_even_paid_tickets']);body.sponsor_vendor_cents=10000000;self.assertEqual(calculate(body,self.current())['break_even_paid_tickets'],0)
 def test_missing_costs_are_explicit_not_complete_profit(self):
  b=self.assumptions();b.processing_fee_percent=None;b.operating_costs[0].amount_cents=None;f=calculate(b,self.current());self.assertTrue(f['provisional']);self.assertIn('Venue',f['missing_or_review']);self.assertIn('processing fee percent',f['missing_or_review'])
 def test_defaults_use_prior_paid_sales_current_both_corner_costs_and_missing_unread_pos(self):
  r=self.client.get(self.path,headers=self.headers());self.assertEqual(r.status_code,200,r.text);d=r.json();a=d['assumptions'];self.assertEqual(a['baseline_event_id'],self.past.id);self.assertEqual(a['average_ticket_cents'],4000);self.assertEqual(a['purse_allowance_cents'],160000);self.assertIsNone(a['concessions_per_ticket_cents']);self.assertIsNone(a['bar_per_ticket_cents']);self.assertIsNone(a['processing_fee_percent']);self.assertIn('Event insurance',[c['name']for c in a['operating_costs']]);self.assertTrue(d['forecast']['provisional'])
 def test_source_clover_food_bar_ratios_are_actual_baseline_per_paid_ticket(self):
  self.db.add(EventPosSnapshot(event_id=self.past.id,source_json=json.dumps({'rows':[{'key':'food','name':'Hot Dog','categories':[],'quantity':10,'net_cents':10000,'order_id':'PFOOD','payment_ids':[]},{'key':'bar','name':'Beer','categories':[],'quantity':10,'net_cents':20000,'order_id':'PBAR','payment_ids':[]}]}),settings_json='{}',version=1,imported_at=datetime.utcnow()));self.db.commit();d=self.client.get(self.path,headers=self.headers()).json();self.assertEqual(d['assumptions']['concessions_per_ticket_cents'],1000);self.assertEqual(d['assumptions']['bar_per_ticket_cents'],2000)
 def test_save_version_and_pdf_never_create_actual_sales_costs_or_payments(self):
  before=(self.db.query(Sale).count(),self.db.query(BoxingEventFee).count(),self.db.query(TicketOrder).count());body=self.assumptions(baseline_event_id=self.past.id).model_dump(mode='json');self.assertEqual(self.client.get(self.path+'.pdf',headers=self.headers()).status_code,409);self.assertEqual(self.client.post(self.path+'/preview',headers=self.headers(),json=body).status_code,200);self.assertEqual(self.db.query(EventBudget).count(),0);r=self.client.put(self.path,headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(self.path,headers=self.headers(),json=body).status_code,409);r=self.client.get(self.path+'.pdf',headers=self.headers());self.assertEqual(r.status_code,200,r.text[:100]);self.assertTrue(r.content.startswith(b'%PDF'));self.assertEqual(before,(self.db.query(Sale).count(),self.db.query(BoxingEventFee).count(),self.db.query(TicketOrder).count()))
 def test_future_current_or_unpaid_event_cannot_be_historical_baseline(self):
  self.assertEqual(self.client.get(self.path+'?baseline_event_id='+str(self.event.id),headers=self.headers()).status_code,422)
 def test_staff_finance_acl_excludes_show_and_member_roles(self):
  self.assertEqual(self.client.get(self.path).status_code,401)
  for role in ['announcer','dj','investor','sponsor']:
   u=User(name=role,email='budget-'+role+'@example.com',role=role,active=True,password_hash='none');self.db.add(u);self.db.commit();self.users[role]=u;self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)

 def test_recorded_receipts_and_costs_cannot_disappear_in_blank_forecast(self):
  current={'summary':{'current_card_fighters':10,'paid_ticket_quantity':114,'ticket_sales_cents':700000,'concessions_sales_cents':40500,'bar_sales_cents':68100,'other_income_cents':108600,'purse_cost_cents':1009500,'other_expenses_cents':628900,'commission_cost_cents':107950,'state_assessment_cents':45000}}
  b=BudgetBody(expected_paid_tickets=114,average_ticket_cents=None,concessions_per_ticket_cents=None,bar_per_ticket_cents=None,sponsor_vendor_cents=None,purse_allowance_cents=None,processing_fee_percent=None)
  f=calculate(b,current)
  for scenario in f['scenarios']:
   self.assertEqual(scenario['income_cents'],808600);self.assertEqual(scenario['cost_cents'],1791350);self.assertEqual(scenario['purse_allowance_cents'],1009500);self.assertEqual(scenario['operating_costs_cents'],628900);self.assertGreaterEqual(scenario['paid_tickets'],114)
  self.assertTrue(f['provisional']);self.assertEqual(f['break_even_status'],'missing_inputs')
 def test_no_prior_event_uses_its_own_known_sales_instead_of_zero(self):
  d=self.client.get(f'/api/events/{self.past.id}/budget',headers=self.headers()).json();self.assertEqual(d['assumptions']['average_ticket_cents'],4000);self.assertGreaterEqual(d['forecast']['scenarios'][1]['income_cents'],40000)

 def test_minimum_worksheet_is_versioned_saved_and_does_not_create_actual_expenses(self):
  before=self.db.query(BoxingEventFee).count();body=self.assumptions().model_dump(mode='json');body['pro_show_minimum']={'fighter_purses_cents':1000000,'fighter_insurance_cents':None}
  r=self.client.put(self.path,headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text)
  d=self.client.get(self.path,headers=self.headers()).json();self.assertEqual(d['forecast']['minimum_pro_show']['known_cost_cents'],1271000);self.assertEqual(d['forecast']['minimum_pro_show']['missing'],['fighter_insurance_cents']);self.assertEqual(d['assumptions']['pro_show_minimum']['fighter_purses_cents'],1000000)
  self.assertEqual(self.db.query(BoxingEventFee).count(),before);self.assertEqual(self.client.get(self.path+'.pdf',headers=self.headers()).status_code,200)

class ProShowBaselineTests(unittest.TestCase):
 def test_known_baseline_counts_commission_once_and_requires_purses_and_insurance(self):
  from app.events.budget import ProShowMinimum
  p=ProShowMinimum();self.assertEqual(sum(v or 0 for v in p.model_dump().values()),1271000)
  self.assertEqual(p.fighter_purses_cents,1000000);self.assertIsNone(p.fighter_insurance_cents)
  p.fighter_purses_cents=1000000;self.assertEqual(sum(v or 0 for v in p.model_dump().values()),1271000)
