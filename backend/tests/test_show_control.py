import unittest,json
import test_stabilization as support
from app.models import User
from app.events.show_control import ShowAssignment,ShowSong,ShowCue
from app.matchmaker.models import BoxingEvent,BoxingBout,BoxingFighter
from app.revenue.models import RevenueOrganization,EventRevenueProspect
class ShowTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  for role in ['announcer','dj','sponsor']:
   u=User(name='Example '+role,email=role+'-show@example.com',role=role,active=True,password_hash='not-a-password');self.db.add(u);self.users[role]=u
  self.event=BoxingEvent(name='Example show',slug='show-event',event_date='2027-01-30');self.red=BoxingFighter(legal_name='Example Red',pro_record='1-0',phone='PRIVATE-PHONE',email='PRIVATE@example.com',bloodwork_notes='PRIVATE MEDICAL');self.blue=BoxingFighter(legal_name='Example Blue',pro_record='2-1');self.db.add_all([self.event,self.red,self.blue]);self.db.flush();self.db.add(BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,bout_order=1,status='booked',red_purse=12345,blue_purse=54321));self.db.commit();self.path=f'/api/show-control/events/{self.event.id}'
 def assign(self,role):
  self.db.add(ShowAssignment(event_id=self.event.id,user_id=self.users[role].id));self.db.commit()
 def cue(self,**extra):return {'title':'Concessions now','kind':'concessions','owner':'announcer','script':'Visit concessions between bouts','request_key':'5d426e15-2c1a-4c23-ad98-ea1406d11061',**extra}
 def test_assigned_only_no_members_financials_or_other_events(self):
  self.assertEqual(self.client.get('/api/show-control').status_code,401)
  for role in ['announcer','dj']:self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)
  self.assign('announcer');r=self.client.get(self.path,headers=self.headers('announcer'));self.assertEqual(r.status_code,200,r.text)
  for secret in ['PRIVATE-PHONE','PRIVATE@example.com','PRIVATE MEDICAL','12345','54321','password_hash']:self.assertNotIn(secret,r.text)
  self.assertEqual(self.client.get('/api/members',headers=self.headers('announcer')).status_code,403);self.assertEqual(self.client.get('/api/partners/business-admin',headers=self.headers('dj')).status_code,403)
  self.assertEqual(self.client.get('/api/show-control',headers=self.headers('sponsor')).status_code,403)
 def test_grant_revoke_and_only_correct_user_roles(self):
  for role in ['announcer','dj','sponsor']:self.assertEqual(self.client.put(self.path+'/assignment',headers=self.headers(role),json={'user_id':self.users['dj'].id}).status_code,403)
  r=self.client.put(self.path+'/assignment',headers=self.headers(),json={'user_id':self.users['dj'].id});self.assertEqual(r.status_code,200);self.assertEqual(len(self.client.get('/api/show-control',headers=self.headers('dj')).json()['events']),1)
  self.assertEqual(self.client.put(self.path+'/assignment',headers=self.headers(),json={'user_id':self.users['dj'].id,'enabled':False}).status_code,200);self.assertEqual(self.client.get(self.path,headers=self.headers('dj')).status_code,403)
  self.assertEqual(self.client.put(self.path+'/assignment',headers=self.headers(),json={'user_id':self.users['sponsor'].id}).status_code,422)
 def test_dj_song_edits_are_event_scoped_versioned_and_not_played(self):
  self.assign('dj');self.assign('announcer');body={'title':'Walkout track','artist':'Example Artist','source_url':'https://example.com/track','start_seconds':35,'confirmed':True,'clean_version':True,'version':0}
  r=self.client.put(self.path+'/songs/'+str(self.red.id),headers=self.headers('dj'),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(self.path+'/songs/'+str(self.red.id),headers=self.headers('dj'),json=body).status_code,409);self.assertEqual(self.client.put(self.path+'/songs/'+str(self.blue.id),headers=self.headers('announcer'),json=body).status_code,403)
  self.assertEqual(self.client.put(self.path+'/songs/999999',headers=self.headers('dj'),json=body).status_code,409);d=self.client.get(self.path,headers=self.headers('announcer')).json();self.assertEqual(d['card'][0]['red']['song']['start_seconds'],35)
  body['source_url']='javascript:alert(1)';self.assertEqual(self.client.put(self.path+'/songs/'+str(self.blue.id),headers=self.headers('dj'),json=body).status_code,422)
 def test_draft_requires_staff_approval_and_role_completion(self):
  self.assign('announcer');self.assign('dj');r=self.client.post(self.path+'/cues',headers=self.headers('announcer'),json=self.cue());self.assertEqual(r.status_code,200,r.text);cid=r.json()['id'];self.assertEqual(self.client.post(self.path+'/cues/'+str(cid)+'/done',headers=self.headers('announcer'),json={'version':1}).status_code,409)
  self.assertEqual(self.client.put(self.path+'/cues/'+str(cid),headers=self.headers('announcer'),json=self.cue(approved=True,version=1)).status_code,403)
  self.assertEqual(self.client.put(self.path+'/cues/'+str(cid),headers=self.headers(),json=self.cue(approved=True,version=1)).status_code,200)
  self.assertEqual(self.client.post(self.path+'/cues/'+str(cid)+'/done',headers=self.headers('dj'),json={'version':2}).status_code,403)
  self.assertEqual(self.client.post(self.path+'/cues/'+str(cid)+'/done',headers=self.headers('announcer'),json={'version':2}).status_code,200)
  self.assertEqual(self.client.post(self.path+'/cues/'+str(cid)+'/done',headers=self.headers('announcer'),json={'version':2}).status_code,409)
 def test_cue_idempotency_versions_and_pdf_export(self):
  r=self.client.post(self.path+'/cues',headers=self.headers(),json=self.cue());cid=r.json()['id'];self.assertEqual(self.client.post(self.path+'/cues',headers=self.headers(),json=self.cue()).json()['id'],cid);self.assertEqual(self.db.query(ShowCue).count(),1)
  self.assertEqual(self.client.put(self.path+'/cues/'+str(cid),headers=self.headers(),json=self.cue(version=99)).status_code,409)
  r=self.client.get(self.path+'/run-of-show.pdf',headers=self.headers());self.assertEqual(r.status_code,200,r.text[:100]);self.assertTrue(r.content.startswith(b'%PDF'));self.assertIn('no-store',r.headers['cache-control'])
 def test_sponsor_templates_only_include_event_commitments_not_leads(self):
  for name,status in [('Approved sponsor','PAID'),('PRIVATE prospect','NEW')]:
   o=RevenueOrganization(business_name=name);self.db.add(o);self.db.flush();self.db.add(EventRevenueProspect(event_id=self.event.id,organization_id=o.id,prospect_type='SPONSOR',status=status))
  self.db.commit();d=self.client.get(self.path,headers=self.headers()).json();self.assertIn('Approved sponsor',d['sponsors']);self.assertNotIn('PRIVATE prospect',json.dumps(d));self.assertIn('No loud music',json.dumps(d))
 def test_profiles_are_self_or_admin_only(self):
  uid=self.users['dj'].id;url='/api/show-control/profiles/'+str(uid)
  self.assertEqual(self.client.put(url,headers=self.headers('dj'),json={'title':'House DJ','phone':'4055550123'}).status_code,200)
  self.assertEqual(self.client.put(url,headers=self.headers('announcer'),json={'title':'Bad','phone':''}).status_code,403)
 def test_new_show_account_roles_are_available_without_auto_event_grants(self):
  for role in ['announcer','dj']:
   r=self.client.post('/api/users',headers=self.headers(),json={'name':'New '+role,'email':'new-'+role+'@example.com','password':'ExampleStrongPassword123!','role':role});self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.db.query(ShowAssignment).count(),0)
