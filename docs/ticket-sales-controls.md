# Seller sales controls and event cutoff

In an event's Ticket Sales screen, use **Ticket sales controls** to pause or activate individual seller links. Pausing preserves seller code, orders, issued tickets, admission, commission and payout history. Bout assignment and link repair do not reactivate paused sellers.

The optional automatic cutoff is entered in **Oklahoma time (America/Chicago)** and stored in UTC. Select explicit event seller IDs as exceptions, and optionally an exempt seller as the redirect destination. Names are not used for authorization. Activating a seller does not bypass the event cutoff. A manually paused exemption remains paused.

For Fall Brawl 6, the requested setting is **November 14, 2026 at 00:00 Central** (end of Friday November 13), exempting and redirecting to TNG Promotions, seller 19. This is event-specific, not a recurring weekly cutoff. Deployment alone does not configure this setting; save it through the authenticated endpoint/UI.

Public catalog requests after cutoff redirect to the configured active exempt seller with a visible notice. New order creation and Clover checkout initiation independently enforce the same rule, including previously created pending orders. A page left open across cutoff refreshes availability upon a rejected checkout and redirects. Unattributed website sales follow the cutoff too. Paid-order retrieval, verified payment settlement, and delivery do not use this gate.

**Provider limitation:** Clover hosted payment pages already issued can remain payable independently of TNGOS. This change prevents new TNGOS checkouts and reusing their URL through the API; it does not cancel hosted sessions already held by a customer. Confirmed payments must still be fulfilled. Printed tickets already distributed and staff recording prior cash sales are unaffected.

Settings use an additive `event_ticket_sales_windows` table, created by the existing metadata startup path. No cron timing or browser clock is needed. The cutoff is evaluated on each request using server UTC.

Validation: backend tests cover authorization, cutoff equality and time conversion, exemptions, invalid targets, paused links, pending checkout blocking, redirects and post-cutoff payment fulfillment. Browser fixtures cover controls, mobile layout, redirect notice and paid-ticket retrieval. No live sale, SMS or ticket void is used for verification.

## Direct seller portals

Canonical sales links now use `/tickets/{seller_public_code}`. Fighter portal shares, staff copies, QR images, seller-link emails, and phone-requested texts use the same URL builder. The public route resolves the saved seller and event before loading their named sales page; it never opens a private fighter account or requires a CRM login. The original `/events/{event_id}/tickets?seller=...` links still work.

Legacy root `?seller=...` and `?seller_code=...` links, plus root `?fighter=...` or `?join=...` containing generated ticket codes such as `F2-1234ABCD`, resolve to the corresponding sales portal. Ordinary membership referral slugs retain their existing signup behavior. Invalid seller codes show an explicit link error rather than falling through to the main login screen. Existing private paid-ticket retrieval links remain unchanged.

The event sales API still enforces paused sellers, cutoff times, and the configured TNG redirect. Canonical link resolution alone does not enable sales or bypass these policies. Phone company selection recognizes the official TNG Promotions seller even when that record was historically stored under the fighter seller type, without changing its identity or commission terms.

Old phone texts containing `/events/{event_id}/tickets?source=phone` without a seller are also resolved to the event's existing TNG Promotions seller when available. This repairs already-sent links without sending replacement messages. Paid/failure return URLs and ordinary event links remain on the existing order-status routes. Resolution never marks an order paid, creates tickets or retries a charge. Customer checkout copy explicitly says that payment must be completed on Clover before QR tickets are issued.
