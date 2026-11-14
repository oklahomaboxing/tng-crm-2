import base64,io,json,unittest,zipfile
from datetime import datetime
from unittest.mock import patch,Mock
import test_stabilization as support
import test_ticketing as tickets
from app.ticketing.models import TicketOrder
from app.ticketing.commission_reports import CommissionReportSettings,CommissionReportSubmission,state
class CommissionSubmissionTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 order=tickets.TicketingTests.order
 def setup_report(self):
  o=self.order();self.o=o
  # Explicit past deadline and future close keep test behavior independent of runtime date.
  self.eid=o.event_id;self.path=f'/api/ticketing/events/{self.eid}/commission-submission'
  return self.client.put(self.path,headers=self.headers(),json={'to':'Heather.Turner@osac.ok.gov','cc':'Diana.Fletcher@osac.ok.gov','confirmed':True,'enabled':True,'deadline_local':'2026-01-01T00:00','closes_local':'2099-01-02T01:00'})
 def test_oklahoma_midnight_and_window_are_saved_as_utc(self):
  self.setup_report()
  r=self.client.put(self.path,headers=self.headers(),json={'to':'Heather.Turner@osac.ok.gov','cc':'Diana.Fletcher@osac.ok.gov','confirmed':True,'deadline_local':'2026-11-15T00:00','closes_local':'2026-11-16T01:00'})
  self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(d['deadline'],'2026-11-15T06:00:00+00:00');self.assertEqual(d['closes_at'],'2026-11-16T07:00:00+00:00')
  self.assertFalse(state(self.db,self.eid,datetime(2026,11,15,5,59))['overdue']);self.assertTrue(state(self.db,self.eid,datetime(2026,11,15,6,0))['overdue'])
 def test_report_package_includes_master_and_every_seller_pdf_csv_with_cc(self):
  d=self.setup_report().json();provider=Mock(return_value={'id':'microsoft365:fixture'})
  with patch('app.mail.microsoft365.send_welcome',provider):
   r=self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']});self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'accepted')
   self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']});provider.assert_called_once()
  payload=provider.call_args.args[1];self.assertEqual(payload['to'],['Heather.Turner@osac.ok.gov']);self.assertEqual(payload['cc'],['Diana.Fletcher@osac.ok.gov'])
  archive=zipfile.ZipFile(io.BytesIO(base64.b64decode(payload['attachments'][1]['content'])));names=archive.namelist();self.assertTrue(any('Master' in n and n.endswith('.csv') for n in names));self.assertTrue(any('Seller_' in n and n.endswith('.pdf') for n in names));self.assertTrue(any('Seller_' in n and n.endswith('.csv') for n in names))
  self.assertFalse(self.client.get(self.path,headers=self.headers()).json()['overdue'])
 def test_new_financial_data_requires_new_submission_and_stale_hash_is_blocked(self):
  d=self.setup_report().json()
  with patch('app.mail.microsoft365.send_welcome',return_value={'id':'fixture'}):self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']})
  self.o.buyer_name='Changed purchaser';self.db.commit();current=self.client.get(self.path,headers=self.headers()).json();self.assertTrue(current['overdue']);self.assertFalse(current['submitted_current_report'])
  with patch('app.mail.microsoft365.send_welcome') as p:self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']}).status_code,409);p.assert_not_called()
 def test_provider_rejection_and_unknown_keep_alert_and_unknown_never_replays(self):
  d=self.setup_report().json()
  with patch('app.mail.microsoft365.send_welcome',side_effect=RuntimeError('rejected')):r=self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']})
  self.assertEqual(r.json()['status'],'rejected');self.assertTrue(self.client.get(self.path,headers=self.headers()).json()['overdue'])
  row=self.db.query(CommissionReportSubmission).one();row.status='unknown';self.db.commit()
  with patch('app.mail.microsoft365.send_welcome') as p:self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']}).status_code,409);p.assert_not_called()
 def test_admin_guard_recipient_confirmation_and_late_acknowledgment(self):
  self.setup_report();self.assertEqual(self.client.get(self.path).status_code,401)
  for role in ('staff','rep','member','fighter'):self.assertEqual(self.client.get(self.path,headers=self.headers(role)).status_code,403)
  cfg=self.db.get(CommissionReportSettings,self.eid);cfg.confirmed=False;self.db.commit();d=self.client.get(self.path,headers=self.headers()).json()
  with patch('app.mail.microsoft365.send_welcome') as p:self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']}).status_code,409);p.assert_not_called()
  cfg.confirmed=True;cfg.closes_at=datetime(2026,1,2);self.db.commit()
  self.assertEqual(self.client.post(self.path+'/send',headers=self.headers(),json={'report_hash':d['report_hash']}).status_code,409)
 def test_command_briefing_does_not_call_paid_ai_or_change_orders(self):
  self.setup_report();before=self.db.query(TicketOrder).count()
  with patch('app.ai.assistant.resolve_topic',side_effect=AssertionError('Paid routing must not run')):
   r=self.client.post('/api/assistant/briefing',headers=self.headers(),json={'question':'How many active members?'});self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['engine'],'live_reports')
  self.assertEqual(self.db.query(TicketOrder).count(),before)
