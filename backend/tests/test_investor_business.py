import unittest,json
from datetime import datetime,timedelta,timezone
import test_stabilization as support
from app.models import User,Member,MembershipProduct,Sale,MerchandiseCheckout
from app.events.investors import overview,InvestorBusinessAccess,BusinessLedgerEntry
from app.events.partners import PartnerGrant
from app.matchmaker.models import BoxingEvent,BoxingFighter,BoxingBout,BoxingContract,BoxingEventFee
from app.ticketing.models import TicketOrder,EventSeller,EventTicketType,IssuedTicket
from app.revenue.models import RevenueOrganization,EventRevenuePayment
class InvestorBusinessTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  for role in ('investor','investor2','sponsor','concessions'):
   u=User(name='Example '+role,email=role+'@example.com',role='investor' if role.startswith('investor') else role,active=True,password_hash='not-a-password');self.db.add(u);self.users[role]=u
  self.db.flush();self.event=BoxingEvent(slug='investor-event',name='Example Investor Event',event_date='2026-11-14',venue='Example venue',status='completed');self.red=BoxingFighter(legal_name='Example Red');self.blue=BoxingFighter(legal_name='Example Blue');self.db.add_all([self.event,self.red,self.blue]);self.db.flush();self.bout=BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,red_purse=1000,blue_purse=500,status='booked');self.db.add(self.bout);self.db.flush()
  self.db.add_all([BoxingContract(event_id=self.event.id,bout_id=self.bout.id,fighter_id=self.red.id,opponent_id=self.blue.id,corner='red',status='signed',gross_purse=1000,travel_expense=100,per_diem_total=50),BoxingContract(event_id=self.event.id,bout_id=self.bout.id,fighter_id=self.blue.id,opponent_id=self.red.id,corner='blue',status='signed',gross_purse=500,travel_expense=50,per_diem_total=25)])
  self.seller=EventSeller(event_id=self.event.id,seller_type='fighter',seller_ref_id=self.red.id,display_name='Example Red',public_code='fixture-investor-red');self.db.add(self.seller);self.db.flush();self.order=TicketOrder(event_id=self.event.id,seller_id=self.seller.id,buyer_name='PRIVATE BUYER NAME',buyer_email='private-buyer@example.com',buyer_phone='+14055550111',subtotal_cents=4000,fee_cents=200,total_cents=4200,payment_id='PAY-TICKET',payment_status='paid',receipt_number='INV-TEST-PAID',items_json='[{"quantity":1}]');self.db.add(self.order);self.db.flush();tt=EventTicketType(event_id=self.event.id,name='General Admission',price_cents=4000);self.db.add(tt);self.db.flush();self.db.add(IssuedTicket(order_id=self.order.id,event_id=self.event.id,ticket_type_id=tt.id,seller_id=self.seller.id,ticket_number='PRIVATE-TICKET-NUMBER',qr_token_hash='private-qr-secret-hash',status='valid',price_cents=4000,commission_cents=400));self.db.commit()
 def enable(self,role='investor'):
  r=self.client.put('/api/partners/business-admin/access/'+str(self.users[role].id),headers=self.headers(),json={'enabled':True,'version':0});self.assertEqual(r.status_code,200,r.text)
 def portal(self,role='investor',**params):return self.client.get('/api/partners/portal',headers=self.headers(role),params=params)
 def sale(self,product,amount,ref='',**extra):
  s=Sale(member_id=self.member.id,sales_rep_id=self.rep.id,product_id=product.id,amount=amount,payment_status='paid',transaction_status='paid',clover_payment_id=ref,**extra);self.db.add(s);self.db.commit();return s
 def ledger(self,**extra):
  body={'kind':'expense','category':'gym_rent','title':'Recorded gym overhead','amount_cents':10000,'occurred_on':'2026-11-01','basis':'paid','private_note':'PRIVATE ADMIN NOTE','request_key':'fixture-business-entry-0001',**extra};return self.client.post('/api/partners/business-admin/ledger',headers=self.headers(),json=body)
 def test_business_access_is_explicit_per_investor_and_not_shared_with_sponsors(self):
  self.assertFalse(self.portal().json()['business_access']);self.assertIsNone(self.portal().json()['business']);self.enable();self.assertTrue(self.portal().json()['business_access']);self.assertIsNone(self.portal('investor2',user_id=self.users['investor'].id).json()['business']);self.assertNotIn('business',self.portal('sponsor').json());self.assertNotIn('business',self.portal('concessions').json())
  self.assertEqual(self.client.put('/api/partners/business-admin/access/'+str(self.users['sponsor'].id),headers=self.headers(),json={'enabled':True,'version':0}).status_code,422)
 def test_investor_has_read_only_safe_views_not_members_users_or_mutations(self):
  self.enable()
  for p in ['/api/members','/api/users','/api/amateurs/directory','/api/partners/business-admin','/api/events/'+str(self.event.id)+'/recap']:
   self.assertEqual(self.client.get(p,headers=self.headers('investor')).status_code,403,p)
  self.assertEqual(self.client.post('/api/partners/business-admin/updates',headers=self.headers('investor'),json={'title':'Bad','body':'Not permitted','published':True}).status_code,403)
  self.assertEqual(self.client.get('/api/partners/portal').status_code,401)
 def test_both_corner_costs_ticket_sales_commissions_and_private_fields(self):
  self.enable();d=self.portal().json();event=next(e for e in d['business']['events'] if e['id']==self.event.id);bout=event['bouts'][0];self.assertEqual(bout['red_direct_cost_cents'],115400);self.assertEqual(bout['blue_direct_cost_cents'],57500);self.assertEqual(bout['combined_bout_cost_cents'],172900);self.assertEqual(bout['combined_ticket_sales_cents'],4000);self.assertEqual(event['sellers'][0]['ticket_quantity'],1);self.assertEqual(event['sellers'][0]['commission_earned_cents'],400);self.assertIsNone(event['sellers'][0]['commission_paid_cents'])
  text=json.dumps(d)
  for private in ['PRIVATE BUYER NAME','private-buyer@example.com','PRIVATE-TICKET-NUMBER','private-qr-secret-hash','purse_hold_reason','purse_notes','password_hash']:self.assertNotIn(private,text)
 def test_membership_metrics_reuse_membership_evidence_and_exclude_ticket_only_profiles(self):
  baseline=overview(self.db)['membership_counts'];customer=Member(first_name='Private',last_name='Customer',email='private-customer@example.com',member_type='CUSTOMER',membership_status='active',status='customer',membership_type='Fight Ticket');self.db.add(customer);self.db.commit();d=overview(self.db);self.assertEqual(d['membership_counts'],baseline);self.assertNotIn('private-customer@example.com',json.dumps(d));self.assertEqual(d['income_categories']['memberships'],15000)
 def test_pending_and_partial_ticket_orders_are_excluded_and_customer_fees_not_income(self):
  for i,status in enumerate(['pending','failed','partial_refund','refunded']):self.db.add(TicketOrder(event_id=self.event.id,buyer_name='Private',buyer_email='private@example.com',subtotal_cents=9900,total_cents=9900,payment_status=status,receipt_number='INV-EXCLUDED-'+str(i)))
  self.db.commit();d=overview(self.db);self.assertEqual(d['income_categories']['event_tickets'],4000);self.assertEqual(d['review_counts']['pending_ticket_orders'],2);self.assertEqual(d['review_counts']['partial_refunds'],1)
 def test_cross_source_ticket_and_sponsor_references_do_not_double_count(self):
  p=MembershipProduct(name='General Admission',price=40,category='tickets',is_membership=False);self.db.add(p);self.db.flush();self.sale(p,40,'PAY-TICKET');org=RevenueOrganization(business_name='Example sponsor');self.db.add(org);self.db.flush();self.db.add(EventRevenuePayment(event_id=self.event.id,organization_id=org.id,provider_payment_id='PAY-TICKET',amount=40,status='PAID'));self.db.add(EventRevenuePayment(event_id=self.event.id,organization_id=org.id,provider_payment_id='SPONSOR-PAID',amount=200,status='PAID'));self.db.commit();d=overview(self.db);self.assertEqual(d['income_categories']['event_tickets'],4000);self.assertEqual(d['income_categories']['sponsor_vendor'],20000);self.assertEqual(d['review_counts']['cross_source_sales_excluded'],1)
 def test_different_products_in_one_payment_survive_but_exact_mirrors_do_not(self):
  product=MembershipProduct(name='Registration Fee',price=20,category='registration',is_membership=False);self.db.add(product);self.db.flush();self.sale(self.product,150,'MULTI-PAY');self.sale(product,20,'MULTI-PAY');self.sale(product,20,'MULTI-PAY');d=overview(self.db);self.assertEqual(d['income_categories']['memberships'],30000);self.assertEqual(d['income_categories']['registration'],2000);self.assertEqual(d['review_counts']['duplicate_ledger_rows'],1)
 def test_merchandise_receipt_and_ledger_are_not_both_counted_and_fallback_is_disclosed(self):
  p=MembershipProduct(name='Example Shirt',price=20,category='merchandise');self.db.add(p);self.db.flush();checkout=MerchandiseCheckout(sales_rep_id=self.rep.id,customer_name='Private Buyer',customer_email='buyer@example.com',cart_json='[]',total_amount=20,status='paid',clover_checkout_id='MERCH-CHK',clover_payment_id='MERCH-PAY');self.db.add(checkout);self.db.commit();d=overview(self.db);self.assertEqual(d['income_categories']['retail_apparel'],2000);self.assertEqual(d['review_counts']['merchandise_receipts_without_ledger'],1);self.sale(p,20,'MERCH-PAY',clover_checkout_id='MERCH-CHK');d=overview(self.db);self.assertEqual(d['income_categories']['retail_apparel'],2000);self.assertEqual(d['review_counts']['merchandise_receipts_without_ledger'],0)
 def test_known_refunds_reduce_income_and_unknown_refunds_are_flagged(self):
  p=MembershipProduct(name='Example Retail',price=50,category='merchandise');self.db.add(p);self.db.flush();self.sale(p,50,'REFUND-PAY',refunded=True,refund_amount=10);self.sale(p,50,'UNKNOWN-REFUND',refunded=True,refund_amount=0);d=overview(self.db);self.assertEqual(d['income_categories']['retail_apparel'],4000);self.assertEqual(d['review_counts']['unknown_sale_refunds'],1)
 def test_private_overhead_and_versioned_edits_affect_shared_totals_without_notes(self):
  before=overview(self.db)['summary']['total_costs_and_obligations_cents'];r=self.ledger();self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.ledger().json()['id'],r.json()['id']);self.assertEqual(self.db.query(BusinessLedgerEntry).count(),1);self.enable();d=self.portal().json()['business'];self.assertEqual(d['summary']['total_costs_and_obligations_cents'],before+10000);self.assertNotIn('PRIVATE ADMIN NOTE',json.dumps(d));row=self.db.query(BusinessLedgerEntry).one();body={'kind':'expense','category':'gym_rent','title':'Corrected overhead','amount_cents':12000,'occurred_on':'2026-11-01','basis':'paid','private_note':'PRIVATE ADMIN NOTE','request_key':'fixture-business-edit-0001','version':row.version};r=self.client.put(f'/api/partners/business-admin/ledger/{row.id}',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(f'/api/partners/business-admin/ledger/{row.id}',headers=self.headers(),json=body).status_code,409);self.db.expire_all();self.assertEqual(self.portal().json()['business']['summary']['total_costs_and_obligations_cents'],before+12000)
 def test_unpublished_updates_stay_private_and_publication_is_admin_only(self):
  for published in (False,True):self.assertEqual(self.client.post('/api/partners/business-admin/updates',headers=self.headers(),json={'title':'Public update' if published else 'PRIVATE DRAFT','body':'Example progress note','published':published}).status_code,200)
  self.enable();d=self.portal().json();self.assertEqual(len(d['business']['updates']),1);self.assertNotIn('PRIVATE DRAFT',json.dumps(d));self.assertEqual(self.client.get('/api/partners/business-admin/overview',headers=self.headers()).status_code,200)
 def test_event_only_grants_remain_scoped_when_business_access_is_off(self):
  self.db.add(PartnerGrant(user_id=self.users['investor'].id,event_id=self.event.id,financials=True,update_text='Approved event update'));self.db.commit();d=self.portal().json();self.assertIsNone(d['business']);self.assertEqual(len(d['events']),1);self.assertIn('financial_detail',d['events'][0]);self.assertEqual(d['events'][0]['financial_detail']['bouts'][0]['combined_bout_cost_cents'],172900)
 def test_event_period_uses_event_date_and_does_not_imply_payment_date_or_final_profit(self):
  self.event.event_date='2027-01-30';self.db.commit();d=overview(self.db,'month',datetime(2026,11,18,tzinfo=timezone.utc));self.assertEqual(d['income_categories']['event_tickets'],0);self.assertEqual(d['events'],[]);self.assertIn('event dates',d['basis']);self.assertTrue(d['provisional'])
 def test_shared_fighter_bout_costs_require_allocation_instead_of_counting_twice(self):
  extra=BoxingFighter(legal_name='Example Extra');self.db.add(extra);self.db.flush();self.db.add(BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=extra.id,status='booked',red_purse=300,blue_purse=300));self.db.commit();d=overview(self.db);event=next(e for e in d['events'] if e['id']==self.event.id);self.assertTrue(all(b['needs_allocation'] for b in event['bouts']));self.assertTrue(all(b['combined_bout_cost_cents'] is None for b in event['bouts']))

 def test_edit_cannot_duplicate_existing_ticket_payment_as_other_income(self):
  r=self.ledger();self.assertEqual(r.status_code,200)
  body={'kind':'income','category':'other_income','title':'Duplicate receipt','amount_cents':4000,'occurred_on':'2026-11-14','basis':'paid','source_reference':'PAY-TICKET','request_key':'fixture-edit-income','version':1}
  self.assertEqual(self.client.put('/api/partners/business-admin/ledger/'+str(r.json()['id']),headers=self.headers(),json=body).status_code,409)
