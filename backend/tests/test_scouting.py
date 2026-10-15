"""Separate nationwide scouting storage, filters, review and safe research saves."""
import unittest
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.scouting import BoxerProspect, ScoutingResearchJob, US_STATES, DIVISIONS, expire_jobs
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
 def test_research_keeps_full_user_focus(self):
  focus='Find new opponents with published gym contacts in Tulsa. '+'x'*140
  with patch('app.matchmaker.scouting.search_public_web',return_value={'leads':[]}) as search:
   r=self.client.post(BASE+'/discover',headers=self.headers(),json={'division':'super_featherweight','states':['OK'],'query':focus})
  self.assertEqual(r.status_code,200,r.text)
  self.assertIn(focus,search.call_args.args[0].query)
 def test_background_research_returns_job_and_persists_progress(self):
  with patch('app.matchmaker.scouting.run_research_job') as worker:
   response=self.client.post(BASE+'/research',headers=self.headers(),json={'divisions':['lightweight','featherweight'],'states':['NY']})
   self.assertEqual(response.status_code,202,response.text)
   job=response.json();worker.assert_called_once_with(job['id'])
  latest=self.client.get(BASE+'/research/latest',headers=self.headers()).json()
  self.assertEqual(latest['total'],2);self.assertEqual(latest['status'],'running')
  with patch('app.matchmaker.scouting.run_research_job') as worker:
   again=self.client.post(BASE+'/research',headers=self.headers(),json={'divisions':['heavyweight']}).json()
   self.assertEqual(again['id'],job['id']);worker.assert_not_called()
  stopped=self.client.post(BASE+f"/research/{job['id']}/stop",headers=self.headers()).json()
  self.assertEqual(stopped['status'],'stopping')
 def test_interrupted_worker_does_not_leave_permanent_spinner(self):
  from datetime import datetime,timedelta
  row=ScoutingResearchJob(active_key='nationwide',request_json='{}',total=1,updated_by=1,updated_at=datetime.utcnow()-timedelta(minutes=6))
  self.db.add(row);self.db.commit();expire_jobs(self.db)
  self.assertEqual(row.status,'interrupted');self.assertIsNone(row.active_key)
 def test_worker_records_success_and_failure_without_losing_prospects(self):
  from fastapi import HTTPException
  with patch('app.matchmaker.scouting.search_public_web',side_effect=[{'leads':[{**P,'kind':'fighter'}]},HTTPException(502,'Public web search is unavailable.')]):
   r=self.client.post(BASE+'/research',headers=self.headers(),json={'divisions':['lightweight','featherweight'],'states':['NY']})
  self.assertEqual(r.status_code,202,r.text)
  job=self.client.get(BASE+'/research/latest',headers=self.headers()).json()
  self.assertEqual(job['status'],'complete');self.assertEqual(job['completed'],2)
  self.assertEqual(job['inserted'],1);self.assertEqual(len(job['errors']),1)
  self.assertEqual(self.db.query(BoxerProspect).count(),1)
 def test_beginner_regional_filter_excludes_unknown_and_experienced_records(self):
  self.create(name='Texas Beginner',state='TX',record='2-1-0 (reported)')
  self.create(name='New Mexico Pro',state='NM',record='0-1')
  self.create(name='California Beginner',state='CA',record='1-0')
  self.create(name='Experienced Texas',state='TX',record='12-0')
  self.create(name='Unknown Texas',state='TX',record='')
  rows=self.client.get(BASE+'/prospects',headers=self.headers(),params={'state':'regional','experience':'beginner'}).json()
  self.assertEqual({r['name'] for r in rows['items']},{'Texas Beginner','New Mexico Pro'})
  self.assertEqual({r['reported_pro_bouts'] for r in rows['items']},{1,3})
 def test_official_profiles_work_without_ai_and_do_not_overwrite_reviews(self):
  row=self.create(name='Example Boxer',state='TX',record='2-0').json()['prospect']
  leads=[{**P,'state':'TX','weight':'Lightweight (135 lbs)','source_url':'https://toprank.com/fighters/example'},
         {**P,'name':'Other Pro','state':'TX','weight':'Heavyweight (220 lbs)'}]
  with patch('app.matchmaker.official_rosters.search_official_rosters',return_value={'leads':leads}),patch('app.matchmaker.scouting.search_public_web') as ai:
   r=self.client.post(BASE+'/discover',headers=self.headers(),json={'division':'lightweight','states':['TX'],'source':'official_rosters'})
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['inserted'],0)
  self.assertEqual(r.json()['prospects'][0]['id'],row['id']);ai.assert_not_called()
 def test_public_profile_parser_uses_source_hometown_and_ignores_foreign_profiles(self):
  from app.matchmaker.official_rosters import parse_profile
  raw='<title>Sample Pro | Top Rank Fighter</title><h1>Sample Pro</h1> Lightweight (135 lbs) 2 Wins 1 Losses 0 Draws Hometown Houston, TX Country United States'
  row=parse_profile('https://toprank.com/fighters/sample',raw)
  self.assertEqual(row['state'],'TX');self.assertEqual(row['city'],'Houston')
  self.assertEqual(row['weight'],'Lightweight (135 lbs)');self.assertTrue(row['record'].startswith('2-1-0'))
  self.assertIsNone(parse_profile('https://toprank.com/fighters/sample',raw.replace('Houston, TX','London, England')))
 def test_red_owl_beginner_profiles_preserve_reported_record_and_hometown(self):
  from app.matchmaker.official_rosters import parse_red_owl
  rows=parse_red_owl('<p>ALEX DONIS 3-0-0 (1 KO) HOUSTON, TX WELTERWEIGHT ARIANA CARRASCO 4-0-0 (1 KO) LAS CRUCES, NM SUPER WELERWEIGHT FOREIGN BOXER 1-0-0 CHIHUAHUA, MX LIGHTWEIGHT</p>')
  self.assertEqual(len(rows),2);self.assertEqual(rows[0]['name'],'Alex Donis')
  self.assertEqual(rows[0]['state'],'TX');self.assertEqual(rows[1]['weight'],'Super Welterweight')
  first=parse_red_owl('<p>BRING ATTENTION TO ALL LEVELS.</p><h3>ADRIAN SALAZAR</h3><p>2-0-0 (1 KO) TYLER, TX WELTERWEIGHT</p>')
  self.assertEqual(first[0]['name'],'Adrian Salazar')
 def test_golden_boy_reads_counter_targets_instead_of_zero_placeholder(self):
  from app.matchmaker.official_rosters import parse_profile
  counters=''.join(f'<h2 data-purecounter-end="{value}">0</h2><p>{label}</p>' for label,value in [('WINS',3),('LOSSES',1),('DRAWS',0)])
  raw='<title>Example Pro - Golden Boy Promotions</title><h1>Example Pro</h1>'+counters+'Weight Class Stance Age Height Lightweight Orthodox 22 6 NATIONALITY: HOMETOWN: Dallas, TX BIOGRAPHY Professional boxer'
  row=parse_profile('https://www.goldenboy.com/fighter-profile/example/',raw)
  self.assertTrue(row['record'].startswith('3-1-0'));self.assertEqual(row['city'],'Dallas')
 def test_public_directory_accepts_canonical_redirect_but_blocks_other_hosts(self):
  from app.matchmaker.official_rosters import get_public_page
  from unittest.mock import Mock
  redirect=Mock(status_code=301,headers={'Location':'https://www.redowlboxing.com/pages/fighters'})
  page=Mock(status_code=200)
  with patch('app.matchmaker.official_rosters.requests.get',side_effect=[redirect,page]) as fetch:
   self.assertIs(get_public_page('https://redowlboxing.com/pages/fighters'),page)
   self.assertEqual(fetch.call_count,2)
  redirect.headers={'Location':'https://127.0.0.1/private'}
  with patch('app.matchmaker.official_rosters.requests.get',return_value=redirect) as fetch:
   self.assertIsNone(get_public_page('https://redowlboxing.com/pages/fighters'))
   self.assertEqual(fetch.call_count,1)
if __name__=='__main__':unittest.main(verbosity=2)
