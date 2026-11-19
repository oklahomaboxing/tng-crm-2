import unittest,json
from unittest.mock import patch
import test_amateur_rosters as source
from app.amateurs.rosters import AmateurEntry,AmateurRoster
from app.amateurs.tournaments import DEFAULT_SESSIONS,TournamentPlan,TournamentDivision
from app.amateurs.directory import DirectoryContact,DirectoryImport
from app.amateurs.officials import OfficialRequest,OfficialMessage

class EventCase(unittest.TestCase):
 setUp=source.AmateurRosterTests.setUp
 tearDown=source.AmateurRosterTests.tearDown
 headers=source.AmateurRosterTests.headers
 upload=source.AmateurRosterTests.upload
 roster=source.AmateurRosterTests.roster
 def plan(self,**extra):
  body={'roster_id':self.roster(),'request_key':'fixture-tournament-0001','name':'Example Tournament','saturday':'2027-01-30','sessions':DEFAULT_SESSIONS,'sunday_am':'auto','slot_minutes':15,**extra}
  r=self.client.post('/api/amateurs/tournaments',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);return r.json()
 def entries(self,rid,count):
  existing=self.db.query(AmateurEntry).filter_by(roster_id=rid).all()
  for i in range(count-len(existing)):
   self.db.add(AmateurEntry(roster_id=rid,row_number=100+i,data={**existing[0].data,'member_id':str(900000+i),'last_name':'Extra '+str(i)},issues=[],excluded=False))
  self.db.commit();return [r.id for r in self.db.query(AmateurEntry).filter_by(roster_id=rid).order_by(AmateurEntry.id)]
 def division(self,p,ids,name='Example Division'):
  r=self.client.post(f"/api/amateurs/tournaments/{p['id']}/divisions",headers=self.headers(),json={'name':name,'entry_ids':ids,'version':p['version']});self.assertEqual(r.status_code,200,r.text);return r.json()
 def schedule(self,p):
  r=self.client.post(f"/api/amateurs/tournaments/{p['id']}/schedule",headers=self.headers(),json={'version':p['version']});self.assertEqual(r.status_code,200,r.text);return r.json()

