"""Local sponsor discovery; all provider refresh calls mocked, no outreach."""
import json
import unittest
from unittest.mock import patch, Mock
import requests
import test_stabilization as support
from app.revenue import scout
from app.revenue.models import RevenueOrganization, EventRevenueProspect, RevenueOutreachMessage
from app.matchmaker.models import BoxingEvent

class SponsorScoutTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers

    def event(self):
        e=BoxingEvent(name='Local Fight Night',slug='sponsor-test');self.db.add(e);self.db.commit();return e

    def search(self,**kwargs):
        return scout.search_sponsors(event_name='TNG Boxing',event_address=scout.GYM_ADDRESS,**kwargs)

    def test_gym_search_works_without_ai_or_network_and_has_sources_not_sponsorship_claims(self):
        scout.CACHE.clear()
        with patch('app.revenue.scout.requests.get',side_effect=AssertionError('Unexpected network')):
            result=self.search(max_results=20)
        self.assertEqual(len(result['results']),20)
        self.assertEqual(result['search_source'],'SAVED_MAP_SNAPSHOT')
        self.assertIn('snapshot',result['notice'])
        self.assertTrue(all(r['source_urls'][0].startswith('https://www.openstreetmap.org/') for r in result['results']))
        self.assertTrue(all(r['verified_sponsorship_history'] is None and not r['sponsorship_evidence'] for r in result['results']))
        self.assertEqual(len({r['business_name'].casefold() for r in result['results']}),20)
        self.assertEqual([r['distance_miles'] for r in result['results']],sorted(r['distance_miles'] for r in result['results']))

    def test_categories_radius_and_bounded_results(self):
        result=self.search(category='automotive',radius_miles=1,max_results=3)
        self.assertLessEqual(len(result['results']),3);self.assertTrue(result['results'])
        self.assertTrue(all(r['distance_miles']<=1 for r in result['results']))
        self.assertTrue(all(r['industry'] in ['car','car repair','car parts','tyres','fuel','car wash','car rental'] for r in result['results']))

    def test_refresh_outage_returns_labeled_local_snapshot(self):
        with patch('app.revenue.scout.requests.get',side_effect=requests.Timeout):
            result=self.search(refresh=True)
        self.assertTrue(result['results']);self.assertEqual(result['search_source'],'SAVED_MAP_SNAPSHOT')

    def test_another_city_cannot_silently_receive_okc_results(self):
        with patch('app.revenue.scout.requests.get',side_effect=requests.Timeout):
            with self.assertRaisesRegex(RuntimeError,'address could not be located'):
                scout.search_sponsors(event_name='Event',event_address='123 Example Rd, Dallas, TX 75201')
        center={'lat':32.8,'lon':-96.8,'address':'Dallas, TX','source':'test'}
        with patch('app.revenue.scout.geocode',return_value=center),patch('app.revenue.scout.map_records',side_effect=requests.Timeout):
            with self.assertRaisesRegex(RuntimeError,'directory is unavailable'):
                scout.search_sponsors(event_name='Event',event_address='123 Example Rd, Dallas, TX 75201',refresh=True)

    def test_map_parsing_and_unsafe_links(self):
        xml=b'<osm><node id="1" lat="35.5687" lon="-97.6632"><tag k="name" v="Example Auto"/><tag k="shop" v="car_repair"/><tag k="website" v="javascript:alert(1)"/></node><node id="2" lat="35.5687" lon="-97.6632"><tag k="name" v="Example Church"/><tag k="amenity" v="place_of_worship"/></node></osm>'
        response=Mock(content=xml);response.raise_for_status.return_value=None
        center=scout.geocode(scout.GYM_ADDRESS)
        with patch('app.revenue.scout.requests.get',return_value=response):data=scout.map_records(center,5)
        results=scout.business_leads(data,center,5,'all','TNG',20)
        self.assertEqual([r['business_name'] for r in results],['Example Auto'])
        self.assertIsNone(results[0]['website'])
        self.assertIsNone(scout.public_url('http://127.0.0.1/private'))
        self.assertIsNone(scout.public_url('https://user:password@example.com'))

    def test_api_authorization_validation_and_read_only_search(self):
        e=self.event();path=f'/api/events/{e.id}/revenue/scout/sponsors';body={'event_name':e.name,'event_address':scout.GYM_ADDRESS}
        r=self.client.post(path,headers=self.headers(),json=body)
        self.assertEqual(r.status_code,200,r.text);self.assertTrue(r.json()['results'])
        self.assertEqual(self.db.query(RevenueOrganization).count(),0)
        self.assertEqual(self.db.query(RevenueOutreachMessage).count(),0)
        self.assertEqual(self.client.post(path,json=body).status_code,401)
        for role in ['fighter','member','rep']:
            self.assertEqual(self.client.post(path,headers=self.headers(role),json=body).status_code,403)
        self.assertEqual(self.client.post(path,headers=self.headers(),json={**body,'radius_miles':100}).status_code,422)
        self.assertEqual(self.client.post('/api/events/99999/revenue/scout/sponsors',headers=self.headers(),json=body).status_code,404)

    def test_pipeline_saves_public_contacts_without_outreach_and_preserves_known_history(self):
        e=self.event();candidate=self.search(max_results=1)['results'][0]
        candidate.update(phone='+14055550123',email='sponsor@example.com',address='123 Example Street',city='Oklahoma City',state='OK')
        path=f'/api/events/{e.id}/revenue/scout/sponsors/add-to-pipeline'
        with patch('app.revenue.routes.send_revenue_proposal_email') as send:
            r=self.client.post(path,headers=self.headers(),json=candidate)
            self.assertEqual(r.status_code,200,r.text);send.assert_not_called()
            org=self.db.get(RevenueOrganization,r.json()['organization_id']);self.assertEqual(org.phone,candidate['phone']);self.assertEqual(org.email,candidate['email'])
            org.verified_sponsorship_history=True;org.notes='Existing relationship';org.marketing_evidence_json=json.dumps({'sponsorship_evidence':['Verified event support'],'source_urls':['https://example.com/history']});self.db.commit()
            again=self.client.post(path,headers=self.headers(),json=candidate)
            self.assertEqual(again.status_code,200,again.text);self.assertTrue(again.json()['already_exists'])
            self.db.refresh(org);self.assertTrue(org.verified_sponsorship_history);self.assertEqual(org.notes,'Existing relationship')
            self.assertIn('Verified event support',org.marketing_evidence_json)
            self.assertEqual(self.db.query(EventRevenueProspect).count(),1)
            self.assertEqual(self.db.query(RevenueOutreachMessage).count(),0);send.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
