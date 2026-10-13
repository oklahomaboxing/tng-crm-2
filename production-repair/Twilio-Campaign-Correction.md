# Twilio campaign correction — draft for business review

The existing TNG Boxing brand is APPROVED. Its ACCOUNT_NOTIFICATION campaign is FAILED.
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

The business must verify that the live consent notice and documented opt-in process meet Twilio's
requirements. The current checkout collects a mobile number for ticket texts, but it does not
record a separate consent checkbox. Do not claim one exists. Twilio may require a clearer consent
flow, message/data-rate disclosure, support information, and accessible privacy/terms links.
Use the business's approved policies; do not assert unverified privacy practices or invent opt-in
records. Any proposed policy/consent changes must be reviewed by the business before publication.

This draft has NOT been submitted. It is not an approved campaign and does not unblock US SMS.
Resubmission may require a provider fee and carrier review. Once the campaign is APPROVED,
confirm the configured phone number remains assigned to it and retry only the failed ticket texts.
Do not resend delivered ticket emails or issue duplicate tickets.

Order 7 also needs a corrected customer mobile number; it currently fails with code 21211.
Order 8's previous text was accepted by Twilio but rejected by the carrier with code 30034.
Both ticket emails were confirmed delivered, and both customers have valid issued QR tickets.
