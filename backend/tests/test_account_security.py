"""Incident regressions; fixture always uses an isolated temporary database."""
import time
import unittest
from unittest.mock import patch
from test_stabilization import StabilizationTests
from app.auth import create_token, hash_password, SECRET_KEY, ALGORITHM
from app.account_security import AccountSecurity, totp, cipher
from jose import jwt


class AccountSecurityTests(StabilizationTests):
    def credentials(self):
        user=self.users['admin']
        user.password_hash=hash_password('SafePassword-123!')
        self.db.commit()
        return {'email':user.email,'password':'SafePassword-123!'}

    def enroll(self):
        credentials=self.credentials()
        headers=self.headers()
        body={'password':credentials['password']}
        setup=self.client.post('/api/auth/security/mfa/setup',json=body,headers=headers)
        self.assertEqual(setup.status_code,200,setup.text)
        self.assertEqual(self.client.get('/api/me',headers=headers).status_code,200)
        secret=setup.json()['secret']
        step=int(time.time())//30
        confirmed=self.client.post('/api/auth/security/mfa/confirm',json={**body,'code':totp(secret,step)},headers=headers)
        self.assertEqual(confirmed.status_code,200,confirmed.text)
        self.assertEqual(self.client.get('/api/me',headers=headers).status_code,401)
        return credentials,secret,step,confirmed.json()['recovery_codes']

    def test_password_reset_revokes_web_and_clover(self):
        credentials=self.credentials()
        old=self.headers()
        pos=self.client.post('/api/clover-pos/login',json=credentials).json()['token']
        changed=self.client.post('/api/users/'+str(self.users['admin'].id)+'/reset-password',json={'password':'NewPassword-456!'},headers=old)
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.get('/api/me',headers=old).status_code,401)
        self.assertEqual(self.client.get('/api/clover-pos/session',headers={'Authorization':'Bearer '+pos}).status_code,401)
        from app.academy.dependencies import academy_current_user
        from fastapi import HTTPException
        self.db.expire_all()
        with self.assertRaises(HTTPException) as rejected:
            academy_current_user(authorization=old['Authorization'],db=self.db)
        self.assertEqual(rejected.exception.status_code,401)

    def test_legacy_unsigned_binding_rejected(self):
        from datetime import datetime,timedelta,timezone
        token=jwt.encode({'sub':str(self.users['admin'].id),'exp':datetime.now(timezone.utc)+timedelta(minutes=5)},SECRET_KEY,algorithm=ALGORITHM)
        self.assertEqual(self.client.get('/api/me',headers={'Authorization':'Bearer '+token}).status_code,401)

    def test_revoke_all_sessions_requires_password(self):
        credentials=self.credentials();headers=self.headers()
        self.assertEqual(self.client.post('/api/auth/security/revoke-sessions',json={'password':'wrong'},headers=headers).status_code,401)
        self.assertEqual(self.client.get('/api/me',headers=headers).status_code,200)
        self.assertEqual(self.client.post('/api/auth/security/revoke-sessions',json={'password':credentials['password']},headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/me',headers=headers).status_code,401)
        self.assertEqual(self.client.post('/api/login',json=credentials).status_code,200)

    def test_authenticator_required_replay_rejected_and_recovery_one_use(self):
        credentials,secret,step,codes=self.enroll()
        self.assertTrue(self.client.post('/api/login',json=credentials).json()['mfa_required'])
        self.assertEqual(self.client.post('/api/login',json={**credentials,'code':totp(secret,step)}).status_code,401)
        with patch('app.account_security.time.time',return_value=(step+1)*30):
            logged=self.client.post('/api/login',json={**credentials,'code':totp(secret,step+1)})
        self.assertEqual(logged.status_code,200,logged.text)
        self.assertIn('token',logged.json())
        recovered=self.client.post('/api/login',json={**credentials,'code':codes[0]})
        self.assertEqual(recovered.status_code,200)
        self.assertIn('token',recovered.json())
        self.assertEqual(self.client.post('/api/login',json={**credentials,'code':codes[0]}).status_code,401)
        state=self.db.get(AccountSecurity,self.users['admin'].id)
        self.assertNotIn(secret,state.mfa_secret)
        self.assertNotIn(codes[0],state.recovery_hashes)

    def test_confirmation_bad_codes_lock_account(self):
        credentials=self.credentials();headers=self.headers();body={'password':credentials['password']}
        secret=self.client.post('/api/auth/security/mfa/setup',json=body,headers=headers).json()['secret']
        bad=next(f'{n:06d}' for n in range(10) if f'{n:06d}' not in [totp(secret,int(time.time())//30+i) for i in [-1,0,1]])
        for _ in range(5):
            self.assertEqual(self.client.post('/api/auth/security/mfa/confirm',json={**body,'code':bad},headers=headers).status_code,401)
        self.assertEqual(self.client.post('/api/login',json=credentials).status_code,423)

    def test_security_overview_does_not_claim_score(self):
        overview=self.client.get('/api/security/overview',headers=self.headers()).json()
        self.assertIsNone(overview['security_score'])

    def test_email_reset_revokes_sessions_and_preserves_mfa(self):
        from app.services.password_reset_service import create_password_reset_token
        credentials,secret,step,codes=self.enroll()
        login=self.client.post('/api/login',json={**credentials,'code':codes[0]})
        headers={'Authorization':'Bearer '+login.json()['token']}
        self.db.expire_all()
        user=self.db.get(type(self.users['admin']),self.users['admin'].id)
        reset=create_password_reset_token(user.id,user.password_hash)
        response=self.client.post('/api/auth/reset-password',json={'token':reset,'password':'AnotherSecure-789!','confirm_password':'AnotherSecure-789!'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.client.get('/api/me',headers=headers).status_code,401)
        again=self.client.post('/api/login',json={**credentials,'password':'AnotherSecure-789!'})
        self.assertTrue(again.json()['mfa_required'])


if __name__=='__main__':
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName('AccountSecurityTests.'+name,__import__(__name__)) for name in AccountSecurityTests.__dict__ if name.startswith('test_'))
    result=unittest.TextTestRunner().run(suite)
    raise SystemExit(not result.wasSuccessful())
