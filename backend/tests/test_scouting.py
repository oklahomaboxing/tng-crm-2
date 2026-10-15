"""Separate nationwide scouting storage, filters, review and safe research saves."""
import unittest
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.scouting import BoxerProspect, US_STATES, DIVISIONS
from app.matchmaker.models import BoxingFighter,BoxingBout
BASE='/api/boxing/scouting'
P={'name':'Example Boxer','state':'NY','city':'Brooklyn','division':'lightweight','weight':'135 lb','record':'1-1 reported','source_url':'https://example.org/boxing','evidence':'Reported professional boxer; booking office example@example.org','business_email':'example@example.org'}
class ScoutingTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def create(self,**kw):return self.client.post(BASE+'/prospects',headers=self.headers(),json={**P,**kw})
 def test_access_is_staff_scoped(self):
  self.assertEqual(self.client.get(BASE+'/prospects').status_code,401)
  for role in ['rep','member','fighter']:
   self.assertEqual(self.client.get(BASE+'/prospects',headers=self.headers(role)).status_code,403)
   self.assertEqual(self.client.post(BASE+'/discover',headers=self.headers(role),json={'division':'lightweight'}).status_code,403)
 def test_all_states_and_weight_groups_available(self):
  r=self.client.get(BASE+'/options',headers=self.headers()).json()
  self.assertEqual(len(r['states']),51);self.assertEqual(len(r['divisions']),19)
  self.assertIn('NY',r['states']);self.assertIn('heavyweight',{x['key'] for x in r['divisions']})
 def test_prospects_separate_from_active_roster_and_bouts(self):
  r=self.create();self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.db.query(BoxingFighter).count(),0);self.assertEqual(self.db.query(BoxingBout).count(),0)
  self.assertEqual(r.json()['prospect']['availability'],'unknown')
 def test_same_source_deduplicates_and_preserves_review(self):
  r=self.create().json();pid=r['prospect']['id']
  self.client.patch(BASE+f'/prospects/{pid}',headers=self.headers(),json={'status':'shortlisted','notes':'Rocky candidate: verify terms'})
  again=self.create(source_url=P['source_url']+'?utm_source=openai').json()
  self.assertFalse(again['created']);self.assertEqual(again['prospect']['id'],pid)
  self.assertEqual(again['prospect']['status'],'shortlisted');self.assertEqual(self.db.query(BoxerProspect).count(),1)
 def test_filter_pagination_and_empty_contact(self):
  self.create();self.create(name='Other Boxer',state='TX',division='heavyweight',business_email='',business_phone='5555555555')
  h=self.headers()
  r=self.client.get(BASE+'/prospects',headers=h,params={'division':'lightweight','state':'NY','page_size':1}).json()
  self.assertEqual(r['total'],1);self.assertEqual(r['database_total'],2)
  self.assertEqual(self.client.get(BASE+'/prospects',headers=h,params={'contact_only':True}).json()['total'],1)
  self.assertEqual(self.client.get(BASE+'/prospects',headers=h,params={'q':'Other'}).json()['total'],1)
  self.assertEqual(self.client.get(BASE+'/prospects',headers=h,params={'page_size':1,'page':2}).json()['items'][0]['name'],'Example Boxer')
 def test_rejects_unsafe_sources_and_statuses(self):
  self.assertEqual(self.create(source_url='https://127.0.0.1').status_code,422)
  self.assertEqual(self.create(state='XX').status_code,422)
  pid=self.create().json()['prospect']['id']
  self.assertEqual(self.client.patch(BASE+f'/prospects/{pid}',headers=self.headers(),json={'status':'booked'}).status_code,400)
 def test_research_saves_cited_leads_without_sending_or_booking(self):
  lead={**P,'kind':'fighter'}
  with patch('app.matchmaker.scouting.search_public_web',return_value={'leads':[lead]}):
   r=self.client.post(BASE+'/discover',headers=self.headers(),json={'division':'lightweight','states':['NY']})
   self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['inserted'],1)
   self.assertEqual(self.client.post(BASE+'/discover',headers=self.headers(),json={'division':'lightweight','states':['NY']}).json()['inserted'],0)
  self.assertEqual(self.db.query(BoxingFighter).count(),0)
 def test_research_rejects_known_weight_mismatch_and_other_combat_sport(self):
  rows=[{**P,'weight':'143 lb'},{**P,'source_url':'https://www.bkfc.com/fighters/example'}]
  with patch('app.matchmaker.scouting.search_public_web',return_value={'leads':rows}):
   r=self.client.post(BASE+'/discover',headers=self.headers(),json={'division':'lightweight','states':['NY']})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['inserted'],0)
 def test_manual_availability_and_shortlist_persist(self):
  pid=self.create().json()['prospect']['id']
  r=self.client.patch(BASE+f'/prospects/{pid}',headers=self.headers('staff'),json={'status':'shortlisted','availability':'available','notes':'Coach confirmed date, verify eligibility before offer'})
  self.assertEqual(r.status_code,200,r.text)
  listing=self.client.get(BASE+'/prospects',headers=self.headers(),params={'status':'shortlisted'}).json()
  self.assertEqual(listing['shortlisted'],1);self.assertEqual(listing['items'][0]['availability'],'available')
if __name__=='__main__':unittest.main(verbosity=2)
