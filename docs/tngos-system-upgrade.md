# TNGOS operations upgrade — October 28, 2026

## Workspaces and everyday navigation

The admin command center now combines paid gym metrics, upcoming events, workflow shortcuts and a prioritized operations queue. Grouped navigation separates gym operations, TNG Promotions, growth and administration. Search navigation in the sidebar or press Ctrl/Cmd K. Roles retain their existing permitted modules; the new System Overview is admin-only.

Workspace URLs use an allowlisted hash route. Member and event targets can be reopened after a refresh, and browser history navigates between workspaces. Target IDs are validated; hashes are navigation state, never authorization. APIs continue to enforce account, role and ownership checks. Individual workspaces load on demand and have a loading state and an error boundary that leaves navigation available.

## Read-only operations overview

`GET /api/operations/overview` returns a private/no-store snapshot of:

- Paid ticket orders with missing or partial ticket issuance, distinct from unfinished checkouts.
- Saved ticket delivery failures, unreconciled paper admissions and marketing SMS failures.
- Expiring paid memberships, paid profiles awaiting activation and shared contacts needing review.
- Outstanding saved DocuSign statuses, upcoming dated events and draft campaign counts.
- Presence of integration configuration, last customer sync and the current admin's authenticator status.

Provider credentials are never returned. Configuration is explicitly **not** a verified connection or approved messaging campaign. This endpoint makes no provider calls, sends no messages and modifies no business records. Provider verification remains in the corresponding existing workflow.

## Safe processing and reporting

Admin login no longer starts a full Clover sales import. The explicit Sync Clover action shows progress, prevents duplicate submissions, reports actual import counts, and explains that new paid memberships may receive setup emails. The periodic customer-profile worker remains enabled under its existing configuration.

Opening sponsor revenue or changing its tabs no longer processes follow-ups. A separate confirmed action processes only the selected event. Processing locks due prospect rows on PostgreSQL so parallel processors skip a prospect already being handled. The existing `AUTO_SPONSOR_FOLLOWUPS` configuration still controls delivery; the upgrade does not enable it or send any campaign.

Gym day/month reporting uses America/Chicago boundaries translated to UTC for stored timestamps, including daylight saving changes. Dashboard sales counts include paid, non-refunded transactions; nutrition and active-member revenue now subtract refunds consistently. The separate transaction count remains available. Saved payments and membership dates are not rewritten.

## Owner's member import rule

Clover **customer-directory imports require both a valid email format and a phone number with 10–15 digits**. Missing/invalid contact records are skipped. Existing profiles, including paid memberships with incomplete contact details, are retained. Paid checkout processing and financial records are preserved. Manual admin profile creation remains available.

## Runtime security and compatibility

Frontend advisory fixes update Axios, Vite, routing and affected transitive packages. Backend requirements update the web framework, uploads, HTTP clients, image handling, cryptography and related dependencies. Authentication uses maintained PyJWT with an explicit HS256 allowlist, required subject/expiration and a token-size limit. Existing credential-bound session markers, passwords, MFA, signing secrets and POS token audiences are preserved. Standard legacy HS256 sessions are covered by a compatibility test.

Unused python-jose/ECDSA dependencies were removed. The unused MediaPipe requirement was also removed after a repository-wide source check found no application imports; this allowed Protobuf to move to a patched version without removing a used training feature. Backend and frontend dependency audit manifests report no known advisories at release. This is a dependency audit result, not a guarantee about all application or infrastructure risks.

No database migration is required. Deploy the same commit for backend and frontend on `fix/membership-stabilization`; the health release is `tngos-2026.10.28`. Rollback uses the preceding deployment/commit and its requirements. No provider keys or app specs are changed.

## Validation

- Complete backend regression suite under the patched, resolved runtime, including ticket printing/activation, QR validation, memberships, security, SMS, scouting and contracts.
- Additional tests for read-only overview access, partial issuance, pending checkout separation, refunds, Central Time/DST, event-scoped follow-ups, old JWT compatibility and worker startup/shutdown.
- Pure navigation tests for role allowlists and URL targets.
- Mock browser checks for desktop/mobile layouts, keyboard search, member/event links, refresh persistence, staff navigation and absence of automatic POSTs.
- Mock sponsor workflow check verifies opening/tabs are read-only and confirmed follow-ups target only the selected event. No real messages or test charges are used.
