import json,unittest
from datetime import datetime
from unittest.mock import patch,Mock
import test_phone_assistant as support
from app.phone.routes import PhoneCall,PhoneConfig,PhoneSettings
from app.phone.tickets import PhoneTicketSmsRoute,PhoneTicketDelivery
from app.matchmaker.models import BoxingEvent,BoxingEventPublication
from app.ticketing.models import EventSeller,EventTicketType,TicketOrder,EventSalesWindow
from app.operations.renewal_reminders import suppress_sms
from app.models import Lead,MembershipProduct

class PhoneTicketTests(unittest.TestCase):
    setUp=support.PhoneAssistantTests.setUp
    tearDown=support.PhoneAssistantTests.tearDown
    headers=support.PhoneAssistantTests.headers
    webhook=support.PhoneAssistantTests.webhook
    root=support.PhoneAssistantTests.root

    def event(self):
        self.event_row=BoxingEvent(name='Public Fight',slug='phone-tickets',event_date='2099-01-01',venue='Public Arena',venue_address='Public Address')
        self.db.add(self.event_row);self.db.flush()
        self.db.add(BoxingEventPublication(event_id=self.event_row.id,published=True,doors_time='17:00',first_bout_time='18:00'))
        self.db.add(EventTicketType(event_id=self.event_row.id,name='GA',price_cents=4000,active=True))
        self.seller=EventSeller(event_id=self.event_row.id,seller_type='staff',seller_ref_id=1,display_name='TNG Promotions',public_code='TNG-PUBLIC',active=True)
        self.db.add(self.seller)
        self.db.add(PhoneTicketSmsRoute(id=1,account_sid='AC-test',from_number='+14055550199',service_sid='MG-test'))
        self.db.commit()

    def test_link_requires_explicit_consent_uses_promoter_and_never_creates_payment(self):
        self.event()
        self.db.add(EventSalesWindow(event_id=self.event_row.id,cutoff_at=datetime(2020,1,1),exempt_seller_ids_json=json.dumps([self.seller.id])));self.db.commit()
        provider=Mock();provider.messages.create.return_value.sid='SM-test'
        with patch('app.phone.tickets.Client',return_value=provider):
            r=self.webhook('menu',Digits='5');self.assertIn('Press 1 to request this one text',r.text)
            provider.messages.create.assert_not_called()
            self.assertEqual(self.db.query(TicketOrder).count(),0)
            r=self.webhook('tickets/confirm',Digits='1');self.assertEqual(r.status_code,200,r.text)
            args=provider.messages.create.call_args.kwargs
            self.assertEqual(args['to'],'+14055550101')
            self.assertIn('seller=TNG-PUBLIC',args['body'])
            self.assertIn('Reply STOP to unsubscribe.',args['body'])
            self.assertEqual(args['messaging_service_sid'],'MG-test')
            self.assertIn('payment confirmation',args['body'])
            self.assertEqual(self.db.query(TicketOrder).count(),0)
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            self.assertEqual(provider.messages.create.call_count,1)
        self.assertEqual(self.db.query(PhoneTicketDelivery).one().status,'accepted')

    def test_stop_is_honored_and_unknown_submissions_are_not_replayed(self):
        self.event();suppress_sms(self.db,'+14055550101');self.db.commit()
        with patch('app.phone.tickets.Client') as provider:
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            provider.assert_not_called()
        suppress_sms(self.db,'+14055550101',stop=False);self.db.commit()
        provider=Mock();provider.messages.create.side_effect=TimeoutError()
        with patch('app.phone.tickets.Client',return_value=provider):
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            self.assertEqual(provider.messages.create.call_count,1)
        self.assertEqual(self.db.query(PhoneTicketDelivery).one().status,'unknown')

    def test_new_mobile_can_be_entered_and_hourly_limits_apply(self):
        self.event();provider=Mock();provider.messages.create.return_value.sid='SM-test'
        with patch('app.phone.tickets.Client',return_value=provider):
            for i in range(4):
                sid='CA'+str(i+2)*32
                self.webhook('menu',Digits='5',CallSid=sid)
                self.webhook('tickets/confirm',Digits='2',CallSid=sid)
                self.webhook('tickets/phone',Digits='4055550102',CallSid=sid)
                self.webhook('tickets/confirm',Digits='1',CallSid=sid)
            self.assertEqual(provider.messages.create.call_count,3)
            self.assertEqual(provider.messages.create.call_args.kwargs['to'],'+14055550102')

    def test_sms_delivery_callback_signature_and_terminal_status(self):
        self.event();provider=Mock();provider.messages.create.return_value.sid='SM-test'
        with patch('app.phone.tickets.Client',return_value=provider):
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
        row=self.db.query(PhoneTicketDelivery).one()
        path=f'/api/phone/tickets/sms-status?delivery_id={row.id}'
        form={'AccountSid':'AC-test','MessageSid':'SM-test','MessageStatus':'delivered','To':row.phone,'From':'+14055550199'}
        from twilio.request_validator import RequestValidator
        signature=RequestValidator('test-voice-secret').compute_signature('https://voice.example.com'+path,form)
        self.assertEqual(self.client.post(path,data=form).status_code,401)
        self.assertEqual(self.client.post(path,data=form,headers={'X-Twilio-Signature':signature}).status_code,204)
        self.db.refresh(row);self.assertEqual(row.status,'delivered')

    def test_marketing_routes_to_its_own_number_and_labels_callback(self):
        r=self.webhook('menu',Digits='6')
        self.assertEqual(self.root(r).find('Dial/Number').text,'+14059895453')
        self.webhook('transfer-result',DialCallStatus='no-answer')
        self.webhook('callback/name',SpeechResult='Marketing Caller')
        self.webhook('callback/details',SpeechResult='I want to sponsor an event')
        self.assertIn('Marketing inquiry',self.db.query(Lead).filter_by(conversion_source='phone_assistant').one().notes)

    def test_public_prices_and_event_times_are_live_and_private_rates_excluded(self):
        self.event()
        row=self.db.get(PhoneSettings,1);cfg=PhoneConfig(**json.loads(row.settings_json));cfg.use_live_membership_prices=True;cfg.use_live_event_info=True;row.settings_json=json.dumps(cfg.model_dump())
        self.db.add(MembershipProduct(name='Private negotiated plan',price=37,active=True,is_membership=True))
        self.db.add(MembershipProduct(name='Registration Fee',price=100,active=True,is_membership=False));self.db.commit()
        r=self.webhook('menu',SpeechResult='How much does membership cost?')
        self.assertIn('150 dollars',r.text);self.assertIn('100 dollars registration fee',r.text)
        self.assertNotIn('Private negotiated',r.text)
        r=self.webhook('menu',SpeechResult='What time is the next fight?')
        self.assertIn('Public Fight',r.text);self.assertIn('5:00 PM',r.text)
        self.assertNotIn('150 dollars',r.text)
        self.assertEqual(self.root(r).find('Gather/Say').attrib['voice'],'Polly.Joanna')
        pub=self.db.query(BoxingEventPublication).filter_by(event_id=self.event_row.id).one();pub.first_bout_time='19:00';self.db.commit()
        self.assertIn('7:00 PM',self.webhook('menu',Digits='3').text)

    def test_card_details_are_not_saved_as_callback_notes(self):
        self.webhook('menu',Digits='4')
        self.webhook('callback/name',SpeechResult='Example Caller')
        r=self.webhook('callback/details',SpeechResult='My credit card number is 4111111111111111 security code 123')
        self.assertIn('secure ticket checkout',r.text)
        self.assertEqual(self.db.query(Lead).filter_by(conversion_source='phone_assistant').count(),0)
        self.assertNotIn('4111111111111111',r.text)

    def test_paused_promoter_or_cancelled_event_never_texts_a_purchase_link(self):
        self.event();self.seller.active=False;self.db.commit()
        with patch('app.phone.tickets.Client') as provider:
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            provider.assert_not_called()
        self.seller.active=True;self.event_row.status='cancelled';self.db.commit()
        with patch('app.phone.tickets.Client') as provider:
            self.webhook('menu',Digits='5');self.webhook('tickets/confirm',Digits='1')
            provider.assert_not_called()
