"""Bout booking creates seller links transactionally, without ticket issuance/outreach."""
import unittest
from unittest.mock import patch
import test_stabilization as support
from app.matchmaker.models import BoxingFighter,BoxingEvent,BoxingBout
from app.ticketing.models import EventSeller,EventTicketType,IssuedTicket,TicketOrder
from app.fighter_portal.models import FighterAccount
from app.ticketing.automation import register_bout_ticket_automation

class BoutTicketAutomationTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers

    def card(self):
        self.red=BoxingFighter(legal_name='Red Example',email='red@example.com')
        self.blue=BoxingFighter(legal_name='Blue Example',email='blue@example.com')
        self.event=BoxingEvent(name='Example Event',slug='auto-ticket-test')
        self.db.add_all([self.red,self.blue,self.event]);self.db.commit()

    def make(self,status='draft'):
        b=BoxingBout(event_id=self.event.id,red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,status=status)
        self.db.add(b);self.db.flush();return b

    def test_api_bout_creates_both_links_visible_to_fighter_without_emails_or_tickets(self):
        self.card();self.db.add(FighterAccount(user_id=self.users['fighter'].id,fighter_id=self.red.id));self.db.commit()
        with patch('app.services.sms_service.send_sms') as sms:
            r=self.client.post('/api/boxing/bouts',headers=self.headers(),json={'event_id':self.event.id,'red_fighter_id':self.red.id,'blue_fighter_id':self.blue.id,'rounds':4})
            self.assertEqual(r.status_code,200,r.text);sms.assert_not_called()
        sellers=self.db.query(EventSeller).filter_by(event_id=self.event.id).all()
        self.assertEqual(len(sellers),2);self.assertTrue(all(s.active for s in sellers))
        self.assertEqual({s.seller_ref_id for s in sellers},{self.red.id,self.blue.id})
        self.assertEqual(self.db.query(IssuedTicket).count(),0)
        self.assertEqual(self.db.query(TicketOrder).count(),0)
        r=self.client.get('/api/fighter/me/ticket-sales',headers=self.headers('fighter'))
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()['events']),1)
        self.assertIn('?seller=',r.json()['events'][0]['ticket_url'])

    def test_import_and_assignment_change_create_missing_links_once(self):
        self.card();bout=self.make();self.db.commit()
        original={s.id:s.public_code for s in self.db.query(EventSeller).all()}
        bout.red_purse=1000;self.db.commit()
        self.assertEqual({s.id:s.public_code for s in self.db.query(EventSeller).all()},original)
        other=BoxingFighter(legal_name='Replacement Example');self.db.add(other);self.db.commit()
        bout.blue_fighter_id=other.id;self.db.commit()
        self.assertEqual(self.db.query(EventSeller).count(),3)
        self.assertTrue(all(self.db.get(EventSeller,k).public_code==v for k,v in original.items()))

    def test_bout_rollback_rolls_back_automatic_seller_rows(self):
        self.card();self.make();self.assertEqual(self.db.query(EventSeller).count(),2)
        self.db.rollback();self.assertEqual(self.db.query(EventSeller).count(),0)
        self.assertEqual(self.db.query(BoxingBout).count(),0)

    def test_existing_code_history_and_explicit_disabled_state_are_preserved(self):
        self.card();seller=EventSeller(event_id=self.event.id,seller_type='fighter',seller_ref_id=self.red.id,
            display_name='Saved Display',public_code='KEEP-ME',active=False)
        self.db.add(seller);self.db.commit();bout=self.make();self.db.commit();self.db.refresh(seller)
        self.assertEqual(seller.public_code,'KEEP-ME');self.assertFalse(seller.active)
        self.assertEqual(seller.display_name,'Saved Display');self.assertEqual(self.db.query(EventSeller).count(),2)
        bout.status='scheduled';self.db.commit();self.assertEqual(self.db.query(EventSeller).count(),2)
        self.db.refresh(seller);self.assertFalse(seller.active)

    def test_cancelled_and_unassigned_bouts_do_not_create_selling_links(self):
        self.card();self.make('cancelled');self.db.commit()
        self.assertEqual(self.db.query(EventSeller).count(),0)
        b=BoxingBout(red_fighter_id=self.red.id,blue_fighter_id=self.blue.id,status='draft')
        self.db.add(b);self.db.commit();self.assertEqual(self.db.query(EventSeller).count(),0)
        b.event_id=self.event.id;self.db.commit();self.assertEqual(self.db.query(EventSeller).count(),2)

    def test_registration_is_idempotent_and_link_preserves_checkout_referral(self):
        register_bout_ticket_automation();register_bout_ticket_automation()
        self.card();self.make();self.db.commit()
        self.assertEqual(self.db.query(EventSeller).count(),2)
        seller=self.db.query(EventSeller).filter_by(seller_ref_id=self.red.id).one()
        kind=EventTicketType(event_id=self.event.id,name='GA',price_cents=4000,commission_type='percent',commission_value=20)
        self.db.add(kind);self.db.commit()
        r=self.client.post(f'/api/ticketing/public/events/{self.event.id}/orders',json={'buyer_name':'Example Buyer','buyer_email':'buyer@example.com','seller_code':seller.public_code,'items':[{'ticket_type_id':kind.id,'quantity':1}]})
        self.assertEqual(r.status_code,200,r.text)
        order=self.db.get(TicketOrder,r.json()['order_id'])
        self.assertEqual(order.seller_id,seller.id);self.assertEqual(order.payment_status,'pending')

if __name__=='__main__':unittest.main(verbosity=2)
