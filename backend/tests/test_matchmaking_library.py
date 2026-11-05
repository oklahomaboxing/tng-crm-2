import unittest,json,hashlib
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.models import BoxingEvent,BoxingFighter,BoxingBout,BoxingContract,BoxingContractSignature,BoxingSignedContractDocument
from app.database import get_db

class MatchmakingLibraryTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.event=BoxingEvent(slug='test-proposed-card',name='Test Event',event_date='2026-11-14');self.red=BoxingFighter(legal_name='Red Example');self.blue=BoxingFighter(legal_name='Blue Example');self.db.add_all([self.event,self.red,self.blue]);self.db.commit()
 def payload(self):return {'event_id':self.event.id,'red_fighter_id':self.red.id,'blue_fighter_id':self.blue.id,'weight_agreed':135,'rounds':4,'red_purse':1000,'blue_purse':0,'notes':'Proposal awaiting agreement'}
 def contract(self,status='draft'):
  bout=BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,status='draft');self.db.add(bout);self.db.flush()
  c=BoxingContract(event_id=self.event.id,bout_id=bout.id,fighter_id=self.red.id,opponent_id=self.blue.id,corner='red',boxer_name='Red Example',opponent_name='Blue Example',status=status);self.db.add(c);self.db.flush();return c
 def test_add_proposal_creates_only_draft_and_prevents_duplicate_booking(self):
  with patch('requests.post') as external:
   first=self.client.post('/api/boxing/bouts',headers=self.headers(),json=self.payload());self.assertEqual(first.status_code,200,first.text)
   self.assertEqual(first.json()['status'],'draft');second=self.client.post('/api/boxing/bouts',headers=self.headers(),json=self.payload());self.assertEqual(second.status_code,400);external.assert_not_called()
  self.assertEqual(self.db.query(BoxingContract).count(),0)
 def test_missing_event_or_fighter_never_creates_bout(self):
  for body in [{**self.payload(),'event_id':999999},{**self.payload(),'blue_fighter_id':999999}]:
   r=self.client.post('/api/boxing/bouts',headers=self.headers(),json=body);self.assertEqual(r.status_code,404,r.text)
 def test_library_requires_staff_access_and_excludes_unsigned_acceptance(self):
  unsigned=self.contract('accepted');signed=self.contract('signed');self.db.add(BoxingSignedContractDocument(contract_id=signed.id,file_name='signed.pdf',file_data=b'%PDF-1.4\n%%EOF',file_size=14));self.db.commit()
  path=f'/api/boxing/events/{self.event.id}/signed-contracts';self.assertEqual(self.client.get(path).status_code,401)
  for role in ('member','fighter','rep'):self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
  with patch('requests.get') as external:
   r=self.client.get(path,headers=self.headers());self.assertEqual(r.status_code,200,r.text);external.assert_not_called()
  self.assertIn('no-store',r.headers['cache-control']);self.assertEqual([c['id'] for c in r.json()['contracts']],[signed.id]);self.assertTrue(r.json()['contracts'][0]['download_available'])
  pdf=self.client.get(f'/api/boxing/contracts/{signed.id}/signed-file',headers=self.headers());self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF-'))
 def test_valid_electronic_signature_and_completed_unsynced_pdf_are_distinguished(self):
  c=self.contract('signed');raw=json.dumps({'contract_id':c.id,'fighter_id':c.fighter_id});self.db.add(BoxingContractSignature(contract_id=c.id,fighter_id=c.fighter_id,signer_user_id=self.users['fighter'].id,typed_legal_name='Red Example',agreed=True,contract_snapshot=raw,snapshot_sha256=hashlib.sha256(raw.encode()).hexdigest()))
  pending=self.contract('signed');pending.signature_provider='docusign';pending.docusign_status='completed';self.db.commit()
  r=self.client.get(f'/api/boxing/events/{self.event.id}/signed-contracts',headers=self.headers());rows={row['id']:row for row in r.json()['contracts']};self.assertTrue(rows[c.id]['download_available']);self.assertFalse(rows[pending.id]['download_available'])
 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_concurrent_proposals_cannot_book_the_same_fighter_twice(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.database import SessionLocal
  from app.main import app
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db;body=self.payload();gate=Barrier(2)
  def run(_):gate.wait();return self.client.post('/api/boxing/bouts',headers=self.headers(),json=body).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(run,range(2)))
  self.assertEqual(sorted(statuses),[200,400]);self.assertEqual(self.db.query(BoxingBout).filter_by(event_id=self.event.id).count(),1)

 def test_all_events_library_is_available_but_still_private(self):
  c=self.contract('signed');self.db.add(BoxingSignedContractDocument(contract_id=c.id,file_name='signed.pdf',file_data=b'%PDF-1.4\n%%EOF',file_size=14));self.db.commit()
  self.assertEqual(self.client.get('/api/boxing/signed-contracts').status_code,401)
  r=self.client.get('/api/boxing/signed-contracts',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['contracts'][0]['event_id'],self.event.id)
