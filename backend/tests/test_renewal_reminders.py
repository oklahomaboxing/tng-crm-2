import os,unittest
from datetime import datetime,timedelta,date
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import Member,MarketingContact,Lead,WaiverSubmission,Sale
from app.operations.renewal_reminders import ReminderSettings,RenewalReminder,ReminderSmsSuppression,plan,enqueue,process,expiry,suppress_sms

class RenewalReminderTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 now=datetime(2026,11,3,16) # 10 AM Central after DST ends.

 def due(self,consent=True):
  self.member.phone='4055550100';self.member.membership_start=self.now-timedelta(days=25);self.member.membership_end=self.now+timedelta(days=5)
  contact=MarketingContact(first_name=self.member.first_name,last_name=self.member.last_name,email=self.member.email,phone=self.member.phone,sms_opt_in=consent,active=True)
  self.db.add(contact);self.db.commit();return contact

 def send(self,now=None):
  with patch.dict(os.environ,{'RESEND_API_KEY':'test-only','TWILIO_ACCOUNT_SID':'test-account','TWILIO_AUTH_TOKEN':'test-secret','TWILIO_PHONE_NUMBER':'+14055550199'}),patch('resend.Emails.send',return_value={'id':'email-accepted'}) as email,patch('app.marketing.sms.approved_routes',return_value={'notification':'verified-service'}),patch('twilio.rest.Client') as twilio:
   twilio.return_value.messages.create.return_value.sid='sms-accepted'
   result=process(self.db,now or self.now)
  return result,email,twilio

 def test_five_day_email_sms_once_per_period_and_no_billing_mutation(self):
  self.due();before=self.db.query(Sale).count()
  result,email,twilio=self.send();self.assertEqual(result['submitted'],2);email.assert_called_once();twilio.return_value.messages.create.assert_called_once()
  result,email,twilio=self.send();self.assertEqual(result['submitted'],0);email.assert_not_called();twilio.return_value.messages.create.assert_not_called()
  self.assertEqual(self.db.query(Sale).count(),before);self.assertEqual(self.db.query(RenewalReminder).count(),2)

 def test_ticket_customers_inactive_and_missing_identity_excluded(self):
  self.due();self.member.member_type='CUSTOMER';self.db.commit();self.assertEqual(plan(self.db,self.now),[])
  self.member.member_type='MEMBER';self.member.membership_status='inactive';self.db.commit();self.assertEqual(plan(self.db,self.now),[])
  self.member.membership_status='active';self.member.email='';self.db.commit();self.assertEqual(plan(self.db,self.now),[])

 def test_sms_requires_documented_consent_and_respects_stop(self):
  contact=self.due(False)
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'],'no_sms_consent')
  contact.sms_opt_in=True;contact.sms_unsubscribed=True;self.db.commit()
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'],'sms_opted_out')
  contact.sms_unsubscribed=False;suppress_sms(self.db,'+14055550100');self.db.commit()
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'],'sms_opted_out')

 def test_renewal_after_queue_cancels_old_term_messages(self):
  self.due();self.assertEqual(enqueue(self.db,self.now),2)
  self.member.membership_end+=timedelta(days=30);self.db.commit()
  result,email,twilio=self.send();email.assert_not_called();twilio.return_value.messages.create.assert_not_called()
  self.assertTrue(all(r.status=='cancelled' for r in self.db.query(RenewalReminder)))

 def test_quiet_hours_queue_without_sending_and_catch_up_next_day(self):
  self.due();result,email,twilio=self.send(datetime(2026,11,4,1)) # 7 PM previous Central day.
  self.assertTrue(result['quiet_hours']);email.assert_not_called();twilio.return_value.messages.create.assert_not_called()
  result,email,twilio=self.send(self.now+timedelta(days=1));self.assertEqual(result['submitted'],2)
  self.assertIn('November 08, 2026',email.call_args.args[0]['text'])

 def test_one_day_followup_off_by_default_and_once_when_enabled(self):
  self.due();self.send();self.assertEqual(self.send(self.now+timedelta(days=4))[0]['submitted'],0)
  self.db.add(ReminderSettings(id=1,enabled=True,email_enabled=True,sms_enabled=True,five_day=True,one_day=True));self.db.commit()
  self.assertEqual(self.send(self.now+timedelta(days=4))[0]['submitted'],2)
  self.assertEqual(self.send(self.now+timedelta(days=4))[0]['submitted'],0)

 def test_unknown_provider_result_not_automatically_retried(self):
  self.due(False)
  with patch.dict(os.environ,{'RESEND_API_KEY':'test'}),patch('resend.Emails.send',side_effect=TimeoutError('private provider detail')) as email:
   process(self.db,self.now);process(self.db,self.now+timedelta(minutes=10));self.assertEqual(email.call_count,1)
  record=self.db.query(RenewalReminder).one();self.assertEqual(record.status,'unknown');self.assertNotIn('private',record.reason)

 def test_shared_contacts_skipped_and_opted_out_email_suppressed(self):
  contact=self.due();self.db.add(Member(first_name='Other',last_name='Person',email=self.member.email,phone=self.member.phone,member_type='CUSTOMER'));self.db.commit()
  rows=plan(self.db,self.now);self.assertTrue(all(i['reason'] in ('shared_email_review','shared_phone_review') for i in rows))
  self.db.query(Member).filter(Member.id!=self.member.id).delete();contact.email_unsubscribed=True;self.db.commit()
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='email')['reason'],'email_opted_out')

 def test_settings_and_preview_are_admin_only_and_preview_does_not_send(self):
  self.due()
  for role in ('staff','member','fighter','rep'):
   self.assertEqual(self.client.get('/api/renewal-reminders',headers=self.headers(role)).status_code,403)
  with patch('app.operations.renewal_reminders.utcnow',return_value=self.now):
   r=self.client.get('/api/renewal-reminders',headers=self.headers())
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(r.json()['preview']),2)
  self.assertEqual(self.db.query(RenewalReminder).count(),0);self.assertNotIn('recipient',r.text);self.assertNotIn(self.member.phone,r.text)
  self.assertEqual(self.client.put('/api/renewal-reminders',headers=self.headers(),json={'enabled':False}).status_code,200)
  self.assertEqual(plan(self.db,self.now),[])

 def test_sms_callbacks_are_authenticated(self):
  self.assertEqual(self.client.post('/api/renewal-reminders/sms-status?delivery_id=1',data={'MessageStatus':'delivered'}).status_code,401)

 def test_sms_callback_before_submission_response_is_not_downgraded(self):
  self.due();self.db.add(ReminderSettings(id=1,enabled=True,email_enabled=False,sms_enabled=True,five_day=True,one_day=False));self.db.commit()
  def accepted(**kwargs):
   row=self.db.query(RenewalReminder).one();row.status='delivered';row.provider_id='sms-accepted';self.db.commit();return Mock(sid='sms-accepted')
  with patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'test','TWILIO_AUTH_TOKEN':'test','TWILIO_PHONE_NUMBER':'+14055550199'}),patch('app.marketing.sms.approved_routes',return_value={'notification':'service'}),patch('twilio.rest.Client') as twilio:
   twilio.return_value.messages.create.side_effect=accepted;process(self.db,self.now)
  self.assertEqual(self.db.query(RenewalReminder).one().status,'delivered')

 def test_merging_profiles_with_queued_reminders_retains_one_click_merge(self):
  self.due(False);end=self.member.membership_end
  source=Member(first_name='Test',last_name='Member',email='other@example.com',phone='4055550133',member_type='MEMBER',membership_status='active',membership_start=self.member.membership_start,membership_end=end,membership_type='Monthly')
  self.db.add(source);self.db.commit();enqueue(self.db,self.now);source.phone=self.member.phone;self.db.commit();source_id=source.id
  r=self.client.post('/api/duplicates/members/merge',headers=self.headers(),json={'keep_id':self.member.id,'merge_id':source_id})
  self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
  self.assertEqual({r.member_id for r in self.db.query(RenewalReminder)}, {self.member.id})
  self.assertEqual(self.send()[0]['submitted'],1)

 def waiver(self,consent):
  lead=Lead(first_name='Test',last_name='Member',email=self.member.email,phone=self.member.phone);self.db.add(lead);self.db.flush()
  waiver=WaiverSubmission(submission_uuid=__import__('uuid').uuid4().hex,lead_id=lead.id,participant_first_name='Test',participant_last_name='Member',participant_date_of_birth=date(2000,1,1),emergency_contact_name='Fixture',emergency_contact_phone='4055550100',waiver_version='v1',waiver_text_snapshot='Fixture waiver',signature_name='Test Member',waiver_accepted=True,medical_acknowledgment=True,sms_consent=consent,sms_consent_at=self.now if consent else None,sms_disclosure_version='v1' if consent else None)
  self.db.add(waiver);self.db.commit()

 def test_latest_waiver_refusal_is_not_overridden_by_marketing_optin(self):
  self.due(True);self.waiver(False)
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'],'no_sms_consent')

 def test_stop_without_marketing_contact_still_suppresses_waiver_consent(self):
  from unittest.mock import AsyncMock
  self.due(False);self.db.query(MarketingContact).delete();self.db.commit();self.waiver(True)
  self.assertIsNone(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'])
  with patch('app.marketing.sms.validate_webhook',new=AsyncMock(return_value={'From':'+14055550100','Body':'STOP'})):
   r=self.client.post('/api/marketing/sms/inbound',data={})
  self.assertEqual(r.status_code,200,r.text);self.db.expire_all()
  self.assertEqual(next(i for i in plan(self.db,self.now) if i['channel']=='sms')['reason'],'sms_opted_out')

 def test_disabled_channel_can_resume_unsent_queue(self):
  self.due(False);enqueue(self.db,self.now)
  self.db.add(ReminderSettings(id=1,enabled=True,email_enabled=False,sms_enabled=False,five_day=True,one_day=False));self.db.commit()
  self.send();self.assertEqual(self.db.query(RenewalReminder).one().status,'cancelled')
  cfg=self.db.get(ReminderSettings,1);cfg.email_enabled=True;self.db.commit()
  self.assertEqual(self.send()[0]['submitted'],1)

 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_concurrent_workers_submit_each_channel_once(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.database import SessionLocal
  self.due(False);gate=Barrier(2)
  def run(_):
   gate.wait()
   with SessionLocal() as db:return process(db,self.now)
  with patch.dict(os.environ,{'RESEND_API_KEY':'test'}),patch('resend.Emails.send',return_value={'id':'accepted-once'}) as email:
   with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
  self.assertEqual(email.call_count,1);self.assertEqual(sum(r['submitted'] for r in results),1)

 def test_expired_notice_sms_only_once_and_no_old_expired_blast(self):
  self.due();self.member.membership_end=self.now-timedelta(hours=1);self.db.commit()
  rows=plan(self.db,self.now);self.assertEqual([(r['channel'],r['lead_days']) for r in rows],[('sms',0)])
  result,email,twilio=self.send();self.assertEqual(result['submitted'],1);email.assert_not_called()
  self.assertIn('membership period ended',twilio.return_value.messages.create.call_args.kwargs['body'])
  self.assertEqual(self.send()[0]['submitted'],0)
  self.member.membership_end=self.now-timedelta(days=30);self.db.commit();self.assertEqual(plan(self.db,self.now),[])

 def test_expired_notice_cancelled_on_renewal_and_inactive_excluded(self):
  self.due();self.member.membership_end=self.now-timedelta(hours=1);self.db.commit();self.assertEqual(enqueue(self.db,self.now),1)
  self.member.membership_end=self.now+timedelta(days=30);self.db.commit();result,email,twilio=self.send();self.assertEqual(result['submitted'],0)
  self.assertEqual(self.db.query(RenewalReminder).one().status,'cancelled')
  self.member.membership_end=self.now-timedelta(hours=1);self.member.membership_status='inactive';self.db.commit();self.assertEqual(plan(self.db,self.now),[])

 def test_expired_settings_can_be_disabled_and_persisted(self):
  self.due();self.member.membership_end=self.now-timedelta(hours=1);self.db.commit()
  r=self.client.put('/api/renewal-reminders',headers=self.headers(),json={'expired_sms':False});self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(plan(self.db,self.now),[])
  overview=self.client.get('/api/renewal-reminders',headers=self.headers());self.assertFalse(overview.json()['settings']['expired_sms'])
