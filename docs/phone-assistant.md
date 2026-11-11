# TNG Boxing phone assistant — speech/keypad version

Public NumberBarn number: **(405) 864-4496 / 405-TNG-4GYM**. Direct staff transfer: **(405) 989-5823**.

This version uses Twilio speech recognition, keypad choices and approved text-to-speech answers. It makes no AI-model API requests. Voice, speech recognition and transfer legs incur the provider's normal charges. No call recordings are enabled by TNGOS.

## Caller flow

- 1 or “hours/location”: approved hours/location answer.
- 2 or “membership”: approved membership answer.
- 3 or “events/tickets”: approved events answer.
- 4 or “callback/tour/visit”: collect a name, callback number and inquiry for staff.
- 0 or “staff”: dial the direct staff number. Account-specific/billing requests are routed to staff rather than looking up private records.

Callback requests create one **Lead** per call, with source `phone_assistant`, name, phone and caller-supplied notes. An unknown email remains blank; no email address, SMS consent, paid membership, attendance entry or payment is invented. Anonymous callers can enter a US callback number. Staff can review callback requests in the existing Leads screen. Duplicate callback webhooks do not create duplicate leads. Empty prompts are bounded, and staff can be reached with zero from callback prompts.

Calls and their final statuses appear in the administrator's recent-call list. Caller numbers are masked in that list. Daily counts use America/Chicago boundaries. Callback details are stored only when a caller requests follow-up; general FAQ conversations are not transcribed into CRM notes.

## Administration and connection

Open **System Overview → TNG phone assistant**. Review approved greeting, location/hours, membership and event answers. The initial answers use the confirmed gym address and route unconfirmed rates/hours to staff; enter specific times/rates only when approved. The staff number must ring staff directly, without forwarding back to NumberBarn or the Twilio line.

1. Save the approved answers and staff number.
2. Acknowledge paid voice services and click **Connect Twilio voice menu**. This modifies voice webhooks only on the existing assigned, voice-capable Twilio number. It does not buy a number or place a call. SMS settings remain intact. The API refuses to replace an unrelated existing voice webhook or TwiML application.
3. Call the **Forwarding destination** shown in TNGOS to test all options and staff transfer.
4. In NumberBarn, select **405-TNG-4GYM**, use a plan that supports call forwarding, and set its forwarding destination to the Twilio number shown in TNGOS. The public number remains with NumberBarn; no porting is performed. This NumberBarn account action must be completed by its owner.
5. Test the public NumberBarn number after forwarding.

Turning the speech/keypad menu off forwards connected calls directly to staff. A failed/no-answer staff transfer offers a callback request. This is not a disconnection of the forwarding line. The NumberBarn forwarding destination is controlled in NumberBarn.

## Security and operation

Voice webhooks require a valid Twilio signature, matching account SID, matching assigned called number and a valid call SID. The signed callback URL uses TNG_BACKEND_URL, falling back to the production backend URL. There is no public member-profile lookup and no automated account/payment change. Callback handling uses the existing Leads architecture; requested ticket links use the approved notification SMS route. No email is sent by the phone menu.

Provider credentials reuse the configured Twilio account. Read-only readiness checks confirmed the assigned number supports voice. The setup does not overwrite a foreign voice integration. NumberBarn forwarding and real inbound test calls are not fabricated during automated tests.

Staff transfers ring 35 seconds so the staff phone can answer or accept its normal voicemail. Voicemail left on that phone is managed by the staff phone carrier, not recorded or copied into TNGOS. Preserve original caller ID in NumberBarn forwarding where supported, then verify it using a test call; TNGOS only receives the caller ID the carrier passes through.

## Updated receptionist

The menu also offers **5 — Buy tickets** and **6 — Marketing**, transferring marketing inquiries to **(405) 989-5453**. The selected natural voice is configurable. Confirmed gym hours are Monday–Thursday, 5–7 AM and 5–9 PM, Central; Friday/weekend questions go to staff. Live answers use only the public signup catalog and published upcoming events, including published doors and first-bout times. Negotiated member rates remain private.

Ticket buyers choose an available published event and explicitly confirm a mobile number and permission for one requested checkout text. The link opens the existing Clover checkout flow and credits the available TNG Promotions seller. Payment confirmation and QR delivery continue through the existing verified payment workflow; sending a link does not create a sale. No card numbers are collected over the phone.

Administrators connect the approved notification messaging service using **Connect approved ticket-text service**; setup sends no text. STOP suppression applies, with one submission per call/event and at most three links per mobile per hour. Unknown provider submissions are not automatically replayed. Ticket-text statuses appear in recent calls. Requested service texts do not grant marketing consent. These texts and voice services incur normal provider usage charges.

## Call Center

Administrators can open **Marketing → Call Center** (`/#/call-center`), or use **Open Call Center** in the phone settings. The ledger shows existing calls that reached TNGOS, caller/callback numbers, saved caller names, final states, department transfers, callback requests, and ticket-text statuses. Filter by Oklahoma-local date, name/number, callback requests, connected transfers, or in-progress calls; **All history** removes the date limits. It refreshes every 30 seconds while visible.

New calls record structured menu selections, transfer outcomes and final provider-reported duration. Existing calls retain their saved states; missing historic timelines/durations are clearly labeled. No spoken menu answers or call recordings are added. Saved callback notes remain accessible to administrators and in Leads. A connected transfer can mean the destination's voicemail answered. Text delivery is not proof of payment. Calls that never reach the forwarding destination remain available only in NumberBarn's logs. This release does not backfill provider call history or place outbound calls.
