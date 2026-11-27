import unittest
from datetime import datetime,timedelta
from uuid import uuid4
import test_venue_bookings as support
from app.events.venue import VenueBooking,VenueBookingPromotion
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import EventTicketType

class YearlyEventTests(unittest.TestCase):
 setUp=support.VenueBookingTests.setUp
 tearDown=support.VenueBookingTests.tearDown
 headers=support.VenueBookingTests.headers
 body=support.VenueBookingTests.body
 add=support.VenueBookingTests.add
 update=support.VenueBookingTests.update
 def plan(self,**extra):return {'name':'Saturday Night Fights','event_date':self.day,'venue':'TNG Boxing','venue_address':'8416 NW Expressway, Oklahoma City, OK 73162',**extra}
 def create_plan(self,role='coordinator',**extra):return self.client.post('/api/venue/planning-events',headers=self.headers(role),json=self.plan(**extra))
 def year(self,year=None,role='coordinator'):
  year=year or int(self.day[:4]);return self.client.get('/api/venue/calendar',headers=self.headers(role),params={'start':f'{year}-01-01','end':f'{year+1}-01-01'})
 def test_whole_year_leap_year_and_authorized_edits_persist(self):
  r=self.create_plan();self.assertEqual(r.status_code,200,r.text);e=r.json();y=self.year();self.assertEqual(y.status_code,200,y.text);self.assertEqual(y.json()['events'][0]['name'],e['name']);self.assertTrue(y.json()['events'][0]['schedule_editable'])
  body=self.plan(name='Updated Show',schedule_version=e['schedule_version']);r=self.client.patch('/api/venue/planning-events/'+str(e['id']),headers=self.headers('coordinator'),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.db.get(BoxingEvent,e['id']).name,'Updated Show');self.assertEqual(self.client.patch('/api/venue/planning-events/'+str(e['id']),headers=self.headers(),json=body).status_code,409)
  self.assertEqual(self.year(2028).status_code,200)
 def test_role_and_conflict_checks_and_protected_ticketing(self):
  for role in ['member','fighter','staff','rep']:
   self.assertEqual(self.create_plan(role).status_code,403);self.assertEqual(self.year(role=role).status_code,403)
  e=self.create_plan().json();self.assertEqual(self.create_plan(name='Conflicting show').status_code,409)
  self.db.add(EventTicketType(event_id=e['id'],name='Admission',price_cents=4000));self.db.commit();self.assertFalse(self.year().json()['events'][0]['schedule_editable'])
  self.assertEqual(self.client.patch('/api/venue/planning-events/'+str(e['id']),headers=self.headers(),json=self.plan(schedule_version=e['schedule_version'],name='Cannot change live')).status_code,409)
 def test_booking_option_creates_one_linked_event_and_retry_is_idempotent(self):
  body=self.body(create_promotion_event=True);self.assertEqual(self.client.post('/api/venue/public/requests',json=body).status_code,403)
  r=self.client.post('/api/venue/bookings',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);eid=r.json()['promotion_event_id'];self.assertIsInstance(eid,int)
  again=self.client.post('/api/venue/bookings',headers=self.headers(),json=body);self.assertEqual(again.json()['promotion_event_id'],eid);self.assertEqual(self.db.query(BoxingEvent).count(),1);self.assertEqual(self.db.query(VenueBookingPromotion).count(),1)
  row=self.db.query(VenueBooking).one();y=self.year().json();self.assertEqual(y['bookings'][0]['promotion_event_id'],eid);self.assertEqual(y['events'][0]['booking_id'],row.id);self.assertFalse(y['events'][0]['schedule_editable'])
  self.assertEqual(self.update(row,'confirmed').status_code,200);self.db.refresh(row)
  r=self.update(row,'confirmed',title='New show name',starts_local=self.day+'T14:00',ends_local=self.day+'T17:00');self.assertEqual(r.status_code,200,r.text);self.db.refresh(row);self.db.expire_all();self.assertEqual(self.db.get(BoxingEvent,eid).name,'New show name')
  self.assertEqual(self.update(row,'cancelled').status_code,200);self.db.refresh(row);self.db.expire_all();self.assertEqual(self.db.get(BoxingEvent,eid).status,'cancelled');self.assertEqual(self.update(row,'on_hold').status_code,200)
 def test_full_day_promotion_conflict_rolls_back_booking(self):
  self.add(starts_local=self.day+'T16:00',ends_local=self.day+'T18:00');row=self.db.query(VenueBooking).one();self.assertEqual(self.update(row,'on_hold').status_code,200)
  body=self.body(request_key=str(uuid4()),create_promotion_event=True);r=self.client.post('/api/venue/bookings',headers=self.headers(),json=body);self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.db.query(VenueBooking).count(),1);self.assertEqual(self.db.query(BoxingEvent).count(),0)
 def test_booking_name_edit_remains_versioned_and_live_link_schedule_is_protected(self):
  self.add();row=self.db.query(VenueBooking).one();self.assertEqual(self.update(row,'requested',title='Renamed rental').status_code,200);self.assertEqual(self.update(row,'requested',title='Stale name').status_code,409)
  day=(datetime.fromisoformat(self.day)+timedelta(days=1)).date().isoformat();r=self.client.post('/api/venue/bookings',headers=self.headers(),json=self.body(request_key=str(uuid4()),starts_local=day+'T10:00',ends_local=day+'T13:00',create_promotion_event=True));eid=r.json()['promotion_event_id'];row=self.db.query(VenueBooking).filter(VenueBooking.id!=row.id).one();self.db.add(EventTicketType(event_id=eid,name='Admission',price_cents=4000));self.db.commit();self.assertEqual(self.update(row,'requested',title='Cannot change live').status_code,409);self.assertEqual(self.update(row,'cancelled').status_code,409)
 def test_linked_booking_can_accept_a_quote_and_confirm_without_self_conflict(self):
  r=self.client.post('/api/venue/bookings',headers=self.headers(),json=self.body(create_promotion_event=True));self.assertEqual(r.status_code,200,r.text);row=self.db.query(VenueBooking).one()
  q=self.client.post(f'/api/venue/bookings/{row.id}/quote',headers=self.headers(),json={'booking_version':row.version,'rental_cents':50000,'deposit_cents':0,'terms':'Review all facility terms before accepting.'});self.assertEqual(q.status_code,200,q.text)
  token=q.json()['quote']['url'].split('#')[1];a=self.client.post('/api/venue/quotes/public/accept',json={'token':token,'name':'Organizer Name','agree':True});self.assertEqual(a.status_code,200,a.text);self.db.refresh(row);self.assertEqual(self.update(row,'confirmed').status_code,200)
