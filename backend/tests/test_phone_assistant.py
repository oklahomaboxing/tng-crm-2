import os,unittest,json
from unittest.mock import patch,Mock
from xml.etree import ElementTree as ET
import test_stabilization as support
from app.phone.routes import PhoneSettings,PhoneConfig,PhoneCall
from app.models import Lead,Member
from twilio.request_validator import RequestValidator

class PhoneAssistantTests(unittest.TestCase):
    def setUp(self):
        support.StabilizationTests.setUp(self)
        self.env=patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'AC-test','TWILIO_AUTH_TOKEN':'test-voice-secret','TWILIO_PHONE_NUMBER':'+14055550199','TNG_BACKEND_URL':'https://voice.example.com'})
        self.env.start()
        self.db.add(PhoneSettings(id=1,settings_json=json.dumps(PhoneConfig(enabled=True).model_dump()),connected=False));self.db.commit()
    def tearDown(self):
        self.env.stop();support.StabilizationTests.tearDown(self)
    headers=support.StabilizationTests.headers
    def webhook(self,path,**changes):
        form={'AccountSid':'AC-test','CallSid':'CA'+'1'*32,'To':'+14055550199','From':'+14055550101'};form.update(changes)
        route='/api/phone/'+path
        signature=RequestValidator('test-voice-secret').compute_signature('https://voice.example.com'+route,form)
        return self.client.post(route,data=form,headers={'X-Twilio-Signature':signature})
    def root(self,response):
        self.assertEqual(response.status_code,200,response.text)
        return ET.fromstring(response.text)

    def test_signature_account_and_called_number_are_verified(self):
        self.assertEqual(self.client.post('/api/phone/incoming',data={'CallSid':'fake'}).status_code,401)
        self.assertEqual(self.webhook('incoming',AccountSid='other').status_code,401)
        self.assertEqual(self.webhook('incoming',To='+14055550999').status_code,403)
        self.assertEqual(self.db.query(PhoneCall).count(),0)

    def test_speech_keypad_menu_and_approved_answers(self):
        root=self.root(self.webhook('incoming'))
        g=root.find('Gather');self.assertEqual(g.attrib['input'],'speech dtmf')
        self.assertIn('press 4',''.join(root.itertext()))
        for changes,answer in (({'Digits':'1'},'8416'),({'SpeechResult':'Membership rates'},'current rates'),({'Digits':'3'},'boxing events')):
            response=self.webhook('menu',**changes);self.root(response);self.assertIn(answer,response.text)
            self.assertNotIn('<Record',response.text)
        self.assertEqual(self.db.query(PhoneCall).count(),1)

    def test_private_member_questions_route_to_staff_without_profile_lookup(self):
        before=self.db.query(Member).count()
        root=self.root(self.webhook('menu',SpeechResult='What is my membership balance?'))
        self.assertEqual(root.find('Dial/Number').text,'+14059895843')
        self.assertEqual(self.db.query(Member).count(),before)
        self.assertNotIn(self.member.email,''.join(root.itertext()))

    def test_callback_creates_one_phone_lead_and_never_a_membership(self):
        before=self.db.query(Member).count();leads=self.db.query(Lead).count()
        self.root(self.webhook('menu',Digits='4'))
        self.root(self.webhook('callback/name',SpeechResult='Example Caller'))
        self.root(self.webhook('callback/details',SpeechResult='I would like a gym tour and membership information.'))
        self.root(self.webhook('callback/details',SpeechResult='I would like a gym tour and membership information.'))
        self.assertEqual(self.db.query(Lead).count(),leads+1)
        lead=self.db.query(Lead).filter_by(conversion_source='phone_assistant').one()
        self.assertEqual((lead.first_name,lead.last_name,lead.phone),('Example','Caller','+14055550101'))
        self.assertEqual(lead.email,'')
        self.assertEqual(self.db.query(Member).count(),before)
        self.assertIn('gym tour',lead.notes)

    def test_anonymous_caller_can_enter_callback_number(self):
        response=self.webhook('menu',Digits='4',From='anonymous');self.assertIn('ten digit',response.text)
        self.root(self.webhook('callback/phone',Digits='4055550102',From='anonymous'))
        self.root(self.webhook('callback/name',SpeechResult='Example Anonymous',From='anonymous'))
        self.root(self.webhook('callback/details',SpeechResult='Membership options please',From='anonymous'))
        self.assertEqual(self.db.query(Lead).filter_by(conversion_source='phone_assistant').one().phone,'+14055550102')

    def test_no_answer_offers_callback_and_disabled_menu_goes_to_staff(self):
        self.root(self.webhook('incoming'))
        self.assertIn('first and last name',self.webhook('transfer-result',DialCallStatus='no-answer').text)
        saved=self.client.put('/api/phone/admin',headers=self.headers(),json=PhoneConfig(enabled=False).model_dump())
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(self.root(self.webhook('incoming')).find('Dial/Number').text,'+14059895843')

    def test_silent_callback_prompts_stop_after_three_attempts(self):
        self.webhook('menu',Digits='4')
        for _ in range(3):r=self.webhook('callback/name',SpeechResult='')
        root=self.root(r)
        self.assertIsNotNone(root.find('Hangup'))
        self.assertIsNone(root.find('Gather'))

    def test_admin_settings_prevent_loops_and_other_roles(self):
        for role in ('staff','member','fighter','rep'):
            self.assertEqual(self.client.get('/api/phone/admin',headers=self.headers(role)).status_code,403)
            self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(role),json=PhoneConfig().model_dump()).status_code,403)
        bad=PhoneConfig().model_dump();bad['staff_number']=bad['public_number']
        self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=bad).status_code,400)
        bad['staff_number']='+14055550199'
        self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=bad).status_code,400)

    def test_connect_requires_charge_acknowledgment_and_preserves_sms_settings(self):
        provider=Mock();number=Mock();number.capabilities={'voice':True};number.voice_application_sid=None;number.voice_url='';provider.incoming_phone_numbers.list.return_value=[number]
        with patch('app.phone.routes.Client',return_value=provider):
            self.assertEqual(self.client.post('/api/phone/admin/connect',headers=self.headers(),json={}).status_code,400)
            number.update.assert_not_called()
            result=self.client.post('/api/phone/admin/connect',headers=self.headers(),json={'acknowledge_voice_charges':True})
            self.assertEqual(result.status_code,200,result.text)
            self.assertTrue(result.json()['connected'])
            self.assertTrue(result.json()['settings']['enabled'])
            kwargs=number.update.call_args.kwargs
            self.assertEqual(kwargs['voice_url'],'https://voice.example.com/api/phone/incoming')
            self.assertTrue(all('sms' not in key.lower() for key in kwargs))
            provider.calls.create.assert_not_called()

    def test_existing_foreign_voice_webhook_is_not_overwritten(self):
        provider=Mock();number=Mock();number.capabilities={'voice':True};number.voice_application_sid=None;number.voice_url='https://other.example.com/voice';provider.incoming_phone_numbers.list.return_value=[number]
        with patch('app.phone.routes.Client',return_value=provider):
            r=self.client.post('/api/phone/admin/connect',headers=self.headers(),json={'acknowledge_voice_charges':True})
            self.assertEqual(r.status_code,409)
            number.update.assert_not_called()

    def test_status_callback_is_terminal_and_admin_view_masks_phone(self):
        self.webhook('incoming')
        self.assertEqual(self.webhook('status',CallStatus='completed').status_code,204)
        self.webhook('status',CallStatus='ringing')
        self.assertEqual(self.db.query(PhoneCall).one().status,'completed')
        r=self.client.get('/api/phone/admin',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['calls'][0]['caller_last_four'],'0101')
        self.assertNotIn('+14055550101',r.text)
        self.assertEqual(r.headers['cache-control'],'private, no-store')

    def test_callback_can_transfer_to_staff_and_disabled_menu_still_saves_callback(self):
        self.webhook('menu',Digits='4')
        self.assertEqual(self.root(self.webhook('callback/name',Digits='0')).find('Dial/Number').text,'+14059895843')
        self.client.put('/api/phone/admin',headers=self.headers(),json=PhoneConfig(enabled=False).model_dump())
        self.webhook('incoming')
        self.webhook('transfer-result',DialCallStatus='no-answer')
        self.webhook('callback/name',SpeechResult='Example Caller')
        self.webhook('callback/details',SpeechResult='Please call me about training')
        self.assertEqual(self.db.query(Lead).filter_by(conversion_source='phone_assistant').count(),1)
