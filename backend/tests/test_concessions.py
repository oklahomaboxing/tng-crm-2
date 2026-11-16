import json,unittest,os
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import User
from app.matchmaker.models import BoxingEvent
from app.events.partners import PartnerGrant
from app.events.concessions import ConcessionsMenuItem,ConcessionsShoppingItem,ConcessionsPlan

class ConcessionsTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  chef=User(name='Example Chef',email='chef@example.com',role='concessions',password_hash='not-a-password',active=True);inactive=User(name='Inactive Chef',email='inactive-chef@example.com',role='concessions',password_hash='not-a-password',active=False);self.db.add_all([chef,inactive]);self.db.flush();self.users['concessions']=chef;self.inactive=inactive
  self.event=BoxingEvent(name='New Chef Event',slug='new-chef-event',event_date='2027-01-30');self.db.add(self.event);self.db.commit();self.path=f'/api/concessions/events/{self.event.id}'
 def menu(self,**extra):return {'name':'Example Nachos','price_cents':700,'planned_quantity':100,'prep_notes':'Private equipment setup','allergens':'Contains milk',**extra}
 def shopping(self,**extra):return {'name':'Chips','store':'SAMS_CLUB','quantity':2,'unit':'cases','estimated_total_cents':2500,**extra}
 def get(self,role='concessions'):return self.client.get(self.path,headers=self.headers(role))
 def post(self,suffix,body):return self.client.post(self.path+suffix,headers=self.headers('concessions'),json=body)
 def test_new_events_auto_assign_active_chefs_and_admin_needs_no_grant(self):
  grants=self.db.query(PartnerGrant).filter_by(event_id=self.event.id).all();self.assertEqual([g.user_id for g in grants],[self.users['concessions'].id]);self.assertFalse(grants[0].financials)
  self.assertEqual(self.get().status_code,200);self.assertEqual(self.get('admin').status_code,200)
  self.assertEqual(self.db.query(PartnerGrant).filter_by(user_id=self.users['admin'].id).count(),0)
  d=self.client.get('/api/concessions/events',headers=self.headers('concessions'));self.assertEqual(d.status_code,200,d.text);self.assertIn('no-store',d.headers['cache-control']);self.assertEqual([e['id'] for e in d.json()['events']],[self.event.id])
 def test_event_creation_rollback_does_not_leave_grants(self):
  e=BoxingEvent(name='Rollback',slug='rollback');self.db.add(e);self.db.flush();eid=e.id;self.assertEqual(self.db.query(PartnerGrant).filter_by(event_id=eid).count(),1);self.db.rollback();self.assertEqual(self.db.query(PartnerGrant).filter_by(event_id=eid).count(),0)
 def test_revoked_event_access_stays_revoked_and_other_roles_blocked(self):
  self.db.query(PartnerGrant).filter_by(event_id=self.event.id).delete();self.db.commit();self.event.name='Renamed';self.db.commit();self.assertEqual(self.get().status_code,403);self.assertEqual(self.post('/menu',self.menu()).status_code,403)
  self.assertEqual(self.client.get(self.path).status_code,401)
  for role in ('member','fighter','rep'):self.assertEqual(self.get(role).status_code,403)
  for role in ('investor','sponsor'):
   u=User(name=role,email=role+'@example.com',role=role,password_hash='not-a-password',active=True);self.db.add(u);self.db.commit();self.users[role]=u;self.assertEqual(self.get(role).status_code,403)
 def test_menu_prices_costs_counts_and_stale_edit_protection(self):
  r=self.post('/menu',self.menu());self.assertEqual(r.status_code,200,r.text);mid=r.json()['id'];d=self.get().json();self.assertIsNone(d['summary']['planned_food_cost_cents']);self.assertIsNone(d['summary']['planned_gross_margin_cents']);self.assertEqual(d['summary']['planned_revenue_cents'],70000)
  body=self.menu(unit_cost_cents=200,sold_quantity=10,waste_quantity=2,version=0)
  r=self.client.put(self.path+f'/menu/{mid}',headers=self.headers('admin'),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(self.path+f'/menu/{mid}',headers=self.headers('concessions'),json=body).status_code,409)
  d=self.get().json();self.assertEqual(d['summary']['planned_food_cost_cents'],20000);self.assertEqual(d['summary']['planned_gross_margin_cents'],50000);self.assertEqual(d['summary']['sold_quantity'],10)
  self.assertEqual(self.post('/menu',self.menu(planned_quantity=1,sold_quantity=2)).status_code,422)
 def test_shopping_list_purchases_and_export(self):
  r=self.post('/shopping',self.shopping(name='=HYPERLINK("example")'));self.assertEqual(r.status_code,200,r.text);sid=r.json()['id']
  r=self.client.put(self.path+f'/shopping/{sid}',headers=self.headers('concessions'),json=self.shopping(name='=HYPERLINK("example")',purchased=True,actual_total_cents=2700,version=0));self.assertEqual(r.status_code,200,r.text)
  d=self.get().json();self.assertEqual(d['summary']['shopping_estimate_cents'],2500);self.assertEqual(d['summary']['shopping_actual_cents'],2700);self.assertEqual(d['summary']['purchased_lines'],1)
  export=self.client.get(self.path+'/shopping.csv',headers=self.headers('admin'));self.assertEqual(export.status_code,200);self.assertIn("'=HYPERLINK",export.text);self.assertIn("Sam's Club",export.text)
  self.assertEqual(self.post('/shopping',self.shopping(store='UNKNOWN')).status_code,422)
  self.assertEqual(self.post('/shopping',self.shopping(quantity='NaN')).status_code,422)
 def test_publish_freezes_customer_fields_only_until_republished(self):
  self.assertEqual(self.post('/publish',{'version':0}).status_code,422)
  mid=self.post('/menu',self.menu(unit_cost_cents=234)).json()['id'];version=self.get().json()['version'];r=self.post('/publish',{'version':version});self.assertEqual(r.status_code,200,r.text)
  snapshot=self.get().json()['published_menu'];item=snapshot['items'][0];self.assertEqual(item['price_cents'],700);self.assertNotIn('unit_cost_cents',item);self.assertNotIn('prep_notes',item)
  self.client.put(self.path+f'/menu/{mid}',headers=self.headers('concessions'),json=self.menu(price_cents=900,version=0));self.assertEqual(self.get().json()['published_menu']['items'][0]['price_cents'],700)
  pdf=self.client.get(self.path+'/menu.pdf',headers=self.headers('concessions'));self.assertEqual(pdf.status_code,200,pdf.text[:100] if pdf.status_code!=200 else '');self.assertTrue(pdf.content.startswith(b'%PDF'));self.assertIn('no-store',pdf.headers['cache-control'])
  self.assertEqual(self.post('/publish',{'version':version}).status_code,409)
 def test_prep_notes_versions_and_scope(self):
  r=self.client.put(self.path+'/notes',headers=self.headers('admin'),json={'notes':'Set up station at 3 PM','version':0});self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.get().json()['notes'],'Set up station at 3 PM');self.assertEqual(self.client.put(self.path+'/notes',headers=self.headers('concessions'),json={'notes':'stale','version':0}).status_code,409)
 def test_template_generation_is_honest_and_apply_is_idempotent(self):
  with patch.dict(os.environ,{'OPENAI_API_KEY':''}):r=self.post('/draft',{'expected_guests':200,'preferences':'Fast service'})
  self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(d['engine'],'starter_template');self.assertIn('not AI-generated',d['notice']);self.assertEqual(self.db.query(ConcessionsMenuItem).count(),0)
  for _ in range(2):self.assertEqual(self.post('/draft/apply',d).status_code,200)
  self.assertEqual(self.db.query(ConcessionsMenuItem).count(),len(d['menu']));self.assertEqual(self.db.query(ConcessionsShoppingItem).count(),len(d['shopping']));self.assertTrue(all(m.sold_quantity==0 and m.unit_cost_cents is None for m in self.db.query(ConcessionsMenuItem)))
 def test_ai_draft_is_validated_and_cannot_assert_purchases_or_food_costs(self):
  client=Mock();client.with_options.return_value=client
  body={'menu':[self.menu(unit_cost_cents=1,allergens='AI claims no allergens',sold_quantity=20)],'shopping':[self.shopping(purchased=True,actual_total_cents=12)]}
  client.chat.completions.create.return_value=Mock(choices=[Mock(message=Mock(content=json.dumps(body)))])
  with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture'}),patch('app.ai.client.client',client):r=self.post('/draft',{'expected_guests':100})
  self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(d['engine'],'ai');self.assertIsNone(d['menu'][0]['unit_cost_cents']);self.assertEqual(d['menu'][0]['allergens'],'');self.assertEqual(d['menu'][0]['sold_quantity'],0);self.assertFalse(d['shopping'][0]['purchased']);self.assertIsNone(d['shopping'][0]['actual_total_cents']);self.assertEqual(self.db.query(ConcessionsMenuItem).count(),0)
 def test_ai_failure_returns_labeled_template_and_no_saved_items(self):
  client=Mock();client.with_options.side_effect=RuntimeError('fixture provider failure')
  with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture'}),patch('app.ai.client.client',client):r=self.post('/draft',{'expected_guests':100})
  self.assertEqual(r.status_code,200);self.assertEqual(r.json()['engine'],'starter_template');self.assertIn('unavailable',r.json()['notice']);self.assertEqual(self.db.query(ConcessionsMenuItem).count(),0)
 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_simultaneous_draft_import_does_not_duplicate_items(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.database import SessionLocal,get_db
  from app.main import app
  headers=self.headers('concessions');gate=Barrier(2)
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db
  body={'request_key':'parallel-fixture-key','menu':[self.menu()],'shopping':[self.shopping()]}
  def run(_):gate.wait();return self.client.post(self.path+'/draft/apply',headers=headers,json=body).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
  self.assertEqual(statuses,[200,200]);self.assertEqual(self.db.query(ConcessionsMenuItem).count(),1);self.assertEqual(self.db.query(ConcessionsShoppingItem).count(),1)
 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_shared_menu_edits_do_not_silently_overwrite(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.database import SessionLocal,get_db
  from app.main import app
  mid=self.post('/menu',self.menu()).json()['id'];headers=self.headers('concessions');gate=Barrier(2)
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db
  def run(n):gate.wait();return self.client.put(self.path+f'/menu/{mid}',headers=headers,json=self.menu(price_cents=800+n,version=0)).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
  self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.db.get(ConcessionsMenuItem,mid).version,1)
