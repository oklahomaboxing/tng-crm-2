import os,unittest
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import Member,User
from app.member_portal.models import MemberInvite,MemberAccount
from app.services.portal_accounts import prepare_accounts

class ActivationEmailResetTests(unittest.TestCase):
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.member=Member(first_name='Unclaimed',last_name='Member',email='unclaimed@example.com',phone='4055550133')
  self.db.add(self.member);self.db.commit()
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def invite(self,**body):
  with patch.dict(os.environ,{'RESEND_API_KEY':'test-only'}),patch('app.member_portal.routes.httpx.post',return_value=Mock(status_code=200)):
   return self.client.post('/api/member/admin/reset-activation' if body.get('replace_existing') else '/api/member/admin/invite',headers=self.headers(),json={'member_id':self.member.id,**body})
 def test_correct_email_resend_invalidates_old_link_and_updates_prepared_login(self):
  self.member.phone='4055550100';self.db.commit();prepare_accounts(self.db,{self.member.id});self.db.commit()
  old=self.invite();self.assertEqual(old.status_code,200,old.text)
  updated=self.invite(email='corrected@example.com',replace_existing=True);self.assertEqual(updated.status_code,200,updated.text)
  self.db.expire_all();self.assertEqual(self.db.get(Member,self.member.id).email,'corrected@example.com')
  account=self.db.query(MemberAccount).filter_by(member_id=self.member.id).one();self.assertEqual(self.db.get(User,account.user_id).email,'corrected@example.com')
  r=self.client.post('/api/member/activate',json={'token':old.json()['activation_token'],'password':'NewFixturePass123!'});self.assertEqual(r.status_code,400,r.text)
  r=self.client.post('/api/member/activate',json={'token':updated.json()['activation_token'],'password':'NewFixturePass123!'});self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.invite(email='another@example.com',replace_existing=True).status_code,409)
 def test_resend_same_email_is_available_without_seven_day_wait(self):
  old=self.invite();new=self.invite(email=self.member.email,replace_existing=True)
  self.assertEqual(new.status_code,200,new.text);self.assertNotEqual(old.json()['activation_token'],new.json()['activation_token'])
 def test_conflicts_permissions_and_provider_failure_do_not_change_email_or_old_link(self):
  old=self.invite();original=self.member.email
  self.db.add(Member(first_name='Other',last_name='Person',email='taken@example.com'));self.db.commit()
  self.assertEqual(self.invite(email='taken@example.com',replace_existing=True).status_code,409)
  for role in ('rep','member','fighter'):
   r=self.client.post('/api/member/admin/invite',headers=self.headers(role),json={'member_id':self.member.id,'email':'new@example.com','replace_existing':True});self.assertEqual(r.status_code,403)
  with patch.dict(os.environ,{'RESEND_API_KEY':'test-only'}),patch('app.member_portal.routes.httpx.post',return_value=Mock(status_code=503,text='test failure')):
   r=self.client.post('/api/member/admin/invite',headers=self.headers(),json={'member_id':self.member.id,'email':'new@example.com','replace_existing':True});self.assertEqual(r.status_code,502)
  self.db.expire_all();self.assertEqual(self.db.get(Member,self.member.id).email,original)
  r=self.client.post('/api/member/activate',json={'token':old.json()['activation_token'],'password':'NewFixturePass123!'});self.assertEqual(r.status_code,200,r.text)

 def test_other_login_with_case_variant_of_own_email_blocks_reset(self):
  prepare_accounts(self.db,{self.member.id});self.db.commit()
  self.db.add(User(name='Other account',email=self.member.email.upper(),role='member',active=True,password_hash='not-a-real-password'));self.db.commit()
  self.assertEqual(self.invite(email=self.member.email,replace_existing=True).status_code,409)
