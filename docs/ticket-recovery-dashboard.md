# Ticket recovery dashboard

Open an event's Event Ticket Sales page and use **Orders & ticket recovery**. Admin and staff accounts can search customer/receipt/fighter/payment references and filter paid orders needing attention, pending payments, and paid orders without seller attribution. Results are paginated; summary values cover the whole event. The backend batches event order, ticket aggregate, and delivery queries instead of querying per order. It currently evaluates event-wide order health in memory before applying filters and pagination.

- **View tickets** retrieves a private ticket page for an already paid and issued order. It sends no notification and issues no tickets. Treat the resulting private URL as a customer credential.
- **Recover / retry** requires confirmation. It uses the existing idempotent recovery path and skips deliveries already accepted or delivered. It does not charge the customer. Invalid, partial, or void/refund ticket sets require manual review. Staff recovery requests are audited.
- **Verify Clover payment** is admin-only. Confirm the customer's Clover order and re-enter the exact saved checkout ID. Existing server verification checks authoritative payment/refund evidence and duplicate payment assignment before issuance. Do not infer association from amount alone.
- Pending orders are not counted as verified revenue. Commission earned is the recorded commission on valid/used tickets for paid orders; it is not an unpaid balance. This change does not modify negotiated rates or historical attribution.
- Email `sent` means provider acceptance. SMS `delivered` is a carrier acknowledgement. The dashboard does not initiate resends during initial load or refresh.

The dashboard also fixes seller PDF/CSV download paths that previously included the backend URL twice.

Validation: 30 ticketing regression tests, frontend production build, and browser checks using synthetic API fixtures for read-only load/view, explicit reconciliation confirmation, and a single recovery submission. No customer notifications are sent by these checks.
