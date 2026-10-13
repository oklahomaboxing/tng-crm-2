# Ticket policy and SMS consent approval

On October 13, 2026 the authorized administrator approved:

- Nonrefundable customer cancellations.
- Refund of the ticket purchase if TNG cancels the event.
- Existing tickets remain valid if TNG reschedules; customers unable to attend may request a refund.
- Support: marketing@tngboxinggym.com / +1 405-959-5823.
- Mobile numbers and text consent are not sold or shared with third parties or affiliates for marketing; sharing is limited to providers needed to deliver the service.

The public ticket privacy notice and terms are implemented in
`frontend/src/pages/TicketPolicies.jsx`, at `/ticket-privacy` and `/ticket-terms`.
Checkout links to both pages and records affirmative, unchecked-by-default SMS
consent in `ticket_sms_consents`, with order, phone, notice text/version, and UTC time.
Declining texts does not prevent purchase or email ticket delivery.
Legacy customer orders are not assigned invented consent records.

These policies cover event ticket purchases, not every gym or membership practice.
Refund requests require staff processing; publishing terms does not automatically
issue Clover refunds. A rejected A2P campaign must still be resubmitted and approved
before US carrier delivery can be verified.
