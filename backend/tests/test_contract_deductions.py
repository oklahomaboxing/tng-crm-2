import unittest
from decimal import Decimal
import test_stabilization as support
from app.matchmaker.models import BoxingEvent,BoxingFighter,BoxingBout,BoxingContract
from app.matchmaker.deductions import ContractDeductions,recorded_total
from app.models import SecurityLog

class ContractDeductionTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def contract(self,status='signed',base=0):
  event=BoxingEvent(name='Deduction Test',slug='deduction-test',event_date='2026-11-14');a=BoxingFighter(legal_name='Test Fighter');b=BoxingFighter(legal_name='Opponent');self.db.add_all([event,a,b]);self.db.flush()
  bout=BoxingBout(event_id=event.id,red_fighter_id=a.id,blue_fighter_id=b.id,status='confirmed');self.db.add(bout);self.db.flush()
  c=BoxingContract(event_id=event.id,bout_id=bout.id,fighter_id=a.id,opponent_id=b.id,corner='red',boxer_name='Test Fighter',event_name='Deduction Test',gross_purse=1000,travel_expense=200,per_diem_total=50,deductions=base,boxer_paid=1250-base,status=status);self.db.add(c);self.db.commit();self.c=c
  return f'/api/boxing/contracts/{c.id}/deductions'
 def body(self,version=0):return {'version':version,'items':[{'label':'Blood work','amount':'120.00'},{'label':'Hotel','amount':'85.00'}]}
 def test_signed_terms_unchanged_and_itemized_statement_total_correct(self):
  path=self.contract();before=(self.c.gross_purse,self.c.travel_expense,self.c.per_diem_total,self.c.deductions,self.c.boxer_paid,self.c.status)
  r=self.client.put(path,headers=self.headers(),json=self.body());self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(d['total_deductions_cents'],20500);self.assertEqual(d['net_payout_cents'],104500);self.assertTrue(d['signed_terms_locked'])
  self.db.expire_all();self.assertEqual(before,(self.c.gross_purse,self.c.travel_expense,self.c.per_diem_total,self.c.deductions,self.c.boxer_paid,self.c.status))
  self.assertEqual(self.db.query(SecurityLog).filter_by(action='CONTRACT_DEDUCTIONS_UPDATED').count(),1)
  pdf=self.client.get(path+'.pdf',headers=self.headers());self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF-'))
 def test_drafts_update_existing_pdf_money_fields_without_double_count(self):
  path=self.contract('draft',base=20)
  r=self.client.put(path,headers=self.headers(),json=self.body());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['total_deductions_cents'],22500)
  self.db.expire_all();self.assertEqual(self.c.deductions,225);self.assertEqual(self.c.boxer_paid,1025);self.assertEqual(recorded_total(self.db,self.c),225)
  r=self.client.put(path,headers=self.headers(),json=self.body(1));self.assertEqual(r.json()['total_deductions_cents'],22500)
  self.assertEqual(self.client.patch(f'/api/boxing/contracts/{self.c.id}',headers=self.headers(),json={'deductions':0}).status_code,409)
 def test_stale_saves_rejected_and_items_can_be_removed(self):
  path=self.contract();self.client.put(path,headers=self.headers(),json=self.body())
  self.assertEqual(self.client.put(path,headers=self.headers(),json=self.body()).status_code,409)
  r=self.client.put(path,headers=self.headers(),json={'version':1,'items':[]});self.assertEqual(r.status_code,200);self.assertEqual(r.json()['total_deductions_cents'],0);self.assertEqual(r.json()['version'],2)
 def test_invalid_amounts_blank_descriptions_and_excessive_totals_rejected(self):
  path=self.contract()
  for item in [{'label':'','amount':'120'},{'label':'Blood','amount':'-1'},{'label':'Hotel','amount':'NaN'},{'label':'Hotel','amount':'1.001'}]:self.assertEqual(self.client.put(path,headers=self.headers(),json={'version':0,'items':[item]}).status_code,422)
  self.assertEqual(self.client.put(path,headers=self.headers(),json={'version':0,'items':[{'label':'Overdraw','amount':'1300'}]}).status_code,400)
  self.assertEqual(self.db.query(ContractDeductions).count(),0)
 def test_authentication_and_role_guards_cover_pdf_and_edits(self):
  path=self.contract();self.assertEqual(self.client.get(path).status_code,401)
  for role in ('rep','member','fighter'):
   self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
   self.assertEqual(self.client.put(path,headers=self.headers(role),json=self.body()).status_code,403)
   self.assertEqual(self.client.get(path+'.pdf',headers=self.headers(role)).status_code,403)
 def test_sent_contracts_are_locked_even_without_signature_row(self):
  path=self.contract('generated');self.c.docusign_status='sent';self.db.commit()
  r=self.client.put(path,headers=self.headers(),json=self.body());self.assertTrue(r.json()['signed_terms_locked']);self.db.refresh(self.c);self.assertEqual(self.c.deductions,0)
 def test_regeneration_keeps_saved_deduction_total(self):
  path=self.contract('draft',base=20);self.client.put(path,headers=self.headers(),json=self.body())
  r=self.client.post(f'/api/boxing/bouts/{self.c.bout_id}/contracts/red',headers=self.headers(),json={'gross_purse':1000,'travel_expense':200,'per_diem_daily':25,'per_diem_days':2,'deductions':0})
  self.assertEqual(r.status_code,200,r.text);self.db.expire_all();self.assertEqual(self.c.deductions,225);self.assertEqual(self.c.boxer_paid,1025)
 def test_workspace_buttons_use_latest_contract_revision(self):
  self.contract('generated');new=BoxingContract(event_id=self.c.event_id,bout_id=self.c.bout_id,fighter_id=self.c.fighter_id,opponent_id=self.c.opponent_id,corner='red',status='signed',boxer_name='Test Fighter',gross_purse=1000);self.db.add(new);self.db.commit()
  r=self.client.get(f'/api/boxing/events/{self.c.event_id}/workspace',headers=self.headers());self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(r.json()['bouts'][0]['red_contract']['id'],new.id)
 def test_official_pdf_prints_itemized_charges_and_current_payout_without_rewriting_signed_terms(self):
  from unittest.mock import patch
  from app.matchmaker import routes
  path=self.contract('signed');self.c.per_diem_total=0;self.db.commit();self.client.put(path,headers=self.headers(),json=self.body())
  captured=[];original=routes.Paragraph
  def paragraph(text,*args,**kwargs):captured.append(str(text));return original(text,*args,**kwargs)
  with patch.object(routes,'Paragraph',side_effect=paragraph):r=self.client.get(f'/api/boxing/contracts/{self.c.id}/official-pdf',headers=self.headers())
  self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.content.startswith(b'%PDF-'))
  text=' '.join(captured);self.assertIn('Blood work',text);self.assertIn('$120.00',text);self.assertIn('Hotel',text);self.assertIn('$85.00',text);self.assertIn('$205.00',text);self.assertIn('$995',text);self.assertIn('PAYOUT REVIEW COPY',text)
  self.db.refresh(self.c);self.assertEqual(self.c.deductions,0)
 def test_unsigned_pdf_includes_deductions_in_new_signing_payload(self):
  from app.matchmaker.deductions import pdf_deductions
  from app.matchmaker.routes import build_official_contract_pdf
  path=self.contract('draft');self.client.put(path,headers=self.headers(),json=self.body())
  summary=pdf_deductions(self.db,self.c,for_signing=True);self.assertEqual(summary['total_deductions_cents'],20500)
  self.c.status='signed';self.db.commit();self.assertIsNone(pdf_deductions(self.db,self.c,for_signing=True))
 def test_long_itemized_lists_can_paginate_in_final_pdf(self):
  path=self.contract('draft');items=[{'label':f'Deduction {i} '+('x'*100),'amount':'1.00'} for i in range(50)]
  self.assertEqual(self.client.put(path,headers=self.headers(),json={'version':0,'items':items}).status_code,200)
  r=self.client.get(f'/api/boxing/contracts/{self.c.id}/official-pdf',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.content.startswith(b'%PDF-'))
 def test_original_signed_download_remains_byte_for_byte_unchanged(self):
  from app.matchmaker.models import BoxingSignedContractDocument
  path=self.contract('signed');original=b'%PDF-original-signed-fixture-preserved'
  doc=BoxingSignedContractDocument(contract_id=self.c.id,file_name='signed.pdf',file_data=original);self.db.add(doc);self.db.commit()
  self.client.put(path,headers=self.headers(),json=self.body())
  review=self.client.get(f'/api/boxing/contracts/{self.c.id}/official-pdf',headers=self.headers());self.assertEqual(review.status_code,200)
  signed=self.client.get(f'/api/boxing/contracts/{self.c.id}/signed-file',headers=self.headers());self.assertEqual(signed.status_code,200);self.assertEqual(signed.content,original)
