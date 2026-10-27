"""Paper allocations and staff-attested cash sales. No provider calls."""
import os
import unittest
from uuid import uuid4
from unittest.mock import patch
import test_stabilization as support
import test_ticketing as ticket_support
from app.ticketing.models import PaperTicketBatch, PaperTicket, TicketOrder, IssuedTicket, TicketDelivery
from app.ticketing.security import decrypt_token
from app.ticketing.service import seller_totals
from app.matchmaker.models import BoxingEvent

class PaperTicketTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    order=ticket_support.TicketingTests.order

    def batch(self, quantity=3, key=None):
        if not hasattr(self,'kind'):self.order()
        return self.client.post(f'/api/ticketing/events/{self.event.id}/paper-batches',headers=self.headers(),json={
            'seller_id':self.seller.id,'ticket_type_id':self.kind.id,'quantity':quantity,'request_key':key or str(uuid4())})

    def details(self,batch):
        return self.client.get(f'/api/ticketing/paper-batches/{batch}/',headers=self.headers()).json()

    def scan(self,paper,event=None):
        return self.client.post('/api/ticketing/scan',headers=self.headers(),json={'event_id':event or self.event.id,'token':decrypt_token(paper.qr_token_encrypted)}).json()

    def sell(self,batch,ids,total=None):
        return self.client.post(f'/api/ticketing/paper-batches/{batch}/record-sales',headers=self.headers(),json={'ticket_ids':ids,'confirm_total_cents':len(ids)*4000 if total is None else total})

    def test_allocation_and_printing_do_not_create_paid_sales_or_active_tickets(self):
        key=str(uuid4());r=self.batch(7,key);self.assertEqual(r.status_code,200,r.text);b=r.json()['id']
        self.assertEqual(self.batch(7,key).json()['id'],b)
        self.assertEqual(self.db.query(PaperTicket).count(),7)
        self.assertEqual(self.db.query(IssuedTicket).count(),0)
        self.assertEqual(seller_totals(self.db,self.event.id)[0]['tickets_sold'],0)
        originals=[t.qr_token_hash for t in self.db.query(PaperTicket).order_by(PaperTicket.id)]
        for _ in range(2):
            pdf=self.client.get(f'/api/ticketing/paper-batches/{b}/print.pdf',headers=self.headers())
            self.assertEqual(pdf.status_code,200,pdf.text[:80] if pdf.status_code!=200 else '')
            self.assertTrue(pdf.content.startswith(b'%PDF'))
            self.assertEqual(pdf.headers['cache-control'],'private, no-store')
        if os.getenv('TNG_PAPER_PREVIEW_PATH'):
            with open(os.environ['TNG_PAPER_PREVIEW_PATH'],'wb') as out:out.write(pdf.content)
        self.assertEqual(originals,[t.qr_token_hash for t in self.db.query(PaperTicket).order_by(PaperTicket.id)])
        paper=self.db.query(PaperTicket).first()
        self.assertEqual(self.scan(paper)['result'],'not_activated')
        self.assertEqual(self.db.query(TicketDelivery).count(),0)

    def test_design_preview_does_not_allocate_or_create_sales(self):
        self.order()
        self.event.event_date='2026-11-14';self.event.venue='Example Arena'
        self.event.venue_address='123 Example Street, Oklahoma City'
        self.db.commit()
        before=[self.db.query(t).count() for t in [PaperTicketBatch,PaperTicket,TicketOrder,IssuedTicket,TicketDelivery]]
        for layout in ['fight-night']:
            r=self.client.get(f'/api/ticketing/events/{self.event.id}/paper-ticket-preview.pdf',headers=self.headers(),params={'ticket_type_id':self.kind.id,'seller_id':self.seller.id,'layout':layout})
            self.assertEqual(r.status_code,200,r.text[:80] if r.status_code!=200 else '')
            self.assertTrue(r.content.startswith(b'%PDF'))
            self.assertEqual(r.headers['cache-control'],'private, no-store')
        self.assertEqual(before,[self.db.query(t).count() for t in [PaperTicketBatch,PaperTicket,TicketOrder,IssuedTicket,TicketDelivery]])

    def test_design_preview_permissions_and_event_scoping(self):
        self.order()
        path=f'/api/ticketing/events/{self.event.id}/paper-ticket-preview.pdf?ticket_type_id={self.kind.id}'
        self.assertEqual(self.client.get(path).status_code,401)
        self.assertEqual(self.client.get(path,headers=self.headers('fighter')).status_code,403)
        other=BoxingEvent(name='Other event',slug='other-design');self.db.add(other);self.db.commit()
        self.assertEqual(self.client.get(f'/api/ticketing/events/{other.id}/paper-ticket-preview.pdf?ticket_type_id={self.kind.id}',headers=self.headers()).status_code,404)
        self.assertEqual(self.client.get(path+'&seller_id=999999',headers=self.headers()).status_code,404)
        self.assertEqual(self.client.get(path+'&layout=unknown',headers=self.headers()).status_code,422)
        self.assertEqual(self.client.get(path+'&layout=compact',headers=self.headers()).status_code,422)

    def test_four_up_reprints_preserve_ticket_tokens(self):
        batch=self.batch(7).json()['id']
        before=[(t.id,t.qr_token_hash,t.status) for t in self.db.query(PaperTicket).order_by(PaperTicket.id)]
        for layout,pages in [('fight-night',2),('fight-night',2)]:
            r=self.client.get(f'/api/ticketing/paper-batches/{batch}/print.pdf?layout={layout}',headers=self.headers())
            self.assertEqual(r.status_code,200)
            self.assertIn(f'/Count {pages}'.encode(),r.content)
        self.assertEqual(before,[(t.id,t.qr_token_hash,t.status) for t in self.db.query(PaperTicket).order_by(PaperTicket.id)])

    def test_default_layout_fits_exactly_four_tickets_per_page(self):
        for quantity,pages in [(4,1),(5,2)]:
            batch=self.batch(quantity).json()['id']
            r=self.client.get(f'/api/ticketing/paper-batches/{batch}/print.pdf',headers=self.headers())
            self.assertEqual(r.status_code,200)
            self.assertIn(f'/Count {pages}'.encode(),r.content)

    def test_activation_qr_lookup_is_read_only_and_event_scoped(self):
        batch=self.batch(1).json()['id'];paper=self.db.query(PaperTicket).filter_by(batch_id=batch).one()
        payload={'event_id':self.event.id,'token':decrypt_token(paper.qr_token_encrypted)}
        path='/api/ticketing/paper-tickets/resolve'
        before=self.db.query(TicketOrder).count()
        self.assertEqual(self.client.post(path,json=payload).status_code,401)
        self.assertEqual(self.client.post(path,json=payload,headers=self.headers('fighter')).status_code,403)
        self.assertEqual(self.client.post(path,json={**payload,'event_id':9999},headers=self.headers()).status_code,409)
        r=self.client.post(path,json=payload,headers=self.headers());self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['price_cents'],4000)
        self.assertEqual(self.db.query(TicketOrder).count(),before)
        self.assertEqual(self.scan(paper)['result'],'not_activated')
        self.assertEqual(self.sell(batch,[paper.id]).status_code,200)
        self.assertEqual(self.client.post(path,json=payload,headers=self.headers()).status_code,409)
        self.db.expire_all();self.assertEqual(self.db.query(IssuedTicket).one().status,'valid')
        self.assertEqual(self.scan(paper)['result'],'admitted')

    def test_activation_qr_lookup_rejects_returned_and_invalid_codes(self):
        batch=self.batch(1).json()['id'];paper=self.db.query(PaperTicket).filter_by(batch_id=batch).one()
        payload={'event_id':self.event.id,'token':decrypt_token(paper.qr_token_encrypted)}
        self.assertEqual(self.client.post('/api/ticketing/paper-tickets/resolve',json={**payload,'token':'bad'},headers=self.headers()).status_code,400)
        self.client.post(f'/api/ticketing/paper-batches/{batch}/return-unsold',json={'ticket_ids':[paper.id]},headers=self.headers())
        self.assertEqual(self.client.post('/api/ticketing/paper-tickets/resolve',json=payload,headers=self.headers()).status_code,409)

    def test_record_sale_activates_same_qr_and_preserves_fighter_commission_once(self):
        b=self.batch().json()['id'];paper=self.db.query(PaperTicket).first();raw=decrypt_token(paper.qr_token_encrypted)
        with patch('app.services.sms_service.send_sms') as sms,patch('app.ticketing.emailing.send_ticket_email') as email:
            for expected in (1,0):
                r=self.sell(b,[paper.id]);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['new_sales_recorded'],expected)
            sms.assert_not_called();email.assert_not_called()
        self.db.expire_all();ticket=self.db.query(IssuedTicket).one()
        self.assertEqual(decrypt_token(ticket.qr_token_encrypted),raw)
        self.assertEqual((ticket.seller_id,ticket.commission_cents),(self.seller.id,400))
        self.assertEqual(self.db.query(TicketOrder).filter_by(payment_provider='paper_cash').count(),1)
        totals=seller_totals(self.db,self.event.id)[0]
        self.assertEqual((totals['tickets_sold'],totals['gross_sales_cents'],totals['commission_cents']),(1,4000,400))
        self.assertEqual(self.scan(paper)['result'],'admitted')
        self.assertEqual(self.scan(paper)['result'],'already_used')
        report=self.client.get(f'/api/ticketing/events/{self.event.id}/recovery-dashboard',headers=self.headers()).json()
        row=next(o for o in report['orders'] if o['payment_provider']=='paper_cash')
        self.assertEqual(row['issues'],[]);self.assertFalse(row['can_recover'])

    def test_commission_uses_terms_when_sold_not_when_printed(self):
        b=self.batch().json()['id'];p=self.db.query(PaperTicket).first()
        self.kind.commission_value=20;self.db.commit()
        r=self.sell(b,[p.id]);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['commission_cents'],800)
        self.assertEqual(self.db.query(IssuedTicket).one().commission_cents,800)

    def test_returned_tickets_cannot_be_sold_or_admitted(self):
        b=self.batch().json()['id'];tickets=self.db.query(PaperTicket).all()
        r=self.client.post(f'/api/ticketing/paper-batches/{b}/return-unsold',headers=self.headers(),json={'ticket_ids':[tickets[0].id]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.sell(b,[tickets[0].id,tickets[1].id]).status_code,409)
        self.assertEqual(self.db.query(IssuedTicket).count(),0)
        self.assertEqual(self.scan(tickets[0])['result'],'void')
        self.assertEqual(self.sell(b,[tickets[1].id]).status_code,200)
        self.assertEqual(self.client.post(f'/api/ticketing/paper-batches/{b}/return-unsold',headers=self.headers(),json={'ticket_ids':[tickets[1].id]}).status_code,409)

    def test_inventory_and_replay_validation(self):
        self.order();self.kind.inventory=2;self.db.commit()
        key=str(uuid4());self.assertEqual(self.batch(2,key).status_code,200)
        self.assertEqual(self.batch(2,key).status_code,200)
        self.assertEqual(self.batch(1,key).status_code,409)
        self.assertEqual(self.batch(1).status_code,409)
        b=self.db.query(PaperTicketBatch).first();p=self.db.query(PaperTicket).first()
        self.client.post(f'/api/ticketing/paper-batches/{b.id}/return-unsold',headers=self.headers(),json={'ticket_ids':[p.id]})
        self.assertEqual(self.batch(1).status_code,200)

    def test_exact_selection_amount_and_event_boundaries(self):
        b=self.batch().json()['id'];other=self.batch(1).json()['id']
        p=self.db.query(PaperTicket).filter_by(batch_id=b).first();outsider=self.db.query(PaperTicket).filter_by(batch_id=other).first()
        self.assertEqual(self.sell(b,[outsider.id]).status_code,400)
        self.assertEqual(self.sell(b,[p.id,p.id]).status_code,400)
        self.assertEqual(self.sell(b,[p.id],3999).status_code,409)
        e=BoxingEvent(slug='other-event',name='Other');self.db.add(e);self.db.commit()
        self.assertEqual(self.scan(p,e.id)['result'],'wrong_event')
        self.assertEqual(self.client.post(f'/api/ticketing/events/{e.id}/paper-batches',headers=self.headers(),json={'seller_id':self.seller.id,'ticket_type_id':self.kind.id,'quantity':1,'request_key':str(uuid4())}).status_code,400)
        self.assertEqual(self.db.query(IssuedTicket).count(),0)

    def test_permissions_and_quantity_limits(self):
        b=self.batch().json()['id'];p=self.db.query(PaperTicket).first()
        for role in ('member','fighter','rep'):
            for path in [f'/api/ticketing/events/{self.event.id}/paper-batches',f'/api/ticketing/paper-batches/{b}',f'/api/ticketing/paper-batches/{b}/print.pdf']:
                self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)
            self.assertEqual(self.client.post(f'/api/ticketing/paper-batches/{b}/record-sales',headers=self.headers(role),json={'ticket_ids':[p.id],'confirm_total_cents':4000}).status_code,403)
        self.assertEqual(self.batch(201).status_code,422)
        self.assertEqual(self.batch(0).status_code,422)

if __name__=='__main__':unittest.main(verbosity=2)