class TournamentTests(EventCase):
 def test_four_boxer_bracket_uses_saturday_semis_and_sunday_final(self):
  p=self.plan();ids=self.entries(p['roster_id'],4);p=self.division(p,ids);p=self.schedule(p);self.assertEqual(len(p['nodes']),3);self.assertEqual(len(p['schedule']['bouts']),3);self.assertFalse(p['schedule']['sunday_am_enabled']);self.assertFalse(p['schedule']['unscheduled']);lookup={n['key']:n for n in p['nodes']}
  for b in p['schedule']['bouts']:self.assertEqual(b['session_key'],'sat_am' if lookup[b['bout_key']]['round']==1 else 'sun_pm')
  r=self.client.get(f"/api/amateurs/tournaments/{p['id']}/schedule.csv",headers=self.headers());self.assertEqual(r.status_code,200);self.assertIn('OIC approval required',r.text)
 def test_sunday_am_is_added_only_when_it_reduces_overflow(self):
  p=self.plan(sessions={k:{**v,'capacity':1} for k,v in DEFAULT_SESSIONS.items()});ids=self.entries(p['roster_id'],8)
  for i in range(4):p=self.division(p,ids[i*2:i*2+2],f'Division {i}')
  p=self.schedule(p);self.assertTrue(p['schedule']['sunday_am_enabled']);self.assertEqual(len(p['schedule']['bouts']),4);self.assertFalse(p['schedule']['unscheduled'])
 def test_eight_boxer_three_round_bracket_is_not_forced_into_two_days(self):
  p=self.plan(sunday_am='on');p=self.division(p,self.entries(p['roster_id'],8));p=self.schedule(p);self.assertEqual(len(p['schedule']['unscheduled']),1);self.assertIn('r3',p['schedule']['unscheduled'][0]['bout_key']);self.assertEqual(len(p['schedule']['bouts']),6)
  lookup={n['key']:n for n in p['nodes']};seen=set()
  for b in p['schedule']['bouts']:
   for eid in lookup[b['bout_key']]['potential_ids']:
    key=(eid,b['start_local'][:10]);self.assertNotIn(key,seen);seen.add(key)
 def test_byes_advance_without_counting_as_bouts_and_duplicate_boxers_rejected(self):
  p=self.plan();ids=self.entries(p['roster_id'],3);p=self.division(p,ids);self.assertEqual(sum(n['bye'] for n in p['nodes']),1);p=self.schedule(p);self.assertEqual(len(p['schedule']['bouts']),2)
  r=self.client.post(f"/api/amateurs/tournaments/{p['id']}/divisions",headers=self.headers(),json={'name':'Duplicate','entry_ids':[ids[0]],'version':p['version']});self.assertEqual(r.status_code,409)
 def test_results_require_parents_and_protect_downstream_winners(self):
  p=self.plan();p=self.division(p,self.entries(p['roster_id'],4));nodes=p['nodes'];url=f"/api/amateurs/tournaments/{p['id']}/results/";final=nodes[-1]
  self.assertEqual(self.client.post(url+final['key'],headers=self.headers(),json={'winner_id':nodes[0]['red_entry_id'],'version':p['version'],'official_result_confirmed':True}).status_code,409)
  for n in nodes[:2]:
   r=self.client.post(url+n['key'],headers=self.headers(),json={'winner_id':n['red_entry_id'],'version':p['version'],'official_result_confirmed':True});self.assertEqual(r.status_code,200,r.text);p=r.json()
  final=p['nodes'][-1];self.assertTrue(final['red_entry_id'] and final['blue_entry_id']);r=self.client.post(url+final['key'],headers=self.headers(),json={'winner_id':final['red_entry_id'],'version':p['version'],'official_result_confirmed':True});self.assertEqual(r.status_code,200,r.text);p=r.json();self.assertEqual(self.client.delete(url+nodes[0]['key'],headers=self.headers(),params={'version':p['version']}).status_code,409)
 def test_date_session_and_versions_validate(self):
  p=self.plan();body={'roster_id':p['roster_id'],'name':'Wrong day','saturday':'2027-01-29','sessions':DEFAULT_SESSIONS};self.assertEqual(self.client.post('/api/amateurs/tournaments',headers=self.headers(),json=body).status_code,422)
  body.update(saturday='2027-01-30',sessions={k:{**v,'capacity':100} for k,v in DEFAULT_SESSIONS.items()});self.assertEqual(self.client.post('/api/amateurs/tournaments',headers=self.headers(),json=body).status_code,422)
  for role in ('member','fighter','rep'):self.assertEqual(self.client.get('/api/amateurs/tournaments',headers=self.headers(role),params={'roster_id':p['roster_id']}).status_code,403)
  self.assertEqual(self.client.get('/api/amateurs/tournaments',params={'roster_id':p['roster_id']}).status_code,401)

