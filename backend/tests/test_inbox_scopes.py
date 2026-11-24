import unittest
import test_text_inbox as support
from app.amateurs.directory import DirectoryContact
from app.models import Member

class InboxScopeTests(unittest.TestCase):
 setUp=support.TextInboxTests.setUp
 tearDown=support.TextInboxTests.tearDown
 headers=support.TextInboxTests.headers
 webhook=support.TextInboxTests.webhook
 def get(self,scope,**params):return self.client.get('/api/messages',headers=self.headers(),params={'scope':scope,**params})
 def test_officials_and_gym_are_disjoint_with_separate_unread_counts(self):
  self.db.add(DirectoryContact(identity_key='scope-official',kind='person',name='Test Official',phones=['4055550123'],details={'categories':['official']}));self.db.commit()
  self.webhook();self.webhook(MessageSid='SM'+'2'*32,From='+14055550456')
  o=self.get('officials').json();g=self.get('gym').json();a=self.get('all').json()
  self.assertEqual(o['inbox_counts'],{'officials':1,'gym':1,'all':2,'clubs':0});self.assertEqual(o['unread_messages'],1);self.assertEqual(g['unread_messages'],1)
  self.assertEqual([c['phone']for c in o['conversations']],['+14055550123']);self.assertEqual([c['phone']for c in g['conversations']],['+14055550456']);self.assertEqual(a['total'],2)
  self.assertEqual(self.get('gym',q='Test Official').json()['total'],0);self.assertEqual(self.get('officials',q='Test Official').json()['total'],1)
  s=self.client.get('/api/messages/summary',headers=self.headers()).json();self.assertEqual(s['officials_unread'],1);self.assertEqual(s['gym_unread'],1)
  mid=o['conversations'][0]['latest']['id'];self.client.post('/api/messages/read',headers=self.headers(),json={'phone':'+14055550123','through_id':mid})
  self.assertEqual(self.get('officials',unread_only=True).json()['total'],0);self.assertEqual(self.get('gym').json()['unread_messages'],1)
 def test_shared_member_number_stays_one_thread_under_officials_and_no_permission_inferred(self):
  self.db.add(DirectoryContact(identity_key='shared-official',kind='person',name='Test Official',phones=['4055550123'],details={'categories':['official']},sms_consent=False));m=self.db.query(Member).first();m.phone='4055550123';self.db.commit();self.webhook()
  self.assertEqual(self.get('officials').json()['total'],1);self.assertEqual(self.get('gym').json()['total'],0);self.assertEqual(self.get('all').json()['total'],1);self.assertEqual(self.get('officials').json()['conversations'][0]['name_match'],'shared')
  self.assertFalse(self.db.query(DirectoryContact).first().sms_consent)
 def test_scope_validation_and_authorization(self):
  self.assertEqual(self.get('invalid').status_code,422)
  self.assertEqual(self.client.get('/api/messages?scope=officials').status_code,401)
  self.assertEqual(self.client.get('/api/messages?scope=officials',headers=self.headers('member')).status_code,403)
