import os,unittest,json,hashlib
from uuid import uuid4
from unittest.mock import Mock,patch
import test_stabilization as support
from app.amateurs.directory import DirectoryContact
from app.messaging.inbox import InboxMessage
from app.models import Member,User
from app.operations.renewal_reminders import ReminderSmsSuppression

class OfficialWorkTextTests(unittest.TestCase):
 setUpBase=support.StabilizationTests.setUp
 headers=support.StabilizationTests.headers
 def setUp(self):
  self.setUpBase();self.env=patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'ACfixture','TWILIO_AUTH_TOKEN':'fixture-secret','TWILIO_PHONE_NUMBER':'+14055550199'});self.env.start();self.path='/api/amateurs/official-work-texts'
  self.a=DirectoryContact(identity_key='official-a',kind='person',name='Official A',phones=['+14055550123'],emails=['a@example.com'],details={'categories':['official'],'official_affiliation':'Oklahoma LBC 27'},roles=[],role_verified=False,sms_consent=True,consent_note='Agreed to work texts in person')
  self.b=DirectoryContact(identity_key='official-b',kind='person',name='Official B',phones=['+14055550124'],emails=[],details={'categories':['official']},roles=[],role_verified=False,sms_consent=False)
  self.db.add_all([self.a,self.b]);self.db.commit();self.clientMock=Mock();self.clientMock.messages.create.return_value=Mock(sid='SM'+'a'*32)
  self.routes=patch('app.amateurs.work_texts.approved_routes',return_value={'notification':'MGapproved'});self.routes.start();self.provider=patch('app.amateurs.work_texts.Client',return_value=self.clientMock);self.provider.start()
 def tearDown(self):self.provider.stop();self.routes.stop();self.env.stop();support.StabilizationTests.tearDown(self)
 def draft(self,ids=None,text='Can you work our next event?'):return {'contact_ids':ids or[self.a.id],'message':text}
 def preview(self,body=None):return self.client.post(self.path+'/preview',headers=self.headers(),json=body or self.draft())
 def send(self,d=None,**changes):
  d=d or self.draft();p=self.preview(d);self.assertEqual(p.status_code,200,p.text);body={**d,'preview_hash':p.json()['preview_hash'],'request_key':str(uuid4()),'work_related':True,**changes};return self.client.post(self.path+'/send',headers=self.headers(),json=body),body
 def test_private_workspace_only_identified_officials_no_messages_from_reads(self):
  self.assertEqual(self.client.get(self.path).status_code,401)
  for role in ('rep','member','fighter'):self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)
  r=self.client.get(self.path,headers=self.headers('staff'));self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(len(r.json()['contacts']),2);self.assertFalse(r.json()['contacts'][1]['can_text']);self.assertEqual(self.db.query(InboxMessage).count(),0);self.clientMock.messages.create.assert_not_called()
 def test_preview_footer_eligibility_and_no_transmission(self):
  r=self.preview(self.draft([self.a.id,self.b.id]));self.assertEqual(r.status_code,200);d=r.json();self.assertEqual(len(d['recipients']),1);self.assertEqual(d['skipped'][0]['contact_id'],self.b.id);self.assertTrue(d['body'].startswith('LBC 27 Boxing Officials: '));self.assertIn('STOP',d['body']);self.assertEqual(self.db.query(InboxMessage).count(),0);self.clientMock.messages.create.assert_not_called()
 def test_permission_requires_evidence_and_never_verifies_credentials(self):
  path=self.path+f'/contacts/{self.b.id}/permission';body={'opt_in':True,'evidence':'Agreed in person on event day','version':1}
  self.assertEqual(self.client.put(path,headers=self.headers(),json={**body,'evidence':'yes'}).status_code,422);self.assertEqual(self.client.put(path,headers=self.headers(),json=body).status_code,200);self.db.expire_all();self.assertTrue(self.db.get(DirectoryContact,self.b.id).sms_consent);self.assertFalse(self.db.get(DirectoryContact,self.b.id).role_verified);self.assertEqual(self.client.put(path,headers=self.headers(),json=body).status_code,409)
 def test_global_stop_cannot_be_overridden_or_sent(self):
  self.db.add(ReminderSmsSuppression(phone_hash=hashlib.sha256(self.a.phones[0].encode()).hexdigest()));self.db.commit();d=self.preview().json();self.assertEqual(d['recipients'],[])
  r,_=self.send();self.assertEqual(r.status_code,422);self.assertEqual(self.client.put(self.path+f'/contacts/{self.a.id}/permission',headers=self.headers(),json={'opt_in':True,'evidence':'Staff says okay to resume work texts','version':1}).status_code,409);self.clientMock.messages.create.assert_not_called()
 def test_send_uses_existing_inbox_approved_service_and_is_idempotent(self):
  before=self.db.query(Member).count();r,body=self.send();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['messages'][0]['status'],'accepted');self.assertEqual(self.clientMock.messages.create.call_count,1)
  kwargs=self.clientMock.messages.create.call_args.kwargs;self.assertEqual(kwargs['messaging_service_sid'],'MGapproved');self.assertIn('/api/messages/status?message_id=',kwargs['status_callback']);self.assertTrue(kwargs['body'].startswith('LBC 27 Boxing Officials: '));self.assertIn('STOP',kwargs['body'])
  replay=self.client.post(self.path+'/send',headers=self.headers(),json=body);self.assertEqual(replay.status_code,200);self.assertTrue(replay.json()['already_submitted']);self.assertEqual(self.clientMock.messages.create.call_count,1);self.assertEqual(self.db.query(InboxMessage).count(),1);self.assertEqual(self.db.query(Member).count(),before)
  self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json={**body,'message':'Different message'}).status_code,409)
 def test_requires_work_confirmation_and_rejects_stale_preview(self):
  p=self.preview().json();self.a.version+=1;self.db.commit();body={**self.draft(),'preview_hash':p['preview_hash'],'request_key':str(uuid4()),'work_related':True}
  self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json=body).status_code,409);r,_=self.send(work_related=False);self.assertEqual(r.status_code,422);self.clientMock.messages.create.assert_not_called()
 def test_duplicate_phone_only_receives_one_text(self):
  self.b.phones=self.a.phones;self.b.sms_consent=True;self.db.commit();r,_=self.send(self.draft([self.a.id,self.b.id]));self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(r.json()['messages']),1);self.assertEqual(len(r.json()['skipped']),1);self.assertEqual(self.clientMock.messages.create.call_count,1)
 def test_uncertain_submission_is_not_resent_and_halts_unattempted_messages(self):
  self.b.sms_consent=True;self.db.commit();self.clientMock.messages.create.side_effect=TimeoutError('provider uncertain');r,body=self.send(self.draft([self.a.id,self.b.id]));self.assertEqual(r.status_code,200,r.text);self.assertEqual([m['status']for m in r.json()['messages']],['unknown','failed']);self.assertEqual(self.clientMock.messages.create.call_count,1);self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json=body).status_code,200);self.assertEqual(self.clientMock.messages.create.call_count,1)
 def test_history_uses_the_existing_inbox_without_leaking_another_phone(self):
  self.db.add_all([InboxMessage(provider_id='SMone',phone=self.a.phones[0],line='+14055550199',direction='inbound',body='I can work Saturday',status='received'),InboxMessage(provider_id='SMtwo',phone=self.b.phones[0],line='+14055550199',direction='inbound',body='OTHER PRIVATE MESSAGE',status='received')]);self.db.commit();r=self.client.get(self.path+f'/contacts/{self.a.id}/history',headers=self.headers());self.assertEqual(r.status_code,200);self.assertIn('I can work Saturday',r.text);self.assertNotIn('OTHER PRIVATE MESSAGE',r.text)
 def test_unapproved_service_never_creates_submission_records(self):
  with patch('app.amateurs.work_texts.approved_routes',return_value={}):
   r,_=self.send();self.assertEqual(r.status_code,409);self.assertEqual(self.db.query(InboxMessage).count(),0)
  self.clientMock.messages.create.assert_not_called()
 def test_nonofficial_and_missing_phone_are_not_eligible(self):
  c=DirectoryContact(identity_key='not-official',kind='person',name='Athlete only',phones=['+14055550150'],emails=[],details={'categories':['athlete']},sms_consent=True);self.db.add(c);self.a.phones=[];self.db.commit();r=self.preview(self.draft([self.a.id,c.id]));self.assertEqual(r.status_code,200);self.assertEqual(r.json()['recipients'],[]);self.assertEqual(len(r.json()['skipped']),2);self.assertEqual(self.client.get(self.path+f'/contacts/{c.id}/history',headers=self.headers()).status_code,404)
 def test_multiple_eligible_officials_receive_one_message_each(self):
  self.b.sms_consent=True;self.db.commit();self.clientMock.messages.create.side_effect=[Mock(sid='SM'+'a'*32),Mock(sid='SM'+'b'*32)]
  r,_=self.send(self.draft([self.a.id,self.b.id]));self.assertEqual(r.status_code,200,r.text);self.assertEqual([m['status']for m in r.json()['messages']],['accepted','accepted']);self.assertEqual(self.clientMock.messages.create.call_count,2);self.assertEqual(self.db.query(InboxMessage).count(),2)
 def test_add_official_links_existing_identity_without_consent_or_credential_inference(self):
  before=self.db.query(DirectoryContact).count();r=self.client.post(self.path+'/contacts',headers=self.headers(),json={'name':self.a.name,'email':self.a.emails[0],'group':'Oklahoma LBC 27'});self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['created']);self.assertEqual(self.db.query(DirectoryContact).count(),before)
  r=self.client.post(self.path+'/contacts',headers=self.headers(),json={'name':'New Official','phone':'4055550187','group':'Oklahoma LBC 27'});self.assertEqual(r.status_code,200,r.text);c=self.db.get(DirectoryContact,r.json()['contact_id']);self.assertFalse(c.role_verified);self.assertFalse(c.sms_consent);self.assertIn('official',c.details['categories']);self.assertEqual(c.phones,['+14055550187'])
