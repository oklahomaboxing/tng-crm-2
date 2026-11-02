import unittest,secrets,hashlib,os,json
from datetime import datetime,timedelta
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import Member,User,Sale,MembershipProduct
from app.member_portal.models import MemberAccount,PortalAccountSetup,MemberInvite,AssignedMembership,MembershipRenewal
from app.services.portal_accounts import prepare_accounts,needs_password_setup
from app.auth import hash_password
from app.services.purchase_history import save_details,CloverPurchaseDetail

class CustomerAccountFlowTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def customer(self,**changes):
  values=dict(first_name='Customer',last_name='Fixture',email='customer@example.com',phone='4055550123',member_type='CUSTOMER',membership_status='pending')
  values.update(changes);m=Member(**values);self.db.add(m);self.db.commit();return m
 def test_accounts_active_without_inventing_membership_or_sending_messages(self):
  m=self.customer();sales=self.db.query(Sale).count()
  r=self.client.post('/api/members/prepare-accounts',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['created'],1)
  account=self.db.query(MemberAccount).filter_by(member_id=m.id).one();user=self.db.get(User,account.user_id)
  self.assertTrue(user.active);self.assertEqual(user.role,'member');self.assertTrue(needs_password_setup(self.db,account,user))
  self.assertEqual(self.db.query(Sale).count(),sales);self.assertEqual(m.member_type,'CUSTOMER')
  self.assertEqual(self.client.post('/api/members/prepare-accounts',headers=self.headers()).json()['created'],0)
 def test_shared_email_and_staff_login_not_reassigned_or_reenabled(self):
  self.customer();self.customer(first_name='Child',email='customer@example.com')
  self.customer(first_name='Staff',email=self.users['admin'].email)
  r=self.client.post('/api/members/prepare-accounts',headers=self.headers()).json()
  self.assertEqual(r['created'],0);self.assertEqual(r['shared_email_review'],3)
  self.db.refresh(self.users['admin']);self.assertEqual(self.users['admin'].role,'admin')
 def test_prepared_account_claims_existing_invite_once_and_rejects_stale_link_after_password_change(self):
  m=self.customer();prepare_accounts(self.db,{m.id});token=secrets.token_urlsafe(32)
  self.db.add(MemberInvite(member_id=m.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.utcnow()+timedelta(days=1)));self.db.commit()
  account=self.db.query(MemberAccount).filter_by(member_id=m.id).one()
  r=self.client.post('/api/member/activate',json={'token':token,'password':'Strong-Password-2026!'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.db.query(MemberAccount).filter_by(member_id=m.id).count(),1)
  self.db.expire_all();self.assertFalse(needs_password_setup(self.db,account,self.db.get(User,account.user_id)))
  self.assertEqual(self.client.post('/api/member/activate',json={'token':token,'password':'Another-Password-2026!'}).status_code,400)
  second=secrets.token_urlsafe(32);self.db.add(MemberInvite(member_id=m.id,token_hash=hashlib.sha256(second.encode()).hexdigest(),expires_at=datetime.utcnow()+timedelta(days=1)));self.db.commit()
  self.assertEqual(self.client.post('/api/member/activate',json={'token':second,'password':'Another-Password-2026!'}).status_code,409)
 def test_password_reset_before_claim_blocks_preexisting_invitation(self):
  m=self.customer();prepare_accounts(self.db,{m.id});account=self.db.query(MemberAccount).filter_by(member_id=m.id).one();user=self.db.get(User,account.user_id)
  token=secrets.token_urlsafe(32);self.db.add(MemberInvite(member_id=m.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.utcnow()+timedelta(days=1)))
  user.password_hash=hash_password('Already-reset-password-2026!');self.db.commit()
  r=self.client.post('/api/member/activate',json={'token':token,'password':'Old-link-overwrite-2026!'})
  self.assertEqual(r.status_code,409,r.text)
 def test_admin_create_active_custom_rate_and_family_phone_can_be_shared(self):
  self.member.phone='4055550123';self.db.commit();sales=self.db.query(Sale).count()
  r=self.client.post('/api/members',headers=self.headers(),json={'first_name':'New','last_name':'Family','email':'family@example.com','phone':'4055550123','membership_name':'Custom Youth Plan','membership_rate':75.5,'membership_months':1})
  self.assertEqual(r.status_code,201,r.text);m=self.db.get(Member,r.json()['id'])
  self.assertEqual(m.membership_status,'active');self.assertEqual(m.monthly_rate,75.5);self.assertIsNotNone(m.membership_end)
  self.assertEqual(self.db.query(Sale).count(),sales)
  assignment=self.db.query(AssignedMembership).filter_by(member_id=m.id).one();self.assertEqual(assignment.rate,75.5)
  account=self.db.query(MemberAccount).filter_by(member_id=m.id).one();self.assertTrue(self.db.get(User,account.user_id).active)
 def test_assigned_renewal_rate_is_server_owned_and_other_plan_tampering_rejected(self):
  old_end=self.member.membership_end
  r=self.client.put(f'/api/members/{self.member.id}/assigned-membership',headers=self.headers(),json={'name':'Discount Monthly','rate':65.25,'months':1,'activate':False})
  self.assertEqual(r.status_code,200,r.text);self.db.refresh(self.member);self.assertEqual(self.member.membership_end,old_end)
  options=self.client.get('/api/member/me/renewal-options',headers=self.headers('member')).json()['options']
  self.assertEqual(len(options),1);self.assertEqual(options[0]['price'],65.25)
  response=Mock(status_code=200);response.json.return_value={'id':'fixture-checkout','href':'https://checkout.clover.com/fixture'}
  with patch.dict(os.environ,{'CLOVER_MERCHANT_ID':'fixture','CLOVER_ECOMMERCE_PRIVATE_KEY':'fixture'}),patch('httpx.post',return_value=response) as post:
   checkout=self.client.post('/api/member/me/renew-checkout',headers=self.headers('member'),json={'product_id':options[0]['id'],'price':1})
   self.assertEqual(checkout.status_code,200,checkout.text)
   self.assertEqual(post.call_args.kwargs['json']['shoppingCart']['lineItems'][0]['price'],6525)
  self.assertEqual(self.client.post('/api/member/me/renew-checkout',headers=self.headers('member'),json={'product_id':self.product.id}).status_code,400)
 def test_purchase_descriptions_follow_member_ownership_and_custom_item_not_mislabeled(self):
  sale=self.db.query(Sale).first();sale.clover_order_id='fixture-order';self.db.commit()
  save_details(self.db,self.member.id,{'id':'fixture-order','lineItems':{'elements':[{'name':'Boxing Gloves','price':5000,'unitQty':2000},{'name':'Monthly Membership','price':15000}]}});self.db.commit()
  data=self.client.get('/api/member/me/transactions',headers=self.headers('member')).json()['transactions'][0]
  self.assertIn('Boxing Gloves',data['purchase_description']);self.assertEqual(data['items'][0]['quantity'],2)
  self.assertEqual(self.client.get(f'/api/members/{self.member.id}/payments',headers=self.headers('member')).status_code,403)
  other=self.customer();self.assertFalse(save_details(self.db,other.id,{'id':'fixture-order','lineItems':{'elements':[{'name':'Wrong owner'}]}}))
 def test_restricted_roles_cannot_grant_accounts_or_memberships(self):
  for role in ('staff','member','rep'):
   self.assertEqual(self.client.post('/api/members/prepare-accounts',headers=self.headers(role)).status_code,403)
   self.assertEqual(self.client.put(f'/api/members/{self.member.id}/assigned-membership',headers=self.headers(role),json={'name':'Free','rate':0,'months':12,'activate':True}).status_code,403)
 def test_existing_recorded_discount_is_preserved_without_extending_membership(self):
  from app.services.assigned_memberships import preserve_recorded_rates
  self.member.monthly_rate=125;self.member.billing_cycle='30_day';self.member.membership_type='Monthly'
  self.db.commit();old_end=self.member.membership_end;old_sales=self.db.query(Sale).count()
  self.assertEqual(preserve_recorded_rates(self.db,self.users['admin'].id),1)
  assignment=self.db.query(AssignedMembership).filter_by(member_id=self.member.id).one()
  self.assertEqual(assignment.rate,125);self.assertEqual(self.member.membership_end,old_end);self.assertEqual(self.db.query(Sale).count(),old_sales)
  self.assertEqual(self.client.get('/api/member/me/renewal-options',headers=self.headers('member')).json()['options'][0]['price'],125)
 def test_explicit_monthly_term_not_inferred_as_year_from_plan_name(self):
  from app.services.assigned_memberships import assign_membership
  from app.services.memberships import membership_months
  assignment=assign_membership(self.db,self.member,'Annual Agreement - Monthly Billing',95,1,activate=False,user_id=self.users['admin'].id)
  self.db.commit();self.assertEqual(membership_months(self.db.get(MembershipProduct,assignment.product_id)),1)
 def test_customer_portal_never_shows_pending_as_account_or_membership_label(self):
  m=self.customer();prepare_accounts(self.db,{m.id});self.db.commit()
  account=self.db.query(MemberAccount).filter_by(member_id=m.id).one()
  from app.auth import create_token
  token=create_token({'sub':str(account.user_id)})
  r=self.client.get('/api/member/me',headers={'Authorization':'Bearer '+token})
  self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(r.json()['member']['account_status'],'active')
  self.assertEqual(r.json()['member']['membership_status'],'not_enrolled')
 def test_multiple_custom_membership_payments_keep_one_assignment_and_negotiated_rate(self):
  from app.services.memberships import apply_membership
  product=MembershipProduct(name='Youth Monthly',price=125,is_membership=True,category='membership',default_membership_months=1)
  self.db.add(product);self.db.commit()
  apply_membership(self.member,product);apply_membership(self.member,product);self.db.commit()
  self.assertEqual(self.db.query(AssignedMembership).filter_by(member_id=self.member.id).count(),1)
  assignment=self.db.query(AssignedMembership).filter_by(member_id=self.member.id).one();assignment.rate=100;self.db.commit()
  apply_membership(self.member,product);self.db.commit();self.assertEqual(self.member.monthly_rate,100)
 def test_unbound_login_cannot_take_customer_records_by_matching_email_and_name(self):
  customer=self.customer()
  user=User(name='Customer Fixture',email=customer.email,role='member',active=True,password_hash=hash_password('Preclaimed-password-2026!'))
  self.db.add(user);self.db.commit();original=user.password_hash
  result=prepare_accounts(self.db,{customer.id});self.db.commit()
  self.assertEqual(result['shared_email_review'],1)
  self.assertIsNone(self.db.query(MemberAccount).filter_by(member_id=customer.id).first())
  self.db.refresh(user);self.assertEqual(user.password_hash,original)
 def test_recording_initial_payment_does_not_give_an_extra_free_month(self):
  from app.services.assigned_memberships import assign_membership
  from app.services.memberships import apply_membership
  assignment=assign_membership(self.db,self.member,'Assigned Monthly',125,1,activate=True,user_id=self.users['admin'].id)
  self.db.commit();initial_end=self.member.membership_end
  apply_membership(self.member,self.db.get(MembershipProduct,assignment.product_id));self.db.commit()
  self.assertEqual(self.member.membership_end,initial_end)
  self.assertFalse(assignment.unrecorded_activation)
  apply_membership(self.member,self.db.get(MembershipProduct,assignment.product_id));self.db.commit()
  self.assertEqual(self.member.membership_end,initial_end+timedelta(days=30))
