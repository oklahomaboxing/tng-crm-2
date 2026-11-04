import json,unittest
from datetime import datetime,timedelta
from unittest.mock import Mock,patch
import test_stabilization as support
from app.models import Member,Sale,User,Attendance
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import TicketOrder,EventSeller,EventTicketType,PaperTicketBatch,PaperTicket
from app.auth import decode_token
from app.auth_sessions import RememberedDevice

class TngAssistantTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers

 def event_data(self):
  event=BoxingEvent(name='Fall Brawl',slug='fall-brawl',event_date='2099-11-14');self.db.add(event);self.db.flush()
  for index,status,qty in [(1,'paid',3),(2,'pending',99),(3,'refunded',20)]:
   self.db.add(TicketOrder(event_id=event.id,buyer_name='PRIVATE BUYER',buyer_email='private@example.com',buyer_phone='4055550199',receipt_number=f'order-{index}',payment_status=status,total_cents=qty*4000,items_json=json.dumps([{'ticket_type_id':1,'quantity':qty}])))
  seller=EventSeller(event_id=event.id,seller_type='staff',seller_ref_id=1,display_name='Seller',public_code='seller');kind=EventTicketType(event_id=event.id,name='GA',price_cents=4000)
  self.db.add_all([seller,kind]);self.db.flush()
  batch=PaperTicketBatch(event_id=event.id,seller_id=seller.id,ticket_type_id=kind.id,quantity=1,price_cents=4000,commission_cents=0,request_key='paper-batch',created_by_user_id=self.users['admin'].id)
  self.db.add(batch);self.db.flush();self.db.add(PaperTicket(batch_id=batch.id,ticket_number='paper-one',qr_token_hash='private-hash',qr_token_encrypted='private-qr',status='released'))
  self.db.add(Member(first_name='Ticket',last_name='Customer',email='ticket@example.com',member_type='CUSTOMER',membership_status='active'));self.db.commit();return event

 def test_snapshot_is_admin_only_and_excludes_private_records(self):
  self.event_data()
  for role in ('staff','member','fighter','rep'):
   self.assertEqual(self.client.get('/api/assistant/snapshot',headers=self.headers(role)).status_code,403)
   self.assertEqual(self.client.post('/api/assistant/ask',headers=self.headers(role),json={'question':'How are we today?'}).status_code,403)
  self.assertEqual(self.client.get('/api/assistant/snapshot').status_code,401)
  r=self.client.get('/api/assistant/snapshot',headers=self.headers());self.assertEqual(r.status_code,200,r.text)
  data=r.json();self.assertEqual(data['members']['active'],1);self.assertEqual(data['tickets']['paid_quantity'],3)
  self.assertEqual(data['tickets']['pending_checkouts'],1);self.assertEqual(data['tickets']['released_paper'],1)
  for secret in ('PRIVATE BUYER','private@example.com','4055550199','private-qr','password_hash'):self.assertNotIn(secret,r.text)
  self.assertIn('no-store',r.headers['cache-control'])

 def test_natural_questions_and_actions_do_not_mutate_operations(self):
  self.event_data();before=(self.db.query(Member).count(),self.db.query(Sale).count(),self.db.query(Attendance).count())
  for question,topic in [('How many active gym members?','members'),('How many tickets sold?','tickets'),('How is the fight card?','card'),('What needs attention?','updates'),('How are we today?','overview'),('Send a text to all members','help')]:
   r=self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':question});self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['topic'],topic)
  self.assertEqual(before,(self.db.query(Member).count(),self.db.query(Sale).count(),self.db.query(Attendance).count()))

 def test_model_can_only_route_topic_never_supply_counts(self):
  self.event_data();mock=Mock();mock.with_options.return_value.chat.completions.create.return_value.choices=[Mock(message=Mock(content='{"topic":"tickets","answer":"999999 sold"}'))]
  with patch('app.ai.assistant.client',mock):
   r=self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'Give me the box office pulse'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['topic'],'tickets');self.assertIn('3 tickets',r.json()['answer']);self.assertNotIn('999999',r.text)

 def test_provider_outage_has_safe_fallback_and_malformed_questions_rejected(self):
  mock=Mock();mock.with_options.side_effect=RuntimeError('provider-private-secret')
  with patch('app.ai.assistant.client',mock):
   r=self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'Something unfamiliar'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['topic'],'help');self.assertNotIn('provider-private-secret',r.text)
  for body in ({'question':' '},{'question':'x'*1601},{'question':'Hi','previous_topic':'delete'}):self.assertEqual(self.client.post('/api/assistant/ask',headers=self.headers(),json=body).status_code,422)

 def test_missing_quantities_are_not_reported_as_exact_sales(self):
  event=self.event_data();order=self.db.query(TicketOrder).filter_by(payment_status='paid').one();order.items_json='not json';self.db.commit()
  r=self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'How many tickets?','event_id':event.id})
  self.assertEqual(r.status_code,200,r.text);self.assertIn('at least 0',r.json()['answer']);self.assertIn('need review',r.json()['answer'])

 def test_rate_limit_is_account_scoped_and_does_not_contact_ai_for_known_questions(self):
  with patch('app.ai.assistant.client') as mock:
   for _ in range(20):self.assertEqual(self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'How many members?'}).status_code,200)
   self.assertEqual(self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'How many members?'}).status_code,429)
   mock.with_options.assert_not_called()

 def test_remembered_session_survives_normal_timeout_but_logout_revokes_it(self):
  r=self.client.post('/api/auth/remember-device',headers=self.headers());self.assertEqual(r.status_code,200,r.text)
  token=r.json()['token'];payload=decode_token(token)
  self.assertTrue(payload['persistent']);self.assertGreater(payload['exp'],(datetime.utcnow()+timedelta(days=365)).timestamp())
  self.assertNotEqual(self.db.query(RememberedDevice).one().token_hash,payload['sid'])
  headers={'Authorization':'Bearer '+token}
  self.assertEqual(self.client.get('/api/me',headers=headers).status_code,200)
  self.assertEqual(self.client.post('/api/auth/logout',headers=headers).status_code,200)
  self.assertEqual(self.client.get('/api/me',headers=headers).status_code,401)

 def test_remembered_session_still_obeys_password_and_role_revocation(self):
  token=self.client.post('/api/auth/remember-device',headers=self.headers()).json()['token']
  self.users['admin'].password_hash='changed-password-hash';self.db.commit()
  self.assertEqual(self.client.get('/api/me',headers={'Authorization':'Bearer '+token}).status_code,401)

 def test_forget_device_revokes_old_token_and_returns_normal_session(self):
  first=self.client.post('/api/auth/remember-device',headers=self.headers()).json()['token']
  r=self.client.post('/api/auth/forget-device',headers={'Authorization':'Bearer '+first});self.assertEqual(r.status_code,200,r.text)
  self.assertFalse(decode_token(r.json()['token']).get('persistent',False))
  self.assertEqual(self.client.get('/api/me',headers={'Authorization':'Bearer '+first}).status_code,401)
  self.assertEqual(self.client.get('/api/me',headers={'Authorization':'Bearer '+r.json()['token']}).status_code,200)

 def test_session_conversion_cannot_rebind_to_a_password_changed_during_request(self):
  from app.auth import create_token
  headers=self.headers()
  def change_before_signing(data,minutes=30,**kwargs):
   self.users['admin'].password_hash='concurrently-reset';self.db.commit()
   return create_token(data,minutes,**kwargs)
  with patch('app.auth_sessions.create_token',side_effect=change_before_signing):
   r=self.client.post('/api/auth/remember-device',headers=headers)
  self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.client.get('/api/me',headers={'Authorization':'Bearer '+r.json()['token']}).status_code,401)

 def test_api_credit_failure_is_visible_without_leaking_provider_details(self):
  class CreditError(Exception):body={'code':'credit_balance_exhausted'}
  mock=Mock();mock.with_options.side_effect=CreditError('secret provider detail')
  with patch('app.ai.assistant.client',mock):
   r=self.client.post('/api/assistant/ask',headers=self.headers(),json={'question':'Tell me the box office pulse'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['engine'],'ai_credits_required')
  self.assertIn('ChatGPT Plus',r.json()['ai_notice']);self.assertNotIn('secret provider detail',r.text)

 def test_password_login_can_remember_device_and_still_requires_mfa(self):
  from app.auth import hash_password
  from app.account_security import AccountSecurity
  self.users['admin'].password_hash=hash_password('TestFixturePass12!');self.db.commit()
  body={'email':self.users['admin'].email,'password':'TestFixturePass12!','remember_device':True}
  r=self.client.post('/api/login',json=body);self.assertEqual(r.status_code,200,r.text)
  self.assertTrue(decode_token(r.json()['token'])['persistent'])
  self.db.add(AccountSecurity(user_id=self.users['admin'].id,generation='initial',mfa_enabled=True));self.db.commit()
  mfa=self.client.post('/api/login',json=body);self.assertEqual(mfa.status_code,200,mfa.text)
  self.assertTrue(mfa.json()['mfa_required']);self.assertNotIn('token',mfa.json())

 def test_login_defaults_to_remembered_but_explicit_timed_login_is_respected(self):
  from app.auth import hash_password
  self.users['admin'].password_hash=hash_password('TestFixturePass12!');self.db.commit()
  body={'email':self.users['admin'].email,'password':'TestFixturePass12!'}
  response=self.client.post('/api/login',json=body);self.assertEqual(response.status_code,200,response.text)
  self.assertTrue(decode_token(response.json()['token'])['persistent'])
  timed=self.client.post('/api/login',json={**body,'remember_device':False});self.assertEqual(timed.status_code,200,timed.text)
  self.assertFalse(decode_token(timed.json()['token']).get('persistent',False))
