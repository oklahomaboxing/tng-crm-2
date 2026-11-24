import unittest
import test_text_inbox as support
from app.messaging.inbox import InboxMessage

class MessageNotificationTests(unittest.TestCase):
 setUp=support.TextInboxTests.setUp
 tearDown=support.TextInboxTests.tearDown
 headers=support.TextInboxTests.headers
 webhook=support.TextInboxTests.webhook
 def test_summary_private_minimal_and_clears_only_read_messages(self):
  self.assertEqual(self.client.get('/api/messages/summary').status_code,401)
  for role in ('rep','member','fighter'):
   self.assertEqual(self.client.get('/api/messages/summary',headers=self.headers(role)).status_code,403)
  for role in ('admin','staff'):
   r=self.client.get('/api/messages/summary',headers=self.headers(role));self.assertEqual(r.status_code,200);self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(r.json(),{'unread_messages':0,'latest_unread_id':None,'officials_unread':0,'gym_unread':0,'clubs_unread':0,'venue_unread':0})
  self.webhook();first=self.db.query(InboxMessage).one().id
  self.db.add(InboxMessage(phone='+14055550456',line='+14055550199',direction='outbound',body='private outgoing',status='accepted'));self.db.commit()
  self.webhook(MessageSid='SM'+'2'*32);last=self.db.query(InboxMessage).filter_by(direction='inbound').order_by(InboxMessage.id.desc()).first().id
  self.assertEqual(self.client.get('/api/messages/summary',headers=self.headers()).json(),{'unread_messages':2,'latest_unread_id':last,'officials_unread':0,'gym_unread':2,'clubs_unread':0,'venue_unread':0})
  self.client.post('/api/messages/read',headers=self.headers(),json={'phone':'+14055550123','through_id':first})
  self.assertEqual(self.client.get('/api/messages/summary',headers=self.headers()).json(),{'unread_messages':1,'latest_unread_id':last,'officials_unread':0,'gym_unread':1,'clubs_unread':0,'venue_unread':0})
  self.client.post('/api/messages/read',headers=self.headers(),json={'phone':'+14055550123','through_id':last})
  self.assertEqual(self.client.get('/api/messages/summary',headers=self.headers()).json(),{'unread_messages':0,'latest_unread_id':None,'officials_unread':0,'gym_unread':0,'clubs_unread':0,'venue_unread':0})
