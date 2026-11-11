import unittest,json
import test_phone_assistant as support
from app.phone.routes import PhoneConfig,PhoneSettings,PhoneCallDepartment,PhoneCall
from app.models import Lead,Member

class CoachPhoneTests(unittest.TestCase):
 setUp=support.PhoneAssistantTests.setUp
 tearDown=support.PhoneAssistantTests.tearDown
 webhook=support.PhoneAssistantTests.webhook
 root=support.PhoneAssistantTests.root
 headers=support.PhoneAssistantTests.headers
 def test_all_coach_digits_transfer_to_owner_supplied_numbers(self):
  expected=[('1','Rodney Porter','+14052090453'),('2','Maurice Williams','+16512390916'),('3','Dora Williams','+14059895453'),('4','Jose Iturinno','+14057773615'),('5','Marlon Geddis','+14056407542')]
  for digit,name,phone in expected:
   sid='CA'+digit*32
   r=self.webhook('menu',Digits='8',CallSid=sid);self.assertIn(name,r.text);self.assertEqual(self.root(r).find('Gather').attrib['input'],'dtmf')
   r=self.webhook('coaches/choose',Digits=digit,CallSid=sid);root=self.root(r)
   self.assertEqual(root.find('Dial/Number').text,phone);self.assertEqual(root.find('Dial').attrib['timeout'],'35')
   self.assertEqual(self.db.get(PhoneCallDepartment,sid).department,'coach_'+digit)
 def test_noise_never_selects_menu_or_coach_and_gathers_never_listen_to_speech(self):
  r=self.webhook('incoming');g=self.root(r).find('Gather');self.assertEqual(g.attrib['input'],'dtmf');self.assertNotIn('speechTimeout',g.attrib)
  r=self.webhook('menu',SpeechResult='marketing sign me up Rodney');self.assertIsNone(self.root(r).find('Dial'));self.assertEqual(self.db.query(PhoneCallDepartment).count(),0)
  self.webhook('menu',Digits='8');r=self.webhook('coaches/choose',SpeechResult='Rodney Porter')
  self.assertIsNone(self.root(r).find('Dial'));self.assertEqual(self.root(r).find('Gather').attrib['input'],'dtmf')
  r=self.webhook('coaches/choose',Digits='2',SpeechResult='Rodney Porter');self.assertEqual(self.root(r).find('Dial/Number').text,'+16512390916')
 def test_coach_no_answer_creates_only_confirmed_labeled_callback(self):
  before=self.db.query(Member).count();self.webhook('menu',Digits='8');self.webhook('coaches/choose',Digits='1');self.webhook('transfer-result',DialCallStatus='no-answer')
  self.assertEqual(self.db.query(Lead).filter_by(conversion_source='phone_assistant').count(),0)
  self.webhook('callback/confirm',Digits='1');self.webhook('callback/confirm',Digits='1')
  lead=self.db.query(Lead).filter_by(conversion_source='phone_assistant').one()
  self.assertIn('Coach Rodney Porter inquiry',lead.notes);self.assertIn('Name and spoken message were not collected',lead.notes);self.assertEqual(lead.phone,'+14055550101');self.assertEqual(self.db.query(Member).count(),before)
 def test_connected_coach_is_in_call_center_transfer_totals(self):
  self.webhook('menu',Digits='8');self.webhook('coaches/choose',Digits='5');self.webhook('transfer-result',DialCallStatus='completed')
  data=self.client.get('/api/phone/admin/calls?outcome=transferred',headers=self.headers()).json();self.assertEqual(data['total'],1);self.assertEqual(data['calls'][0]['department_name'],'Coach Marlon Geddis')
  self.assertEqual(data['calls'][0]['stage'],'coach_connected')
 def test_directory_can_return_to_main_menu_and_invalid_presses_are_bounded(self):
  self.webhook('menu',Digits='8');r=self.webhook('coaches/choose',Digits='9');self.assertIn('7 to sign up now',r.text)
  self.webhook('menu',Digits='8')
  for _ in range(3):r=self.webhook('coaches/choose',Digits='6')
  self.assertEqual(self.root(r).find('Dial/Number').text,'+14059895823')
 def test_coach_settings_reject_loops_duplicate_keys_and_blank_names(self):
  body=PhoneConfig(enabled=True).model_dump();body['coaches'][0]['phone']=body['public_number']
  self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=body).status_code,400)
  body=PhoneConfig(enabled=True).model_dump();body['coaches'][0]['phone']='+14055550199'
  self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=body).status_code,400)
  body=PhoneConfig(enabled=True).model_dump();body['coaches'][1]['digit']='1'
  self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=body).status_code,422)
  body=PhoneConfig(enabled=True).model_dump();body['coaches'][0]['name']='   '
  self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=body).status_code,422)
 def test_disabled_coach_is_not_announced_or_dialed_and_forged_requests_fail(self):
  body=PhoneConfig(enabled=True).model_dump();body['coaches'][0]['enabled']=False
  self.assertEqual(self.client.put('/api/phone/admin',headers=self.headers(),json=body).status_code,200)
  self.assertNotIn('Rodney',self.webhook('menu',Digits='8').text);self.assertIsNone(self.root(self.webhook('coaches/choose',Digits='1')).find('Dial'))
  self.assertEqual(self.client.post('/api/phone/coaches/choose',data={'Digits':'1'}).status_code,401)
 def test_callback_number_can_be_changed_without_any_spoken_input(self):
  self.webhook('menu',Digits='4');self.webhook('callback/confirm',Digits='2');self.webhook('callback/phone',Digits='4055550123');self.webhook('callback/confirm',Digits='1')
  self.assertEqual(self.db.query(Lead).filter_by(conversion_source='phone_assistant').one().phone,'+14055550123')
