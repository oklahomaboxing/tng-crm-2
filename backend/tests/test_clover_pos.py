"""Member-only Clover API tests use the existing isolated regression database."""
import os, unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import test_stabilization as support
from app.auth import create_token
from app.models import Attendance, Member
from app.clover_pos.routes import AUDIENCE

class CloverPosTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 def headers(self, role='staff', **claims):
  return {'Authorization':'Bearer '+create_token({'sub':str(self.users[role].id),'aud':AUDIENCE,'merchant':os.getenv('CLOVER_MERCHANT_ID','').strip(),**claims})}
 def test_pos_login_uses_staff_verification(self):
  with patch('app.main.verify_password',return_value=True) as verify:
   r=self.client.post('/api/clover-pos/login',json={'email':'staff@example.com','password':'example-password'})
  self.assertEqual(r.status_code,200,r.text);verify.assert_called_once()
  token=r.json()['token'];headers={'Authorization':'Bearer '+token}
  self.assertEqual(self.client.get('/api/clover-pos/session',headers=headers).status_code,200)
  self.assertEqual(self.client.get('/api/members',headers=headers).status_code,401)
 def test_regular_crm_token_cannot_access_pos(self):
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=support.StabilizationTests.headers(self)).status_code,401)
  ordinary={'Authorization':'Bearer '+create_token({'sub':str(self.users['staff'].id),'merchant':os.getenv('CLOVER_MERCHANT_ID','').strip()})}
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=ordinary).status_code,401)
 def test_wrong_merchant_and_expired_session_rejected(self):
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=self.headers(merchant='different-merchant')).status_code,401)
  expired={'Authorization':'Bearer '+create_token({'sub':str(self.users['staff'].id),'aud':AUDIENCE,'merchant':os.getenv('CLOVER_MERCHANT_ID','').strip()},minutes=-1)}
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=expired).status_code,401)
 def test_disabled_or_nonstaff_user_cannot_access(self):
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=self.headers('member')).status_code,403)
  self.users['staff'].active=False;self.db.commit()
  self.assertEqual(self.client.get('/api/clover-pos/members',headers=self.headers()).status_code,403)
 def test_list_search_and_profile(self):
  r=self.client.get('/api/clover-pos/members?q=1',headers=self.headers());self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(r.json()['items'][0]['member_number'],'1')
  self.assertEqual(self.client.get('/api/clover-pos/members?q=Test%20Member',headers=self.headers()).json()['total'],1)
  self.assertEqual(self.client.get('/api/clover-pos/members?q=%25',headers=self.headers()).json()['total'],0)
  r=self.client.get(f'/api/clover-pos/members/{self.member.id}',headers=self.headers());self.assertEqual(r.status_code,200)
  self.assertEqual(r.json()['qr_value'],'TNG000001');self.assertNotIn('emergency_phone',r.json());self.assertNotIn('notes',r.json())
 def test_customers_are_not_members(self):
  row=Member(first_name='Retail',last_name='Customer',member_type='CUSTOMER',member_number='2');self.db.add(row);self.db.commit()
  self.assertEqual(self.client.get(f'/api/clover-pos/members/{row.id}',headers=self.headers()).status_code,404)
 def test_contact_edit_cannot_activate_or_reprice(self):
  url=f'/api/clover-pos/members/{self.member.id}'
  data={'first_name':'Updated','last_name':'Member','email':'updated@example.com','phone':'5550102'}
  r=self.client.patch(url,headers=self.headers(),json=data);self.assertEqual(r.status_code,200,r.text)
  self.db.refresh(self.member);self.assertEqual(self.member.first_name,'Updated');self.assertEqual(self.member.notes,'Keep this note')
  self.assertEqual(self.client.patch(url,headers=self.headers(),json={**data,'membership_status':'active'}).status_code,422)
 def test_short_number_checkin_and_attendance(self):
  r=self.client.post('/api/clover-pos/checkin',headers=self.headers(),json={'code':'1'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['member']['member_number'],'1')
  self.assertEqual(self.db.query(Attendance).count(),1)
  profile=self.client.get(f'/api/clover-pos/members/{self.member.id}',headers=self.headers()).json()
  self.assertEqual(len(profile['attendance']),1)
 def test_inactive_member_not_checked_in(self):
  self.member.membership_end=datetime.utcnow()-timedelta(days=1);self.db.commit()
  r=self.client.post('/api/clover-pos/checkin',headers=self.headers(),json={'code':'1'})
  self.assertEqual(r.status_code,403);self.assertEqual(self.db.query(Attendance).count(),0)
 def test_invalid_credentials_and_unknown_number(self):
  with patch('app.main.verify_password',return_value=False):
   self.assertEqual(self.client.post('/api/clover-pos/login',json={'email':'staff@example.com','password':'wrong'}).status_code,401)
  self.assertEqual(self.client.post('/api/clover-pos/checkin',headers=self.headers(),json={'code':'99999999'}).status_code,404)
  self.assertEqual(self.client.post('/api/clover-pos/checkin',headers=self.headers(),json={'code':'1','membership_status':'active'}).status_code,422)

if __name__=='__main__':unittest.main()