class DirectoryOfficialTests(EventCase):
 def contact(self,**extra):
  body={'kind':'person','name':'Example Official','email':'official@example.com','phone':'4055550113','roles':['judge'],'role_verified':True,**extra};r=self.client.post('/api/amateurs/directory',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);return r.json()
 def invitation(self,contact=None):
  rid=self.roster();self.client.put(f'/api/amateurs/rosters/{rid}/settings',headers=self.headers(),json={'name':'Amateur Event','competition_date':'2027-01-30','version':1});c=contact or self.contact();r=self.client.post(f'/api/amateurs/officials/events/{rid}/requests',headers=self.headers(),json={'contact_id':c['id']});self.assertEqual(r.status_code,200,r.text);return rid,r.json()['request_id']
 def test_source_membership_does_not_infer_official_role_sms_permission_or_gym_membership(self):
  from app.amateurs.directory import MEMBER_HEADERS
  import csv,io
  out=io.StringIO();w=csv.writer(out,delimiter='\t');w.writerow(MEMBER_HEADERS);row=['123456','Official','Example','','','OKC','OK','73162','United States','official@example.com','4055550113','01/01/1990','Non-Athlete','Current','Example Club','Oklahoma'];w.writerow(row)
  users=self.db.query(source.User).count();r=self.client.post('/api/amateurs/directory/import',headers=self.headers(),files={'file':('example.txt',out.getvalue(),'text/plain')});self.assertEqual(r.status_code,200,r.text);c=self.db.query(DirectoryContact).one();self.assertFalse(c.role_verified);self.assertFalse(c.sms_consent);self.assertEqual(c.roles,[]);self.assertEqual(self.db.query(source.User).count(),users)
  r2=self.client.post('/api/amateurs/directory/import',headers=self.headers(),files={'file':('copy.txt',out.getvalue(),'text/plain')});self.assertTrue(r2.json()['existing']);self.assertEqual(self.db.query(DirectoryContact).count(),1)
 def test_public_reply_is_scoped_and_availability_is_separate_from_assignment(self):
  rid,qid=self.invitation();p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();token=p['reply_link'].split('#')[-1]
  r=self.client.post('/api/amateurs/officials/public/view',json={'token':token});self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertNotIn('email',r.text);self.assertNotIn('phones',r.text);self.assertNotIn('staff_note',d)
  r=self.client.post('/api/amateurs/officials/public/reply',json={'token':token,'version':d['version'],'availability':{'event':'available'},'note':'Available'});self.assertEqual(r.status_code,200,r.text);q=self.db.get(OfficialRequest,qid);self.db.refresh(q);self.assertEqual(q.confirmed_roles,{})
  self.client.put(f'/api/amateurs/officials/events/{rid}/requirements',headers=self.headers(),json={'requirements':{'event':{'judge':2}},'version':1})
  c=self.client.get(f'/api/amateurs/officials/events/{rid}',headers=self.headers()).json();self.assertEqual(c['coverage'][0]['shortfall'],2)
  self.assertEqual(self.client.put(f'/api/amateurs/officials/requests/{qid}',headers=self.headers(),json={'availability':q.availability,'confirmed_roles':{'event':'judge'},'version':q.version}).status_code,200)
  c=self.client.get(f'/api/amateurs/officials/events/{rid}',headers=self.headers()).json();self.assertEqual(c['coverage'][0]['confirmed'],1);self.assertEqual(c['coverage'][0]['shortfall'],1)
 def test_changed_dates_invalidate_reply_and_reissue_revokes_old_link(self):
  rid,qid=self.invitation();p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();old=p['reply_link'].split('#')[-1];r=self.db.get(AmateurRoster,rid);r.competition_date=source.datetime(2027,2,1).date() if hasattr(source,'datetime') else __import__('datetime').date(2027,2,1);self.db.commit()
  self.assertEqual(self.client.post('/api/amateurs/officials/public/view',json={'token':old}).status_code,409);q=self.db.get(OfficialRequest,qid);self.assertEqual(self.client.post(f'/api/amateurs/officials/requests/{qid}/refresh',headers=self.headers(),json={'version':q.version}).status_code,200);self.assertEqual(self.client.post('/api/amateurs/officials/public/view',json={'token':old}).status_code,404)
 def test_sending_requires_review_and_sms_permission_and_is_idempotent(self):
  _,qid=self.invitation();p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();url=f'/api/amateurs/officials/requests/{qid}/send';body={'channel':'sms','preview_hash':p['preview_hash'],'request_key':'fixture-send-00000001'};self.assertEqual(self.client.post(url,headers=self.headers(),json=body).status_code,422)
  with patch('app.mail.microsoft365.selected_provider',return_value='resend'),patch.dict('os.environ',{'RESEND_API_KEY':'fixture'}),patch('resend.Emails.send',return_value={'id':'fixture-email'}) as provider:
   body['channel']='email';r=self.client.post(url,headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'accepted');again=self.client.post(url,headers=self.headers(),json=body);self.assertEqual(again.json()['status'],'accepted');self.assertEqual(provider.call_count,1)
  self.assertEqual(self.client.post('/api/amateurs/officials/public/view',json={'token':'invalid-token-of-minimum-length-12345'}).status_code,404)

