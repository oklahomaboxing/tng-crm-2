import unittest,io
from datetime import date
import test_stabilization as support
from app.amateurs.rosters import AmateurRoster,AmateurEntry,AmateurRulebook,AmateurMatchRun,read_rows,DEFAULT_PREFERENCES
from app.amateurs.rules_2026 import compatible,DOCUMENT_SHA256,IMPLEMENTATION,TITLE,APPENDIX_TRANSCRIPT
from app.models import User
from app.matchmaker.models import BoxingFighter,BoxingBout
HEAD='Member ID,First name,Last name,Date of birth,Age,Sex,Weight,Number of bouts,Coach First Name,Coach Last Name,LBC,City,State,Boxing Club Name\n'
CSV=(HEAD+'000123,Example,Alpha,02/21/2010,16,MALE,125lbs (57kg),2,Coach,One,OK,OKC,OK,Club One\n'+'000124,Example,Bravo,02/20/2010,16,MALE,128lbs (58kg),3,Coach,Two,OK,Tulsa,OK,Club Two\n').encode()
class AmateurRosterTests(unittest.TestCase):
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def setUp(self):
  support.StabilizationTests.setUp(self)
  self.db.add(AmateurRulebook(year=2027,title=TITLE,source_url='https://www.usaboxing.org/usa-boxing-rulebook',document_sha256=DOCUMENT_SHA256,appendix_text=APPENDIX_TRANSCRIPT,config={'implementation':IMPLEMENTATION,'reference_year':2026},verified_by=self.users['admin'].id,enabled=True));self.db.commit()
 def upload(self,content=CSV,filename='example.csv',role='admin'):
  return self.client.post('/api/amateurs/rosters/import',headers=self.headers(role),files={'file':(filename,content,'text/csv')})
 def roster(self):
  r=self.upload();self.assertEqual(r.status_code,200,r.text);return r.json()['roster_id']
 def test_import_preserves_ids_rows_and_does_not_create_pro_fighters_or_logins(self):
  users=self.db.query(User).count();fighters=self.db.query(BoxingFighter).count();r=self.upload();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['rows'],2);rid=r.json()['roster_id'];self.assertEqual(self.upload().json()['roster_id'],rid);self.assertEqual(self.db.query(AmateurEntry).count(),2)
  d=self.client.get(f'/api/amateurs/rosters/{rid}',headers=self.headers()).json();self.assertEqual(d['entries'][0]['data']['member_id'],'000123');self.assertEqual(d['entries'][0]['data']['weight_lb'],125);self.assertIsNone(d['entries'][0]['data']['wins']);self.assertEqual(d['rules']['reference_year'],2026);self.assertTrue(d['rules']['verified']);self.assertEqual(self.db.query(User).count(),users);self.assertEqual(self.db.query(BoxingFighter).count(),fighters)
 def test_invalid_rows_and_duplicate_ids_are_kept_and_flagged(self):
  bad=(HEAD+'000123,Example,Alpha,bad,16,MALE,heavy,no,Coach,One,OK,OKC,OK,Club One\n'+'000123,Example,Bravo,02/21/2010,16,MALE,125lbs,0,Coach,Two,OK,OKC,OK,Club Two\n').encode();r=self.upload(bad);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['needs_review'],2);rows=self.db.query(AmateurEntry).all();self.assertTrue(all(x.issues for x in rows));self.assertEqual(len(rows),2)
 def test_file_validation_xlsx_and_size(self):
  self.assertEqual(self.upload(b'bad',filename='x.exe').status_code,422);self.assertEqual(self.upload(b'A,B\n1,2').status_code,422);self.assertEqual(self.upload(b'x'*(5*1024*1024+1)).status_code,413)
  from openpyxl import Workbook
  book=Workbook();sheet=book.active
  import csv
  for row in csv.reader(io.StringIO(CSV.decode())):sheet.append(row)
  out=io.BytesIO();book.save(out);r=self.upload(out.getvalue(),'example.xlsx');self.assertEqual(r.status_code,200,r.text)
 def test_anonymous_and_unrelated_roles_denied(self):
  self.assertEqual(self.client.get('/api/amateurs/rosters').status_code,401)
  for role in ('fighter','member','rep'):
   self.assertEqual(self.upload(role=role).status_code,403)
  self.assertEqual(self.upload(role='staff').status_code,200)
 def test_settings_version_date_and_unknown_rules_are_enforced(self):
  rid=self.roster();path=f'/api/amateurs/rosters/{rid}';self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).status_code,409)
  body={'name':'Amateur show','competition_date':'2027-01-30','version':1};r=self.client.put(path+'/settings',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(path+'/settings',headers=self.headers(),json=body).status_code,409)
  r=self.db.query(AmateurRulebook).one();r.enabled=False;self.db.commit();self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).status_code,409)
 def test_matching_produces_disjoint_proposals_with_missing_experience_warning_and_no_card_changes(self):
  rid=self.roster();path=f'/api/amateurs/rosters/{rid}';self.client.put(path+'/settings',headers=self.headers(),json={'name':'Amateur show','competition_date':'2027-01-30','version':1});before=self.db.query(BoxingBout).count();r=self.client.post(path+'/auto-match',headers=self.headers());self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(len(d['proposals']),1);p=d['proposals'][0];self.assertTrue(p['winning_percentages_missing']);self.assertTrue(p['experience_review_required']);self.assertEqual(p['max_round_minutes'],2);self.assertEqual(d['reference_year'],2026);self.assertEqual(d['age_basis'],'birthday');self.assertEqual(self.db.query(BoxingBout).count(),before);self.assertTrue(self.client.post(path+'/auto-match',headers=self.headers()).json()['existing']);self.assertEqual(self.db.query(AmateurMatchRun).count(),1);self.assertFalse(self.client.get(path,headers=self.headers()).json()['last_match']['stale'])
 def test_edit_and_exclusion_are_versioned_and_change_proposals(self):
  rid=self.roster();path=f'/api/amateurs/rosters/{rid}';self.client.put(path+'/settings',headers=self.headers(),json={'name':'Amateur show','competition_date':'2027-01-30','version':1});self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).status_code,200);entry=self.db.query(AmateurEntry).first();body={'data':entry.data,'version':1,'excluded':True};r=self.client.put(path+f'/entries/{entry.id}',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.put(path+f'/entries/{entry.id}',headers=self.headers(),json=body).status_code,409);self.assertTrue(self.client.get(path,headers=self.headers()).json()['last_match']['stale']);r=self.client.post(path+'/auto-match',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(r.json()['proposals']),0);self.assertEqual(len(r.json()['unmatched']),2)

