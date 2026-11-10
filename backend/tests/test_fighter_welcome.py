import unittest
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.models import BoxingEvent,BoxingEventPublication,BoxingFighter,BoxingBout
from app.matchmaker.welcome_letter import FighterWelcomeDelivery

class FighterWelcomeTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers

    def card(self):
        e=BoxingEvent(name='Welcome Test',slug='welcome-test',event_date='2026-11-14',venue='TNG Boxing',venue_address='8416 NW Expressway, Oklahoma City, OK 73162')
        self.db.add(e);self.db.flush();self.event=e
        self.db.add(BoxingEventPublication(event_id=e.id,doors_time='17:00',first_bout_time='18:00'))
        a=BoxingFighter(legal_name='Red Example',email='team@example.com')
        b=BoxingFighter(legal_name='Blue Example',email='TEAM@example.com')
        c=BoxingFighter(legal_name='Cancelled Example',email='cancelled@example.com')
        self.db.add_all([a,b,c]);self.db.flush()
        self.db.add_all([BoxingBout(event_id=e.id,red_fighter_id=a.id,blue_fighter_id=b.id,status='draft'),BoxingBout(event_id=e.id,red_fighter_id=a.id,blue_fighter_id=c.id,status='cancelled')])
        self.db.commit();return f'/api/boxing/events/{e.id}/fighter-welcome'

    def settings(self):
        return {'weigh_in_datetime':'Friday, November 13, 2026 at 5:00 PM','weigh_in_location':'TNG Boxing, 8416 NW Expressway, Oklahoma City, OK 73162','fighter_arrival':'Saturday, November 14, 2026 at 3:30 PM; no later than 4:00 PM'}

    def test_draft_has_known_event_times_and_blocks_unconfirmed_schedule(self):
        path=self.card()
        r=self.client.get(path,headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()['recipients']),1)
        self.assertIn('5:00 PM',r.json()['text'])
        self.assertIn('6:00 PM',r.json()['text'])
        self.assertEqual(len(r.json()['missing_fields']),3)
        with patch('resend.Emails.send') as provider:
            r=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':r.json()['preview_hash']})
            self.assertEqual(r.status_code,409)
            provider.assert_not_called()
        pdf=self.client.get(path+'.pdf',headers=self.headers())
        self.assertEqual(pdf.status_code,200)
        self.assertTrue(pdf.content.startswith(b'%PDF-'))

    def test_save_pdf_and_one_email_per_unique_booked_address_with_attachment(self):
        path=self.card()
        r=self.client.put(path,headers=self.headers(),json=self.settings())
        self.assertEqual(r.status_code,200,r.text)
        body=r.json()
        self.assertEqual(body['missing_fields'],[])
        self.assertIn('no later than 4:00 PM',body['text'])
        self.assertEqual(r.headers['cache-control'],'private, no-store')
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('resend.Emails.send',return_value={'id':'test-provider-id'}) as provider:
            sent=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':body['preview_hash']})
            self.assertEqual(sent.status_code,200,sent.text)
            self.assertEqual(sent.json()['accepted'],1)
            self.assertEqual(provider.call_count,1)
            payload=provider.call_args.args[0]
            self.assertEqual(payload['to'],['team@example.com'])
            self.assertTrue(payload['attachments'][0]['content'])
            self.assertNotIn('cancelled@example.com',str(payload))
            again=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':body['preview_hash']})
            self.assertEqual(again.json()['already_submitted'],1)
            self.assertEqual(provider.call_count,1)
        self.assertEqual(self.db.query(FighterWelcomeDelivery).count(),1)

    def test_stale_preview_and_roles_cannot_send(self):
        path=self.card()
        old=self.client.get(path,headers=self.headers()).json()
        self.client.put(path,headers=self.headers(),json=self.settings())
        with patch('resend.Emails.send') as provider:
            self.assertEqual(self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':old['preview_hash']}).status_code,409)
            for role in ('member','fighter','rep'):
                self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
                self.assertEqual(self.client.get(path+'.pdf',headers=self.headers(role)).status_code,403)
                self.assertEqual(self.client.put(path,headers=self.headers(role),json=self.settings()).status_code,403)
                self.assertEqual(self.client.post(path+'/send',headers=self.headers(role),json={'preview_hash':old['preview_hash']}).status_code,403)
            provider.assert_not_called()

    def test_uncertain_provider_result_is_not_replayed(self):
        path=self.card()
        data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('resend.Emails.send',side_effect=TimeoutError) as provider:
            sent=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(sent.json()['needs_review'],1)
            again=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(again.json()['needs_review'],1)
            self.assertEqual(provider.call_count,1)

    def test_marketing_sender_and_explicit_retry_reuse_exact_payload_and_key(self):
        path=self.card()
        data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only','RESEND_FROM_EMAIL':'Old <noreply@example.com>'}),patch('app.matchmaker.welcome_letter.time.sleep'),patch('resend.Emails.send',side_effect=[TimeoutError(),{'id':'recovered-provider-id'}]) as provider:
            first=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(first.json()['needs_review'],1)
            payload=provider.call_args_list[0].args[0]
            self.assertEqual(payload['from'],'TNG Promotions <marketing@tngboxinggym.com>')
            self.assertEqual(payload['reply_to'],'marketing@tngboxinggym.com')
            retry=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash'],'retry_unconfirmed':True})
            self.assertEqual(retry.json()['accepted'],1,retry.text)
            self.assertEqual(provider.call_args_list[0],provider.call_args_list[1])
            final=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash'],'retry_unconfirmed':True})
            self.assertEqual(final.json()['already_submitted'],1)
            self.assertEqual(provider.call_count,2)

    def test_expired_unknown_submission_is_never_replayed(self):
        from datetime import datetime,timedelta
        path=self.card()
        data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        self.db.add(FighterWelcomeDelivery(event_id=self.event.id,content_hash=data['content_hash'],recipient='team@example.com',status='unknown',created_at=datetime.utcnow()-timedelta(hours=25)))
        self.db.commit()
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('resend.Emails.send') as provider:
            retry=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash'],'retry_unconfirmed':True})
            self.assertEqual(retry.json()['needs_review'],1)
            provider.assert_not_called()

    def test_connected_microsoft_routes_new_welcome_without_resend(self):
        from app.mail.microsoft365 import MicrosoftMailbox,encrypt
        from datetime import datetime,timedelta
        path=self.card()
        self.db.add(MicrosoftMailbox(id=1,tenant_id='11111111-1111-1111-1111-111111111111',client_id='22222222-2222-2222-2222-222222222222',client_secret=encrypt('secret'),refresh_token=encrypt('refresh'),access_token=encrypt('access'),expires_at=datetime.utcnow()+timedelta(hours=1),mailbox='marketing@tngboxinggym.com',enabled=True,generation=1));self.db.commit()
        data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        self.assertEqual(data['email_provider'],'microsoft365')
        with patch.dict('os.environ',{'RESEND_API_KEY':''}),patch('app.matchmaker.welcome_letter.time.sleep'),patch('app.mail.microsoft365.send_welcome',return_value={'id':'microsoft365:test-request'}) as microsoft,patch('resend.Emails.send') as resend:
            result=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['accepted'],1)
            microsoft.assert_called_once();resend.assert_not_called()

    def connect_microsoft(self):
        from app.mail.microsoft365 import MicrosoftMailbox,encrypt
        from datetime import datetime,timedelta
        self.db.add(MicrosoftMailbox(id=1,tenant_id='11111111-1111-1111-1111-111111111111',client_id='22222222-2222-2222-2222-222222222222',client_secret=encrypt('secret'),refresh_token=encrypt('refresh'),access_token=encrypt('access'),expires_at=datetime.utcnow()+timedelta(hours=1),mailbox='marketing@tngboxinggym.com',enabled=True,generation=1));self.db.commit()

    def test_explicit_move_of_rejected_resend_to_microsoft_preserves_history(self):
        from app.matchmaker.welcome_letter import FighterWelcomeProviderHistory,FighterWelcomeSubmission
        import json
        path=self.card();data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        failure=RuntimeError('Rate limit');failure.code='429'
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('app.matchmaker.welcome_letter.time.sleep'),patch('resend.Emails.send',side_effect=failure):
            rejected=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(rejected.json()['needs_review'],1)
        self.connect_microsoft()
        preview=self.client.get(path,headers=self.headers()).json()
        self.assertEqual(preview['rejected_resend'],1)
        with patch('app.matchmaker.welcome_letter.time.sleep'),patch('app.mail.microsoft365.send_welcome',return_value={'id':'microsoft365:confirmed'}) as microsoft,patch('resend.Emails.send') as resend:
            moved=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':preview['preview_hash'],'use_microsoft_for_rejected':True})
            self.assertEqual(moved.json()['accepted'],1,moved.text)
            microsoft.assert_called_once();resend.assert_not_called()
            repeated=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':preview['preview_hash'],'use_microsoft_for_rejected':True})
            self.assertEqual(repeated.json()['already_submitted'],1)
            self.assertEqual(microsoft.call_count,1)
        self.assertEqual(self.db.query(FighterWelcomeProviderHistory).count(),1)
        history=self.db.query(FighterWelcomeProviderHistory).one()
        self.assertEqual(history.previous_error_code,'429')
        self.assertEqual(json.loads(history.previous_payload_json)['_tng_provider'],'resend')
        self.assertEqual(json.loads(self.db.query(FighterWelcomeSubmission).one().payload_json)['_tng_provider'],'microsoft365')

    def test_microsoft_move_does_not_send_unknown_or_never_attempted_emails(self):
        path=self.card();data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        self.connect_microsoft()
        with patch('app.mail.microsoft365.send_welcome') as microsoft,patch('resend.Emails.send') as resend:
            request={'preview_hash':data['preview_hash'],'use_microsoft_for_rejected':True}
            new=self.client.post(path+'/send',headers=self.headers(),json=request)
            self.assertEqual(new.json()['accepted'],0)
            self.assertEqual(self.db.query(FighterWelcomeDelivery).count(),0)
            self.db.add(FighterWelcomeDelivery(event_id=self.event.id,content_hash=data['content_hash'],recipient='team@example.com',status='unknown'));self.db.commit()
            unknown=self.client.post(path+'/send',headers=self.headers(),json=request)
            self.assertEqual(unknown.json()['needs_review'],1)
            microsoft.assert_not_called();resend.assert_not_called()

    def test_additional_recipients_normalize_deduplicate_and_preserve_letter_hash(self):
        path=self.card()
        initial=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        body={**self.settings(),'additional_emails':'Coach@Example.com; TEAM@example.com\ncoach@example.com, manager@example.com'}
        r=self.client.put(path,headers=self.headers(),json=body)
        self.assertEqual(r.status_code,200,r.text)
        data=r.json()
        self.assertEqual(data['settings']['additional_emails'],['coach@example.com','team@example.com','manager@example.com'])
        self.assertEqual(len(data['recipients']),3)
        self.assertEqual(data['content_hash'],initial['content_hash'])
        self.assertNotEqual(data['preview_hash'],initial['preview_hash'])
        self.assertNotIn('coach@example.com',data['text'])
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('app.matchmaker.welcome_letter.time.sleep'),patch('resend.Emails.send',return_value={'id':'provider-test'}) as provider:
            stale=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':initial['preview_hash']})
            self.assertEqual(stale.status_code,409)
            provider.assert_not_called()
            sent=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            self.assertEqual(sent.json()['accepted'],3,sent.text)
            recipients=[c.args[0]['to'] for c in provider.call_args_list]
            self.assertCountEqual(recipients,[['team@example.com'],['coach@example.com'],['manager@example.com']])
            self.assertTrue(all(len(addresses)==1 for addresses in recipients))

    def test_adding_email_sends_only_the_new_recipient_and_removal_updates_preview(self):
        path=self.card()
        data=self.client.put(path,headers=self.headers(),json=self.settings()).json()
        with patch.dict('os.environ',{'RESEND_API_KEY':'test-only'}),patch('app.matchmaker.welcome_letter.time.sleep'),patch('resend.Emails.send',return_value={'id':'provider-test'}) as provider:
            self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':data['preview_hash']})
            provider.reset_mock()
            updated=self.client.put(path,headers=self.headers(),json={**self.settings(),'additional_emails':['coach@example.com']}).json()
            sent=self.client.post(path+'/send',headers=self.headers(),json={'preview_hash':updated['preview_hash']})
            self.assertEqual(sent.json()['accepted'],1)
            self.assertEqual(sent.json()['already_submitted'],1)
            self.assertEqual(provider.call_args.args[0]['to'],['coach@example.com'])
            self.assertEqual(provider.call_count,1)
        removed=self.client.put(path,headers=self.headers(),json={**self.settings(),'additional_emails':[]}).json()
        self.assertEqual(len(removed['recipients']),1)
        self.assertEqual(removed['accepted'],1)

    def test_invalid_or_excess_additional_addresses_do_not_change_saved_settings(self):
        path=self.card()
        self.client.put(path,headers=self.headers(),json=self.settings())
        for addresses in ('not-an-email',['coach@example.com\r\nBcc: another@example.com'],[None],[f'coach{i}@example.com' for i in range(101)]):
            bad=self.client.put(path,headers=self.headers(),json={**self.settings(),'additional_emails':addresses})
            self.assertEqual(bad.status_code,422,bad.text)
        self.assertEqual(self.client.get(path,headers=self.headers()).json()['settings']['additional_emails'],[])
