import unittest
from datetime import datetime
import test_phone_assistant as support
from app.phone.tracking import PhoneCallActivity
from app.phone.routes import PhoneCall
from app.models import User

class PhoneTrackingTests(unittest.TestCase):
    setUp=support.PhoneAssistantTests.setUp
    tearDown=support.PhoneAssistantTests.tearDown
    webhook=support.PhoneAssistantTests.webhook
    headers=support.PhoneAssistantTests.headers

    def test_admin_only_call_details_and_no_store(self):
        self.webhook('incoming')
        path='/api/phone/admin/calls'
        self.assertEqual(self.client.get(path).status_code,401)
        self.users['admin'].role='staff';self.db.commit()
        self.assertEqual(self.client.get(path,headers=self.headers()).status_code,403)
        self.users['admin'].role='admin';self.db.commit()
        response=self.client.get(path,headers=self.headers())
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response.headers['cache-control'])
        self.assertEqual(response.json()['calls'][0]['caller_phone'],'+14055550101')
        self.assertEqual(self.client.get(path+'/missing',headers=self.headers()).status_code,404)

    def test_timeline_tracks_choices_transfers_and_duration_without_speech(self):
        self.webhook('incoming')
        self.webhook('menu',SpeechResult='I want membership prices please')
        self.webhook('menu',Digits='6')
        self.webhook('transfer-result',DialCallStatus='completed')
        self.webhook('status',CallStatus='completed',CallDuration='75')
        self.webhook('status',CallStatus='completed',CallDuration='75')
        response=self.client.get('/api/phone/admin/calls/'+'CA'+'1'*32,headers=self.headers())
        self.assertEqual(response.status_code,200)
        data=response.json();self.assertEqual(data['duration_seconds'],75)
        self.assertEqual(data['stage'],'marketing_connected')
        self.assertEqual([e['detail'] for e in data['timeline']],['Call reached TNGOS','Memberships','marketing','completed','completed'])
        self.assertNotIn('I want membership',response.text)
        self.assertEqual(self.db.query(PhoneCall).count(),1)

    def test_date_search_outcome_pagination_and_old_calls(self):
        self.db.add_all([PhoneCall(call_sid='CA'+'2'*32,caller_name='Old Caller',caller_phone='+14055550202',created_at=datetime(2026,11,10,5,59),status='completed'),PhoneCall(call_sid='CA'+'3'*32,caller_name='New Caller',caller_phone='+14055550303',created_at=datetime(2026,11,10,6,0),status='completed',stage='staff_connected')]);self.db.commit()
        path='/api/phone/admin/calls'
        data=self.client.get(path+'?start=2026-11-10&end=2026-11-10',headers=self.headers()).json()
        self.assertEqual(data['total'],1);self.assertEqual(data['summary']['transferred'],1)
        data=self.client.get(path+'?q=0202',headers=self.headers()).json();self.assertEqual(data['total'],1)
        data=self.client.get(path+'?outcome=transferred',headers=self.headers()).json();self.assertEqual(data['total'],1)
        data=self.client.get(path+'?page_size=1&page=2',headers=self.headers()).json();self.assertEqual(len(data['calls']),1);self.assertEqual(data['total'],2)
        old=self.client.get(path+'/'+'CA'+'2'*32,headers=self.headers()).json();self.assertEqual(old['timeline'],[]);self.assertIsNone(old['duration_seconds'])
        self.assertEqual(self.client.get(path+'?start=2026-11-11&end=2026-11-10',headers=self.headers()).status_code,400)
        self.assertEqual(self.client.get(path+'?outcome=invalid',headers=self.headers()).status_code,400)

    def test_forged_webhook_cannot_write_history(self):
        response=self.client.post('/api/phone/menu',data={'Digits':'6'})
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.db.query(PhoneCallActivity).count(),0)
