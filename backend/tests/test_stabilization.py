"""Run with python -B backend/tests/test_stabilization.py; uses only a temporary DB."""
import ast
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="tng-regression-")
ORIGINAL_CWD = os.getcwd()
os.chdir(TEMP.name)
os.environ.update({
    "DATABASE_URL": "sqlite:///" + Path(TEMP.name, "test.db").as_posix(),
    "SECRET_KEY": "test-only-signing-secret-not-used-in-production",
    "OPENAI_API_KEY": "",
    "RESEND_API_KEY": "", "BOOTSTRAP_ADMIN_PASSWORD": "",
    "CLOVER_WEBHOOK_SECRET": "test-only-clover-secret",
    "CLOVER_MERCHANT_ID": "test-merchant",
    "TICKET_QR_SECRET": "test-only-ticket-secret-longer-than-32-characters",
})
with patch("dotenv.load_dotenv", return_value=False):
    from app.main import app
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import User, Member, MembershipProduct, Sale, SalesRep, Lead, Attendance
from app.member_portal.models import MemberAccount, MemberInvite, MembershipRenewal
from app.auth import create_token
from app.services.memberships import apply_membership, recalculate_member_from_payments


class StabilizationTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.db = SessionLocal()
        self.users = {}
        for role in ["admin", "staff", "rep", "member", "fighter"]:
            user = User(name=role, email=f"{role}@example.com", role=role,
                        password_hash="not-a-login-password", active=True)
            self.db.add(user)
            self.users[role] = user
        self.db.flush()
        self.rep = SalesRep(user_id=self.users["staff"].id, referral_slug="front-desk")
        self.product = MembershipProduct(name="Monthly", price=150, category="membership",
                                         is_membership=True, default_membership_months=1)
        self.member = Member(first_name="Test", last_name="Member", email="member@example.com",
                             member_number="TNG-000001", barcode="TNG000001", member_type="MEMBER",
                             membership_status="active", status="active",
                             membership_type="Monthly",
                             membership_start=datetime.utcnow()-timedelta(days=10),
                             membership_end=datetime.utcnow()+timedelta(days=40),
                             assigned_coach="Coach", emergency_contact="Contact",
                             emergency_phone="5550101", notes="Keep this note")
        self.db.add_all([self.rep, self.product, self.member])
        self.db.flush()
        self.db.add(MemberAccount(user_id=self.users["member"].id, member_id=self.member.id))
        self.db.add(Sale(member_id=self.member.id, product_id=self.product.id,
                         sales_rep_id=self.rep.id, amount=150, payment_status="paid",
                         sale_date=datetime.utcnow()-timedelta(days=10)))
        self.db.commit()
        self.client = TestClient(app)
        self.email_patch = patch("resend.Emails.send", side_effect=AssertionError("Unexpected email"))
        self.email_patch.start()

    def tearDown(self):
        self.email_patch.stop()
        self.client.close()
        self.db.close()

    def headers(self, role="admin"):
        return {"Authorization": "Bearer " + create_token({"sub": str(self.users[role].id)})}

    def payment(self, checkout_id, **overrides):
        data = {"Type": "PAYMENT", "Status": "APPROVED", "Id": "payment-1",
                "Data": checkout_id, "MerchantId": "test-merchant"}
        data.update(overrides)
        body = json.dumps(data).encode()
        timestamp = str(int(time.time()))
        digest = hmac.new(os.environ["CLOVER_WEBHOOK_SECRET"].encode(),
                          timestamp.encode()+b"."+body, hashlib.sha256).hexdigest()
        return self.client.post("/api/clover/webhook", content=body,
                                headers={"Clover-Signature": f"t={timestamp},v1={digest}"})

    def test_all_active_python_parses(self):
        for path in ROOT.joinpath("app").rglob("*.py"):
            if ".before_" not in path.name:
                with self.subTest(path=path.name):
                    ast.parse(path.read_text(encoding="utf-8-sig"))

    def test_routes_are_not_duplicated(self):
        seen = set()
        for route in app.routes:
            for method in getattr(route, "methods", []):
                key = (method, route.path)
                self.assertNotIn(key, seen, key)
                seen.add(key)

    def test_member_reads_preserve_manual_renewal_and_fields(self):
        before = self.member.membership_end
        for path in ["/api/members", f"/api/members/{self.member.id}", "/api/dashboard"]:
            response = self.client.get(path, headers=self.headers())
            self.assertEqual(response.status_code, 200, response.text)
        self.db.refresh(self.member)
        self.assertEqual(before, self.member.membership_end)
        profile = self.client.get(f"/api/members/{self.member.id}", headers=self.headers()).json()
        for key in ["assigned_coach", "emergency_contact", "emergency_phone", "notes"]:
            self.assertEqual(profile[key], getattr(self.member, key))

    def test_member_edit_returns_saved_profile_fields(self):
        values = {"assigned_coach": "New coach", "notes": "Updated", "emergency_phone": "5550202"}
        response = self.client.put(f"/api/members/{self.member.id}", json=values, headers=self.headers("staff"))
        self.assertEqual(response.status_code, 200, response.text)
        for key, value in values.items():
            self.assertEqual(response.json()[key], value)

    def test_member_and_rep_cannot_access_staff_endpoints(self):
        for role in ["member", "fighter", "rep"]:
            for path in ["/api/members", f"/api/members/{self.member.id}",
                         f"/api/members/{self.member.id}/payments", "/api/dashboard",
                         "/api/events/1/revenue/organizations", "/api/ticketing/events/1/report"]:
                with self.subTest(role=role, path=path):
                    self.assertEqual(self.client.get(path, headers=self.headers(role)).status_code, 403)
            self.assertEqual(self.client.put(f"/api/members/{self.member.id}", json={"notes":"bad"},
                                            headers=self.headers(role)).status_code, 403)

    def test_public_side_effects_require_authentication(self):
        self.assertEqual(self.client.post("/api/checkin", json={"code":"TNG000001"}).status_code, 401)
        self.assertEqual(self.client.post("/api/email/test").status_code, 401)
        self.assertEqual(self.client.get("/test-sms").status_code, 401)
        self.assertEqual(self.client.post("/api/events/1/revenue/organizations", json={}).status_code, 401)

    def test_disabled_portal_account_loses_access(self):
        headers = self.headers("member")
        self.users["member"].active = False
        self.db.commit()
        self.assertEqual(self.client.get("/api/member/me", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/fighter/me", headers=headers).status_code, 403)

    def test_expired_membership_is_inactive_and_cannot_check_in(self):
        self.member.membership_end = datetime.utcnow()-timedelta(days=1)
        self.db.commit()
        profile = self.client.get(f"/api/members/{self.member.id}", headers=self.headers()).json()
        self.assertEqual(profile["membership_status"], "inactive")
        response = self.client.post("/api/checkin", json={"code":"TNG000001"}, headers=self.headers("staff"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.query(Attendance).count(), 0)

    def test_year_and_configured_plan_durations(self):
        for name, months in [("Full Year",12), ("3 Months Special",3), ("Six months",6)]:
            product = MembershipProduct(name=name, price=900, category="membership", is_membership=True,
                                         default_membership_months=months if months == 6 else 1)
            member = Member(first_name="A",last_name="B")
            apply_membership(member, product, datetime(2026,1,1))
            expected = datetime(2027,1,1) if months == 12 else datetime(2026,months+1,1)
            self.assertEqual(member.membership_end, expected)

    def test_early_renewal_keeps_remaining_time(self):
        old_end = self.member.membership_end
        apply_membership(self.member, self.product, datetime.utcnow())
        self.assertEqual(self.member.membership_end, old_end+timedelta(days=30))

    def test_rebuild_ignores_unpaid_and_refunded_sales(self):
        original_end = datetime.utcnow()-timedelta(days=10)+timedelta(days=30)
        for status, refunded in [("pending",False),("paid",True)]:
            self.db.add(Sale(member_id=self.member.id,product_id=self.product.id,sales_rep_id=self.rep.id,
                             amount=150,payment_status=status,refunded=refunded,sale_date=datetime.utcnow()))
        self.db.commit()
        recalculate_member_from_payments(self.member,self.db)
        self.assertLess(abs((self.member.membership_end-original_end).total_seconds()),2)

    def test_unsigned_and_wrong_merchant_payments_are_rejected(self):
        response=self.client.post("/api/clover/webhook",json={"Type":"PAYMENT","Status":"APPROVED"})
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.payment("unknown",MerchantId="wrong").status_code,401)

    def test_stale_or_tampered_payment_signature_is_rejected(self):
        body=b'{"Type":"PAYMENT"}'
        timestamp=str(int(time.time())-600)
        digest=hmac.new(os.environ["CLOVER_WEBHOOK_SECRET"].encode(),
                         timestamp.encode()+b"."+body,hashlib.sha256).hexdigest()
        response=self.client.post("/api/clover/webhook",content=body,
                                  headers={"Clover-Signature":f"t={timestamp},v1={digest}"})
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.client.post("/api/clover/webhook",content=body,
                                         headers={"Clover-Signature":f"t={int(time.time())},v1=bad"}).status_code,401)

    def test_renewal_checkout_is_saved_for_payment_processing(self):
        response=Mock(status_code=200)
        response.json.return_value={"checkoutSessionId":"saved-renewal","href":"https://checkout.example.test/pay"}
        with patch.dict(os.environ,{"CLOVER_ECOMMERCE_PRIVATE_KEY":"test-only"}), \
             patch("app.member_portal.routes.httpx.post",return_value=response):
            result=self.client.post("/api/member/me/renew-checkout",headers=self.headers("member"))
        self.assertEqual(result.status_code,200,result.text)
        renewal=self.db.query(MembershipRenewal).filter_by(checkout_id="saved-renewal").one()
        self.assertEqual(renewal.member_id,self.member.id)
        self.assertEqual(renewal.amount,150)

    def test_members_cannot_read_leads_or_sales(self):
        for role in ["member","fighter"]:
            for path in ["/api/leads","/api/sales"]:
                self.assertEqual(self.client.get(path,headers=self.headers(role)).status_code,403)

    def test_health_reports_release(self):
        self.assertEqual(self.client.get("/api/health").json(),
                         {"status":"ok","release":"membership-stabilization-1"})

    def test_new_member_payment_and_retry(self):
        lead=Lead(first_name="New",last_name="Member",email="new@example.com",phone="5550303",
                  product_id=self.product.id,clover_checkout_id="new-checkout",status="started_checkout")
        self.db.add(lead); self.db.commit()
        response=self.payment("new-checkout")
        self.assertEqual(response.status_code,200,response.text)
        member_id=response.json()["member_id"]
        self.assertEqual(self.payment("new-checkout").status_code,200)
        self.db.expire_all()
        self.assertEqual(self.db.query(Member).count(),2)
        self.assertEqual(self.db.query(Sale).filter(Sale.clover_checkout_id=="new-checkout").count(),1)
        self.assertEqual(self.db.query(MemberInvite).filter(MemberInvite.member_id==member_id).count(),0)

    def test_existing_member_payment_does_not_create_duplicate(self):
        before=self.member.membership_end
        self.db.add(Lead(first_name="Test",last_name="Member",email=self.member.email,
                         product_id=self.product.id,clover_checkout_id="existing",status="started_checkout"))
        self.db.commit()
        response=self.payment("existing")
        self.assertEqual(response.status_code,200,response.text)
        self.db.refresh(self.member)
        self.assertEqual(self.db.query(Member).count(),1)
        self.assertEqual(self.member.membership_end,before+timedelta(days=30))

    def test_renewal_payment_is_applied_once(self):
        before=self.member.membership_end
        self.db.add(MembershipRenewal(member_id=self.member.id,product_id=self.product.id,
                                     checkout_id="renewal",amount=150))
        self.db.commit()
        for _ in range(2):
            response=self.payment("renewal")
            self.assertEqual(response.status_code,200,response.text)
        self.db.refresh(self.member)
        self.assertEqual(self.member.membership_end,before+timedelta(days=30))
        self.assertEqual(self.db.query(Sale).filter(Sale.clover_checkout_id=="renewal").count(),1)

    def test_failed_invitation_can_be_retried(self):
        other=Member(first_name="Invite",last_name="Test",email="invite@example.com")
        self.db.add(other);self.db.commit()
        with patch.dict(os.environ,{"RESEND_API_KEY":"test-only"}):
            response=self.client.post("/api/member/admin/invite",json={"member_id":other.id},headers=self.headers())
            self.assertEqual(response.status_code,502,response.text)
            self.assertEqual(self.db.query(MemberInvite).count(),0)
            with patch("resend.Emails.send",return_value={"id":"test-email"}):
                response=self.client.post("/api/member/admin/invite",json={"member_id":other.id},headers=self.headers())
                self.assertEqual(response.status_code,200,response.text)
                self.assertTrue(response.json()["email_sent"])


if __name__ == "__main__":
    try:
        result=unittest.main(verbosity=2,exit=False).result
    finally:
        engine.dispose()
        os.chdir(ORIGINAL_CWD)
        TEMP.cleanup()
    sys.exit(0 if result.wasSuccessful() else 1)
