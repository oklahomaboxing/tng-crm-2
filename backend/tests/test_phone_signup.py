import json,os,unittest
from unittest.mock import Mock,patch
import test_phone_assistant as support
from app.phone.signup import PhoneSignupLink
from app.phone.tickets import PhoneTicketSmsRoute,claim_rate
from app.phone.routes import PhoneSettings,PhoneConfig
from app.models import Member,Lead,WaiverSubmission,Sale
from app.operations.renewal_reminders import suppress_sms

class PhoneSignupTests(unittest.TestCase):
 setUpBase=support.PhoneAssistantTests.setUp
 tearDown=support.PhoneAssistantTests.tearDown
 webhook=support.PhoneAssistantTests.webhook
 root=support.PhoneAssistantTests.root
 headers=support.PhoneAssistantTests.headers
 def setUp(self):
  self.setUpBase();self.db.add(PhoneTicketSmsRoute(id=1,account_sid='AC-test',from_number='+14055550199',service_sid='MGfixture'));self.db.commit()
 def provider(self):
  p=Mock();p.messages.create.return_value=Mock(sid='SM'+'9'*32);return p
 def test_keypad_offers_registration_waiver_link_only_after_consent(self):
  before=[self.db.query(m).count() for m in (Member,Lead,WaiverSubmission,Sale)]
  p=self.provider()
  with patch('app.phone.signup.Client',return_value=p):
   self.assertIn('registration and waiver',self.webhook('menu',Digits='7').text)
   p.messages.create.assert_not_called()
   r=self.webhook('signup/confirm',Digits='1');self.assertEqual(r.status_code,200);self.assertIn('activated after payment is confirmed',r.text)
   args=p.messages.create.call_args.kwargs
   self.assertIn('https://tngos.tngboxinggym.com/register?source=phone',args['body']);self.assertIn('waiver',args['body']);self.assertTrue(args['body'].endswith('Reply STOP to unsubscribe.'))
   self.assertEqual(args['messaging_service_sid'],'MGfixture');self.assertEqual(args['to'],'+14055550101')
   self.webhook('signup/confirm',Digits='1');self.webhook('menu',Digits='7');p.messages.create.assert_called_once()
  self.assertEqual(before,[self.db.query(m).count() for m in (Member,Lead,WaiverSubmission,Sale)])
  row=self.db.query(PhoneSignupLink).one();self.assertEqual(row.status,'accepted');self.assertIn('pressed 1',row.consent_notice)
  r=self.client.get('/api/phone/admin/calls/'+'CA'+'1'*32,headers=self.headers());self.assertEqual(r.json()['signup_links'][0]['status'],'accepted')
  self.assertEqual(self.root(self.webhook('menu',SpeechResult='I want to join the gym',CallSid='CA'+'2'*32)).find('Gather').attrib['input'],'dtmf')
  self.assertEqual(self.db.query(PhoneSignupLink).count(),1)
 def test_alternate_mobile_and_anonymous_callers_are_supported(self):
  p=self.provider()
  with patch('app.phone.signup.Client',return_value=p):
   self.webhook('menu',Digits='7',From='anonymous');self.assertIn('ten digit',self.webhook('signup/phone',Digits='bad').text)
   self.webhook('signup/phone',Digits='4055550108');self.webhook('signup/confirm',Digits='2');self.webhook('signup/phone',Digits='4055550109');self.webhook('signup/confirm',Digits='1')
   self.assertEqual(p.messages.create.call_args.kwargs['to'],'+14055550109')
 def test_forwarded_business_number_is_never_texted_automatically(self):
  r=self.webhook('menu',Digits='7',From='+14058644496');self.assertIn('ten digit',r.text)
  for _ in range(3):r=self.webhook('signup/phone',Digits='14058644496')
  self.assertEqual(self.root(r).find('Dial/Number').text,'+14059895823')
 def test_optout_disabled_menu_and_unconfigured_route_never_send(self):
  p=self.provider();suppress_sms(self.db,'+14055550101');self.db.commit()
  with patch('app.phone.signup.Client',return_value=p):
   self.webhook('menu',Digits='7');self.assertIn('opted out',self.webhook('signup/confirm',Digits='1').text);p.messages.create.assert_not_called()
   row=self.db.get(PhoneSettings,1);cfg=PhoneConfig(**json.loads(row.settings_json));cfg.signup_links_enabled=False;row.settings_json=json.dumps(cfg.model_dump());self.db.commit()
   self.assertIn('unavailable',self.webhook('menu',Digits='7').text)
   cfg.enabled=False;row.settings_json=json.dumps(cfg.model_dump());self.db.commit()
   self.assertEqual(self.root(self.webhook('signup/confirm',Digits='1')).find('Dial/Number').text,'+14059895823');p.messages.create.assert_not_called()
   cfg.enabled=True;cfg.signup_links_enabled=True;row.settings_json=json.dumps(cfg.model_dump());self.db.delete(self.db.get(PhoneTicketSmsRoute,1));self.db.commit()
   self.assertIn('unavailable',self.webhook('menu',Digits='7').text);p.messages.create.assert_not_called()
 def test_unknown_submission_is_not_replayed(self):
  p=self.provider();p.messages.create.side_effect=TimeoutError()
  with patch('app.phone.signup.Client',return_value=p):
   self.webhook('menu',Digits='7');self.webhook('signup/confirm',Digits='1');self.webhook('signup/confirm',Digits='1');p.messages.create.assert_called_once()
  self.assertEqual(self.db.query(PhoneSignupLink).one().status,'unknown')
 def test_shared_ticket_and_signup_rate_limit(self):
  self.assertTrue(claim_rate(self.db,'+14055550101'));self.assertTrue(claim_rate(self.db,'+14055550101'));self.db.commit();p=self.provider()
  with patch('app.phone.signup.Client',return_value=p):
   self.webhook('menu',Digits='7');self.webhook('signup/confirm',Digits='1')
   self.webhook('menu',Digits='7',CallSid='CA'+'2'*32);r=self.webhook('signup/confirm',Digits='1',CallSid='CA'+'2'*32)
   self.assertIn('Too many',r.text);p.messages.create.assert_called_once()
 def test_signed_delivery_callback_and_early_terminal_status(self):
  p=self.provider()
  def send(**kw):
   path=kw['status_callback'].replace('https://voice.example.com/api/phone/','')
   r=self.webhook(path,MessageSid='SM'+'9'*32,To='+14055550101',From='+14055550199',MessageStatus='delivered');self.assertEqual(r.status_code,204)
   return Mock(sid='SM'+'9'*32)
  p.messages.create.side_effect=send
  with patch('app.phone.signup.Client',return_value=p):self.webhook('menu',Digits='7');self.webhook('signup/confirm',Digits='1')
  self.db.expire_all();self.assertEqual(self.db.query(PhoneSignupLink).one().status,'delivered')
  path='signup/status?call_sid=CA'+'1'*32
  self.assertEqual(self.webhook(path,MessageSid='SM'+'8'*32,MessageStatus='sent').status_code,403)
  self.assertEqual(self.client.post('/api/phone/'+path,data={}).status_code,401)
  self.webhook(path,MessageSid='SM'+'9'*32,MessageStatus='sent');self.db.expire_all();self.assertEqual(self.db.query(PhoneSignupLink).one().status,'delivered')
 def test_silence_is_bounded_and_staff_remains_available(self):
  self.webhook('menu',Digits='7')
  for _ in range(3):r=self.webhook('signup/confirm')
  self.assertEqual(self.root(r).find('Dial/Number').text,'+14059895823')

 def test_provider_optout_error_blocks_future_signup_texts(self):
  p=self.provider();error=Exception('optout');error.code=21610;p.messages.create.side_effect=error
  with patch('app.phone.signup.Client',return_value=p):
   self.webhook('menu',Digits='7');self.webhook('signup/confirm',Digits='1')
   self.webhook('menu',Digits='7',CallSid='CA'+'2'*32);r=self.webhook('signup/confirm',Digits='1',CallSid='CA'+'2'*32)
   self.assertIn('opted out',r.text);p.messages.create.assert_called_once()
