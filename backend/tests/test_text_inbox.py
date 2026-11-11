import os,unittest
from datetime import datetime,timedelta
from unittest.mock import Mock,patch
from uuid import uuid4
import test_stabilization as support
from app.messaging.inbox import InboxMessage
from app.models import Member,MarketingContact
from twilio.request_validator import RequestValidator

class TextInboxTests(unittest.TestCase):
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.env=patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'ACfixture','TWILIO_AUTH_TOKEN':'inbox-secret','TWILIO_PHONE_NUMBER':'+14055550199','TNG_BACKEND_URL':'https://inbox.example.com'});self.env.start()
 def tearDown(self):self.env.stop();support.StabilizationTests.tearDown(self)
 headers=support.StabilizationTests.headers
 def webhook(self,path='/api/marketing/sms/inbound',**changes):
  form={'AccountSid':'ACfixture','MessageSid':'SM'+'1'*32,'From':'+14055550123','To':'+14055550199','Body':'What are your hours?'};form.update(changes)
  signature=RequestValidator('inbox-secret').compute_signature('https://inbox.example.com'+path,form)
  return self.client.post(path,data=form,headers={'X-Twilio-Signature':signature})
 def reply(self,**changes):
  body={'phone':'+14055550123','message':'We open at five.','request_key':str(uuid4()),'service_reply':True};body.update(changes)
  return body
 def test_verified_inbound_saved_once_and_access_is_restricted(self):
  before=self.db.query(Member).count();self.assertEqual(self.webhook().status_code,200);self.assertEqual(self.webhook().status_code,200)
  self.assertEqual(self.db.query(InboxMessage).count(),1);self.assertEqual(self.db.query(Member).count(),before)
  self.assertEqual(self.client.get('/api/messages').status_code,401)
  self.assertEqual(self.client.get('/api/messages',headers=self.headers('rep')).status_code,403)
  r=self.client.get('/api/messages',headers=self.headers('staff'));self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(r.json()['unread_messages'],1)
  self.assertEqual(self.client.post('/api/marketing/sms/inbound',data={}).status_code,401)
  self.assertEqual(self.webhook(To='+14055550000',MessageSid='SM'+'2'*32).status_code,403)
  self.assertEqual(self.webhook(MessageSid='bad').status_code,400)
 def test_mark_read_cannot_mark_later_or_other_numbers(self):
  self.webhook();first=self.db.query(InboxMessage).one().id
  self.webhook(MessageSid='SM'+'2'*32);self.webhook(MessageSid='SM'+'3'*32,From='+14055550456')
  r=self.client.post('/api/messages/read',headers=self.headers(),json={'phone':'+14055550123','through_id':first});self.assertEqual(r.status_code,200)
  data=self.client.get('/api/messages?unread_only=true',headers=self.headers()).json();self.assertEqual(data['total'],2);self.assertEqual(data['unread_messages'],2)
  self.assertEqual(self.client.get('/api/messages?q=0456',headers=self.headers()).json()['total'],1)
 def test_stop_start_does_not_grant_marketing_consent_or_create_members(self):
  c=MarketingContact(first_name='Test',phone='+14055550123',active=True,sms_opt_in=False);self.db.add(c);self.db.commit()
  self.webhook(Body='STOP');self.db.refresh(c);self.assertTrue(c.sms_unsubscribed)
  with patch('app.messaging.inbox.Client') as provider:
   self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply()).status_code,409);provider.assert_not_called()
  self.webhook(Body='START',MessageSid='SM'+'2'*32);self.db.refresh(c);self.assertFalse(c.sms_opt_in);self.assertFalse(c.sms_unsubscribed)
  self.assertFalse(self.client.get('/api/messages/thread?phone=%2B14055550123',headers=self.headers()).json()['can_reply'])
  self.webhook(MessageSid='SM'+'3'*32)
  self.assertTrue(self.client.get('/api/messages/thread?phone=%2B14055550123',headers=self.headers()).json()['can_reply'])
 def test_reply_requires_context_ack_approved_route_and_idempotency(self):
  self.webhook();payload=self.reply();provider=Mock();provider.messages.create.return_value=Mock(sid='SM'+'9'*32)
  self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json={**payload,'service_reply':False}).status_code,400)
  with patch('app.messaging.inbox.approved_routes',return_value={}):self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json=payload).status_code,409)
  with patch('app.messaging.inbox.approved_routes',return_value={'notification':'MGfixture'}),patch('app.messaging.inbox.Client',return_value=provider):
   r=self.client.post('/api/messages/reply',headers=self.headers(),json=payload);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['message']['status'],'accepted')
   self.assertTrue(self.client.post('/api/messages/reply',headers=self.headers(),json=payload).json()['already_submitted'])
   self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json={**payload,'message':'Different reply'}).status_code,409)
   provider.messages.create.assert_called_once();args=provider.messages.create.call_args.kwargs
   self.assertEqual(args['to'],'+14055550123');self.assertEqual(args['from_'],'+14055550199');self.assertEqual(args['messaging_service_sid'],'MGfixture');self.assertTrue(args['body'].endswith('Reply STOP to unsubscribe.'))
 def test_uncertain_submission_is_never_automatically_replayed(self):
  self.webhook();payload=self.reply();provider=Mock();provider.messages.create.side_effect=TimeoutError()
  with patch('app.messaging.inbox.approved_routes',return_value={'notification':'MGfixture'}),patch('app.messaging.inbox.Client',return_value=provider):
   r=self.client.post('/api/messages/reply',headers=self.headers(),json=payload);self.assertEqual(r.json()['message']['status'],'unknown')
   self.client.post('/api/messages/reply',headers=self.headers(),json=payload);provider.messages.create.assert_called_once()
 def test_signed_delivery_status_and_no_terminal_downgrade(self):
  self.webhook();provider=Mock();provider.messages.create.return_value=Mock(sid='SM'+'9'*32)
  with patch('app.messaging.inbox.approved_routes',return_value={'notification':'MGfixture'}),patch('app.messaging.inbox.Client',return_value=provider):r=self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply())
  row_id=r.json()['message']['id'];path=f'/api/messages/status?message_id={row_id}'
  self.assertEqual(self.webhook(path,MessageSid='SM'+'8'*32,From='+14055550199',To='+14055550123',MessageStatus='delivered').status_code,403)
  self.assertEqual(self.webhook(path,MessageSid='SM'+'9'*32,From='+14055550199',To='+14055550123',MessageStatus='delivered').status_code,204)
  self.webhook(path,MessageSid='SM'+'9'*32,MessageStatus='sent');self.db.expire_all();self.assertEqual(self.db.get(InboxMessage,row_id).status,'delivered')
 def test_expired_context_and_staff_rate_limit_block_sends(self):
  self.webhook();row=self.db.query(InboxMessage).one();row.created_at=datetime.utcnow()-timedelta(days=8);self.db.commit()
  with patch('app.messaging.inbox.Client') as provider:
   self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply()).status_code,409);provider.assert_not_called()
  row.created_at=datetime.utcnow()
  self.db.add_all([InboxMessage(phone='+14055550123',line='+14055550199',direction='outbound',body='fixture',status='accepted',staff_id=self.users['admin'].id) for _ in range(30)]);self.db.commit()
  with patch('app.messaging.inbox.Client') as provider:
   self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply()).status_code,429);provider.assert_not_called()
 def test_media_does_not_fetch_untrusted_urls_and_history_is_paginated(self):
  self.webhook(Body='',NumMedia='1',MediaUrl0='http://127.0.0.1/private')
  row=self.db.query(InboxMessage).one();self.assertEqual(row.media_count,1);self.assertEqual(row.body,'')
  self.db.add_all([InboxMessage(phone=row.phone,line=row.line,direction='inbound',body='fixture',status='received') for _ in range(101)]);self.db.commit()
  data=self.client.get('/api/messages/thread?phone=%2B14055550123',headers=self.headers()).json();self.assertEqual(len(data['messages']),100);self.assertTrue(data['has_more'])
 def test_early_delivery_callback_is_not_downgraded(self):
  self.webhook();provider=Mock()
  def send(**kwargs):
   path=kwargs['status_callback'].replace('https://inbox.example.com','')
   self.assertEqual(self.webhook(path,MessageSid='SM'+'9'*32,From='+14055550199',To='+14055550123',MessageStatus='delivered').status_code,204)
   return Mock(sid='SM'+'9'*32)
  provider.messages.create.side_effect=send
  with patch('app.messaging.inbox.approved_routes',return_value={'notification':'MGfixture'}),patch('app.messaging.inbox.Client',return_value=provider):
   r=self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply());self.assertEqual(r.json()['message']['status'],'delivered')
 def test_provider_optout_error_suppresses_further_replies(self):
  self.webhook();provider=Mock();error=Exception('opted out');error.code=21610;provider.messages.create.side_effect=error
  with patch('app.messaging.inbox.approved_routes',return_value={'notification':'MGfixture'}),patch('app.messaging.inbox.Client',return_value=provider):
   r=self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply());self.assertEqual(r.json()['message']['status'],'failed')
   self.assertEqual(self.client.post('/api/messages/reply',headers=self.headers(),json=self.reply()).status_code,409);provider.messages.create.assert_called_once()
