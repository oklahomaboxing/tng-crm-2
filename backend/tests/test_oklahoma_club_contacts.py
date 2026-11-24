import unittest
import test_stabilization as support
from app.amateurs.directory import DirectoryContact
from app.models import User,Member

class OklahomaClubContactTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 def test_oklahoma_filter_accepts_full_name_and_abbreviation_before_pagination(self):
  for i,state in enumerate(['OK','Oklahoma',' ok ','TX','']):
   self.db.add(DirectoryContact(identity_key=f'club-{i}',kind='club',name=f'Club {i}',details={'state':state},phones=['+14055550123']))
  self.db.commit()
  for state in ['OK','Oklahoma','oklahoma']:
   r=self.client.get('/api/amateurs/directory',params={'kind':'club','state':state},headers=self.headers());self.assertEqual(r.status_code,200);self.assertEqual(r.json()['total'],3)
  self.assertEqual(self.client.get('/api/amateurs/directory?kind=club',headers=self.headers()).json()['total'],5)
 def test_create_edit_search_and_clear_club_contact_preserves_existing_sources(self):
  before=(self.db.query(User).count(),self.db.query(Member).count())
  body={'kind':'club','name':'Example Boxing Club','phone':'4055550123','email':'coach@example.com','state':'OK','contact_name':'Coach Example'}
  r=self.client.post('/api/amateurs/directory',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);c=r.json();self.assertEqual(c['details']['contact_name'],'Coach Example');self.assertEqual(c['phones'],['+14055550123']);self.assertFalse(c['sms_consent'])
  row=self.db.get(DirectoryContact,c['id']);row.observations=[{'file':'source fixture','values':{'contact':'Old coach'}}];self.db.commit()
  r=self.client.put(f'/api/amateurs/directory/{c["id"]}',headers=self.headers(),json={**body,'version':c['version'],'contact_name':'Updated Coach'});self.assertEqual(r.status_code,200);c=r.json()
  found=self.client.get('/api/amateurs/directory?kind=club&state=OK&q=Updated%20Coach',headers=self.headers()).json();self.assertEqual(found['total'],1)
  r=self.client.put(f'/api/amateurs/directory/{c["id"]}',headers=self.headers(),json={**body,'version':c['version'],'contact_name':''});self.assertEqual(r.status_code,200);self.assertEqual(r.json()['details']['contact_name'],'')
  self.db.expire_all();self.assertEqual(self.db.get(DirectoryContact,c['id']).observations[0]['file'],'source fixture');self.assertEqual(before,(self.db.query(User).count(),self.db.query(Member).count()))
 def test_directory_remains_private(self):
  self.assertEqual(self.client.get('/api/amateurs/directory?kind=club&state=OK').status_code,401)
  self.assertEqual(self.client.get('/api/amateurs/directory?kind=club&state=OK',headers=self.headers('member')).status_code,403)
