import unittest
import test_stabilization as support
from app.models import User
from app.matchmaker.models import BoxingEvent
from app.auth import hash_password

class PartnerAndDeskTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.event=BoxingEvent(name='Assigned Event',slug='assigned-event',event_date='2027-01-30');self.other=BoxingEvent(name='Private Event',slug='private-event');self.db.add_all([self.event,self.other])
  for role in ('investor','sponsor','concessions','matchmaker'):
   u=User(name=role,email=role+'@example.com',role=role,password_hash=hash_password('Example-only-password-123!'),active=True);self.db.add(u);self.users[role]=u
  self.db.commit()
 def test_partner_accounts_created_by_admin_only_and_no_automatic_event_access(self):
  for role in ('investor','sponsor','concessions'):
   body={'name':'New '+role,'email':'new-'+role+'@example.com','role':role,'password':'Example-only-password-123!','title':'Executive Chef','phone':'+16515550123'}
   r=self.client.post('/api/users',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text)
   if role=='concessions':
    from app.events.partners import PartnerProfile
    profile=self.db.get(PartnerProfile,r.json()['user']['id']);self.assertEqual(profile.title,'Executive Chef');self.assertEqual(profile.phone,'+16515550123')
   r=self.client.get('/api/partners/portal',headers=self.headers(role));self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['events'],[]);self.assertIn('no-store',r.headers['cache-control'])
  self.assertEqual(self.client.post('/api/users',headers=self.headers('staff'),json=body).status_code,403)
 def grant(self,role,**extra):return self.client.put('/api/partners/access',headers=self.headers(),json={'user_id':self.users[role].id,'event_id':self.event.id,'update_text':'Your event update',**extra})
 def test_grants_are_event_specific_and_sponsor_cannot_receive_financials(self):
  self.assertEqual(self.grant('investor',financials=True).status_code,200);self.assertEqual(self.grant('sponsor',financials=True).status_code,200);self.assertEqual(self.grant('concessions').status_code,200)
  for role in ('investor','sponsor','concessions'):
   d=self.client.get('/api/partners/portal',headers=self.headers(role)).json();self.assertEqual([e['name'] for e in d['events']],['Assigned Event']);self.assertEqual('financials' in d['events'][0],role=='investor');self.assertNotIn('fighters',d['events'][0]);self.assertNotIn('contracts',d['events'][0])
 def test_revocation_and_disabled_login_take_effect(self):
  self.grant('investor');access=self.client.get('/api/partners/access',headers=self.headers()).json();gid=access['grants'][0]['id'];self.assertEqual(self.client.delete(f'/api/partners/access/{gid}',headers=self.headers()).status_code,200);self.assertEqual(self.client.get('/api/partners/portal',headers=self.headers('investor')).json()['events'],[])
  h=self.headers('sponsor');self.users['sponsor'].active=False;self.db.commit();self.assertEqual(self.client.get('/api/partners/portal',headers=h).status_code,403)
 def test_partner_roles_cannot_access_business_operations_even_legacy_routes(self):
  for role in ('investor','sponsor','concessions'):
   for path in ['/api/users','/api/members','/api/sales','/api/boxing/fighters','/api/boxing/events','/api/merchandise-checkouts/1','/api/partners/access','/api/messages',f'/api/events/{self.event.id}/recap',f'/api/matchmaker-desk/events/{self.event.id}']:
    r=self.client.get(path,headers=self.headers(role));self.assertEqual(r.status_code,403,(role,path,r.text))
   self.assertEqual(self.client.get('/api/me',headers=self.headers(role)).status_code,200)
 def test_contact_without_numbers_slot_and_notes_are_saved_and_event_scoped(self):
  h=self.headers('matchmaker');r=self.client.post('/api/matchmaker-desk/contacts',headers=h,json={'name':'Example Matchmaker'});self.assertEqual(r.status_code,200,r.text);cid=r.json()['id']
  self.assertEqual(self.client.put(f'/api/matchmaker-desk/contacts/{cid}',headers=h,json={'name':'Example Matchmaker','phone':'+14055550123'}).status_code,200)
  r=self.client.post(f'/api/matchmaker-desk/events/{self.event.id}/slots',headers=h,json={'contact_id':cid,'title':'135 lb opponent needed','terms':'4 rounds; $1000 plus travel'});self.assertEqual(r.status_code,200,r.text);sid=r.json()['id']
  path=f'/api/matchmaker-desk/events/{self.event.id}/slots/{sid}'
  self.assertEqual(self.client.post(path+'/notes',headers=h,json={'body':'Called; awaiting roster.'}).status_code,200)
  self.assertEqual(self.client.patch(path,headers=h,json={'status':'contacted','version':0}).status_code,200);self.assertEqual(self.client.patch(path,headers=h,json={'status':'closed','version':0}).status_code,409)
  d=self.client.get(f'/api/matchmaker-desk/events/{self.event.id}',headers=h).json();self.assertEqual(d['slots'][0]['notes'][0]['body'],'Called; awaiting roster.');self.assertEqual(d['slots'][0]['status'],'contacted')
  self.assertEqual(self.client.get(f'/api/matchmaker-desk/events/{self.other.id}',headers=h).json()['slots'],[]);self.assertEqual(self.client.post(f'/api/matchmaker-desk/events/{self.other.id}/slots/{sid}/notes',headers=h,json={'body':'Wrong event'}).status_code,404)
 def test_desk_requires_staff_and_valid_contact_data(self):
  path=f'/api/matchmaker-desk/events/{self.event.id}';self.assertEqual(self.client.get(path).status_code,401)
  for role in ('member','fighter','rep','sponsor','investor','concessions'):self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
  for body in [{'name':' '},{'name':'Name','phone':'405-12'},{'name':'Name','email':'bad'}]:self.assertEqual(self.client.post('/api/matchmaker-desk/contacts',headers=self.headers(),json=body).status_code,422)

 def test_concessions_profile_and_assigned_updates_have_no_financials(self):
  from app.events.partners import PartnerProfile
  self.db.add(PartnerProfile(user_id=self.users['concessions'].id,title='Executive Chef',phone='+16515550123'));self.db.commit()
  self.assertEqual(self.grant('concessions',financials=True).status_code,422)
  self.assertEqual(self.grant('concessions').status_code,200)
  d=self.client.get('/api/partners/portal',headers=self.headers('concessions')).json()
  self.assertEqual(d['title'],'Executive Chef');self.assertEqual(d['role'],'concessions');self.assertEqual(len(d['events']),1)
  self.assertNotIn('financials',d['events'][0]);self.assertNotIn('current_bouts',d['events'][0]);self.assertNotIn('phone',d)

 def test_cost_only_statement_requires_event_grant_and_redacts_sensitive_records(self):
  from app.matchmaker.models import BoxingEventFee
  self.db.add(BoxingEventFee(event_id=self.event.id,name='Production',fee_key='production',actual_amount=500,paid=True));self.db.commit()
  path=f'/api/partners/events/{self.event.id}/cost-statement'
  self.assertEqual(self.client.get(path,headers=self.headers('sponsor')).status_code,403)
  self.grant('sponsor',financials=True)
  r=self.client.get(path,headers=self.headers('sponsor'));self.assertEqual(r.status_code,200,r.text)
  d=r.json();self.assertEqual(d['total_cost_cents'],95000);self.assertEqual(d['recorded_paid_cents'],50000);self.assertEqual(d['unpaid_or_unrecorded_cents'],45000)
  self.assertEqual(d['expenses'][0]['name'],'Production')
  for key in ('fighters','sellers','other_income','buyer_email','purse_hold_reason','contract_ids'):self.assertNotIn(key,r.text)
  pdf=self.client.get(path+'.pdf',headers=self.headers('sponsor'));self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF'));self.assertIn('no-store',pdf.headers['cache-control'])
  self.assertEqual(self.client.get(f'/api/partners/events/{self.other.id}/cost-statement',headers=self.headers('sponsor')).status_code,403)
  for role in ('concessions','member','fighter','rep'):self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
  portal=self.client.get('/api/partners/portal',headers=self.headers('sponsor')).json();self.assertIn('cost_statement',portal['events'][0]);self.assertNotIn('financials',portal['events'][0]);self.assertNotIn('business',portal)
  self.grant('sponsor',financials=False);self.assertEqual(self.client.get(path,headers=self.headers('sponsor')).status_code,403)
