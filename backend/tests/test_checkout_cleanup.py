import csv,io,json,unittest
from unittest.mock import patch,Mock
import os,requests
import test_stabilization as support
import test_ticketing as ticket_support
from app.ticketing.models import TicketOrder,TicketSmsConsent
class CheckoutCleanupTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 order=ticket_support.TicketingTests.order
 def test_order_request_retry_is_idempotent_and_payload_change_rejected(self):
  self.order();path=f'/api/ticketing/public/events/{self.event.id}/orders'
  body={'request_key':'a'*32,'buyer_name':'Retry Buyer','buyer_email':'retry@example.com','buyer_phone':'+15555550125','ticket_sms_consent':True,'seller_code':self.seller.public_code,'items':[{'ticket_type_id':self.kind.id,'quantity':1}]}
  r=self.client.post(path,json=body);self.assertEqual(r.status_code,200,r.text);oid=r.json()['order_id'];before=self.db.query(TicketOrder).count()
  again=self.client.post(path,json=body);self.assertEqual(again.json()['order_id'],oid);self.assertEqual(self.db.query(TicketOrder).count(),before);self.assertEqual(self.db.query(TicketSmsConsent).filter_by(order_id=oid).count(),1)
  changed={**body,'items':[{'ticket_type_id':self.kind.id,'quantity':2}]};self.assertEqual(self.client.post(path,json=changed).status_code,409)
  body['request_key']='b'*32;self.assertNotEqual(self.client.post(path,json=body).json()['order_id'],oid)
 def test_paid_elsewhere_flag_and_private_call_list_exclude_completed_buyers(self):
  pending=self.order();paid=TicketOrder(event_id=self.event.id,buyer_name='Paid buyer',buyer_email=pending.buyer_email.upper(),buyer_phone='15555550123',payment_status='paid',receipt_number='paid-elsewhere',total_cents=8000,items_json='[]');self.db.add(paid)
  other=TicketOrder(event_id=self.event.id,buyer_name='=Needs call',buyer_email='call@example.com',buyer_phone='+15555550199',payment_status='pending',receipt_number='call-1',total_cents=4000,items_json='[]');self.db.add(other);self.db.commit()
  base=f'/api/ticketing/events/{self.event.id}'
  d=self.client.get(base+'/recovery-dashboard',headers=self.headers()).json();row=next(x for x in d['orders'] if x['order_id']==pending.id);self.assertEqual(row['other_paid_order_ids'],[paid.id]);self.assertIn('another paid purchase',row['payment_status_label']);self.assertEqual(d['summary']['unfinished_without_paid_purchase'],1)
  r=self.client.get(base+'/unfinished-customers.csv',headers=self.headers());self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);rows=list(csv.reader(io.StringIO(r.text.lstrip('\ufeff'))));self.assertEqual(len(rows),2);self.assertEqual(rows[1][0],"'=Needs call");self.assertNotIn(pending.buyer_email,r.text);self.assertNotIn('access_token',r.text)
  all_rows=self.client.get(base+'/unfinished-customers.csv?include_completed=true',headers=self.headers());self.assertIn('Do not request another payment',all_rows.text)
  self.assertEqual(self.client.get(base+'/unfinished-customers.csv').status_code,401)
  for role in ('member','fighter','rep'):self.assertEqual(self.client.get(base+'/unfinished-customers.csv',headers=self.headers(role)).status_code,403)

 def test_decline_is_authoritative_and_cannot_overwrite_later_paid_order(self):
  o=self.order();self.assertEqual(support.StabilizationTests.payment(self,o.clover_checkout_id,Status='DECLINED').status_code,200)
  r=self.client.get(f'/api/ticketing/public/orders/{o.id}/tickets',params={'email':o.buyer_email});self.assertEqual(r.json()['payment_status'],'failed');self.assertEqual(r.json()['payment_failure'],'declined')
  with patch('app.services.sms_service.send_sms',return_value='sms'),patch('app.ticketing.emailing.send_ticket_email',return_value={'id':'email'}):
   self.assertEqual(support.StabilizationTests.payment(self,o.clover_checkout_id).status_code,200)
  support.StabilizationTests.payment(self,o.clover_checkout_id,Status='DECLINED')
  self.db.refresh(o);self.assertEqual(o.payment_status,'paid')
 def test_checkout_timeout_is_not_replayed_and_success_reuses_same_payment_link(self):
  o=self.order();o.clover_checkout_id=None;self.db.commit();path=f'/api/ticketing/public/orders/{o.id}/checkout'
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'fixture','CLOVER_MERCHANT_ID':'fixture'}),patch('app.ticketing.checkout_routes.requests.post',side_effect=requests.Timeout()) as provider:
   self.assertEqual(self.client.post(path).status_code,503)
   self.assertEqual(self.client.post(path).status_code,409);provider.assert_called_once()
 def test_completed_checkout_link_is_reused_and_failure_return_is_authenticated(self):
  o=self.order();o.clover_checkout_id=None;self.db.commit();path=f'/api/ticketing/public/orders/{o.id}/checkout'
  with patch.dict(os.environ,{'CLOVER_API_TOKEN':'fixture','CLOVER_MERCHANT_ID':'fixture'}),patch('app.ticketing.checkout_routes.requests.post',return_value=Mock(status_code=200,json=lambda:{'id':'new-checkout','href':'https://www.clover.com/checkout/fixture'})) as provider:
   one=self.client.post(path);two=self.client.post(path);self.assertEqual(one.status_code,200,one.text);self.assertEqual(one.json()['checkout_url'],two.json()['checkout_url']);provider.assert_called_once()
   failure=provider.call_args.kwargs['json']['redirectUrls']['failure'];self.assertIn('ticket_payment=failure',failure);self.assertIn('access_token=',failure)

 @unittest.skipUnless(support.TEST_DATABASE_URL,'PostgreSQL concurrent idempotency check')
 def test_concurrent_purchase_requests_create_one_order(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from fastapi.testclient import TestClient
  self.order();path=f'/api/ticketing/public/events/{self.event.id}/orders';body={'request_key':'c'*32,'buyer_name':'Concurrent Buyer','buyer_email':'concurrent@example.com','items':[{'ticket_type_id':self.kind.id,'quantity':1}]};gate=Barrier(2)
  def submit(_):
   client=TestClient(support.app)
   try:gate.wait();return client.post(path,json=body)
   finally:client.close()
  before=self.db.query(TicketOrder).count()
  with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(submit,range(2)))
  self.assertEqual([r.status_code for r in responses],[200,200],[r.text for r in responses]);self.assertEqual(len({r.json()['order_id'] for r in responses}),1);self.assertEqual(self.db.query(TicketOrder).count(),before+1)
