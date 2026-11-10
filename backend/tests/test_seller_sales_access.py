import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import test_stabilization as support
import test_ticketing as ticket_support
from app.ticketing.models import EventSalesWindow, EventSeller, TicketOrder
from app.ticketing.sales_access import sales_access

class SellerSalesTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers
    order = ticket_support.TicketingTests.order

    def test_pause_blocks_catalog_order_and_saved_checkout_but_not_history(self):
        order = self.order()
        path = f'/api/ticketing/events/{self.event.id}/sellers/{self.seller.id}/sales'
        self.assertEqual(self.client.patch(path, headers=self.headers('member'), json={'active':False}).status_code,403)
        self.assertEqual(self.client.patch(path, headers=self.headers(), json={'active':False}).status_code,200)
        public=f'/api/ticketing/public/events/{self.event.id}'
        self.assertEqual(self.client.get(public+'/tickets',params={'seller':self.seller.public_code}).status_code,403)
        with patch('app.ticketing.checkout_routes.requests.post') as post:
            self.assertEqual(self.client.post(f'/api/ticketing/public/orders/{order.id}/checkout').status_code,403)
            post.assert_not_called()
        self.assertEqual(self.db.get(TicketOrder,order.id).payment_status,'pending')
        self.assertEqual(self.client.patch(path, headers=self.headers(), json={'active':True}).status_code,200)
        self.assertEqual(self.client.get(public+'/tickets',params={'seller':self.seller.public_code}).status_code,200)

    def test_cutoff_boundary_timezone_exemption_and_manual_pause(self):
        self.order()
        tng=EventSeller(event_id=self.event.id,seller_type='staff',seller_ref_id=1,display_name='TNG Promotions',public_code='TNG-TEST')
        self.db.add(tng);self.db.commit()
        path=f'/api/ticketing/events/{self.event.id}/sales-window'
        r=self.client.put(path,headers=self.headers(),json={'cutoff_local':'2026-11-14T00:00','exempt_seller_ids':[tng.id]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['cutoff_at'],'2026-11-14T06:00:00+00:00')
        self.db.expire_all()
        before=datetime(2026,11,14,5,59,59,tzinfo=timezone.utc)
        at=datetime(2026,11,14,6,tzinfo=timezone.utc)
        self.assertTrue(sales_access(self.db,self.event.id,self.seller,before)['sales_open'])
        self.assertFalse(sales_access(self.db,self.event.id,self.seller,at)['sales_open'])
        self.assertFalse(sales_access(self.db,self.event.id,None,at)['sales_open'])
        self.assertTrue(sales_access(self.db,self.event.id,tng,at)['sales_open'])
        tng.active=False
        self.assertFalse(sales_access(self.db,self.event.id,tng,at)['sales_open'])
        self.assertEqual(self.client.put(path,headers=self.headers(),json={'cutoff_local':'bad'}).status_code,400)
        self.assertEqual(self.client.put(path,headers=self.headers(),json={'exempt_seller_ids':[999999]}).status_code,400)
        self.assertEqual(self.client.put(path,headers=self.headers('member'),json={}).status_code,403)

    def test_past_cutoff_rejects_order_creation_and_direct_sales(self):
        self.order()
        self.db.add(EventSalesWindow(event_id=self.event.id,cutoff_at=datetime(2020,1,1),exempt_seller_ids_json='[]'));self.db.commit()
        base=f'/api/ticketing/public/events/{self.event.id}'
        payload={'buyer_name':'Buyer','buyer_email':'buyer@example.com','items':[{'ticket_type_id':self.kind.id,'quantity':1}]}
        for code in (None,self.seller.public_code):
            self.assertEqual(self.client.post(base+'/orders',json={**payload,'seller_code':code}).status_code,403)
        self.assertEqual(self.client.get(base+'/tickets').status_code,403)
        self.assertEqual(self.db.query(TicketOrder).count(),1)

    def test_confirmed_payment_still_issues_tickets_after_pause_and_cutoff(self):
        from app.ticketing.service import issue_paid_order
        from app.ticketing.models import IssuedTicket
        order = self.order()
        self.seller.active = False
        self.db.add(EventSalesWindow(event_id=self.event.id,cutoff_at=datetime(2020,1,1),exempt_seller_ids_json='[]'))
        self.db.commit()
        order.payment_status = "paid"
        self.db.commit()
        issue_paid_order(self.db, order, [{'ticket_type_id':self.kind.id,'quantity':2}])
        self.db.commit()
        self.assertEqual(self.db.query(IssuedTicket).filter_by(order_id=order.id,status='valid').count(),2)

    def test_closed_catalog_redirects_only_to_active_exempt_seller(self):
        import json
        self.order()
        tng=EventSeller(event_id=self.event.id,seller_type='staff',seller_ref_id=1,display_name='TNG Promotions',public_code='TNG-TEST')
        self.db.add(tng);self.db.flush()
        self.db.add(EventSalesWindow(event_id=self.event.id,cutoff_at=datetime(2020,1,1),exempt_seller_ids_json=json.dumps([tng.id]),redirect_seller_id=tng.id))
        self.db.commit()
        base=f'/api/ticketing/public/events/{self.event.id}/tickets'
        for params in ({},{'seller':self.seller.public_code}):
            r=self.client.get(base,params=params)
            self.assertEqual(r.status_code,200,r.text)
            self.assertTrue(r.json()['sales_closed'])
            self.assertEqual(r.json()['redirect_seller_code'],tng.public_code)
            self.assertNotIn('email',r.text)
        self.assertEqual(self.client.get(base,params={'seller':tng.public_code}).json()['seller']['id'],tng.id)
        self.assertEqual(self.client.get(base,params={'seller':'BAD'}).status_code,404)
        tng.active=False;self.db.commit()
        self.assertEqual(self.client.get(base).status_code,403)

    def test_repair_does_not_reactivate_paused_seller(self):
        from app.matchmaker.models import BoxingFighter, BoxingBout
        self.order()
        fighter=BoxingFighter(legal_name='Example Fighter')
        self.db.add(fighter);self.db.flush()
        self.seller.seller_ref_id=fighter.id
        self.seller.active=False
        self.db.add(BoxingBout(event_id=self.event.id,red_fighter_id=fighter.id,status='draft'))
        self.db.commit()
        r=self.client.post(f'/api/ticketing/events/{self.event.id}/enable-all-fighter-ticket-sales',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['paused_preserved'],1)
        self.db.refresh(self.seller)
        self.assertFalse(self.seller.active)
