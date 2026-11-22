import unittest
import test_text_inbox as support
from app.amateurs.directory import DirectoryContact
from app.models import Member,MarketingContact
from app.matchmaker.models import BoxingFighter
from app.messaging.inbox import InboxMessage

class InboxContactNameTests(unittest.TestCase):
 setUp=support.TextInboxTests.setUp
 tearDown=support.TextInboxTests.tearDown
 headers=support.TextInboxTests.headers
 webhook=support.TextInboxTests.webhook
 def contact(self,name,phones,kind='person'):
  c=DirectoryContact(identity_key=name+kind,kind=kind,name=name,phones=phones,details={});self.db.add(c);self.db.commit();return c
 def inbox(self,q=''):
  return self.client.get('/api/messages',headers=self.headers(),params={'q':q}).json()
 def test_official_name_matches_normalized_phone_in_list_thread_and_search(self):
  self.contact('Example Official',['405-555-0123']);self.webhook()
  c=self.inbox()['conversations'][0];self.assertEqual(c['display_name'],'Example Official');self.assertEqual(c['name_match'],'single');self.assertEqual(c['phone'],'+14055550123')
  thread=self.client.get('/api/messages/thread',params={'phone':c['phone']},headers=self.headers()).json();self.assertEqual(thread['matched_names'],['Example Official'])
  self.assertEqual(self.inbox('example')['total'],1);self.assertEqual(self.inbox('(405) 555-0123')['total'],1);self.assertEqual(self.inbox('missing')['total'],0)
 def test_same_name_across_sources_is_not_shared_and_unknown_stays_unknown(self):
  self.contact('Example Official',['+14055550123']);self.db.add(MarketingContact(first_name='example',last_name='official',phone='4055550123'));self.db.commit();self.webhook()
  self.assertEqual(self.inbox()['conversations'][0]['name_match'],'single')
  self.webhook(MessageSid='SM'+'2'*32,From='+14055550456');c=self.inbox()['conversations'][0];self.assertEqual(c['display_name'],'Unknown contact');self.assertEqual(c['matched_names'],[])
 def test_shared_number_shows_both_names_without_claiming_sender_identity(self):
  self.contact('Example Official',['4055550123']);self.contact('Another Person',['+14055550123']);self.webhook()
  c=self.inbox()['conversations'][0];self.assertEqual(c['display_name'],'Shared number');self.assertEqual(c['name_match'],'shared');self.assertEqual(c['matched_names'],['Another Person','Example Official']);self.assertEqual(self.inbox('another')['total'],1)
 def test_member_and_fighter_names_update_without_altering_records_or_read_status(self):
  member=self.db.query(Member).first();member.phone='4055550123';member.first_name='Member';member.last_name='Example';self.db.commit();self.webhook()
  self.assertEqual(self.inbox()['conversations'][0]['display_name'],'Member Example')
  member.first_name='Updated';self.db.commit();self.assertEqual(self.inbox()['conversations'][0]['display_name'],'Updated Example')
  self.db.add(BoxingFighter(legal_name='Fighter Example',phone='4055550456'));self.db.commit();self.webhook(MessageSid='SM'+'2'*32,From='+14055550456')
  self.assertEqual(self.inbox()['conversations'][0]['display_name'],'Fighter Example');self.assertEqual(self.inbox()['unread_messages'],2);self.assertEqual(self.db.query(InboxMessage).count(),2)
 def test_club_and_emergency_phone_do_not_claim_a_person_identity(self):
  self.contact('Shared Gym',['4055550123'],kind='club');member=self.db.query(Member).first();member.phone='invalid';member.emergency_phone='4055550123';self.db.commit();self.webhook()
  self.assertEqual(self.inbox()['conversations'][0]['name_match'],'unknown')
