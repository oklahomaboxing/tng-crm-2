import unittest
import test_stabilization as support
import test_ticketing as ticket_support
from app.ticketing.sales_links import public_sales_url
class TicketSalesLinksTests(unittest.TestCase):
 setUp=support.StabilizationTests.setUp
 tearDown=support.StabilizationTests.tearDown
 headers=support.StabilizationTests.headers
 order=ticket_support.TicketingTests.order
 def test_public_seller_portal_lookup_resolves_only_public_sales_details(self):
  self.order();r=self.client.get('/api/ticketing/public/sellers/'+self.seller.public_code.lower()+'/portal');self.assertEqual(r.status_code,200,r.text);d=r.json();self.assertEqual(d['event_id'],self.event.id);self.assertEqual(d['seller_code'],self.seller.public_code);self.assertEqual(d['public_url'],public_sales_url(self.event.id,self.seller.public_code));self.assertNotIn('email',d);self.assertNotIn('seller_ref_id',d);self.assertIn('no-store',r.headers['cache-control'])
  self.assertEqual(self.client.get('/api/ticketing/public/sellers/NOT-A-SELLER/portal').status_code,404)
 def test_qr_and_phone_link_helper_use_canonical_seller_path(self):
  self.order();r=self.client.get(f'/api/ticketing/events/{self.event.id}/sellers/{self.seller.id}/qr',headers=self.headers());self.assertEqual(r.status_code,200);self.assertEqual(r.json()['url'],public_sales_url(self.event.id,self.seller.public_code));self.assertIn('/tickets/'+self.seller.public_code,r.json()['url']);self.assertEqual(public_sales_url(self.event.id,self.seller.public_code,'phone'),r.json()['url']+'?source=phone')
 def test_resolving_a_paused_link_does_not_bypass_sales_policy(self):
  self.order();self.seller.active=False;self.db.commit();self.assertEqual(self.client.get('/api/ticketing/public/sellers/'+self.seller.public_code+'/portal').status_code,200);self.assertEqual(self.client.get(f'/api/ticketing/public/events/{self.event.id}/tickets',params={'seller':self.seller.public_code}).status_code,403)

 def test_legacy_phone_links_find_the_company_even_with_fighter_seller_type(self):
  from app.ticketing.models import EventSeller
  self.order();company=EventSeller(event_id=self.event.id,seller_type='fighter',seller_ref_id=99,display_name='TNG Promotions',public_code='F2-0000ABCD',active=True);self.db.add(company);self.db.commit()
  r=self.client.get(f'/api/ticketing/public/events/{self.event.id}/phone-portal');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['seller_code'],company.public_code);self.assertIn('/tickets/'+company.public_code,r.json()['public_url'])
