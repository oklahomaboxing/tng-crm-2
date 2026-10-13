# TNG production ticket repair

Repair base: `fix/membership-stabilization` at `1a2d0eacd9ed48ded251668b61017c4aecdc6c78`.
Repair branch: `ticket-production-repair`.
Backend: `sea-lion-app-2`, component `tng-crm-2-backend`.
Frontend: Goldfish, customer site `https://tngos.tngboxinggym.com`.

## Incident evidence and limits

Production screenshots show event 2 orders 7 and 8 pending, no payment IDs, no issued tickets,
and intact seller IDs. These are not paid-state records yet. A saved webhook signing secret
and a correct endpoint URL do not establish successful callback delivery or matching.
The deployed verifier matches Clover's official Hosted Checkout HMAC contract:
https://docs.clover.com/dev/docs/ecomm-hosted-checkout-webhook.
Do not disable it, fabricate signed payment events, or mark pending orders paid from amounts alone.
The supplied Clover order ID `YQ31QWGSE3P7A` has not yet been matched to a particular TNG order.

## What the repair changes

- Payment state, complete QR issuance, and notification queue commit together.
- Duplicate callbacks heal paid orders with zero tickets and reuse existing QR codes.
- Concurrent issuance, notifications, and admission scans serialize on database rows.
- Purchase price and commission snapshots prevent later catalog edits changing a paid order.
- Invalid fighter/seller links are rejected instead of silently losing credit.
- Saved checkout sessions are reused rather than replaced, preserving callback matching.
- Signed customer ticket links work across devices without local browser storage.
- Ticket texts and email acceptance/failures are tracked. Pending/failed delivery retries every
  30 seconds with exponential delays, up to eight attempts. Staff recovery retries failed channels.
  A provider acceptance ID is not confirmation of handset delivery. After an ambiguous provider
  timeout or process crash, a notification retry may produce another message; tickets remain unique.
- Pending orders can be reconciled by an admin against Clover merchant API paid-order evidence,
  an exact amount, successful payments, refund/void checks, and explicit checkout association.
  The recovery audit preserves the original fighter attribution and prevents reuse of the Clover order.
- Orders without a saved phone cannot be texted; their email and ticket page still work.
- Refunded/void tickets are excluded from fighter commissions/reports.

## Server configuration

Keep existing DigitalOcean settings and secrets. Verify these names, never print their values:
`DATABASE_URL`, `CLOVER_MERCHANT_ID`, `CLOVER_API_TOKEN` (merchant orders/payments read access),
`CLOVER_ECOMMERCE_PRIVATE_KEY` (existing Hosted Checkout key), `CLOVER_WEBHOOK_SECRET`,
`TICKET_QR_SECRET` (stable, at least 32 characters), `TNG_APP_URL`, `RESEND_API_KEY`,
`TICKET_FROM_EMAIL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
Do not rotate `TICKET_QR_SECRET`; it decrypts existing QR tickets.
`TNG_APP_URL` should be `https://tngos.tngboxinggym.com`.
The frontend `VITE_API_URL` should be `https://sea-lion-app-2-gxyfr.ondigitalocean.app`.
Twilio must allow sending to the customer numbers; verify sender registration and trial restrictions.
`TICKET_DELIVERY_WORKER_ENABLED=0` disables automatic delivery retries when operationally necessary.

The new tables `ticket_deliveries`, `ticket_recoveries`, and `ticket_checkout_attempts` are additive
and created by the application's existing `Base.metadata.create_all` startup flow. No existing
customer records are changed during deployment. The database user must be able to create tables.

## Validation and deployment

Tests use an isolated temporary database and fake notification/payment providers. No real charges:

```powershell
Set-Location 'C:\Users\Bount\Downloads\TNG_Ticket_Production_Repair'
git fetch origin
git switch ticket-production-repair
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B backend/tests/test_stabilization.py
python -B backend/tests/test_ticketing.py
Push-Location frontend
npm ci
npm run build
Pop-Location
```

Use the repository's existing Python virtual environment with `backend/requirements.txt` installed.
Both regression suites also support the dedicated local PostgreSQL test database described in
`backend/tests/test_stabilization.py`; they deliberately refuse arbitrary PostgreSQL targets.

Publish the tested repair branch, fast-forward the deployment branch, and deploy backend plus Goldfish.
Do not reset branches, discard local changes, or copy secrets into this repository. Goldfish's
actual branch/build settings must be checked; a backend deployment alone does not update the ticket page.
Before deployment take a managed PostgreSQL backup/snapshot through DigitalOcean if available.
Verify `/api/health` returns `ticket-production-repair-1` and `/openapi.json` includes
`/api/ticketing/orders/{order_id}/reconcile-clover`. Review runtime callback/worker errors.

## Recover affected purchases from PowerShell

```powershell
.\production-repair\Ticket-Repair.ps1 -Mode Diagnose -EventId 2
```

For an already-paid order with missing tickets/failed notifications:

```powershell
.\production-repair\Ticket-Repair.ps1 -Mode Recover -OrderId 7
```

This refuses a pending order. For a pending order, first explicitly match the customer's Clover
order to the TNG checkout. Then supply **that verified association**, rather than assuming that the
previously supplied Clover ID belongs to order 7 or 8:

```powershell
.\production-repair\Ticket-Repair.ps1 -Mode Reconcile -OrderId <TNG_ORDER_ID> `
  -CloverOrderId '<VERIFIED_CLOVER_ORDER_ID>' -ConfirmCheckoutId '<TNG_CHECKOUT_UUID>'
```

The endpoint makes only read requests to Clover, records verified payment, issues the exact purchased
QR tickets, preserves seller ID, and attempts texts/email. Running it again reuses the tickets.
Compare order state, ticket quantity, fighter report, commission, and provider acceptance afterwards.
Do not publish the returned private ticket link or customer diagnostics publicly.

PowerShell commands are for your Windows machine. DigitalOcean's web console is Bash;
PowerShell here-strings and Windows paths do not work there. This script has not been executed
on Windows in the cloud task.

## Remaining production verification

An end-to-end sandbox payment should produce an authenticated callback, paid order, correct ticket
quantity, customer QR page, notification provider acceptance, fighter totals, and one-time admission.
Production recovery requires real Clover evidence and authorized admin access. Local passing tests
are not evidence that an affected customer has received a message.
If callbacks return 401, compare the Hosted Checkout signing secret with the DigitalOcean binding
securely; a 503 indicates missing signing configuration. A 404 indicates an unmatched checkout.
Log bodies/secrets must not be copied into public reports.

Rollback application code to the previous deployment through DigitalOcean if necessary. Leave
the additive tables and recovery history intact. Rolling back the frontend/backend can affect
notification retries, but must not delete issued tickets or charge customers again.
