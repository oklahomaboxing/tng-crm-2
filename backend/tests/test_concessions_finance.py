import unittest,json
from unittest.mock import patch
import test_stabilization as support
from app.events.concessions_finance import normalize_orders,allocate,report_data,EventPosSnapshot,pos_revenue
from app.matchmaker.models import BoxingEvent,BoxingEventFee
from app.events.recap import recap
from app.events.investors import overview
from app.models import Sale,MembershipProduct,User
class FinancialTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self);self.event=BoxingEvent(slug='finance-event',name='Finance Event',event_date='2026-11-14');self.db.add(self.event);self.db.commit();self.path=f'/api/concessions/events/{self.event.id}/financials'
 def order(self,**changes):
  return {'id':'ORDER1','paymentState':'PAID','total':2200,'payments':{'elements':[{'id':'PAY1','result':'SUCCESS','amount':2200,'taxAmount':200,'tipAmount':300}]},'lineItems':{'elements':[{'name':'Hot Dog','price':1000},{'name':'Mixed Drink','price':1000}]},**changes}
 def source(self,orders=None):return normalize_orders(orders or [self.order()],{})
 def sync(self,source=None,version=0):
  with patch('app.events.concessions_finance.fetch_clover',return_value=source or self.source()):return self.client.post(self.path+'/sync',headers=self.headers(),json={'start_local':'2026-11-14T00:00','end_local':'2026-11-15T06:00','version':version})
 def test_only_paid_reconciled_items_count_without_tax_tips_or_buyer_fields(self):
  source=self.source([self.order(customer={'email':'PRIVATE@example.com'}),self.order(id='OPEN',paymentState='OPEN')]);self.assertEqual(sum(r['net_cents']for r in source['rows']),2000);self.assertNotIn('PRIVATE',json.dumps(source));self.assertEqual(source['review_counts']['unpaid_or_refunded_orders'],1)
 def test_bad_payment_refund_and_unexplained_adjustments_need_review(self):
  for changes in [{'total':2001},{'paymentState':'PARTIALLY_PAID'},{'payments':{'elements':[{'id':'P','result':'SUCCESS','amount':2200,'taxAmount':200,'refunds':{'elements':[{'amount':100}]}}]}},{'serviceCharge':{'amount':100}},{'lineItems':{'elements':[{'name':'Hot Dog','price':500}]}}]:self.assertEqual(self.source([self.order(**changes)])['rows'],[])
 def test_discount_allocation_exact_cents_and_mixed_food_bar_split(self):
  o=self.order(total=2001,payments={'elements':[{'id':'P','result':'SUCCESS','amount':2001,'taxAmount':200}]},discounts={'elements':[{'amount':199}]});s=self.source([o]);self.assertEqual(sum(r['net_cents']for r in s['rows']),1801);self.assertLessEqual(abs(s['rows'][0]['net_cents']-s['rows'][1]['net_cents']),1);self.assertEqual(sum(allocate(10,[1,1,1])),10)
 def test_auth_scope_and_no_remote_calls_from_report_read(self):
  self.assertEqual(self.client.get(self.path).status_code,401)
  for role in ['rep','member']:
   if role in self.users:self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)
  u=User(name='Chef',role='concessions',email='chef-finance@example.com',password_hash='none',active=True);self.db.add(u);self.db.commit();self.users['concessions']=u;self.assertEqual(self.client.get(self.path,headers=self.headers('concessions')).status_code,403)
  with patch('requests.get',side_effect=AssertionError('Read must not contact Clover')):self.assertEqual(self.client.get(self.path,headers=self.headers()).status_code,200)
 def test_sync_is_versioned_refresh_not_duplicate_income(self):
  self.assertEqual(self.sync().status_code,200);self.assertEqual(self.sync().status_code,409);self.assertEqual(self.sync(version=1).status_code,200);self.assertEqual(pos_revenue(self.db,self.event.id),{'concessions':1000,'bar':1000});self.assertEqual(self.db.query(EventPosSnapshot).count(),1)
 def test_source_failure_preserves_previous_snapshot(self):
  self.assertEqual(self.sync().status_code,200)
  from fastapi import HTTPException
  with patch('app.events.concessions_finance.fetch_clover',side_effect=HTTPException(502,'Provider failed')):self.assertEqual(self.client.post(self.path+'/sync',headers=self.headers(),json={'start_local':'2026-11-14T00:00','end_local':'2026-11-15T06:00','version':1}).status_code,502)
  self.assertEqual(self.client.get(self.path,headers=self.headers()).json()['sections']['bar']['revenue_cents'],1000)
 def test_cost_receipt_is_idempotent_and_uses_same_event_expense(self):
  body={'name':'Beer receipt','amount_cents':5000,'channel':'bar','paid':False,'request_key':'a31d9116-72e5-43d8-a1d8-e20783e2c6be'}
  for _ in range(2):self.assertEqual(self.client.post(self.path+'/expenses',headers=self.headers(),json=body).status_code,200)
  self.assertEqual(self.db.query(BoxingEventFee).filter_by(event_id=self.event.id).count(),1);d=self.client.get(self.path,headers=self.headers()).json();self.assertEqual(d['sections']['bar']['cost_cents'],5000);self.assertIsNone(d['sections']['bar']['profit_cents']);self.assertFalse(d['expenses'][0]['paid']);self.assertEqual(recap(self.db,self.event.id)['summary']['other_expenses_cents'],5000)
 def test_unknown_sales_and_missing_costs_prevent_confirmed_profit(self):
  s=self.source([self.order(lineItems={'elements':[{'name':'Custom Item','price':1000},{'name':'Shot','price':1000}]})]);self.assertEqual(self.sync(s).status_code,200);d=self.client.get(self.path,headers=self.headers()).json();self.assertEqual(d['totals']['review'],1000)
  body={'version':1,'items':{},'expenses':{},'costs_complete':{'bar':True}};self.assertEqual(self.client.put(self.path+'/settings',headers=self.headers(),json=body).status_code,200);d=self.client.get(self.path,headers=self.headers()).json();self.assertIsNone(d['sections']['bar']['profit_cents'])
  body.update(version=2,items={s['rows'][0]['key']:'exclude'});self.assertEqual(self.client.put(self.path+'/settings',headers=self.headers(),json=body).status_code,200);d=self.client.get(self.path,headers=self.headers()).json();self.assertEqual(d['sections']['bar']['profit_cents'],1000)
 def test_event_recap_and_investor_income_deduplicate_existing_food_sale(self):
  self.assertEqual(self.sync().status_code,200);p=MembershipProduct(name='Hot Dog',price=10,category='concessions',is_membership=False);self.db.add(p);self.db.flush();self.db.add(Sale(member_id=self.member.id,sales_rep_id=self.rep.id,product_id=p.id,amount=10,payment_status='paid',clover_order_id='ORDER1',clover_payment_id='PAY1'));self.db.commit();d=overview(self.db);self.assertEqual(d['income_categories']['concessions'],1000);self.assertEqual(d['income_categories']['bar'],1000);self.assertEqual(recap(self.db,self.event.id)['summary']['total_recorded_income_cents'],2000)
 def test_one_clover_order_cannot_be_attributed_to_two_events(self):
  self.assertEqual(self.sync().status_code,200);e=BoxingEvent(name='Other event',slug='other-finance-event',event_date='2026-11-14');self.db.add(e);self.db.commit();self.path=f'/api/concessions/events/{e.id}/financials';self.assertEqual(self.sync().status_code,409)
 def test_pdf_and_csv_are_private_and_formula_safe(self):
  self.db.add(BoxingEventFee(event_id=self.event.id,fee_key='receipt',name='=unsafe',actual_amount=12.34,paid=False));self.db.commit()
  for suffix in ['.pdf','.pdf?view=expenses','.csv']:
   r=self.client.get(self.path+suffix,headers=self.headers());self.assertEqual(r.status_code,200,r.text[:100]if suffix=='.csv'else'');self.assertIn('no-store',r.headers['cache-control'])
   if suffix.startswith('.pdf'):self.assertTrue(r.content.startswith(b'%PDF'))
   else:self.assertIn("'=unsafe",r.text)
 def test_new_welcome_letter_has_headphone_rule(self):
  from app.matchmaker.welcome_letter import draft
  self.assertIn('No loud music. Please bring headphones if you want to listen to music.',draft(self.db,self.event.id)[3])

 def test_generic_ledger_mirror_of_fully_classified_pos_order_is_not_extra_revenue(self):
  self.assertEqual(self.sync().status_code,200);p=MembershipProduct(name='Generic POS purchase',price=22,category='retail',is_membership=False);self.db.add(p);self.db.flush();self.db.add(Sale(member_id=self.member.id,sales_rep_id=self.rep.id,product_id=p.id,amount=22,payment_status='paid',clover_order_id='ORDER1',clover_payment_id='PAY1'));self.db.commit();d=overview(self.db);self.assertEqual(d['income_categories']['concessions'],1000);self.assertEqual(d['income_categories']['bar'],1000);self.assertEqual(d['income_categories']['retail_apparel'],0)
