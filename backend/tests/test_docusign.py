"""Offline DocuSign diagnostics; provider calls mocked, no contracts sent."""
import os
import unittest
from unittest.mock import Mock, patch
import requests
import test_stabilization as support
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.matchmaker.routes import _docusign_access_token

class DocuSignTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers

    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.pem = cls.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()).decode()
        cls.config = {'DOCUSIGN_INTEGRATION_KEY':'test-integration-ABC123', 'DOCUSIGN_USER_ID':'test-user',
            'DOCUSIGN_ACCOUNT_ID':'test-account', 'DOCUSIGN_PRIVATE_KEY':cls.pem,
            'DOCUSIGN_AUTH_SERVER':'account-d.docusign.com', 'DOCUSIGN_BASE_URI':'https://demo.docusign.net'}

    def check(self):
        return self.client.post('/api/boxing/docusign/connection-check', headers=self.headers())

    def test_connection_check_verifies_account_without_envelope_or_secret_disclosure(self):
        response = Mock(ok=True); response.json.return_value = {'accounts':[{'account_id':'test-account','base_uri':'https://demo.docusign.net'}]}
        with patch.dict(os.environ,self.config), patch('app.matchmaker.routes._docusign_access_token',return_value='fake-access-token'), patch('requests.get',return_value=response) as get, patch('requests.post') as post:
            r=self.check(); self.assertEqual(r.status_code,200,r.text)
            self.assertTrue(r.json()['ready']); self.assertTrue(r.json()['no_contracts_sent'])
            self.assertEqual(r.json()['integration_key_suffix'],'ABC123')
            self.assertEqual(get.call_args.args[0],'https://account-d.docusign.com/oauth/userinfo')
            post.assert_not_called()
            self.assertNotIn('fake-access-token',r.text); self.assertNotIn('PRIVATE KEY',r.text)

    def test_connection_check_rejects_wrong_account_or_api_base(self):
        for accounts,message in [([], 'does not have access'), ([{'account_id':'test-account','base_uri':'https://na2.docusign.net'}], 'DOCUSIGN_BASE_URI')]:
            response=Mock(ok=True);response.json.return_value={'accounts':accounts}
            with patch.dict(os.environ,self.config),patch('app.matchmaker.routes._docusign_access_token',return_value='fake'),patch('requests.get',return_value=response):
                r=self.check();self.assertFalse(r.json()['ready']);self.assertIn(message,r.json()['message'])

    def test_rsa_mismatch_is_actionable_and_does_not_expose_provider_body(self):
        response=Mock(ok=False);response.json.return_value={'error':'invalid_grant','error_description':'no_valid_keys_or_signatures','untrusted_detail':'PRIVATE_PROVIDER_DETAIL'}
        with patch.dict(os.environ,self.config),patch('requests.post',return_value=response) as post:
            r=self.check();self.assertFalse(r.json()['ready']);self.assertIn('RSA signing key',r.json()['message'])
            self.assertNotIn('PRIVATE_PROVIDER_DETAIL',r.text)
            self.assertTrue(post.call_args.args[0].endswith('/oauth/token'))

    def test_consent_error_explains_required_scopes(self):
        response=Mock(ok=False);response.json.return_value={'error':'consent_required'}
        with patch.dict(os.environ,self.config),patch('requests.post',return_value=response):
            r=self.check();self.assertFalse(r.json()['ready']);self.assertIn('signature and impersonation consent',r.json()['message'])

    def test_network_failure_returns_actionable_error(self):
        with patch.dict(os.environ,self.config),patch('requests.post',side_effect=requests.Timeout('hidden URL')):
            r=self.check();self.assertFalse(r.json()['ready']);self.assertIn('could not be reached',r.json()['message']);self.assertNotIn('hidden URL',r.text)

    def test_public_key_matches_server_key_and_is_admin_only(self):
        with patch.dict(os.environ,self.config):
            r=self.client.get('/api/boxing/docusign/public-key',headers=self.headers())
            self.assertEqual(r.status_code,200,r.text)
            loaded=serialization.load_pem_public_key(r.content)
            self.assertEqual(loaded.public_numbers(),self.key.public_key().public_numbers())
            self.assertNotIn(b'PRIVATE KEY',r.content)
            self.assertEqual(r.headers['cache-control'],'no-store')
        for role in ('staff','fighter','member','rep'):
            self.assertEqual(self.client.get('/api/boxing/docusign/public-key',headers=self.headers(role)).status_code,403)

    def test_diagnostics_require_operations_access(self):
        self.assertEqual(self.client.post('/api/boxing/docusign/connection-check').status_code,401)
        for role in ('fighter','member','rep'):
            self.assertEqual(self.client.post('/api/boxing/docusign/connection-check',headers=self.headers(role)).status_code,403)

    def test_invalid_private_key_and_invalid_provider_json_are_handled(self):
        with patch.dict(os.environ,{**self.config,'DOCUSIGN_PRIVATE_KEY':'not-a-key'}):
            r=self.check();self.assertFalse(r.json()['ready']);self.assertNotIn('not-a-key',r.text)
        response=Mock(ok=True);response.json.side_effect=ValueError('invalid')
        with patch.dict(os.environ,self.config),patch('requests.post',return_value=response):
            with self.assertRaises(HTTPException) as exc:_docusign_access_token()
            self.assertEqual(exc.exception.status_code,502)

if __name__=='__main__': unittest.main(verbosity=2)
