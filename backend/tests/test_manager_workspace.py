import unittest
from datetime import datetime
import test_stabilization as support
from app.models import User
from app.auth import create_token,decode_token
from app.matchmaker.models import BoxingFighter,BoxingManagerAccount,BoxingManagerFighter,BoxingEvent,BoxingBout,BoxingContract
from app.fighter_portal.models import FighterAccount
from app.managers.routes import ManagerRosterSubmission

class ManagerWorkspaceTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.managers={}
  for role in ('manager','other_manager'):
   u=User(name=role,email=role+'@example.com',role='manager',password_hash='not-a-password',active=True);self.db.add(u);self.db.flush();self.users[role]=u;m=BoxingManagerAccount(user_id=u.id,display_name=role,email=u.email,active=True);self.db.add(m);self.db.flush();self.managers[role]=m
  self.a=BoxingFighter(legal_name='Boxer Alpha',boxrec_id='100001',email='alpha@example.com',phone='405-555-0101',pro_record='2-1');self.b=BoxingFighter(legal_name='Boxer Bravo',boxrec_id='100002',email='bravo@example.com');self.c=BoxingFighter(legal_name='Boxer Charlie',boxrec_id='100003',email='charlie@example.com');self.db.add_all([self.a,self.b,self.c]);self.db.flush()
  self.db.add_all([BoxingManagerFighter(manager_account_id=self.managers['manager'].id,fighter_id=self.a.id,active=True),BoxingManagerFighter(manager_account_id=self.managers['manager'].id,fighter_id=self.c.id,active=True),BoxingManagerFighter(manager_account_id=self.managers['other_manager'].id,fighter_id=self.b.id,active=True),FighterAccount(user_id=self.users['fighter'].id,fighter_id=self.a.id)])
  self.event=BoxingEvent(name='Managed Event',slug='managed-event',event_date='2027-01-30');self.db.add(self.event);self.db.flush();self.bout=BoxingBout(event_id=self.event.id,red_fighter_id=self.a.id,blue_fighter_id=self.c.id,rounds=4,weight_agreed=135,status='draft');self.db.add(self.bout);self.db.flush();self.contract=BoxingContract(event_id=self.event.id,bout_id=self.bout.id,fighter_id=self.a.id,opponent_id=self.c.id,corner='red',status='sent',gross_purse=1000);self.db.add(self.contract);self.db.commit()
 def scope(self,fid,role='manager'):
  r=self.client.post(f'/api/manager-workspace/fighters/{fid}/token',headers=self.headers(role));self.assertEqual(r.status_code,200,r.text);return {'Authorization':'Bearer '+r.json()['token']}
 def add(self,**extra):
  body={'legal_name':'New Boxer','email':'newboxer@example.com','boxrec_id':'999991','pro_record':'0-0','request_key':'fixture-new-0001',**extra};return self.client.post('/api/manager-workspace/fighters',headers=self.headers('manager'),json=body)
 def test_manager_selects_only_active_own_roster_and_token_preserves_actor(self):
  r=self.client.get('/api/manager-workspace/roster',headers=self.headers('manager'));self.assertEqual(r.status_code,200,r.text);self.assertEqual({f['id'] for f in r.json()['fighters']},{self.a.id,self.c.id});self.assertIn('no-store',r.headers['cache-control'])
  h=self.scope(self.a.id);payload=decode_token(h['Authorization'][7:]);self.assertEqual(payload['sub'],str(self.users['manager'].id));self.assertEqual(payload['managed_fighter_id'],self.a.id)
  d=self.client.get('/api/fighter/me',headers=h);self.assertEqual(d.status_code,200,d.text);self.assertEqual(d.json()['fighter']['id'],self.a.id);self.assertEqual(d.json()['user']['role'],'manager')
  self.assertEqual(self.client.post(f'/api/manager-workspace/fighters/{self.b.id}/token',headers=self.headers('manager')).status_code,403)
  self.assertEqual(self.client.get('/api/fighter/me',headers=self.headers('manager')).status_code,403)
 def test_scoped_token_cannot_switch_fighter_escalate_or_personally_sign(self):
  h=self.scope(self.a.id)
  for path in ['/api/users','/api/boxing/fighters',f'/api/events/fighters/{self.c.id}/contribution',f'/api/events/fighters/{self.b.id}/results',f'/api/fighter/me/contracts/{self.contract.id}/docusign-signing-url']:
   self.assertEqual(self.client.get(path,headers=h).status_code,403,path)
  self.assertEqual(self.client.post(f'/api/fighter/me/contracts/{self.contract.id}/esign',headers=h,json={}).status_code,403)
  self.assertEqual(self.client.post(f'/api/manager-workspace/fighters/{self.c.id}/token',headers=h).status_code,403)
  r=self.client.get('/api/fighter/me?fighter_id='+str(self.b.id),headers=h);self.assertEqual(r.json()['fighter']['id'],self.a.id)
 def test_reused_portal_features_and_reports_are_scoped(self):
  h=self.scope(self.a.id)
  for path in ['/api/fighter/me/contracts','/api/fighter/me/ticket-sales','/api/fighter/me/photos','/api/fighter/me/videos','/api/fighter/me/fight-offers',f'/api/events/fighters/{self.a.id}/contribution',f'/api/events/fighters/{self.a.id}/results']:
   r=self.client.get(path,headers=h);self.assertEqual(r.status_code,200,(path,r.text))
  contracts=self.client.get('/api/fighter/me/contracts',headers=h).json();self.assertIn(str(self.contract.id),str(contracts))
 def test_new_boxer_enters_pool_and_roster_once_without_a_second_login(self):
  before=self.db.query(User).count();r=self.add();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'added');fid=r.json()['fighter_id'];self.assertEqual(self.add().json()['fighter_id'],fid)
  self.assertEqual(self.db.query(BoxingFighter).filter_by(boxrec_id='999991').count(),1);self.assertTrue(self.db.query(BoxingManagerFighter).filter_by(fighter_id=fid,manager_account_id=self.managers['manager'].id,active=True).first());f=self.db.get(BoxingFighter,fid);self.assertEqual(f.source,'manager_portal');self.assertEqual(f.bloodwork_status,'missing');self.assertEqual(f.suspension_status,'needs_review');self.assertEqual(self.db.query(User).count(),before)
  self.assertEqual(self.scope(fid)['Authorization'].startswith('Bearer '),True)
 def test_existing_boxer_requires_review_and_is_not_duplicated_or_claimed(self):
  before=self.db.query(BoxingFighter).count();r=self.add(legal_name='Boxer Bravo',email='bravo@example.com',boxrec_id='100002');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'needs_review');self.assertIsNone(r.json()['fighter_id']);self.assertEqual(self.db.query(BoxingFighter).count(),before)
  requests=self.client.get('/api/manager-workspace/roster-requests',headers=self.headers()).json();self.assertEqual(len(requests),1);review='/api/manager-workspace/roster-requests/'+str(requests[0]['id'])+'/review'
  self.assertEqual(self.client.post(review,headers=self.headers('manager'),json={'decision':'approve'}).status_code,403)
  self.assertEqual(self.client.post(review,headers=self.headers(),json={'decision':'approve'}).status_code,409)
  link=self.db.query(BoxingManagerFighter).filter_by(fighter_id=self.b.id,active=True).one();link.active=False;self.db.commit();self.assertEqual(self.client.post(review,headers=self.headers(),json={'decision':'approve'}).status_code,200);self.assertEqual(self.client.get('/api/fighter/me',headers=self.scope(self.b.id)).status_code,200)
 def test_release_revokes_existing_tokens_preserves_boxer_account_contracts_and_pool(self):
  h=self.scope(self.a.id);r=self.client.delete(f'/api/manager-workspace/fighters/{self.a.id}',headers=self.headers('manager'));self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['fighter_pool_record_preserved']);self.assertEqual(self.client.get('/api/fighter/me',headers=h).status_code,403);self.assertIsNotNone(self.db.get(BoxingFighter,self.a.id));self.assertIsNotNone(self.db.get(BoxingContract,self.contract.id));self.assertEqual(self.client.get('/api/fighter/me',headers=self.headers('fighter')).status_code,200)
 def test_disabled_manager_profile_stops_previously_minted_token(self):
  h=self.scope(self.a.id);self.managers['manager'].active=False;self.db.commit();self.assertEqual(self.client.get('/api/fighter/me',headers=h).status_code,403)
 def test_profile_edits_are_versioned_and_cannot_set_approvals_or_official_record(self):
  d=self.client.get('/api/manager-workspace/roster',headers=self.headers('manager')).json();f=next(x for x in d['fighters'] if x['id']==self.a.id)
  from app.managers.routes import ProfileBody
  body={k:f[k] for k in ProfileBody.model_fields};body.update(expected_updated_at=f['updated_at'],city='Dallas')
  path=f'/api/manager-workspace/fighters/{self.a.id}';r=self.client.put(path,headers=self.headers('manager'),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(path,headers=self.headers('manager'),json=body).status_code,409)
  self.assertEqual(self.client.put(path,headers=self.headers('manager'),json={**body,'bloodwork_status':'approved'}).status_code,422)
  self.assertEqual(self.client.put(path,headers=self.headers('other_manager'),json=body).status_code,403);self.db.refresh(self.a);self.assertEqual(self.a.city,'Dallas');self.assertEqual(self.a.pro_record,'2-1')
 def test_device_revocation_also_revokes_workspace_token(self):
  from app.auth_sessions import persistent_token,RememberedDevice
  token=persistent_token(self.db,self.users['manager']);r=self.client.post(f'/api/manager-workspace/fighters/{self.a.id}/token',headers={'Authorization':'Bearer '+token});self.assertEqual(r.status_code,200,r.text);scoped=r.json()['token'];self.db.query(RememberedDevice).filter_by(user_id=self.users['manager'].id).update({'revoked':True});self.db.commit();self.assertEqual(self.client.get('/api/fighter/me',headers={'Authorization':'Bearer '+scoped}).status_code,401)
 def test_normal_boxer_cannot_use_manager_endpoints_and_invalid_profiles_do_not_create_pool_rows(self):
  self.assertEqual(self.client.get('/api/manager-workspace/roster').status_code,401)
  for role in ('fighter','member','rep','staff','admin'):self.assertEqual(self.client.get('/api/manager-workspace/roster',headers=self.headers(role)).status_code,403)
  self.assertEqual(self.add(boxrec_id='',email='',phone='').status_code,422);self.assertEqual(self.add(bloodwork_status='approved').status_code,422);self.assertEqual(self.add(available_weight_min=150,available_weight_max=130).status_code,422)

 def test_removed_boxer_offers_are_no_longer_listed(self):
  from app.matchmaker.models import BoxingFightOffer
  offer=BoxingFightOffer(event_id=self.event.id,fighter_id=self.a.id,manager_account_id=self.managers['manager'].id,recipient_user_id=self.users['manager'].id,status='sent')
  self.db.add(offer);self.db.commit()
  path='/api/boxing/manager/me/offers'
  before=self.client.get(path,headers=self.headers('manager'));self.assertEqual(before.status_code,200,before.text);self.assertIn(offer.id,[r['id'] for r in before.json()])
  self.client.delete(f'/api/manager-workspace/fighters/{self.a.id}',headers=self.headers('manager'))
  after=self.client.get(path,headers=self.headers('manager'));self.assertEqual(after.status_code,200,after.text);self.assertNotIn(offer.id,[r['id'] for r in after.json()])
 def test_save_key_cannot_be_reused_for_a_different_boxer(self):
  self.assertEqual(self.add().status_code,200)
  self.assertEqual(self.add(legal_name='Different Boxer').status_code,409)

 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_simultaneous_manager_submissions_create_one_pool_boxer(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.main import app
  from app.database import SessionLocal,get_db
  gate=Barrier(2);headers=[self.headers('manager'),self.headers('other_manager')]
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db
  body={'legal_name':'Concurrent Boxer','email':'concurrent@example.com','boxrec_id':'999993','request_key':'concurrent-fixture-1'}
  def run(i):
   gate.wait();r=self.client.post('/api/manager-workspace/fighters',headers=headers[i],json=body);self.assertEqual(r.status_code,200,r.text);return r.json()['status']
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
  self.assertEqual(sorted(statuses),['added','needs_review']);self.assertEqual(self.db.query(BoxingFighter).filter_by(boxrec_id='999993').count(),1)
  fighter=self.db.query(BoxingFighter).filter_by(boxrec_id='999993').one();self.assertEqual(self.db.query(BoxingManagerFighter).filter_by(fighter_id=fighter.id,active=True).count(),1)
