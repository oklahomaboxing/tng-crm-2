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
  for role in ('investor','sponsor','matchmaker'):
   u=User(name=role,email=role+'@example.com',role=role,password_hash=hash_password('Example-only-password-123!'),active=True);self.db.add(u);self.users[role]=u
  self.db.commit()
 def test_partner_accounts_created_by_admin_only_and_no_automatic_event_access(self):
  for role in ('investor','sponsor'):
   body={'name':'New '+role,'email':'new-'+role+'@example.com','role':role,'password':'Example-only-password-123!'}
   r=self.client.post('/api/users',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text)
   r=self.client.get('/api/partners/portal',headers=self.headers(role));self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['events'],[]);self.assertIn('no-store',r.headers['cache-control'])
  self.assertEqual(self.client.post('/api/users',headers=self.headers('staff'),json=body).status_code,403)
 def grant(self,role,**extra):return self.client.put('/api/partners/access',headers=self.headers(),json={'user_id':self.users[role].id,'event_id':self.event.id,'update_text':'Your event update',**extra})
 def test_grants_are_event_specific_and_sponsor_cannot_receive_financials(self):
  self.assertEqual(self.grant('investor',financials=True).status_code,200);self.assertEqual(self.grant('sponsor',financials=True).status_code,422);self.assertEqual(self.grant('sponsor').status_code,200)
  for role in ('investor','sponsor'):
   d=self.client.get('/api/partners/portal',headers=self.headers(role)).json();self.assertEqual([e['name'] for e in d['events']],['Assigned Event']);self.assertEqual('financials' in d['events'][0],role=='investor');self.assertNotIn('fighters',d['events'][0]);self.assertNotIn('contracts',d['events'][0])
 def test_revocation_and_disabled_login_take_effect(self):
  self.grant('investor');access=self.client.get('/api/partners/access',headers=self.headers()).json();gid=access['grants'][0]['id'];self.assertEqual(self.client.delete(f'/api/partners/access/{gid}',headers=self.headers()).status_code,200);self.assertEqual(self.client.get('/api/partners/portal',headers=self.headers('investor')).json()['events'],[])
  h=self.headers('sponsor');self.users['sponsor'].active=False;self.db.commit();self.assertEqual(self.client.get('/api/partners/portal',headers=h).status_code,403)
 def test_partner_roles_cannot_access_business_operations_even_legacy_routes(self):
  for role in ('investor','sponsor'):
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
  for role in ('member','fighter','rep','sponsor','investor'):self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
  for body in [{'name':' '},{'name':'Name','phone':'405-12'},{'name':'Name','email':'bad'}]:self.assertEqual(self.client.post('/api/matchmaker-desk/contacts',headers=self.headers(),json=body).status_code,422)
