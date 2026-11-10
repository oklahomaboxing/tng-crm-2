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
