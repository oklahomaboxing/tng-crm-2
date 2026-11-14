import csv,io,unittest
import test_stabilization as support
from app.events.media import MediaApplication
from app.matchmaker.models import BoxingEvent
from app.ticketing.models import TicketOrder
from app.models import Member
class EventMediaTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def event(self,enabled=True):
  e=BoxingEvent(slug='media-night',name='Test Fight Night',event_date='2026-11-14',venue='Test Venue');self.db.add(e);self.db.commit();self.e=e;self.base=f'/api/events/{e.id}/media'
  if enabled:self.assertEqual(self.client.put(self.base+'/settings',headers=self.headers(),json={'enabled':True}).status_code,200)
  return e
 def body(self,**kw):return {'name':'Media Person','email':'press@example.com','phone':'4055550100','outlet':'Independent Sports','role':'photographer','website':'https://example.com/press','team_size':1,'coverage':'Event photos','referred_by':'Test Fighter','acknowledge':True,**kw}
 def test_public_form_is_private_and_creates_no_ticket_or_gym_membership(self):
  self.event();members=self.db.query(Member).count();orders=self.db.query(TicketOrder).count()
  metadata=self.client.get(self.base+'/public');self.assertEqual(metadata.status_code,200);self.assertTrue(metadata.json()['open']);self.assertNotIn('email',metadata.text)
  r=self.client.post(self.base+'/apply',json=self.body());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json(),{'received':True})
  row=self.db.query(MediaApplication).one();self.assertEqual(row.status,'pending');self.assertEqual(row.phone,'+14055550100');self.assertEqual(row.referred_by,'Test Fighter');self.assertEqual(self.db.query(Member).count(),members);self.assertEqual(self.db.query(TicketOrder).count(),orders)
  for path in ('/requests','/requests.csv'):self.assertEqual(self.client.get(self.base+path).status_code,401)
  for role in ('member','fighter','rep'):self.assertEqual(self.client.get(self.base+'/requests',headers=self.headers(role)).status_code,403)
 def test_duplicate_application_cannot_overwrite_staff_approval_or_details(self):
  self.event();self.client.post(self.base+'/apply',json=self.body());row=self.db.query(MediaApplication).one()
  r=self.client.put(self.base+f'/requests/{row.id}',headers=self.headers(),json={'status':'approved','staff_notes':'Private staff note'});self.assertEqual(r.status_code,200,r.text);self.assertFalse(r.json()['notification_sent'])
  again=self.client.post(self.base+'/apply',json=self.body(email='PRESS@example.com',name='Different person',outlet='Changed outlet'));self.assertEqual(again.json(),{'received':True});self.db.refresh(row);self.assertEqual(row.name,'Media Person');self.assertEqual(row.status,'approved');self.assertEqual(self.db.query(MediaApplication).count(),1)
  self.assertNotIn('Private staff note',self.client.get(self.base+'/public').text)
 def test_disabled_event_honeypot_and_validation(self):
  self.event(False);self.assertFalse(self.client.get(self.base+'/public').json()['open']);self.assertNotIn('Test Venue',self.client.get(self.base+'/public').text);self.assertEqual(self.client.post(self.base+'/apply',json=self.body()).status_code,409)
  self.client.put(self.base+'/settings',headers=self.headers(),json={'enabled':True})
  self.assertEqual(self.client.post(self.base+'/apply',json=self.body(website_confirmation='spam')).status_code,200);self.assertEqual(self.db.query(MediaApplication).count(),0)
  for changes in ({'acknowledge':False},{'website':'javascript:alert(1)'},{'team_size':11},{'name':'  '},{'phone':'invalid'}):self.assertEqual(self.client.post(self.base+'/apply',json=self.body(**changes)).status_code,422)
 def test_staff_review_and_csv_safety(self):
  self.event();self.client.post(self.base+'/apply',json=self.body(name='=Media name'));row=self.db.query(MediaApplication).one()
  r=self.client.get(self.base+'/requests',headers=self.headers('staff'));self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(len(r.json()['requests']),1)
  r=self.client.get(self.base+'/requests.csv',headers=self.headers());self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);rows=list(csv.reader(io.StringIO(r.text.lstrip('\ufeff'))));self.assertEqual(rows[1][0],"'=Media name")
  self.assertEqual(self.client.put(self.base+f'/requests/{row.id}',headers=self.headers('fighter'),json={'status':'approved'}).status_code,403)
  self.assertEqual(self.client.put(self.base+f'/requests/{row.id}',headers=self.headers(),json={'status':'issued_ticket'}).status_code,422)
 def test_rate_limit_counts_duplicate_and_bot_attempts(self):
  self.event()
  for i in range(10):self.assertEqual(self.client.post(self.base+'/apply',json=self.body(website_confirmation='bot')).status_code,200)
  r=self.client.post(self.base+'/apply',json=self.body());self.assertEqual(r.status_code,429);self.assertEqual(r.headers['retry-after'],'60');self.assertEqual(self.db.query(MediaApplication).count(),0)
