"""Offline production-ticket regressions. python -B backend/tests/test_ticketing.py"""
import json
import os
import unittest
from unittest.mock import Mock, patch
import test_stabilization as support
from app.ticketing.models import EventSeller, EventTicketType, TicketOrder, IssuedTicket, TicketDelivery, TicketRecovery
from app.matchmaker.models import BoxingEvent
from app.ticketing.security import order_access_token, decrypt_token
from app.ticketing.service import issue_paid_order, seller_totals


class TicketingTests(unittest.TestCase):
    setUp = support.StabilizationTests.setUp
    tearDown = support.StabilizationTests.tearDown
    headers = support.StabilizationTests.headers
    payment = support.StabilizationTests.payment

    def order(self, quantity=2, price=4000):
        self.event = BoxingEvent(slug="test-night", name="Test Fight Night")
        self.db.add(self.event); self.db.flush()
        self.seller = EventSeller(event_id=self.event.id, seller_type="fighter", seller_ref_id=42,
                                  display_name="Test Fighter", public_code="FIGHTER-42")
        self.kind = EventTicketType(event_id=self.event.id, name="GA", price_cents=price,
                                    commission_type="percent", commission_value=10)
        self.db.add_all([self.seller, self.kind]); self.db.commit()
        r = self.client.post(f"/api/ticketing/public/events/{self.event.id}/orders", json={
            "buyer_name":"Test Customer", "buyer_email":"tickets@example.com", "buyer_phone":"+15555550123",
            "seller_code":self.seller.public_code, "items":[{"ticket_type_id":self.kind.id, "quantity":quantity}]})
        self.assertEqual(r.status_code,200,r.text)
        o = self.db.get(TicketOrder,r.json()["order_id"])
        o.clover_checkout_id="test-checkout"; self.db.commit()
        return o

    def providers(self, sms="test-sms", email=None):
        from contextlib import ExitStack
        stack=ExitStack()
        self.addCleanup(stack.close)
        sm=stack.enter_context(patch("app.services.sms_service.send_sms", return_value=sms))
        em=stack.enter_context(patch("app.ticketing.emailing.send_ticket_email", return_value=email or {"id":"test-email"}))
        return sm,em

    def test_payment_tickets_sms_customer_page_fighter_credit_and_retry(self):
        o=self.order();sm,em=self.providers()
        r=self.payment(o.clover_checkout_id);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)
        self.db.expire_all()
        tickets=self.db.query(IssuedTicket).all()
        self.assertEqual(len(tickets),2)
        self.assertEqual(len({t.qr_token_hash for t in tickets}),2)
        self.assertEqual({t.seller_id for t in tickets},{self.seller.id})
        totals=seller_totals(self.db,self.event.id)[0]
        self.assertEqual((totals["tickets_sold"],totals["gross_sales_cents"],totals["commission_cents"]),(2,8000,800))
        sm.assert_called_once();em.assert_called_once()
        link=sm.call_args.args[1].split("View your QR tickets: ")[1]
        r=self.client.get(link.replace("https://tngos.tngboxinggym.com", ""))
        # The frontend route is served by Goldfish; call its underlying public ticket API.
        r=self.client.get(f"/api/ticketing/public/orders/{o.id}/tickets",params={"access_token":order_access_token(o)})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()["tickets"]),2)
        self.assertTrue(all(t["qr_png_base64"] for t in r.json()["tickets"]))
        self.assertEqual(self.client.get(f"/api/ticketing/public/orders/{o.id}/tickets",params={"access_token":"bad"}).status_code,403)
        raw=decrypt_token(tickets[0].qr_token_encrypted)
        for expected in ("admitted","already_used"):
            r=self.client.post("/api/ticketing/scan",json={"event_id":self.event.id,"token":raw},headers=self.headers())
            self.assertEqual(r.json()["result"],expected)

    def test_failed_notifications_persist_and_retry_without_duplicate_tickets(self):
        o=self.order();sm,em=self.providers();sm.side_effect=RuntimeError("offline SMS failure")
        em.side_effect=RuntimeError("offline email failure")
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)
        self.db.expire_all()
        self.assertEqual(self.db.get(TicketOrder,o.id).payment_status,"paid")
        self.assertEqual({d.status for d in self.db.query(TicketDelivery).all()},{"failed"})
        sm.side_effect=None;em.side_effect=None
        r=self.client.post(f"/api/ticketing/orders/{o.id}/recover",headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        self.db.expire_all()
        self.assertEqual(self.db.query(IssuedTicket).count(),2)
        self.assertEqual({(d.status,d.attempts) for d in self.db.query(TicketDelivery).all()},{("sent",2)})

    def test_paid_order_with_no_tickets_is_healed(self):
        o=self.order();self.providers();o.payment_status="paid";o.payment_id="payment-1";self.db.commit()
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)
        self.assertEqual(self.db.query(IssuedTicket).count(),2)

    def test_qr_failure_rolls_back_payment_and_retries(self):
        o=self.order();self.providers()
        with patch("app.ticketing.service.make_raw_token",side_effect=RuntimeError("Missing QR secret")):
            self.assertEqual(self.payment(o.clover_checkout_id).status_code,503)
        self.db.expire_all()
        self.assertEqual(self.db.get(TicketOrder,o.id).payment_status,"pending")
        self.assertEqual(self.db.query(IssuedTicket).count(),0)
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)

    def test_pending_order_cannot_be_recovered_without_payment_proof(self):
        o=self.order()
        self.assertEqual(self.client.post(f"/api/ticketing/orders/{o.id}/recover",headers=self.headers()).status_code,409)
        self.assertEqual(self.db.query(IssuedTicket).count(),0)

    def test_declined_unsigned_and_unknown_payments_do_not_issue(self):
        o=self.order()
        self.assertEqual(self.payment(o.clover_checkout_id,Status="DECLINED").status_code,200)
        self.client.post("/api/clover/webhook",json={"Data":o.clover_checkout_id,"Status":"APPROVED"})
        self.assertEqual(self.payment("unmatched-checkout").status_code,404)
        self.assertEqual(self.db.query(IssuedTicket).count(),0)

    def test_purchase_snapshots_prices_and_commissions(self):
        o=self.order();self.providers();self.kind.price_cents=9000;self.kind.commission_value=50;self.db.commit()
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)
        self.assertEqual({(t.price_cents,t.commission_cents) for t in self.db.query(IssuedTicket).all()},{(4000,400)})

    def test_invalid_fighter_link_rejected_and_no_order_created(self):
        self.order();before=self.db.query(TicketOrder).count()
        r=self.client.post(f"/api/ticketing/public/events/{self.event.id}/orders",json={
            "buyer_name":"A", "buyer_email":"a@example.com", "seller_code":"invalid",
            "items":[{"ticket_type_id":self.kind.id,"quantity":1}]})
        self.assertEqual(r.status_code,400,r.text)
        self.assertEqual(self.db.query(TicketOrder).count(),before)

    def test_mobile_phone_normalization_and_invalid_numbers(self):
        from app.ticketing.delivery import normalize_ticket_phone
        self.assertEqual(normalize_ticket_phone('(405) 555-0123'),'+14055550123')
        self.assertEqual(normalize_ticket_phone('+44 7700 900123'),'+447700900123')
        with self.assertRaises(ValueError):
            normalize_ticket_phone('not a phone')

    def evidence(self,o):
        return {"id":"CLOVER-ORDER", "paymentState":"PAID","total":o.total_cents,"currency":"USD",
                "payments":{"elements":[{"id":"verified-payment","result":"SUCCESS","amount":o.total_cents}]}}

    def reconcile(self,o,evidence):
        response=Mock(status_code=200);response.json.return_value=evidence
        def provider_get(url, **kwargs):
            if "/orders/" in url:
                return response
            detail=Mock(status_code=200)
            detail.json.return_value={"id":"verified-payment", "result":"SUCCESS", "amount":o.total_cents,
                                      "order":{"id":"CLOVER-ORDER"}, "refunds":{"elements":[]}}
            return detail
        with patch.dict(os.environ,{"CLOVER_API_TOKEN":"test-only"}),patch("app.ticketing.recovery.requests.get",side_effect=provider_get) as get:
            r=self.client.post(f"/api/ticketing/orders/{o.id}/reconcile-clover",json={
                "clover_order_id":"CLOVER-ORDER","confirm_checkout_id":o.clover_checkout_id},headers=self.headers())
        self.assertEqual(get.call_args_list[0].kwargs["params"],{"expand":"payments"})
        return r

    def test_verified_clover_reconciliation_and_retry_preserve_fighter(self):
        o=self.order();self.providers()
        for _ in range(2):
            r=self.reconcile(o,self.evidence(o));self.assertEqual(r.status_code,200,r.text)
        self.db.expire_all()
        self.assertEqual(self.db.query(IssuedTicket).count(),2)
        self.assertEqual(self.db.query(TicketRecovery).count(),1)
        self.assertEqual(self.db.get(TicketOrder,o.id).seller_id,self.seller.id)

    def test_unpaid_wrong_amount_refunded_evidence_cannot_reconcile(self):
        o=self.order()
        for change in ("pending","amount","refund"):
            e=self.evidence(o)
            if change=="pending":e["paymentState"]="OPEN"
            if change=="amount":e["payments"]["elements"][0]["amount"]-=1
            if change=="refund":e["payments"]["elements"][0]["refunded"]=True
            self.assertEqual(self.reconcile(o,e).status_code,409)
        self.db.expire_all();self.assertEqual(self.db.get(TicketOrder,o.id).payment_status,"pending")
        self.assertEqual(self.db.query(IssuedTicket).count(),0)

    def test_recovery_requires_staff_and_reconciliation_requires_admin(self):
        o=self.order()
        for role in ("fighter","member","rep"):
            self.assertEqual(self.client.post(f"/api/ticketing/orders/{o.id}/recover",headers=self.headers(role)).status_code,403)
        self.assertEqual(self.client.post(f"/api/ticketing/orders/{o.id}/reconcile-clover",json={
            "clover_order_id":"CLOVER-ORDER","confirm_checkout_id":o.clover_checkout_id},headers=self.headers("staff")).status_code,403)

    def test_comp_issues_once_and_delivers(self):
        o=self.order(price=0);sm,em=self.providers()
        o.clover_checkout_id=None;self.db.commit()
        for _ in range(2):
            r=self.client.post(f"/api/ticketing/public/orders/{o.id}/checkout")
            self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.db.query(IssuedTicket).count(),2)
        sm.assert_called_once()

    def test_checkout_retries_reuse_session_and_preserve_fighter(self):
        o=self.order();o.clover_checkout_id=None;self.db.commit()
        response=Mock(status_code=200)
        response.json.return_value={"checkoutSessionId":"saved-checkout","href":"https://checkout.test/pay"}
        with patch.dict(os.environ,{"CLOVER_API_TOKEN":"test-only"}), \
             patch("app.ticketing.checkout_routes.requests.post",return_value=response) as post:
            for _ in range(2):
                r=self.client.post(f"/api/ticketing/public/orders/{o.id}/checkout")
                self.assertEqual(r.status_code,200,r.text)
                self.assertEqual(r.json()["checkout_url"],"https://checkout.test/pay")
            post.assert_called_once()
            self.assertIn("access_token=",post.call_args.kwargs["json"]["redirectUrls"]["success"])
        self.db.refresh(o);self.assertEqual(o.seller_id,self.seller.id)

    def test_concurrent_issuance_and_scans_are_serialized(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.database import SessionLocal
        from app.ticketing.service import scan_ticket
        o=self.order();o.payment_status="paid";self.db.commit()
        order_id=o.id;event_id=o.event_id
        def issue():
            with SessionLocal() as db:
                order=db.get(TicketOrder,order_id)
                tickets=issue_paid_order(db,order,json.loads(order.items_json))
                numbers=[t["ticket"].ticket_number for t in tickets]
                db.commit();return numbers
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:issue(),range(2)))
        self.assertEqual(results[0],results[1])
        self.db.expire_all();self.assertEqual(self.db.query(IssuedTicket).count(),2)
        raw=decrypt_token(self.db.query(IssuedTicket).first().qr_token_encrypted)
        def scan():
            with SessionLocal() as db:
                return scan_ticket(db,event_id,raw,None)["result"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:scan(),range(2)))
        self.assertCountEqual(results,["admitted","already_used"])

    def test_background_worker_retries_due_failures_and_preserves_sent_channels(self):
        from datetime import datetime, timedelta
        from app.ticketing.worker import retry_deliveries
        o=self.order();sm,em=self.providers();sm.side_effect=RuntimeError("offline")
        self.assertEqual(self.payment(o.clover_checkout_id).status_code,200)
        self.db.expire_all()
        row=self.db.query(TicketDelivery).filter_by(channel="sms").one()
        row.next_attempt_at=datetime.utcnow()-timedelta(seconds=1);self.db.commit()
        sm.side_effect=None
        retry_deliveries()
        self.db.expire_all();self.assertEqual(self.db.query(TicketDelivery).filter_by(channel="sms").one().status,"sent")
        self.assertEqual(sm.call_count,2);em.assert_called_once()

    def test_concurrent_notification_retries_send_each_channel_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.database import SessionLocal
        from app.ticketing.delivery import queue_deliveries, deliver_order
        o=self.order();o.payment_status="paid"
        issue_paid_order(self.db,o,json.loads(o.items_json));queue_deliveries(self.db,o);self.db.commit()
        order_id=o.id;sm,em=self.providers()
        def deliver():
            with SessionLocal() as db:
                return deliver_order(db,db.get(TicketOrder,order_id))
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _:deliver(),range(2)))
        sm.assert_called_once();em.assert_called_once()


if __name__ == "__main__":
    result=unittest.main(verbosity=2,exit=False).result
    support.engine.dispose()
    os.chdir(support.ORIGINAL_CWD)
    support.TEMP.cleanup()
    raise SystemExit(not result.wasSuccessful())
