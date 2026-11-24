import unittest
from datetime import datetime,timedelta
import test_text_inbox as support
from app.amateurs.directory import DirectoryContact
from app.events.venue import VenueBooking
from app.messaging.inbox import InboxMessage
from app.messaging.routing import InboxConversation
from app.models import Member

class DedicatedInboxTests(unittest.TestCase):
 setUp=support.TextInboxTests.setUp
 tearDown=support.TextInboxTests.tearDown
 headers=support.TextInboxTests.headers
 webhook=support.TextInboxTests.webhook
 def inbox(self,scope):return self.client.get('/api/messages',headers=self.headers(),params={'scope':scope}).json()
 def venue(self,phone='+14055550456'):
  now=datetime.utcnow();row=VenueBooking(reference='TNG-V-FIXTURE',request_key='venue-fixture',title='Example event',event_type='Private party',contact_name='Example Organizer',email='organizer@example.com',phone=phone,starts_at=now+timedelta(days=10),ends_at=now+timedelta(days=10,hours=2));self.db.add(row);self.db.commit()
 def test_club_venue_gym_and_official_views_are_disjoint(self):
  self.db.add_all([DirectoryContact(identity_key='club',kind='club',name='Example Club',phones=['4055550123'],details={'state':'OK'}),DirectoryContact(identity_key='official',kind='person',name='Example Official',phones=['4055550789'],details={'categories':['official']})]);self.db.commit();self.venue()
  self.webhook();self.webhook(MessageSid='SM'+'2'*32,From='+14055550456');self.webhook(MessageSid='SM'+'3'*32,From='+14055550789');self.webhook(MessageSid='SM'+'4'*32,From='+14055550999')
  groups={k:self.inbox(k)for k in ['gym','clubs','officials','venue','all']}
  self.assertEqual(groups['all']['total'],4)
  for scope in ['gym','clubs','officials','venue']:self.assertEqual(groups[scope]['total'],1);self.assertEqual(groups[scope]['unread_messages'],1)
  sets=[{c['phone']for c in groups[k]['conversations']}for k in ['gym','clubs','officials','venue']];self.assertEqual(len(set.union(*sets)),sum(map(len,sets)))
  v=groups['venue']['conversations'][0];self.assertEqual(v['display_name'],'Example Organizer')
  s=self.client.get('/api/messages/summary',headers=self.headers()).json();self.assertEqual(sum(s[k+'_unread']for k in ['gym','clubs','venue','officials']),s['unread_messages'])
 def test_move_persists_for_shared_numbers_without_changing_messages_consent_or_members(self):
  self.db.add(DirectoryContact(identity_key='club',kind='club',name='Example Club',phones=['4055550123'],details={'state':'OK'},sms_consent=False));self.db.commit();self.venue('+14055550123');self.webhook()
  self.assertEqual(self.inbox('venue')['total'],1);before=(self.db.query(InboxMessage).count(),self.db.query(Member).count());row=self.db.query(InboxMessage).one();body=row.body
  r=self.client.post('/api/messages/move',headers=self.headers(),json={'phone':'4055550123','folder':'clubs'});self.assertEqual(r.status_code,200);self.assertEqual(self.inbox('venue')['total'],0);self.assertEqual(self.inbox('clubs')['total'],1)
  self.db.expire_all();self.assertEqual(self.db.query(InboxConversation).one().folder,'clubs');self.assertEqual(self.db.query(InboxMessage).one().body,body);self.assertIsNone(self.db.query(InboxMessage).one().read_at);self.assertFalse(self.db.query(DirectoryContact).one().sms_consent);self.assertEqual(before,(self.db.query(InboxMessage).count(),self.db.query(Member).count()))
  self.client.post('/api/messages/move',headers=self.headers(),json={'phone':'4055550123','folder':'auto'});self.assertEqual(self.inbox('venue')['total'],1);self.assertEqual(self.db.query(InboxConversation).count(),0)
 def test_move_auth_validation_and_later_messages_follow_saved_inbox(self):
  self.webhook();payload={'phone':'4055550123','folder':'venue'}
  self.assertEqual(self.client.post('/api/messages/move',json=payload).status_code,401);self.assertEqual(self.client.post('/api/messages/move',headers=self.headers('member'),json=payload).status_code,403)
  self.assertEqual(self.client.post('/api/messages/move',headers=self.headers(),json={**payload,'folder':'invalid'}).status_code,422)
  self.assertEqual(self.client.post('/api/messages/move',headers=self.headers(),json={**payload,'phone':'4055550999'}).status_code,404)
  self.client.post('/api/messages/move',headers=self.headers('staff'),json=payload);self.webhook(MessageSid='SM'+'2'*32);self.assertEqual(self.inbox('venue')['total'],1);self.assertEqual(self.inbox('venue')['unread_messages'],2);self.assertEqual(self.inbox('gym')['total'],0)

 def test_latest_work_text_routes_shared_number_but_staff_override_wins(self):
  self.venue('+14055550123');self.webhook();self.assertEqual(self.inbox('venue')['total'],1)
  self.db.add(InboxMessage(phone='+14055550123',line='+14055550199',direction='outbound',request_key='club:fixture',body='Club logistics',status='accepted'));self.db.commit();self.assertEqual(self.inbox('clubs')['total'],1)
  self.client.post('/api/messages/move',headers=self.headers(),json={'phone':'4055550123','folder':'venue'})
  self.db.add(InboxMessage(phone='+14055550123',line='+14055550199',direction='outbound',request_key='official:fixture',body='Official logistics',status='accepted'));self.db.commit();self.assertEqual(self.inbox('venue')['total'],1)
  self.client.post('/api/messages/move',headers=self.headers(),json={'phone':'4055550123','folder':'auto'});self.assertEqual(self.inbox('officials')['total'],1)
