import unittest
import test_amateur_rosters as support
from app.amateurs.experience import experience_class,experience_pair
from app.amateurs.rosters import AmateurEntry,AmateurRoster

class ExperiencePolicyTests(unittest.TestCase):
 def test_boundaries_unknowns_and_mixed_consideration(self):
  for n in [0,7,8,9,10]:self.assertEqual(experience_class(n),'novice')
  for n in [11,12,1000]:self.assertEqual(experience_class(n),'open')
  for n in [None,True,'',-1,8.5,1001]:self.assertEqual(experience_class(n),'review')
  self.assertIsNone(experience_pair({'bouts':7},{'bouts':11}))
  for n in [8,9,10]:
   self.assertTrue(experience_pair({'bouts':n},{'bouts':11})['novice_open_review_required']);self.assertIsNone(experience_pair({'bouts':n},{'bouts':11},False))
  self.assertFalse(experience_pair({'bouts':0},{'bouts':10})['novice_open_review_required']);self.assertFalse(experience_pair({'bouts':11},{'bouts':12})['novice_open_review_required'])

class ExperienceApiTests(unittest.TestCase):
 setUp=support.AmateurRosterTests.setUp
 tearDown=support.AmateurRosterTests.tearDown
 headers=support.AmateurRosterTests.headers
 upload=support.AmateurRosterTests.upload
 def roster(self,bouts=(7,11),weights=(125,128)):
  rows=support.HEAD+f'001,Able,Boxer,02/21/2010,16,MALE,{weights[0]}lbs,{bouts[0]},Coach,One,OK,OKC,OK,Club One\n'+f'002,Baker,Boxer,02/21/2010,16,MALE,{weights[1]}lbs,{bouts[1]},Coach,Two,OK,Tulsa,OK,Club Two\n'
  rid=self.upload(rows.encode()).json()['roster_id'];path=f'/api/amateurs/rosters/{rid}';r=self.client.put(path+'/settings',headers=self.headers(),json={'name':'Experience show','competition_date':'2027-01-30','version':1});self.assertEqual(r.status_code,200,r.text);return rid,path
 def test_zero_to_seven_cannot_face_open_and_eight_can_only_be_flagged(self):
  rid,path=self.roster();r=self.client.post(path+'/auto-match',headers=self.headers());self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['maximum_bouts'],0)
  boxer=self.db.query(AmateurEntry).filter_by(roster_id=rid).order_by(AmateurEntry.id).first();body={**boxer.data,'bouts':8};r=self.client.put(path+f'/entries/{boxer.id}',headers=self.headers(),json={'data':body,'excluded':False,'version':boxer.version});self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['experience_class'],'novice');self.assertTrue(self.client.get(path,headers=self.headers()).json()['last_match']['stale'])
  d=self.client.post(path+'/auto-match',headers=self.headers()).json();self.assertEqual(d['maximum_bouts'],1);self.assertTrue(d['proposals'][0]['novice_open_review_required']);self.assertEqual(d['novice_open_consideration_bouts'],1)
  self.db.expire_all();roster=self.db.get(AmateurRoster,rid);self.assertEqual(self.client.put(path+'/settings',headers=self.headers(),json={'name':roster.name,'competition_date':'2027-01-30','version':roster.version,'preferences':{'allow_novice_open_consideration':False}}).status_code,200);self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).json()['maximum_bouts'],0)
 def test_exactly_ten_is_novice_and_eleven_is_open_and_weight_checks_still_apply(self):
  rid,path=self.roster((10,11));d=self.client.get(path,headers=self.headers()).json();self.assertEqual([e['experience_class']for e in d['entries']],['novice','open']);self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).json()['maximum_bouts'],1)
  rid,path=self.roster((8,11),(125,145));self.assertEqual(self.client.post(path+'/auto-match',headers=self.headers()).json()['maximum_bouts'],0)
 def test_same_class_pairs_preferred_when_cardinality_is_equal(self):
  rows=support.HEAD+''.join(f'00{i+1},Boxer,Number{i},02/21/2010,16,MALE,{weight}lbs,{bouts},Coach,{i},OK,OKC,OK,Club {i}\n'for i,(bouts,weight)in enumerate([(8,125),(9,130),(11,125),(12,130)]));rid=self.upload(rows.encode()).json()['roster_id'];path=f'/api/amateurs/rosters/{rid}';self.client.put(path+'/settings',headers=self.headers(),json={'name':'Class preference','competition_date':'2027-01-30','version':1});d=self.client.post(path+'/auto-match',headers=self.headers()).json();self.assertEqual(d['maximum_bouts'],2);self.assertEqual(d['novice_open_consideration_bouts'],0);self.assertTrue(all(len(set(p['experience_classes']))==1 for p in d['proposals']))
