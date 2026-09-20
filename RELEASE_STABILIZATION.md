# Membership stabilization release

This release repairs the existing application; it does not replace member data or rebuild the production database.

## Changes

- Member list, profile and dashboard reads no longer recalculate and save membership terms.
- Profile responses preserve coach, emergency contact and notes fields used by the editor.
- Renewals retain remaining paid time; annual and configured multi-month plans use their intended duration.
- Explicit membership rebuilds use paid, non-refunded sales in chronological order.
- Member checkout handles both new and existing members and repeated notifications.
- Member renewal checkout is saved in the new `membership_renewals` table and processed once by the payment webhook.
- Clover Hosted Checkout notifications require a valid HMAC signature and matching merchant.
- Member operations, revenue operations, ticket administration, attendance and diagnostic messaging require authorized staff; member/fighter accounts cannot read staff sales or leads.
- All portals use the shared active-account authentication check.
- Failed member invitation emails no longer leave a new seven-day invitation blocking retry.
- The member portal's conditional React hooks are corrected. Expired browser sessions return to login.
- Public default-password account creation is removed from startup and the seed script.
- SQLite has a stable backend-relative default path. Alembic now uses `DATABASE_URL` and imports feature metadata.
- `/api/health` identifies this release as `membership-stabilization-1`.

## Required release preparation

1. Confirm the DigitalOcean frontend and backend repository/branch settings before pushing a deployment branch. Source repository: `oklahomaboxing/tng-crm-2`; inspected local branch: `v3-development`.
2. Back up the live database using the existing provider's backup mechanism. Preserve its `DATABASE_URL` and uploads/storage settings. Do not upload the ZIP's SQLite files over live data.
3. Set **CLOVER_WEBHOOK_SECRET** on the backend to the existing Hosted Checkout signing secret from Clover. Keep the existing `CLOVER_MERCHANT_ID`. Do this before releasing the backend: unsigned requests or a missing signing secret will be rejected. See [Clover signature documentation](https://docs.clover.com/dev/docs/ecomm-hosted-checkout-webhook).
4. Confirm `VITE_API_URL` routes the frontend to the intended backend. User-confirmed frontend: `https://tngos.tngboxinggym.com`; backend: `https://sea-lion-app-2-gxyfr.ondigitalocean.app`. The checked-in frontend production environment currently uses the frontend origin, so retain it only if an API reverse proxy is configured.
5. Deploy the authenticated revenue frontend before the backend that requires those authorization headers. Existing open tabs may need a refresh.
6. The existing SQLAlchemy startup registration creates the additive `membership_renewals` table. Existing data is preserved. Do not run historical Alembic migrations blindly against the live database: the old revisions still lack a complete baseline.
7. Verify the backend `/api/health`, member login, staff member profile, QR check-in and normal renewal flow. Payment-provider validation should use the provider's supported test process, not a real charge without separate authorization.

`BOOTSTRAP_ADMIN_PASSWORD` is needed only to create a missing initial admin. Existing administrator credentials are not changed. The seed script requires at least 12 characters and never prints the password.

## Validation

Run `python -B backend/tests/test_stabilization.py` from the project root in an environment with the backend dependencies installed. The suite uses a temporary SQLite database, disables `.env` loading, mocks email/Clover checkout, and does not send messages or charge payments.

Twenty regression tests cover profile persistence, roles, disabled accounts, expiration, annual/configured plans, early renewal, payment signatures/retries, new/existing member checkout, renewal tracking, invitation retry and duplicate routes.

For browser QA, `python -B backend/tests/preview_stabilization.py` starts synthetic data on `127.0.0.1:8765`. Start Vite with `VITE_API_URL=http://127.0.0.1:8765`. Preview-only accounts: `member@example.com` and `admin@example.com`, password `LocalPreview123!`. Never run this fixture as a public deployment.

## Remaining limitations

- InBody result-to-scan persistence still needs the actual provider response schema and configured test account. Manual scan entry remains available.
- The Roku receiver remains a starter screen.
- The historical Alembic migrations need a separately reviewed baseline migration before adopting migration-only startup.
- Live external integrations and PostgreSQL behavior require deployment-environment verification; the local regression database is SQLite.
- Invitations left pending by email failures before this release are not automatically invalidated.
- This is not a complete security audit of every existing feature.

## Rollback

Redeploy the previously recorded frontend/backend revisions through DigitalOcean. Keep the additive renewal table and its payment records; do not delete payment history or restore a database over new transactions. The prior backend does not process the new renewal table, so pause new renewal checkout if a backend rollback is needed and reconcile any in-flight payments before resuming it.
