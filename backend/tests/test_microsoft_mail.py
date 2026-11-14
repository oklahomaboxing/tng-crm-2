import unittest,json
from datetime import datetime,timedelta
from urllib.parse import urlsplit,parse_qs
from unittest.mock import patch,Mock
import requests
import test_stabilization as support
from app.mail.microsoft365 import MicrosoftMailbox,MicrosoftMailAttempt,MicrosoftMailOAuthState,encrypt,decrypt,send_welcome,MailSubmissionError

class MicrosoftMailTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    base='/api/mail/microsoft365'
    config={'tenant_id':'11111111-1111-1111-1111-111111111111','client_id':'22222222-2222-2222-2222-222222222222','client_secret':'private-test-secret-value'}

    def configure(self):
        r=self.client.put(self.base+'/config',headers=self.headers(),json=self.config)
        self.assertEqual(r.status_code,200,r.text)
        return r
    def flow(self):
        self.client.base_url='https://testserver'
        self.configure()
        r=self.client.post(self.base+'/connect',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        start=urlsplit(r.json()['authorization_url'])
        r=self.client.get(start.path+'?'+start.query,follow_redirects=False)
        self.assertEqual(r.status_code,303,r.text)
        query=parse_qs(urlsplit(r.headers['location']).query)
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertIn('Mail.Send',query['scope'][0])
        self.assertNotIn('Mail.Read',query['scope'][0])
        self.assertIn('httponly',r.headers['set-cookie'].lower())
        return query['state'][0]
    def connected(self):
        cfg=MicrosoftMailbox(id=1,tenant_id=self.config['tenant_id'],client_id=self.config['client_id'],client_secret=encrypt('secret'),refresh_token=encrypt('refresh'),access_token=encrypt('access'),expires_at=datetime.utcnow()+timedelta(hours=1),mailbox='marketing@tngboxinggym.com',enabled=True,generation=1)
        self.db.add(cfg);self.db.commit();return cfg
    def payload(self):
        return {'subject':'TNG event details','html':'<p>Verified schedule</p>','to':['fighter@example.com'],'attachments':[{'filename':'welcome.pdf','content':'JVBERi0='}]}

    def test_config_is_admin_only_and_never_returns_credentials(self):
        r=self.configure()
        self.assertNotIn(self.config['client_secret'],r.text)
        cfg=self.db.get(MicrosoftMailbox,1)
        self.assertNotEqual(cfg.client_secret,self.config['client_secret'])
        self.assertEqual(decrypt(cfg.client_secret),self.config['client_secret'])
        for role in ('member','staff','fighter','rep'):
            self.assertEqual(self.client.get(self.base+'/status',headers=self.headers(role)).status_code,403)
            self.assertEqual(self.client.put(self.base+'/config',headers=self.headers(role),json=self.config).status_code,403)
            self.assertEqual(self.client.post(self.base+'/connect',headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.get(self.base+'/status',headers=self.headers()).headers['cache-control'],'private, no-store')

    def test_pkce_callback_binds_browser_admin_and_exact_mailbox(self):
        state=self.flow()
        tokens=Mock(status_code=200);tokens.json.return_value={'access_token':'sensitive-access','refresh_token':'sensitive-refresh','scope':'Mail.Send User.Read','expires_in':3600}
        profile=Mock(status_code=200);profile.json.return_value={'mail':'marketing@tngboxinggym.com'}
        with patch('app.mail.microsoft365.requests.post',return_value=tokens) as post,patch('app.mail.microsoft365.requests.get',return_value=profile):
            r=self.client.get(self.base+'/callback',params={'state':state,'code':'one-time-code'},follow_redirects=False)
            self.assertEqual(r.status_code,303,r.text)
            self.assertNotIn('sensitive',str(r.headers))
            sent=post.call_args.kwargs['data']
            self.assertTrue(sent['code_verifier'])
            self.assertEqual(self.client.get(self.base+'/callback',params={'state':state,'code':'one-time-code'}).status_code,400)
            self.assertEqual(post.call_count,1)
        cfg=self.db.get(MicrosoftMailbox,1);self.db.refresh(cfg)
        self.assertTrue(cfg.enabled)
        self.assertEqual(decrypt(cfg.refresh_token),'sensitive-refresh')
        self.assertNotEqual(cfg.refresh_token,'sensitive-refresh')

    def test_missing_cookie_or_changed_admin_rejected_without_token_exchange(self):
        state=self.flow()
        with patch('app.mail.microsoft365.requests.post') as post:
            self.client.cookies.clear()
            self.assertEqual(self.client.get(self.base+'/callback',params={'state':state,'code':'x'}).status_code,400)
            post.assert_not_called()
        state=self.flow()
        self.users['admin'].active=False;self.db.commit()
        with patch('app.mail.microsoft365.requests.post') as post:
            self.assertEqual(self.client.get(self.base+'/callback',params={'state':state,'code':'x'}).status_code,403)
            post.assert_not_called()

    def test_wrong_microsoft_mailbox_is_not_connected(self):
        state=self.flow()
        tokens=Mock(status_code=200);tokens.json.return_value={'access_token':'access','refresh_token':'refresh','scope':'Mail.Send User.Read'}
        profile=Mock(status_code=200);profile.json.return_value={'mail':'someoneelse@example.com'}
        with patch('app.mail.microsoft365.requests.post',return_value=tokens),patch('app.mail.microsoft365.requests.get',return_value=profile):
            self.assertEqual(self.client.get(self.base+'/callback',params={'state':state,'code':'x'}).status_code,400)
        cfg=self.db.get(MicrosoftMailbox,1);self.db.refresh(cfg);self.assertFalse(cfg.enabled)

    def test_graph_sends_pdf_and_saves_sent_items_without_resend_fallback(self):
        self.connected()
        with patch('app.mail.microsoft365.requests.post',return_value=Mock(status_code=202)) as post:
            result=send_welcome(self.db,self.payload(),'welcome-test-1')
            self.assertTrue(result['id'].startswith('microsoft365:'))
            data=post.call_args.kwargs['json']
            self.assertTrue(data['saveToSentItems'])
            self.assertEqual(data['message']['toRecipients'][0]['emailAddress']['address'],'fighter@example.com')
            self.assertEqual(data['message']['attachments'][0]['contentBytes'],'JVBERi0=')
            self.assertEqual(send_welcome(self.db,self.payload(),'welcome-test-1'),result)
            self.assertEqual(post.call_count,1)

    def test_graph_timeout_is_never_replayed(self):
        self.connected()
        with patch('app.mail.microsoft365.requests.post',side_effect=requests.Timeout) as post:
            with self.assertRaises(MailSubmissionError):send_welcome(self.db,self.payload(),'welcome-test-2')
            with self.assertRaises(MailSubmissionError):send_welcome(self.db,self.payload(),'welcome-test-2')
            self.assertEqual(post.call_count,1)
        self.assertEqual(self.db.get(MicrosoftMailAttempt,'welcome-test-2').status,'unknown')

    def test_disconnect_clears_tokens_and_invalidates_pending_authorization(self):
        self.connected()
        r=self.client.post(self.base+'/disconnect',headers=self.headers())
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['provider'],'resend')
        cfg=self.db.get(MicrosoftMailbox,1);self.db.refresh(cfg)
        self.assertIsNone(cfg.access_token);self.assertIsNone(cfg.refresh_token)

    def test_graph_commission_cc_and_zip_content_type(self):
        self.connected()
        payload=self.payload();payload['cc']=['Diana.Fletcher@osac.ok.gov']
        payload['attachments'].append({'filename':'reports.zip','content':'UEs=','content_type':'application/zip'})
        with patch('app.mail.microsoft365.requests.post',return_value=Mock(status_code=202)) as post:
            send_welcome(self.db,payload,'commission-serialization')
        message=post.call_args.kwargs['json']['message']
        self.assertEqual(message['ccRecipients'][0]['emailAddress']['address'],'Diana.Fletcher@osac.ok.gov')
        self.assertEqual(message['attachments'][0]['contentType'],'application/pdf')
        self.assertEqual(message['attachments'][1]['contentType'],'application/zip')
