# Twilio ticket campaign — corrected and resubmitted

The existing TNG Boxing brand is APPROVED. Its ACCOUNT_NOTIFICATION campaign was FAILED.
On October 13, 2026 the corrected campaign update was accepted by Twilio with status
IN_PROGRESS and an empty errors list. This is pending review, not carrier approval.
The configured phone number belongs to the account and is assigned to TNG Boxing's messaging
service. No alternate approved sender exists in this account.

Twilio returned these actual rejection reasons:

- 30886: invalid campaign description.
- 30893: invalid sample message content.
- 30909: the submitted opt-in/call-to-action could not be verified.

The separate marketing campaign also failed privacy-policy verification (30908). Do not switch
transactional ticket notifications to that failed marketing campaign.

## Proposed ticket-notification description

TNG Boxing sends purchased-event ticket confirmations and secure QR ticket links to customers
who request ticket text notifications. Messages identify TNG Boxing and the event. This campaign
is for transaction-related ticket notifications, not promotional offers.

## Sample matching the repaired application's actual message

Your TNG tickets for Fall Brawl 6 are ready. View your QR tickets:
https://tngos.tngboxinggym.com/events/2/tickets?[PRIVATE_ORDER_ACCESS_PARAMETERS]
Reply STOP to opt out.

Use a sample URL without an actual customer's access token when submitting registration.

## Required opt-in evidence before resubmission

Supply the exact public checkout page, not the CRM login page:
https://tngos.tngboxinggym.com/events/2/tickets

The public checkout now records an optional, unchecked ticket-text consent checkbox,
with the exact wording and timestamp tied to the order. It links to:
https://tngos.tngboxinggym.com/ticket-privacy
https://tngos.tngboxinggym.com/ticket-terms
Support is marketing@tngboxinggym.com / +1 405-959-5823.
The administrator approved the mobile-data non-sharing policy and refund terms.

The corrected description, two samples matching the private ticket-link message, recorded
checkout opt-in flow, public privacy URL, and public terms URL have been submitted.
Twilio returned IN_PROGRESS; US SMS is not yet unblocked. Once the campaign is APPROVED,
confirm the configured phone number remains assigned to it and retry only the failed ticket texts.
Do not resend delivered ticket emails or issue duplicate tickets.

Order 7 also needs a corrected customer mobile number; it currently fails with code 21211.
Order 8's previous text was accepted by Twilio but rejected by the carrier with code 30034.
Both ticket emails were confirmed delivered, and both customers have valid issued QR tickets.

## Follow-up rejection and resubmission — October 14, 2026 (Central)

The ticket campaign returned FAILED with 30896 (opt-in information). The separate
marketing campaign remains unrelated and rejected; it was not resubmitted.

Following Twilio's 30896 guidance, the production frontend now provides public,
JavaScript-independent privacy and terms documents and a consent evidence page:

- https://tngos.tngboxinggym.com/ticket-privacy.html
- https://tngos.tngboxinggym.com/ticket-terms.html
- https://tngos.tngboxinggym.com/ticket-text-consent.html
- https://tngos.tngboxinggym.com/ticket-text-consent.png

The screenshot contains empty buyer fields, unchecked consent, and public event data;
no customer records were published. Policy documents are rendered from the same React
policy component during prebuild, rather than maintained as separate policy wording.
All four public resources returned HTTP 200 and their expected content was verified.

The existing campaign update was accepted with IN_PROGRESS status and an empty errors
list. This is resubmission acceptance, not carrier approval or successful SMS delivery.

### Provider settings that remain unresolved

The campaign still exposes legacy opt_in_keywords JOIN / START / TNG and an
opt_in_message advertising membership updates, appointment reminders, event
announcements, and special offers. These contradict the website-only ticket campaign.
The supported update method does not expose these fields. A request including empty
OptInKeywords and OptInMessage was accepted for the campaign update, but read-back
showed that Twilio retained those legacy values. Do not claim they were cleared.

In Twilio Console, open Messaging → Regulatory Compliance → Campaigns → TNG Boxing.
If Edit is available, select website-only enrollment for this campaign and disable
keyword enrollment / remove its legacy keyword and promotional welcome fields.
Preserve normal STOP opt-out and standard START re-subscription behavior; do not turn
off opt-out protection. The campaign is for ticket notifications, not marketing.
Use the published evidence/policy URLs above. If those registration fields are locked
or cannot be corrected, Twilio support must correct the retained campaign metadata.
No support message has been sent and no campaign has been deleted or recreated.
