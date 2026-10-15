"""Regional discovery permissions, provenance, and follow-up regressions."""
import json
import unittest
from unittest.mock import patch, Mock
import test_stabilization as support
from app.matchmaker.discovery import clean_lead, public_url, SearchRequest, search_public_web, DiscoveryLead

LEAD={"kind":"gym","name":"Example Pro Boxing Gym","city":"Tulsa","state":"OK","source_url":"https://example.org/boxing",
      "business_email":"coach@example.org","business_phone":"+1 918 555 0100","evidence":"Boxing enquiries: coach@example.org; +1 918 555 0100"}

class DiscoveryTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    def test_permissions_and_no_unauthenticated_search(self):
        self.assertEqual(self.client.get('/api/boxing/discovery/leads').status_code,401)
        for role in ['rep','member','fighter']:
            self.assertEqual(self.client.get('/api/boxing/discovery/leads',headers=self.headers(role)).status_code,403)
            self.assertEqual(self.client.post('/api/boxing/discovery/search',headers=self.headers(role),json={}).status_code,403)
    def test_save_is_idempotent_and_followup_does_not_infer_availability(self):
        url='/api/boxing/discovery/leads';h=self.headers('admin')
        r=self.client.post(url,headers=h,json=LEAD);self.assertEqual(r.status_code,200,r.text);row=r.json()
        self.assertEqual(row['availability'],'unknown');self.assertIsNone(row['availability_checked_at'])
        again=self.client.post(url,headers=h,json=LEAD);self.assertEqual(again.json()['id'],row['id'])
        self.assertEqual(self.db.query(DiscoveryLead).count(),1)
        r=self.client.patch(url+'/'+str(row['id']),headers=h,json={'outreach_status':'contacted','availability':'unknown','notes':'Call gym for November bout availability'})
        self.assertEqual(r.json()['availability'],'unknown');self.assertIsNone(r.json()['availability_checked_at'])
        r=self.client.patch(url+'/'+str(row['id']),headers=h,json={'outreach_status':'interested','availability':'available','notes':'Gym confirmed November 14 by phone'})
        self.assertEqual(r.status_code,200,r.text);self.assertIsNotNone(r.json()['availability_checked_at'])
        self.assertEqual(self.client.get(url,headers=h).json()[0]['notes'],'Gym confirmed November 14 by phone')
    def test_rejects_bad_urls_and_unsupported_states(self):
        for url in ['javascript:alert(1)','https://127.0.0.1/x','https://192.168.0.1/x','https://user:pass@example.org/x','https://host.internal/x','http://example.org']:
            self.assertIsNone(public_url(url),url)
        self.assertIsNone(clean_lead({**LEAD,'state':'ZZ'}))
        self.assertEqual(self.client.post('/api/boxing/discovery/search',headers=self.headers('admin'),json={'states':['ZZ']}).status_code,422)
        self.assertEqual(self.client.post('/api/boxing/discovery/search',headers=self.headers('admin'),json={'weight_min':200,'weight_max':150}).status_code,400)
    def test_uncited_sources_and_unsupported_contacts_are_removed(self):
        self.assertIsNone(clean_lead(LEAD,{'https://other.example.org'}))
        self.assertIsNotNone(clean_lead(LEAD,{LEAD['source_url']+'?utm_source=openai'}))
        lead=clean_lead({**LEAD,'evidence':'A gym located in Tulsa.'},{LEAD['source_url']})
        self.assertEqual(lead['business_phone'],'');self.assertEqual(lead['business_email'],'')
        self.assertEqual(clean_lead(LEAD,{LEAD['source_url']})['business_email'],'coach@example.org')
    def test_missing_provider_is_explicit(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            r=self.client.post('/api/boxing/discovery/search',headers=self.headers('admin'),json={})
        self.assertEqual(r.status_code,503)
    def test_search_returns_only_requested_kind_region_and_real_sources(self):
        rows=[LEAD,{**LEAD,'name':'Not cited','source_url':'https://invented.example.org'}, {**LEAD,'kind':'manager'},{**LEAD,'state':'TX'}]
        payload={'output':[{'type':'web_search_call','action':{'sources':[{'url':LEAD['source_url']}]}}, {'type':'message','content':[{'type':'output_text','text':'Public research follows. ```json\n'+json.dumps({'leads':rows})+'\n``` Source notes after JSON.','annotations':[]}]}]}
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.return_value=json.dumps(payload).encode()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'local-test-only'}),patch('urllib.request.urlopen',return_value=response):
            result=search_public_web(SearchRequest(kind='gym',states=['OK']))
        self.assertEqual(len(result['leads']),1);self.assertEqual(result['leads'][0]['source_url'],LEAD['source_url'])
        self.assertNotIn('availability',result['leads'][0])
    def test_activity_dates_are_explicit_and_validated(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            SearchRequest(active_since="not-a-date")
        lead=clean_lead({**LEAD,'last_bout_date':'2099-01-01'})
        self.assertEqual(lead['last_bout_date'],'')
        lead=clean_lead({**LEAD,'last_bout_date':'2024-01-02'})
        self.assertEqual(lead['last_bout_date'],'2024-01-02')
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'leads':[lead]}),'annotations':[{'type':'url_citation','url':LEAD['source_url']}]}]}]}).encode()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'local-test-only'}),patch('urllib.request.urlopen',return_value=response):
            self.assertEqual(search_public_web(SearchRequest(kind='gym',states=['OK'],active_since='2025-01-01'))['leads'],[])

    def test_invalid_update_and_missing_lead(self):
        h=self.headers('staff');url='/api/boxing/discovery/leads/999'
        self.assertEqual(self.client.patch(url,headers=h,json={'outreach_status':'sent','availability':'unknown'}).status_code,400)
        self.assertEqual(self.client.patch(url,headers=h,json={'outreach_status':'contacted','availability':'unknown'}).status_code,404)

    def test_cited_prose_is_extracted_without_losing_source_validation(self):
        first={'output':[{'type':'message','content':[{'type':'output_text','text':'Example Pro Boxing Gym is in Tulsa, Oklahoma. Published boxing office coach@example.org.',
            'annotations':[{'type':'url_citation','url':LEAD['source_url']}]}]}]}
        second={'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'leads':[LEAD,{**LEAD,'source_url':'https://uncited.example.org'}]})}]}]}
        responses=[]
        for payload in [first,second]:
            response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.return_value=json.dumps(payload).encode();responses.append(response)
        with patch.dict('os.environ',{'OPENAI_API_KEY':'local-test-only'}),patch('urllib.request.urlopen',side_effect=responses) as send:
            result=search_public_web(SearchRequest(kind='gym',states=['OK']))
        self.assertEqual(len(result['leads']),1)
        research=json.loads(send.call_args_list[0].args[0].data)
        extract=json.loads(send.call_args_list[1].args[0].data)
        self.assertNotIn('text',research);self.assertNotIn('tools',extract)
        self.assertEqual(extract['text']['format']['type'],'json_schema')

    def test_exhausted_api_credits_have_actionable_error(self):
        import io,urllib.error
        error=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'Quota',{},io.BytesIO(json.dumps({'error':{'code':'credit_balance_exhausted'}}).encode()))
        with patch.dict('os.environ',{'OPENAI_API_KEY':'local-test-only'}),patch('urllib.request.urlopen',side_effect=error):
            r=self.client.post('/api/boxing/discovery/search',headers=self.headers(),json={})
        self.assertEqual(r.status_code,503);self.assertIn('Official promoter profiles',r.json()['detail'])

    def test_saved_fighter_search_works_without_provider_and_filters_losing_records(self):
        from app.matchmaker.scouting import ProspectCreate,store_prospect
        from types import SimpleNamespace
        common=dict(state='TX',city='Dallas',weight='133 lb',source_url='https://example.org/pro-result')
        for name,record in [('Losing Pro','1-4'),('Winning Pro','4-1'),('Unknown Pro','')]:
            store_prospect(ProspectCreate(name=name,record=record,**common),self.db,SimpleNamespace(id=1))
        with patch('app.matchmaker.discovery.search_public_web') as web:
            r=self.client.post('/api/boxing/discovery/search',headers=self.headers(),json={'source':'catalog','states':['TX'],'query':'Dallas','record_type':'losing','weight_min':130,'weight_max':135})
        self.assertEqual(r.status_code,200,r.text);web.assert_not_called()
        self.assertEqual([p['name'] for p in r.json()['leads']],['Losing Pro'])
        self.assertNotIn('id',r.json()['leads'][0])
        saved=self.client.post('/api/boxing/discovery/leads',headers=self.headers(),json=r.json()['leads'][0])
        self.assertEqual(saved.status_code,200,saved.text)

    def test_saved_search_requires_actual_bout_date_not_article_publication(self):
        from app.matchmaker.discovery import filter_research_leads
        base={**LEAD,'kind':'fighter','business_phone':'','business_email':''}
        body=SearchRequest(source='catalog',states=['OK'],active_since='2026-01-01')
        rows=filter_research_leads(body,[{**base,'name':'Publication only','last_activity':'Professional coverage published 2026-09-24'},
            {**base,'name':'Actual bout','last_activity':'Professional bout listed in official TDLR results on 2026-09-24; 4 scheduled rounds.'}])
        self.assertEqual([p['name'] for p in rows],['Actual bout'])

    def test_official_source_and_saved_gyms_work_without_provider(self):
        self.client.post('/api/boxing/discovery/leads',headers=self.headers(),json=LEAD)
        r=self.client.post('/api/boxing/discovery/search',headers=self.headers(),json={'source':'catalog','kind':'gym','states':['OK']})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['total'],1)
        with patch('app.matchmaker.official_rosters.search_official_rosters',return_value={'leads':[{**LEAD,'kind':'fighter','record':'0-2','weight':'130 lb'}]}):
            r=self.client.post('/api/boxing/discovery/search',headers=self.headers(),json={'source':'official_rosters','states':['OK'],'record_type':'losing'})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['total'],1)

if __name__=='__main__':unittest.main(verbosity=2)
