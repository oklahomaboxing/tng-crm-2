# Seller sales controls and event cutoff

In an event's Ticket Sales screen, use **Ticket sales controls** to pause or activate individual seller links. Pausing preserves seller code, orders, issued tickets, admission, commission and payout history. Bout assignment and link repair do not reactivate paused sellers.

The optional automatic cutoff is entered in **Oklahoma time (America/Chicago)** and stored in UTC. Select explicit event seller IDs as exceptions, and optionally an exempt seller as the redirect destination. Names are not used for authorization. Activating a seller does not bypass the event cutoff. A manually paused exemption remains paused.

For Fall Brawl 6, the requested setting is **November 14, 2026 at 00:00 Central** (end of Friday November 13), exempting and redirecting to TNG Promotions, seller 19. This is event-specific, not a recurring weekly cutoff. Deployment alone does not configure this setting; save it through the authenticated endpoint/UI.

Public catalog requests after cutoff redirect to the configured active exempt seller with a visible notice. New order creation and Clover checkout initiation independently enforce the same rule, including previously created pending orders. A page left open across cutoff refreshes availability upon a rejected checkout and redirects. Unattributed website sales follow the cutoff too. Paid-order retrieval, verified payment settlement, and delivery do not use this gate.

**Provider limitation:** Clover hosted payment pages already issued can remain payable independently of TNGOS. This change prevents new TNGOS checkouts and reusing their URL through the API; it does not cancel hosted sessions already held by a customer. Confirmed payments must still be fulfilled. Printed tickets already distributed and staff recording prior cash sales are unaffected.

Settings use an additive `event_ticket_sales_windows` table, created by the existing metadata startup path. No cron timing or browser clock is needed. The cutoff is evaluated on each request using server UTC.

Validation: backend tests cover authorization, cutoff equality and time conversion, exemptions, invalid targets, paused links, pending checkout blocking, redirects and post-cutoff payment fulfillment. Browser fixtures cover controls, mobile layout, redirect notice and paid-ticket retrieval. No live sale, SMS or ticket void is used for verification.