class ExtraDirectoryOfficialTests(EventCase):
 contact=DirectoryOfficialTests.contact
 invitation=DirectoryOfficialTests.invitation
 def test_sms_uses_approved_service_and_stop_footer_and_blocks_optouts(self):
  from app.operations.renewal_reminders import suppress_sms
  c=self.contact(sms_consent=True,consent_note='Fixture official gave permission in writing');_,qid=self.invitation(c);p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();body={'channel':'sms','preview_hash':p['preview_hash'],'request_key':'fixture-sms-00000001'}
  with patch('app.marketing.sms.approved_routes',return_value={'notification':'MGfixture'}),patch.dict('os.environ',{'TWILIO_ACCOUNT_SID':'fixture','TWILIO_AUTH_TOKEN':'fixture'}),patch('twilio.rest.Client') as provider:
   provider.return_value.messages.create.return_value.sid='SM'+'a'*32;r=self.client.post(f'/api/amateurs/officials/requests/{qid}/send',headers=self.headers(),json=body);self.assertEqual(r.json()['status'],'accepted');kw=provider.return_value.messages.create.call_args.kwargs;self.assertEqual(kw['messaging_service_sid'],'MGfixture');self.assertEqual(kw['body'].count('Reply STOP to unsubscribe.'),1)
   suppress_sms(self.db,c['phones'][0]);self.db.commit();body['request_key']='fixture-sms-blocked-0001';self.assertEqual(self.client.post(f'/api/amateurs/officials/requests/{qid}/send',headers=self.headers(),json=body).status_code,422);self.assertEqual(provider.return_value.messages.create.call_count,1)
 def test_unknown_email_submission_is_not_replayed(self):
  _,qid=self.invitation();p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();body={'channel':'email','preview_hash':p['preview_hash'],'request_key':'fixture-unknown-000001'}
  with patch('app.mail.microsoft365.selected_provider',return_value='microsoft365'),patch('app.mail.microsoft365.send_welcome',side_effect=RuntimeError('fixture offline')) as provider,patch('resend.Emails.send') as fallback:
   for _ in range(2):self.assertEqual(self.client.post(f'/api/amateurs/officials/requests/{qid}/send',headers=self.headers(),json=body).json()['status'],'unknown')
   self.assertEqual(provider.call_count,1);fallback.assert_not_called()
 def test_public_withdrawal_removes_confirmed_assignment(self):
  _,qid=self.invitation();q=self.db.get(OfficialRequest,qid);q.availability={'event':'available'};q.confirmed_roles={'event':'judge'};self.db.commit();p=self.client.get(f'/api/amateurs/officials/requests/{qid}/preview',headers=self.headers()).json();token=p['reply_link'].split('#')[-1]
  r=self.client.post('/api/amateurs/officials/public/reply',json={'token':token,'version':q.version,'availability':{'event':'unavailable'},'note':'Cannot attend'});self.assertEqual(r.status_code,200,r.text);self.db.refresh(q);self.assertEqual(q.confirmed_roles,{});self.assertEqual(self.db.query(OfficialMessage).filter_by(channel='reply',request_id=qid).count(),1)
 def test_broken_flat_export_is_retained_then_recovered_only_against_equivalent_excel(self):
  from app.amateurs.directory import CLUB_HEADERS
  import html
  row=['Example Club','4055550111','club@example.com','Example','Contact','club@example.com','','Example Contact','','123 Example St','','OKC','OK','73162'];flat='\t'.join(CLUB_HEADERS)+'\t'.join(row);broken=flat.replace('\t\t','\t',1)
  def send(filename,content):return self.client.post('/api/amateurs/directory/import',headers=self.headers(),files={'file':(filename,content,'text/plain')})
  first=send('broken.txt',broken);self.assertTrue(first.json()['needs_review']);self.assertEqual(self.db.query(DirectoryContact).count(),0)
  source_html='<html><table>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in values)+'</tr>' for values in [CLUB_HEADERS,row])+'</table></html>'
  self.assertEqual(send('equivalent.xls',source_html).status_code,200);r=send('broken.txt',broken);self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['recovered_from_equivalent_excel']);self.assertEqual(self.db.query(DirectoryContact).count(),1);self.assertEqual(self.db.query(DirectoryImport).count(),2)

class TournamentIdempotencyTests(EventCase):
 def test_create_retry_reopens_same_plan_without_resetting_divisions(self):
  p=self.plan();ids=self.entries(p['roster_id'],2);p=self.division(p,ids);body={'roster_id':p['roster_id'],'name':p['name'],'saturday':p['saturday'],'sessions':p['sessions'],'sunday_am':p['sunday_am'],'slot_minutes':p['slot_minutes'],'request_key':'fixture-tournament-0001'};r=self.client.post('/api/amateurs/tournaments',headers=self.headers(),json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['id'],p['id']);self.assertEqual(len(r.json()['divisions']),1);self.assertEqual(self.db.query(TournamentPlan).count(),1)

 def test_default_noon_sessions_fit_sunday_pm_and_preserve_legacy_time_label(self):
  from app.amateurs.tournaments import session_list,session_label
  p=self.plan();self.assertEqual(p['sessions']['sat_am']['start'],'12:00');self.assertEqual(p['sessions']['sun_am']['start'],'12:00')
  row=self.db.get(TournamentPlan,p['id']);sessions=session_list(row,True)
  self.assertEqual(sessions[0]['label'],'Saturday Noon');self.assertEqual(sessions[2]['label'],'Sunday Noon')
  self.assertLessEqual(sessions[2]['ends_at'],sessions[3]['starts_at'])
  self.assertEqual(session_label('sat_am','09:00'),'Saturday Morning (saved time)')
