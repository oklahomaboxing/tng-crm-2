import unittest,hashlib
from uuid import uuid4
from unittest.mock import patch
import test_official_work_texts as support
from app.amateurs.directory import DirectoryContact
from app.messaging.inbox import InboxMessage
from app.models import Member,SecurityLog
from app.operations.renewal_reminders import ReminderSmsSuppression

class ClubWorkTextTests(unittest.TestCase):
 setUpBase=support.OfficialWorkTextTests.setUpBase
 tearDown=support.OfficialWorkTextTests.tearDown
 headers=support.OfficialWorkTextTests.headers
 def setUp(self):
  support.OfficialWorkTextTests.setUp(self)
  self.club=DirectoryContact(identity_key='ok-club',kind='club',name='Example Oklahoma Club',phones=['+14055550555'],emails=[],details={'state':'Oklahoma','contact_name':'Coach Example'},roles=[],role_verified=False,sms_consent=True,consent_note='Agreed to scheduling texts in person')
  self.other=DirectoryContact(identity_key='tx-club',kind='club',name='Example Texas Club',phones=['+12145550555'],details={'state':'TX'},sms_consent=True)
  self.db.add_all([self.club,self.other]);self.db.commit()
 def request(self,suffix='',method='get',body=None):
  return getattr(self.client,method)(self.path+suffix+'?scope=clubs',headers=self.headers(),**({'json':body}if body is not None else{}))
 def draft(self,ids=None):return {'contact_ids':ids or[self.club.id],'message':'Which boxers are available for our next event?'}
 def payload(self,d=None):
  d=d or self.draft();r=self.request('/preview','post',d);self.assertEqual(r.status_code,200,r.text);return{**d,'preview_hash':r.json()['preview_hash'],'request_key':str(uuid4()),'work_related':True}
 def test_workspace_only_oklahoma_clubs_private_and_reads_do_not_send(self):
  r=self.request();self.assertEqual(r.status_code,200);self.assertEqual([c['name']for c in r.json()['contacts']],[self.club.name]);self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(self.db.query(InboxMessage).count(),0)
  self.assertEqual(self.client.get(self.path+'?scope=clubs').status_code,401)
  self.assertEqual(self.client.get(self.path+'?scope=clubs',headers=self.headers('member')).status_code,403);self.clientMock.messages.create.assert_not_called()
 def test_preview_scope_footer_and_no_transmission(self):
  r=self.request('/preview','post',self.draft([self.club.id,self.a.id,self.other.id]));d=r.json();self.assertEqual(len(d['recipients']),1);self.assertEqual(len(d['skipped']),2);self.assertTrue(d['body'].startswith('TNG Boxing clubs:'));self.assertTrue(d['body'].endswith('Reply STOP to unsubscribe.'));self.clientMock.messages.create.assert_not_called()
  self.assertEqual(self.client.post(self.path+'/preview',headers=self.headers(),json=self.draft()).json()['recipients'],[])
 def test_permission_evidence_version_and_directory_scope(self):
  self.club.sms_consent=False;self.db.commit();body={'opt_in':True,'evidence':'Agreed by phone for event logistics','version':self.club.version}
  self.assertEqual(self.request(f'/contacts/{self.club.id}/permission','put',{**body,'evidence':'yes'}).status_code,422)
  self.assertEqual(self.request(f'/contacts/{self.other.id}/permission','put',body).status_code,404)
  self.assertEqual(self.request(f'/contacts/{self.club.id}/permission','put',body).status_code,200);self.assertEqual(self.request(f'/contacts/{self.club.id}/permission','put',body).status_code,409);self.db.expire_all();self.assertFalse(self.db.get(DirectoryContact,self.club.id).role_verified)
 def test_send_reuses_approved_route_callback_and_durable_idempotency(self):
  before=self.db.query(Member).count();body=self.payload();r=self.request('/send','post',body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['messages'][0]['status'],'accepted')
  args=self.clientMock.messages.create.call_args.kwargs;self.assertEqual(args['messaging_service_sid'],'MGapproved');self.assertEqual(args['to'],self.club.phones[0]);self.assertIn('/api/messages/status?message_id=',args['status_callback'])
  self.assertTrue(self.db.query(InboxMessage).one().request_key.startswith('club:'));self.assertEqual(self.db.query(SecurityLog).filter_by(action='CLUB_WORK_SMS_BATCH').count(),1)
  self.assertTrue(self.request('/send','post',body).json()['already_submitted']);self.clientMock.messages.create.assert_called_once();self.assertEqual(self.db.query(Member).count(),before)
  self.assertEqual(self.request('/send','post',{**body,'message':'Different work message'}).status_code,409)
 def test_stop_and_stale_permission_prevent_sending(self):
  body=self.payload();self.club.sms_consent=False;self.club.version+=1;self.db.commit();self.assertEqual(self.request('/send','post',body).status_code,409)
  self.db.add(ReminderSmsSuppression(phone_hash=hashlib.sha256(self.club.phones[0].encode()).hexdigest()));self.db.commit();self.assertEqual(self.request('/preview','post',self.draft()).json()['recipients'],[])
  self.assertEqual(self.request(f'/contacts/{self.club.id}/permission','put',{'opt_in':True,'evidence':'Staff says resume work texts','version':self.club.version}).status_code,409);self.clientMock.messages.create.assert_not_called()
 def test_unknown_provider_submission_not_resent_and_unapproved_route_does_not_record_batch(self):
  body=self.payload()
  with patch('app.amateurs.work_texts.approved_routes',return_value={}):self.assertEqual(self.request('/send','post',body).status_code,409)
  self.assertEqual(self.db.query(InboxMessage).count(),0);self.clientMock.messages.create.side_effect=TimeoutError();r=self.request('/send','post',body);self.assertEqual(r.json()['messages'][0]['status'],'unknown');self.request('/send','post',body);self.clientMock.messages.create.assert_called_once()
 def test_duplicate_club_phone_sends_one_and_appears_in_club_inbox(self):
  duplicate=DirectoryContact(identity_key='second-ok-club',kind='club',name='Second Club',phones=self.club.phones,details={'state':'OK'},sms_consent=True);self.db.add(duplicate);self.db.commit();body=self.payload(self.draft([self.club.id,duplicate.id]));r=self.request('/send','post',body);self.assertEqual(len(r.json()['messages']),1);self.clientMock.messages.create.assert_called_once()
  row=InboxMessage(phone=self.club.phones[0],line='+14055550199',direction='inbound',body='Yes we have boxers',status='received');self.db.add(row);self.db.commit()
  inbox=self.client.get('/api/messages?scope=clubs&q=Oklahoma',headers=self.headers()).json();self.assertEqual(inbox['total'],1);self.assertEqual(inbox['unread_messages'],1);self.assertIn(self.club.name,inbox['conversations'][0]['club_names']);self.assertEqual(self.request(f'/contacts/{self.club.id}/history').json()['messages'][-1]['body'],'Yes we have boxers')
  self.assertEqual(self.request(f'/contacts/{self.other.id}/history').status_code,404)
