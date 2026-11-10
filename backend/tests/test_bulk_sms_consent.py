import unittest
from unittest.mock import patch,Mock
import test_stabilization as support
from app.models import MarketingContact,SecurityLog
from app.operations.renewal_reminders import suppress_sms
from app.services.sms_service import ensure_stop_footer,send_sms

class BulkSmsConsentTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    path='/api/marketing/sms/contacts/consent/bulk'
    def contact(self,phone='+14055550101',**changes):
        c=MarketingContact(first_name='Example',phone=phone,active=changes.pop('active',True),sms_opt_in=changes.pop('sms_opt_in',False),sms_unsubscribed=changes.pop('sms_unsubscribed',False),**changes)
        self.db.add(c);self.db.commit();return c
    def payload(self,ids):
        return {'contact_ids':ids,'opt_in':True,'evidence':'Staff verified signup Subscribe explicitly included SMS permission.'}

    def test_selected_bulk_updates_only_eligible_and_audits_once_without_sending(self):
        a=self.contact();b=self.contact('+14055550102');already=self.contact('+14055550103',sms_opt_in=True)
        invalid=self.contact('not-phone');stopped=self.contact('+14055550104',sms_unsubscribed=True)
        inactive=self.contact('+14055550105',active=False);unselected=self.contact('+14055550106')
        ids=[a.id,b.id,already.id,invalid.id,stopped.id,inactive.id,999999,a.id]
        with patch('app.marketing.sms.Client') as provider,patch('app.services.sms_service.Client') as generic:
            r=self.client.post(self.path,headers=self.headers(),json=self.payload(ids))
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json(),{'recorded':2,'already_recorded':1,'skipped_opted_out':1,'skipped_invalid_phone':1,'skipped_inactive':1,'not_found':1})
            provider.assert_not_called();generic.assert_not_called()
        self.db.refresh(unselected);self.assertFalse(unselected.sms_opt_in)
        again=self.client.post(self.path,headers=self.headers(),json=self.payload(ids))
        self.assertEqual(again.json()['recorded'],0)
        self.assertEqual(self.db.query(SecurityLog).filter_by(action='SMS_BULK_CONSENT_RECORDED').count(),1)

    def test_global_stop_and_stopped_duplicate_phone_cannot_be_overridden(self):
        a=self.contact();b=self.contact('+14055550102');other=self.contact('+14055550102',sms_unsubscribed=True)
        suppress_sms(self.db,a.phone);self.db.commit()
        r=self.client.post(self.path,headers=self.headers(),json=self.payload([a.id,b.id]))
        self.assertEqual(r.json()['skipped_opted_out'],2)
        for c in (a,b):
            self.db.refresh(c);self.assertFalse(c.sms_opt_in)
            single=self.client.post(f'/api/marketing/sms/contacts/{c.id}/consent',headers=self.headers(),json={'opt_in':True,'evidence':'Documented signup SMS permission'})
            self.assertEqual(single.status_code,409)

    def test_validation_and_permissions(self):
        c=self.contact()
        for role in ('member','fighter','rep'):
            self.assertEqual(self.client.post(self.path,headers=self.headers(role),json=self.payload([c.id])).status_code,403)
        for body in ({**self.payload([c.id]),'opt_in':False},{**self.payload([c.id]),'evidence':' ' * 20},{**self.payload([c.id]),'evidence':'short'},{**self.payload([])}):
            self.assertIn(self.client.post(self.path,headers=self.headers(),json=body).status_code,(400,422))
        self.db.refresh(c);self.assertFalse(c.sms_opt_in)

    def test_common_sender_always_appends_one_consistent_stop_footer(self):
        for message in ('TNG Boxing reminder','TNG reminder Reply STOP to opt out.','TNG reminder Reply STOP to unsubscribe.','TNG notice REPLY STOP TO OPT-OUT.'):
            result=ensure_stop_footer(message)
            self.assertTrue(result.endswith('Reply STOP to unsubscribe.'))
            self.assertEqual(result.lower().count('reply stop'),1)
        provider=Mock();provider.messages.create.return_value.sid='SM-test-only'
        with patch.dict('os.environ',{'TWILIO_ACCOUNT_SID':'test','TWILIO_AUTH_TOKEN':'test','TWILIO_PHONE_NUMBER':'+14055550199'}),patch('app.services.sms_service.Client',return_value=provider):
            self.assertEqual(send_sms('+14055550101','Test body'),'SM-test-only')
            self.assertTrue(provider.messages.create.call_args.kwargs['body'].endswith('Reply STOP to unsubscribe.'))
