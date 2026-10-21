import os,time,json,unittest
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import MarketingContact,MarketingCampaign,Member
from app.marketing.models import SmsDelivery
from twilio.request_validator import RequestValidator

class MarketingTests(unittest.TestCase):
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.environment=patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'ACfixture','TWILIO_AUTH_TOKEN':'fixture-token','TWILIO_PHONE_NUMBER':'+16512390916'});self.environment.start()
 def tearDown(self):
  self.environment.stop();support.StabilizationTests.tearDown(self)
 headers=support.StabilizationTests.headers
 def contact(self,**changes):
  row=MarketingContact(first_name='Member',phone='+16512390916',active=True,sms_opt_in=True,**changes);self.db.add(row);self.db.commit();return row
 def campaign(self,ids,purpose='notification'):
  r=self.client.post('/api/marketing/campaigns',headers=self.headers(),json={'name':'Test member notice','campaign_type':'sms','message':'Your member update','contact_ids':ids,'sms_purpose':purpose});self.assertEqual(r.status_code,200,r.text);return r.json()['campaign']['id']
 def test_no_credentials_or_bad_provider_returns_labeled_template(self):
  r=self.client.post('/api/marketing/generate',headers=self.headers(),json={'prompt':'Youth boxing classes'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['generation_source'],'template');self.assertTrue(r.json()['sms'])
  with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture'}),patch('app.main.client',Mock(with_options=Mock(side_effect=RuntimeError('quota unavailable')))):
   r=self.client.post('/api/marketing/generate',headers=self.headers(),json={'prompt':'Adult boxing'})
   self.assertEqual(r.json()['generation_source'],'template')
 def test_structured_ai_response_and_empty_prompt(self):
  fields={'subject':'Title','email':'Email copy','sms':'TNG Boxing notice','social':'Social copy'};response=Mock();response.choices=[Mock(message=Mock(content=json.dumps(fields)))];configured=Mock();configured.chat.completions.create.return_value=response
  with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture'}),patch('app.main.client',Mock(with_options=Mock(return_value=configured))):
   r=self.client.post('/api/marketing/generate',headers=self.headers(),json={'prompt':'A gym schedule notice'})
   self.assertEqual(r.json()['generation_source'],'ai')
  self.assertEqual(self.client.post('/api/marketing/generate',headers=self.headers(),json={'prompt':' '}).status_code,400)
 def test_consent_and_optout_filtering(self):
  valid=self.contact();other=self.contact(email='other@example.com');other.sms_opt_in=False;self.db.commit();campaign=self.campaign([valid.id,other.id])
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}):
   r=self.client.get(f'/api/marketing/sms/campaigns/{campaign}/preview',headers=self.headers());self.assertEqual(r.json()['eligible_count'],1);self.assertEqual(r.json()['skipped']['no_consent'],1)
 def test_send_only_once_and_actual_callback_delivery(self):
  c=self.contact();campaign=self.campaign([c.id]);provider=Mock();provider.messages.create.return_value=Mock(sid='SMfixture')
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}),patch('app.marketing.sms.Client',return_value=provider):
   r=self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['sent_count'],1)
   self.assertEqual(self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers()).status_code,409);provider.messages.create.assert_called_once()
  row=self.db.query(SmsDelivery).one();self.assertEqual(row.status,'accepted')
  form={'AccountSid':'ACfixture','MessageSid':'SMfixture','MessageStatus':'delivered'};path=f'/api/marketing/sms/status?delivery_id={row.id}'
  with patch.dict(os.environ,{'TWILIO_AUTH_TOKEN':'fixture-token','TWILIO_ACCOUNT_SID':'ACfixture'}):
   signature=RequestValidator('fixture-token').compute_signature('https://sea-lion-app-2-gxyfr.ondigitalocean.app'+path,form)
   self.assertEqual(self.client.post(path,data=form,headers={'X-Twilio-Signature':signature}).status_code,200)
  self.db.refresh(row);self.assertEqual(row.status,'delivered');self.db.refresh(self.db.get(MarketingCampaign,campaign));self.assertEqual(self.db.get(MarketingCampaign,campaign).delivered_count,1)
 def test_duplicate_phones_and_uncertain_submission_never_replayed(self):
  one=self.contact();two=self.contact(email='same-phone@example.com');campaign=self.campaign([one.id,two.id]);provider=Mock();provider.messages.create.side_effect=TimeoutError()
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}),patch('app.marketing.sms.Client',return_value=provider):
   preview=self.client.get(f'/api/marketing/sms/campaigns/{campaign}/preview',headers=self.headers()).json();self.assertEqual(preview['eligible_count'],1);self.assertEqual(preview['skipped']['duplicate_phone'],1)
   r=self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers());self.assertEqual(r.status_code,200);self.assertEqual(r.json()['failed_count'],1)
   self.assertEqual(self.db.query(SmsDelivery).one().status,'unknown')
   self.assertEqual(self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers()).status_code,409);provider.messages.create.assert_called_once()
 def test_unapproved_promotions_never_call_provider(self):
  c=self.contact();campaign=self.campaign([c.id],'promotion')
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}),patch('app.marketing.sms.Client') as provider:
   self.assertEqual(self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers()).status_code,409);provider.assert_not_called()
 def test_stop_start_and_forged_webhooks(self):
  c=self.contact();path='/api/marketing/sms/inbound';form={'AccountSid':'ACfixture','From':c.phone,'Body':'STOP'}
  self.assertEqual(self.client.post(path,data=form).status_code,401)
  with patch.dict(os.environ,{'TWILIO_AUTH_TOKEN':'fixture-token','TWILIO_ACCOUNT_SID':'ACfixture'}):
   for body in ['STOP','START']:
    form['Body']=body;signature=RequestValidator('fixture-token').compute_signature('https://sea-lion-app-2-gxyfr.ondigitalocean.app'+path,form);self.assertEqual(self.client.post(path,data=form,headers={'X-Twilio-Signature':signature}).status_code,200)
    self.db.refresh(c);self.assertFalse(c.sms_opt_in);self.assertEqual(c.sms_unsubscribed,body=='STOP')
 def test_consent_requires_evidence_and_cannot_override_stop(self):
  c=self.contact();c.sms_opt_in=False;self.db.commit();path=f'/api/marketing/sms/contacts/{c.id}/consent'
  self.assertEqual(self.client.post(path,headers=self.headers(),json={'opt_in':True}).status_code,400)
  self.assertEqual(self.client.post(path,headers=self.headers(),json={'opt_in':True,'evidence':'Signed SMS consent form on file'}).status_code,200)
  c.sms_unsubscribed=True;self.db.commit();self.assertEqual(self.client.post(path,headers=self.headers(),json={'opt_in':True,'evidence':'Signed SMS consent form on file'}).status_code,409)
 def test_member_audience_excludes_retail_customer(self):
  c=self.contact();self.member.phone=c.phone;self.db.commit()
  r=self.client.get('/api/marketing/sms/member-audience',headers=self.headers());self.assertEqual(r.json()['contact_ids'],[c.id])
 def test_sync_does_not_transfer_consent_to_a_new_number(self):
  c=self.contact(email=self.member.email);self.member.phone='+15555550123';self.db.commit()
  r=self.client.post('/api/marketing/sync-audiences',headers=self.headers());self.assertEqual(r.status_code,200,r.text)
  self.db.refresh(c);self.assertFalse(c.sms_opt_in)
 def test_permissions_and_invalid_number_do_not_send(self):
  self.assertEqual(self.client.get('/api/marketing/sms/readiness',headers=self.headers('member')).status_code,403)
  c=self.contact();c.phone='not-a-number';self.db.commit();campaign=self.campaign([c.id])
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}),patch('app.marketing.sms.Client') as provider:
   self.assertEqual(self.client.post(f'/api/marketing/campaigns/{campaign}/send',headers=self.headers()).status_code,400);provider.assert_not_called()

if __name__=='__main__':unittest.main()
