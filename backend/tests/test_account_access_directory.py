import unittest
from datetime import datetime,timedelta
import test_stabilization as support
from app.models import User
from app.auth import create_token

class AccountAccessDirectoryTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def test_admin_gets_all_roles_statuses_and_last_sign_in_without_secrets(self):
  for role in ('investor','sponsor','concessions','manager','matchmaker'):
   self.db.add(User(name=role,email=role+'@example.com',role=role,password_hash='private-hash',active=True))
  disabled=User(name='Disabled example',email='disabled@example.com',role='staff',password_hash='private-hash',active=False);self.db.add(disabled)
  self.users['admin'].last_login=datetime(2026,11,17,14,0,0);self.users['staff'].locked_until=datetime.utcnow()+timedelta(minutes=5);self.db.commit()
  response=self.client.get('/api/users',headers=self.headers());self.assertEqual(response.status_code,200,response.text);self.assertIn('no-store',response.headers['cache-control'])
  rows=response.json();self.assertEqual(len(rows),self.db.query(User).count());self.assertTrue({'admin','staff','member','fighter','rep','investor','sponsor','concessions','manager','matchmaker'}.issubset({row['role'] for row in rows}))
  byid={row['id']:row for row in rows};self.assertEqual(byid[self.users['admin'].id]['last_login'],'2026-11-17T14:00:00Z');self.assertFalse(byid[disabled.id]['active']);self.assertIsNotNone(byid[self.users['staff'].id]['locked_until'])
  for row in rows:
   self.assertNotIn('password_hash',row);self.assertNotIn('password',row);self.assertNotIn('token',row);self.assertNotIn('mfa_secret',row);self.assertNotIn('last_login_ip',row)
 def test_directory_is_admin_only_and_does_not_change_permissions(self):
  before=[(u.id,u.role,u.active) for u in self.db.query(User).order_by(User.id)]
  self.assertEqual(self.client.get('/api/users').status_code,401)
  for role in ('staff','member','fighter','rep'):self.assertEqual(self.client.get('/api/users',headers=self.headers(role)).status_code,403)
  for role in ('investor','sponsor','concessions','manager','matchmaker'):
   u=User(name=role,email=role+'@example.com',role=role,password_hash='private-hash',active=True);self.db.add(u);self.db.commit();headers={'Authorization':'Bearer '+create_token({'sub':str(u.id)})};self.assertEqual(self.client.get('/api/users',headers=headers).status_code,403)
  self.assertEqual(before,[(u.id,u.role,u.active) for u in self.db.query(User).filter(User.id.in_([x[0] for x in before])).order_by(User.id)])
