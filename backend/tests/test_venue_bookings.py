import unittest
from datetime import datetime,timedelta
import test_stabilization as support
from app.models import User
from app.auth import create_token
from app.events.venue import VenueBooking
from app.matchmaker.models import BoxingEvent

class VenueBookingTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  u=User(name='Coordinator',email='coordinator@example.com',role='event_coordinator',active=True,password_hash='not-a-password');self.db.add(u);self.db.commit();self.users['coordinator']=u
  self.day=f'{datetime.utcnow().year+1}-01-15'
 def body(self,**extra):
  return {'title':'Example Rental','event_type':'Private event','contact_name':'Example Organizer','email':'organizer@example.com','phone':'4055550112','starts_local':self.day+'T10:00','ends_local':self.day+'T13:00','guests':50,'acknowledge':True,'request_key':'fixture-booking-0001',**extra}
 def add(self,**extra):return self.client.post('/api/venue/public/requests',json=self.body(**extra))
 def calendar(self,role='coordinator'):
  start=self.day[:7]+'-01';end=(datetime.fromisoformat(start)+timedelta(days=32)).replace(day=1).date().isoformat()
  return self.client.get('/api/venue/calendar',params={'start':start,'end':end},headers=self.headers(role))
 def update(self,row,status,**extra):return self.client.patch(f'/api/venue/bookings/{row.id}',headers=self.headers('coordinator'),json={'status':status,'staff_notes':'Internal review','version':row.version,**extra})
 def test_public_request_does_not_reserve_or_expose_contacts(self):
  r=self.add();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'requested');self.assertNotIn('email',r.json());row=self.db.query(VenueBooking).one();self.assertEqual(row.starts_at.hour,16)
  r=self.client.get('/api/venue/public/availability',params={'start':self.day,'end':(datetime.fromisoformat(self.day)+timedelta(days=1)).date().isoformat()});self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['unavailable'],[]);self.assertNotIn('organizer',r.text)
  self.assertEqual(self.calendar().json()['requests'][0]['email'],'organizer@example.com')
 def test_idempotent_retry_and_key_conflict(self):
  first=self.add();self.assertEqual(first.status_code,200,first.text);self.assertEqual(self.add().json()['reference'],first.json()['reference']);self.assertEqual(self.db.query(VenueBooking).count(),1);self.assertEqual(self.add(title='Different Event').status_code,409)
 def test_hold_blocks_overlaps_and_cancel_reopens(self):
  self.add();row=self.db.query(VenueBooking).one();r=self.update(row,'on_hold');self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.add(request_key='fixture-booking-0002').status_code,409)
  self.db.refresh(row);self.assertEqual(self.update(row,'cancelled').status_code,200)
  self.assertEqual(self.add(request_key='fixture-booking-0002').status_code,200)
 def test_overlapping_requests_cannot_both_be_confirmed_and_stale_update_rejected(self):
  self.add();self.add(request_key='fixture-booking-0002');a,b=self.db.query(VenueBooking).order_by(VenueBooking.id).all()
  self.assertEqual(self.update(a,'confirmed').status_code,200);self.assertEqual(self.update(b,'confirmed').status_code,409);self.assertEqual(self.update(a,'cancelled').status_code,409)
 def test_existing_tng_facility_event_blocks_but_other_venue_does_not(self):
  e=BoxingEvent(name='Gym Event',slug='gym-event',event_date=self.day,venue='8416 NW Expressway',status='planning');self.db.add(e);self.db.commit();self.assertEqual(self.add().status_code,409)
  e.venue='Another venue';self.db.commit();self.assertEqual(self.add().status_code,200);c=self.calendar().json();self.assertEqual(c['events'][0]['name'],'Gym Event');self.assertFalse(c['events'][0]['blocks_facility']);self.assertNotIn('purse',str(c))
 def test_coordinator_cannot_access_members_financials_users_or_fighter_pool(self):
  for p in ['/api/users','/api/members','/api/boxing/events','/api/boxing/fighters','/api/partners/access','/api/concessions/events']:
   self.assertEqual(self.client.get(p,headers=self.headers('coordinator')).status_code,403,p)
  for role in ('member','fighter','staff','rep'):
   self.assertEqual(self.calendar(role).status_code,403)
  self.assertEqual(self.calendar('admin').status_code,200)
 def test_disable_form_does_not_prevent_internal_booking(self):
  r=self.client.put('/api/venue/settings',headers=self.headers('coordinator'),json={'enabled':False,'version':1});self.assertEqual(r.status_code,200,r.text);self.assertFalse(self.client.get('/api/venue/public').json()['enabled']);self.assertEqual(self.add().status_code,409)
  self.assertEqual(self.client.post('/api/venue/bookings',headers=self.headers('coordinator'),json=self.body()).status_code,200)
 def test_invalid_dates_contact_and_honeypot_and_throttle(self):
  for body in [self.body(acknowledge=False),self.body(ends_local=self.day+'T09:00'),self.body(email='bad'),self.body(phone='123'),self.body(starts_local=self.day+'T10:00Z')]:
   self.assertEqual(self.client.post('/api/venue/public/requests',json=body).status_code,422)
  r=self.add(website_confirmation='spam');self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.db.query(VenueBooking).count(),0)
  for i in range(4):self.assertEqual(self.add(request_key='fixture-rate-'+str(i)+'-0000').status_code,200)
  self.assertEqual(self.add(request_key='fixture-rate-last-0000').status_code,429)
 def test_admin_can_create_coordinator_role_and_no_other_user_can(self):
  body={'name':'New Coordinator','email':'newcoord@example.com','password':'FixturePass12345!','role':'event_coordinator'}
  r=self.client.post('/api/users',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.db.query(User).filter_by(email='newcoord@example.com').one().role,'event_coordinator')
  self.assertEqual(self.client.post('/api/users',headers=self.headers('coordinator'),json=body).status_code,403)

 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_simultaneous_confirmations_allow_only_one_reservation(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.main import app
  from app.database import SessionLocal,get_db
  self.add();self.add(request_key='fixture-booking-0002');ids=[r.id for r in self.db.query(VenueBooking).all()];gate=Barrier(2);headers=self.headers('coordinator')
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db
  def run(i):gate.wait();return self.client.patch(f'/api/venue/bookings/{ids[i]}',headers=headers,json={'status':'confirmed','staff_notes':'','version':1}).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
  self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.db.query(VenueBooking).filter_by(status='confirmed').count(),1)

 def test_rescheduling_uses_oklahoma_time_and_rechecks_overlap(self):
  self.add();row=self.db.query(VenueBooking).one();self.assertEqual(self.update(row,'confirmed').status_code,200);self.db.refresh(row)
  r=self.update(row,'confirmed',starts_local=self.day+'T14:00',ends_local=self.day+'T17:00');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['starts_at'],self.day+'T20:00:00Z')
  self.assertEqual(self.add(request_key='fixture-booking-0002').status_code,200)
  b=self.db.query(VenueBooking).filter(VenueBooking.id!=row.id).one();self.assertEqual(self.update(b,'confirmed').status_code,200);self.db.refresh(row)
  self.assertEqual(self.update(row,'confirmed',starts_local=self.day+'T11:00',ends_local=self.day+'T17:00').status_code,409)
