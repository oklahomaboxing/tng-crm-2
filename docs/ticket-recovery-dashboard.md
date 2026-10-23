# Ticket recovery dashboard

Open an event's Event Ticket Sales page and use **Orders & ticket recovery**. Admin and staff accounts can search customer/receipt/fighter/payment references and filter paid orders needing attention, pending payments, and paid orders without seller attribution. Results are paginated; summary values cover the whole event. The backend batches event order, ticket aggregate, and delivery queries instead of querying per order. It currently evaluates event-wide order health in memory before applying filters and pagination.

- **View tickets** retrieves a private ticket page for an already paid and issued order. It sends no notification and issues no tickets. Treat the resulting private URL as a customer credential.
- **Recover / retry** requires confirmation. It uses the existing idempotent recovery path and skips deliveries already accepted or delivered. It does not charge the customer. Invalid, partial, or void/refund ticket sets require manual review. Staff recovery requests are audited.
- **Verify Clover payment** is admin-only. Confirm the customer's Clover order and re-enter the exact saved checkout ID. Existing server verification checks authoritative payment/refund evidence and duplicate payment assignment before issuance. Do not infer association from amount alone.
- Pending orders are not counted as verified revenue. Commission earned is the recorded commission on valid/used tickets for paid orders; it is not an unpaid balance. This change does not modify negotiated rates or historical attribution.
- Email `sent` means provider acceptance. SMS `delivered` is a carrier acknowledgement. The dashboard does not initiate resends during initial load or refresh.

The dashboard also fixes seller PDF/CSV download paths that previously included the backend URL twice.

Validation: 30 ticketing regression tests, frontend production build, and browser checks using synthetic API fixtures for read-only load/view, explicit reconciliation confirmation, and a single recovery submission. No customer notifications are sent by these checks.

Deployment runtime: `.python-version` files pin Python 3.11.15, the existing live runtime. DigitalOcean selected 3.11.17 from an unpinned 3.11 declaration but its Ubuntu 22.04 runtime archive returned HTTP 404; the 3.11.15 archive was verified available before retry. Review the pin when a newer runtime is available.

## Paid purchases and unfinished checkout views

The staff UI defaults to **Paid purchases** (`issue=paid`) and provides a separate **Unfinished checkouts** view (`issue=unfinished`, pending/failed records). **All records** retains access to every record, including refunds. The API default remains `all` for compatibility; the existing `pending` filter also remains valid.

A pending record with a checkout reference is labeled **Checkout started — payment not confirmed**. A record without that reference is **Details saved — checkout not confirmed**. Only an explicitly recorded failed state is labeled as a payment failure. These labels do not infer abandonment, a card decline, or a technical error from elapsed time or missing payment evidence.

Unconfirmed rows show selected tickets, checkout value, the original fighter referral, no earned commission, and delivery awaiting confirmed payment. An admin can still verify a Clover receipt when a customer reports having paid. No record is deleted, marked paid, or imported into marketing by changing views. Existing payment verification, automatic paid-ticket delivery, and commission rules remain authoritative.

Validation: 32 ticketing tests and the frontend production build pass. Browser fixtures confirm paid-only default results, the separate unfinished view, explicit unconfirmed-payment wording, preserved all-records access, and GET-only requests during view changes.
