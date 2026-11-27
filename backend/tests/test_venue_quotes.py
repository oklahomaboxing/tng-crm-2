import unittest
from unittest.mock import patch
from datetime import datetime,timedelta
from uuid import uuid4
import test_venue_bookings as support
from app.events.venue import VenueBooking,TZ
from app.events.venue_quotes import VenueQuote,VenueQuoteReceipt

class QuoteTests(unittest.TestCase):
 tearDown=support.VenueBookingTests.tearDown
 calendar=support.VenueBookingTests.calendar
 headers=support.VenueBookingTests.headers
 body=support.VenueBookingTests.body
 add=support.VenueBookingTests.add
 update=support.VenueBookingTests.update
 def setUp(self):
  support.VenueBookingTests.setUp(self)
  from app.models import User
  for role in ['investor','sponsor']:
   u=User(name=role,email=role+'@example.com',role=role,active=True,password_hash='fixture');self.db.add(u);self.db.commit();self.users[role]=u
  self.add();self.row=self.db.query(VenueBooking).one()
 def create(self,**changes):
  self.db.refresh(self.row)
  body={'booking_version':self.row.version,'rental_cents':50000,'services_cents':10000,'deposit_cents':15000,'services':'Setup and cleanup','inclusions':'Three hours, tables and chairs','terms':'Deposit due before confirmation. Contact TNG to agree on payment and cancellation terms.',**changes}
  return self.client.post(f'/api/venue/bookings/{self.row.id}/quote',headers=self.headers('coordinator'),json=body)
 def token(self,data):return data['quote']['url'].split('#')[1]
 def accept(self,token):return self.client.post('/api/venue/quotes/public/accept',json={'token':token,'name':'Organizer Name','agree':True})
 def receipt(self,key=None,**changes):return self.client.post(f'/api/venue/bookings/{self.row.id}/quote/receipts',headers=self.headers('coordinator'),json={'amount_cents':15000,'reference':'BANK-RECEIPT-123','paid_on':datetime.now(TZ).date().isoformat(),'request_key':key or str(uuid4()),**changes})
 def test_quote_accept_deposit_confirm_and_no_public_private_data(self):
  r=self.create();self.assertEqual(r.status_code,200,r.text);data=r.json();token=self.token(data)
  public=self.client.post('/api/venue/quotes/public/view',json={'token':token});self.assertEqual(public.status_code,200,public.text)
  for secret in ['email','phone','staff_notes','url','receipts','created_by','token']:self.assertNotIn(secret,public.json())
  self.db.refresh(self.row);self.assertEqual(self.update(self.row,'confirmed').status_code,409)
  self.assertEqual(self.receipt().status_code,409)
  self.assertEqual(self.accept(token).status_code,200);self.assertEqual(self.accept(token).status_code,200)
  self.assertEqual(self.update(self.row,'confirmed').status_code,409)
  k=str(uuid4());first=self.receipt(k);self.assertEqual(first.status_code,200,first.text);self.assertEqual(first.json()['stage'],'deposit_paid');self.assertEqual(self.calendar().json()['quote_statuses'][str(self.row.id)]['stage'],'deposit_paid');self.assertEqual(self.receipt(k).status_code,200);self.assertEqual(self.db.query(VenueQuoteReceipt).count(),1)
  self.assertEqual(self.receipt(k,amount_cents=100).status_code,409);self.assertEqual(self.receipt(amount_cents=60000).status_code,422)
  self.assertEqual(self.update(self.row,'confirmed').status_code,200);self.assertEqual(self.create().status_code,409)
 def test_revisions_revoke_previous_acceptance_and_paid_quotes_cannot_be_replaced(self):
  old=self.create().json();token=self.token(old);self.assertEqual(self.accept(token).status_code,200)
  new=self.create(rental_cents=55000);self.assertEqual(new.status_code,200,new.text);self.assertEqual(new.json()['quote']['revision'],2);self.assertIsNone(new.json()['quote']['accepted_at'])
  self.assertEqual(self.accept(token).status_code,409);token=self.token(new.json());self.accept(token);self.receipt();self.assertEqual(self.create().status_code,409)
 def test_roles_invalid_amounts_expired_quotes_and_schedule_changes(self):
  for role in ['member','fighter','staff','rep','investor','sponsor']:
   self.assertEqual(self.client.get(f'/api/venue/bookings/{self.row.id}/quote',headers=self.headers(role)).status_code,403)
  self.assertEqual(self.create(deposit_cents=999999).status_code,422);self.assertEqual(self.create(rental_cents=1.1).status_code,422);self.assertEqual(self.create(services='').status_code,422)
  r=self.create().json();token=self.token(r);q=self.db.query(VenueQuote).one();q.expires_at=datetime.utcnow()-timedelta(days=1);self.db.commit();self.assertEqual(self.accept(token).status_code,410)
  r=self.create().json();token=self.token(r);self.db.refresh(self.row);self.assertEqual(self.update(self.row,'on_hold',starts_local=self.day+'T14:00',ends_local=self.day+'T17:00').status_code,200);self.assertEqual(self.accept(token).status_code,409)
 def test_conversation_is_scoped_idempotent_and_private_notes_stay_private(self):
  token=self.token(self.create().json());body={'token':token,'message':'Can we add one more hour?','request_key':str(uuid4())}
  r=self.client.post('/api/venue/quotes/public/messages',json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.client.post('/api/venue/quotes/public/messages',json=body).status_code,200);self.assertEqual(len(r.json()['messages']),1)
  r=self.client.post(f'/api/venue/bookings/{self.row.id}/quote/messages',headers=self.headers('coordinator'),json={'message':'We can revise the schedule and price.','request_key':str(uuid4())});self.assertEqual(r.status_code,200,r.text)
  view=self.client.post('/api/venue/quotes/public/view',json={'token':token}).json();self.assertEqual(len(view['messages']),2);self.assertNotIn('staff_notes',view)
  self.assertEqual(self.client.post('/api/venue/quotes/public/view',json={'token':'x'*48}).status_code,404)
 def test_email_is_explicit_idempotent_and_uses_existing_provider(self):
  self.create()
  with patch('app.mail.microsoft365.selected_provider',return_value='microsoft365'),patch('app.mail.microsoft365.send_welcome',return_value={'id':'fixture'}) as sender:
   self.assertFalse(sender.called);r=self.client.post(f'/api/venue/bookings/{self.row.id}/quote/send',headers=self.headers('coordinator'));self.assertEqual(r.status_code,200,r.text);self.assertEqual(sender.call_count,1);payload=sender.call_args.args[1];self.assertIn('html',payload);self.assertIn('/venue/quote#',payload['text']);self.assertEqual(self.client.post(f'/api/venue/bookings/{self.row.id}/quote/send',headers=self.headers('coordinator')).status_code,409);self.assertEqual(sender.call_count,1)
 def test_uncertain_email_blocks_replay_and_zero_deposit_requires_acceptance(self):
  r=self.create(deposit_cents=0).json();self.db.refresh(self.row);self.assertEqual(self.update(self.row,'confirmed').status_code,409)
  with patch('app.mail.microsoft365.selected_provider',return_value='microsoft365'),patch('app.mail.microsoft365.send_welcome',side_effect=RuntimeError('timeout')) as sender:
   self.assertEqual(self.client.post(f'/api/venue/bookings/{self.row.id}/quote/send',headers=self.headers('coordinator')).status_code,502);self.assertEqual(self.client.post(f'/api/venue/bookings/{self.row.id}/quote/send',headers=self.headers('coordinator')).status_code,409);self.assertEqual(sender.call_count,1)
  self.accept(self.token(r));self.assertEqual(self.update(self.row,'confirmed').status_code,200)
