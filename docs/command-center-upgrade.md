# Command center upgrade — first release

The shared admin frame uses graphite navigation, TNG red actions, restrained blue accents, a subtle grid backdrop and consistent surfaces, inputs and tables. The dashboard separates gym metrics from event ticket payments and unrecorded paper allocations. Figures are loaded from existing reporting APIs; there are no simulated growth trends, security scores or provider-health claims. The assistant landing page uses the same visual language. Public check-in retains its dedicated full-screen interface.

Navigation labels, role restrictions, event/member deep links and Ctrl/Cmd-K search are retained. Mobile navigation remains a drawer, touch targets remain at least 44 pixels, animations respect reduced-motion settings and the main content has space for the floating assistant control. Shared component styling does not replace payment, ticket-printing or attendance workflows.

## Payment and access review

System Overview includes a read-only reconciliation queue (`GET /api/operations/reconciliation`, admin only). It flags paid ticket orders with missing quantities or valid/used ticket shortfalls, saved delivery failures, gym records missing identity information, recorded membership payments missing terms, and eligible gym profiles lacking portal access. Each item opens its existing event or member record. Pending checkouts are displayed separately and do not count as paid sales. No charge, refund, ticket issuance, invitation or membership activation is performed by reviewing this queue. It does not reconcile directly with Clover's bank/payment records.

## Trusted devices

Security Center lists the signed-in user's remembered device sessions. New sessions have a browser/device label inferred from the user agent and a hashed credential binding stored in a separate additive table. Users can rename known devices and revoke individual sessions, including the current one. Revoking the current session clears the app's sign-in immediately; revoking another device does not revoke all sessions. All endpoints scope records to the requesting user. Tokens, token hashes, password hashes and credential fingerprints are never returned by the listing endpoint.

Previously issued sessions remain usable. Legacy non-current sessions are marked unverified because their old credential binding cannot be reconstructed from a hash. A legacy current session can establish its details by renaming itself. Remembered access is distinct from device online status. Kiosk pairings remain separate. Existing password/MFA/session revocation rules are preserved.

## Validation and remaining work

Backend tests cover read-only reconciliation, unpaid-order separation, role restrictions, device ownership, individual revocation, legacy sessions and credential invalidation. PostgreSQL regressions and browser checks cover the new flows. Desktop and mobile screenshots use fixtures, never pretend to show current business activity.

This is the initial shared-interface and operational-review release. Direct provider reconciliation automation, expanded customer timelines, broader delivery automation and verified production backup restoration remain separate follow-up upgrades. No production backup restoration has been claimed or performed as part of the UI release.
