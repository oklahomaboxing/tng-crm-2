# Facility pricing and booking coordination

From Facility Management → Venue & Event Bookings, open a request and select Pricing & coordination.

1. Create quote: enter rental price, priced extra services, required deposit, included hours/equipment and customer terms. The total is rental plus extra services; the deposit is part of that total. No tax, refund, cancellation policy or default rental rate is invented.
2. Review the customer page, then use Send quote for the existing Microsoft 365/Resend route, or Copy quote link to share it yourself. Creating a quote or posting a conversation message does not send a notification. Send quote explicitly addresses the booking email; provider acceptance is not proof of delivery.
3. The customer opens the private link, reviews prices/times/terms, enters a name, accepts, or posts a question. Use Refresh conversation to check replies. This thread is specific to the quote, separate from the SMS Venue Inbox. Internal notes, customer email/phone, receipt references and staff data are excluded from public responses.
4. After verifying actual payment externally, staff record the amount, payment date and receipt/transaction reference. This is a receipt record, not a card charge or Clover checkout integration. Quote receipts are not automatically posted into other business ledgers.
5. On Booking details, confirm only after the current quote is accepted and the required deposit is recorded. Server validation enforces both and rechecks schedule conflicts. Quotes/acceptance alone do not reserve the calendar; use On hold to reserve time during discussion.

A revision replaces the old private link and requires new acceptance. Quoted times are snapshotted; schedule changes require a revision. Paid quotes cannot be replaced or rescheduled without staff reconciliation. Payment correction/refund automation is not included. Existing blockouts and legacy bookings with no quote retain the direct confirmation workflow.

The list shows quote-ready, sent, accepted, deposit-paid, expired/revision-required and confirmed states. Zero-deposit quotes still require acceptance. Private links expire if not accepted; accepted quotes remain viewable until replaced/cancelled. Treat links as private bearer access. Public actions are rate-limited. Message/receipt retries use unique request keys; uncertain email submissions block automatic replay.

## Deployment and checks

New tables: venue_quotes, venue_quote_messages, venue_quote_receipts. They are registered through the existing venue router before metadata initialization and created through the existing startup process. Existing booking columns/records are preserved. Reverting application code leaves the new tables for forward recovery.

Tests cover authorization, private-field exclusion, stale/revised/expired links, receipt idempotency/overpayment, acceptance/deposit confirmation gates, conversation scoping and explicit/uncertain email submissions. Existing booking conflicts and role restrictions are retained. A PostgreSQL-only simultaneous-booking test is skipped unless an isolated TEST_DATABASE_URL is configured.

An isolated browser/API walk-through created an itemized quote, mocked its email submission, accepted it as a customer, posted a customer reply, recorded a receipt, and confirmed the booking. Customer phone layout had no page overflow; no browser errors occurred. No live customers were contacted and no production bookings or payments were changed. Sidebar main category labels/icons are red and submenu labels white.