class AppendixF2026Tests(unittest.TestCase):
 day=date(2027,6,15)
 def boxer(self,dob='2012-06-15',weight=125,bouts=0,sex='MALE',club='One',**extra):return {'dob':dob,'weight_lb':weight,'bouts':bouts,'sex':sex,'club':club,**extra}
 def pair(self,a,b,**preferences):return compatible(a,b,self.day,{**DEFAULT_PREFERENCES,**preferences})
 def test_local_age_limits_are_mutual_and_enforce_exact_24_months(self):
  self.assertIsNone(self.pair(self.boxer('2019-06-15'),self.boxer('2017-06-15',club='Two')))
  self.assertIsNotNone(self.pair(self.boxer('2018-06-15'),self.boxer('2016-06-15',club='Two')))
  self.assertIsNone(self.pair(self.boxer('2018-06-16'),self.boxer('2016-06-15',club='Two')))
  self.assertIsNone(self.pair(self.boxer('2018-01-01'),self.boxer('2015-12-31',club='Two')))
  self.assertIsNone(self.pair(self.boxer('2011-06-15'),self.boxer('2009-06-15',club='Two')))
  self.assertIsNotNone(self.pair(self.boxer('2010-06-15'),self.boxer('2009-06-15',club='Two')))
  self.assertIsNotNone(self.pair(self.boxer('2009-06-15'),self.boxer('1987-06-15',club='Two',masters_class='elite')))
 def test_birthday_not_calendar_year_and_under_eight_never_matches(self):
  self.assertIsNone(self.pair(self.boxer('2019-06-16'),self.boxer('2019-01-01',club='Two')))
 def test_weight_thresholds_use_lower_age_division_and_each_boxer(self):
  self.assertIsNotNone(self.pair(self.boxer(weight=101),self.boxer(weight=106,club='Two')))
  self.assertIsNone(self.pair(self.boxer(weight=101),self.boxer(weight=107,club='Two')))
  self.assertIsNotNone(self.pair(self.boxer(weight=125),self.boxer(weight=134,club='Two')))
  self.assertIsNone(self.pair(self.boxer(weight=114),self.boxer(weight=122,club='Two')))
  self.assertIsNone(self.pair(self.boxer(weight=154),self.boxer(weight=165,club='Two')))
 def test_peewee_coed_is_optional_and_never_applies_to_older_boxers(self):
  a=self.boxer('2018-06-15');b=self.boxer('2018-02-01',sex='FEMALE',club='Two');self.assertIsNone(self.pair(a,b));self.assertIsNotNone(self.pair(a,b,allow_coed_peewee=True));self.assertIsNone(self.pair(self.boxer(),self.boxer(sex='FEMALE',club='Two'),allow_coed_peewee=True))
 def test_masters_need_registered_class_and_ten_year_birthdate_limit(self):
  a=self.boxer('1985-06-15');b=self.boxer('1990-06-15',club='Two');self.assertIsNone(self.pair(a,b));b['masters_class']='masters';self.assertTrue(self.pair(a,b)['masters']);self.assertIsNone(self.pair(a,self.boxer('1994-06-15',club='Two')));self.assertIsNotNone(self.pair(self.boxer('1975-06-15'),self.boxer('1985-06-15',club='Two')));self.assertIsNone(self.pair(self.boxer('1975-06-14'),self.boxer('1985-06-15',club='Two')))
 def test_preferences_are_not_rulebook_limits(self):
  a=self.boxer(bouts=0);b=self.boxer(bouts=6,club='Two');self.assertIsNone(self.pair(a,b));self.assertIsNotNone(self.pair(a,b,max_bout_gap=6));self.assertIsNone(self.pair(a,self.boxer()));self.assertIsNotNone(self.pair(a,self.boxer(),allow_same_club=True))
  a=self.boxer('2000-01-01',weight=200);b=self.boxer('2000-01-01',weight=235,club='Two');self.assertIsNone(self.pair(a,b));self.assertIsNotNone(self.pair(a,b,max_unlimited_weight_gap_lb=35))

class AmateurConcurrencyTests(unittest.TestCase):
 setUp=AmateurRosterTests.setUp
 tearDown=AmateurRosterTests.tearDown
 headers=AmateurRosterTests.headers
 @unittest.skipUnless(support.TEST_DATABASE_URL,'Requires isolated PostgreSQL')
 def test_simultaneous_uploads_create_one_roster(self):
  from concurrent.futures import ThreadPoolExecutor
  from threading import Barrier
  from app.main import app
  from app.database import SessionLocal,get_db
  gate=Barrier(2);headers=self.headers()
  def separate_db():
   with SessionLocal() as db:yield db
  app.dependency_overrides[get_db]=separate_db
  def run(_):
   gate.wait();r=self.client.post('/api/amateurs/rosters/import',headers=headers,files={'file':('example.csv',CSV,'text/csv')});self.assertEqual(r.status_code,200,r.text);return r.json()['roster_id']
  with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(run,range(2)))
  self.assertEqual(len(set(ids)),1);self.assertEqual(self.db.query(AmateurRoster).count(),1);self.assertEqual(self.db.query(AmateurEntry).count(),2)
