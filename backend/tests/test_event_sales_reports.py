import csv
import io
import unittest
import test_stabilization as support
import test_ticketing as ticket_support
from app.ticketing.models import TicketOrder, IssuedTicket
from app.ticketing.sales_reports import commission_summary
from app.ticketing.service import issue_paid_order

class EventSalesReportTests(unittest.TestCase):
    setUp=support.StabilizationTests.setUp
    tearDown=support.StabilizationTests.tearDown
    headers=support.StabilizationTests.headers
    order=ticket_support.TicketingTests.order

    def paid(self, price=4000, quantity=2):
        o=self.order(price=price,quantity=quantity)
        o.payment_status='paid';o.payment_provider='cash';o.payment_id='REPORT-CASH';self.db.commit()
        issue_paid_order(self.db,o,[{'ticket_type_id':self.kind.id,'quantity':quantity}]);self.db.commit()
        return o

    def test_paid_gross_includes_cash_before_seller_commission_and_excludes_fees(self):
        o=self.paid()
        o.fee_cents=500;o.total_cents=8500;self.db.commit()
        r=self.client.get(f'/api/ticketing/events/{self.event.id}/report',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        summary=r.json()['state_athletic_commission']
        self.assertEqual(summary['paid_ticket_gross_cents'],8000)
        self.assertEqual(summary['state_commission_cents'],400)
        self.assertEqual(summary['paid_ticket_quantity'],2)
        self.assertEqual(summary['paid_orders_missing_tickets'],0)
        self.assertEqual(r.json()['commission_cents'],800)

    def test_unpaid_refunds_and_paper_stock_never_inflate_base(self):
        o=self.order()
        self.assertEqual(commission_summary(self.db,self.event.id)['state_commission_cents'],0)
        o.payment_status='refunded';self.db.commit()
        self.assertEqual(commission_summary(self.db,self.event.id)['paid_ticket_gross_cents'],0)
        o.payment_status='partial_refund';self.db.commit()
        summary=commission_summary(self.db,self.event.id)
        self.assertEqual(summary['partial_refund_orders'],1)
        self.assertEqual(summary['state_commission_cents'],0)
        from app.ticketing.models import PaperTicketBatch,PaperTicket
        b=PaperTicketBatch(event_id=self.event.id,seller_id=self.seller.id,ticket_type_id=self.kind.id,quantity=1,price_cents=4000,commission_cents=800,request_key='report-paper',created_by_user_id=self.users['admin'].id)
        self.db.add(b);self.db.flush()
        self.db.add(PaperTicket(batch_id=b.id,ticket_number='UNSOLD-TEST',qr_token_hash='report-unsold-hash',qr_token_encrypted='not-a-live-token',status='released'));self.db.commit()
        summary=commission_summary(self.db,self.event.id)
        self.assertEqual(summary['unreconciled_paper_tickets'],1)
        self.assertEqual(summary['paid_ticket_gross_cents'],0)

    def test_paid_missing_issuance_still_counts_revenue_and_flags_review(self):
        o=self.order(price=201,quantity=1)
        o.payment_status='paid';self.db.commit()
        summary=commission_summary(self.db,self.event.id)
        self.assertEqual(summary['paid_ticket_gross_cents'],201)
        self.assertEqual(summary['state_commission_cents'],10)
        self.assertEqual(summary['paid_orders_missing_tickets'],1)
        # Half-cent rounding occurs once on the event total.
        o.subtotal_cents=210;self.db.commit()
        self.assertEqual(commission_summary(self.db,self.event.id)['state_commission_cents'],11)

    def test_csv_includes_summary_orders_and_ledger_without_qr_tokens(self):
        o=self.paid();o.buyer_name='=HYPERLINK("https://example.com")';self.db.commit()
        r=self.client.get(f'/api/ticketing/events/{self.event.id}/report.csv',headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        rows=list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
        self.assertIn(['Oklahoma State Athletic Commission amount','$4.00'],rows)
        self.assertIn('Issued ticket ledger',r.text)
        self.assertIn('REPORT-CASH',r.text)
        self.assertIn("'=HYPERLINK",r.text)
        for ticket in self.db.query(IssuedTicket).all():
            self.assertIn(ticket.ticket_number,r.text)
            self.assertNotIn(ticket.qr_token_hash,r.text)
            self.assertNotIn(ticket.qr_token_encrypted,r.text)
        self.assertEqual(r.headers['cache-control'],'private, no-store')

    def test_pdf_exports_and_permissions_and_unknown_event(self):
        self.paid()
        path=f'/api/ticketing/events/{self.event.id}/report'
        for ext in ('.pdf','.csv'):
            self.assertEqual(self.client.get(path+ext,headers=self.headers('member')).status_code,403)
            self.assertEqual(self.client.get('/api/ticketing/events/999999/report'+ext,headers=self.headers()).status_code,404)
        r=self.client.get(path+'.pdf',headers=self.headers('staff'))
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.content.startswith(b'%PDF-'))
        self.assertEqual(r.headers['cache-control'],'private, no-store')
        self.assertGreater(len(r.content),2000)
