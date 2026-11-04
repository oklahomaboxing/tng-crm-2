# Membership renewal reminders

Admin workspace: `/#/renewal-reminders` (also linked from Members and Gym Operations).

## Defaults and timing

- Enabled by default: email and consented SMS, five days before the recorded membership period ends.
- Optional one-day follow-up is off by default. Admins can disable either channel or the entire scheduler.
- The worker checks every five minutes. Submissions occur only between 10 AM and 6 PM America/Chicago, including daylight-saving adjustments.
- The five-day notice catches up if the service missed its initial day, while at least one Central calendar day remains before expiration. Expired and inactive memberships are excluded.
- The member's existing membership details and renewal options remain authoritative. Reminders do not charge cards, renew memberships, change negotiated rates, or create sales/attendance.

## Eligibility and privacy

Uses the existing gym membership reporting definition: a usable name/email and genuine membership evidence or a recorded manual term. Event-ticket customers alone are not gym members.

Email opt-outs are respected. SMS requires documented consent from a matching waiver (participant name, lead email and normalized phone), or an active matching marketing contact with recorded SMS opt-in. The latest matching waiver refusal takes precedence. Merely having a phone number, buying a ticket, or being a gym member never grants consent. Shared email/phone identities are skipped for review rather than guessing the recipient.

Validated Twilio STOP/START callbacks maintain a phone-hash suppression record even if no marketing contact exists. START removes suppression but does not create promotional consent. Texts use the existing verified account-notification Messaging Service and include STOP instructions. No new campaign or promotional message is created.

Admin previews omit recipients and do not send or enqueue messages. The message contains the member's first name, period-end date, public portal link and gym support number; it contains no billing or private profile details.

## Reliability and results

The persistent outbox deduplicates by normalized recipient, expiration date, notice stage and channel. Submission claims prevent concurrent workers from sending the same notice. A queued reminder rechecks current membership, expiry, contact, consent and settings immediately before claiming submission. A recorded renewal cancels the old-period notice. Once a provider has accepted a submission, subsequent renewal cannot retract it.

`accepted` means provider acknowledgment, not confirmed inbox/handset delivery. Signed Twilio callbacks record SMS delivery/failure and cannot downgrade a delivered result. Email inbox delivery is not inferred. Timeouts and interrupted submissions become `unknown` and are never automatically replayed; an operator must inspect the provider before any manual outreach. Explicit rejected requests may retry after 30 minutes, at most three attempts. Missing provider configuration waits without submitting. Resend also receives a stable per-reminder idempotency key.

The history lists the latest 100 reminder rows. The worker's last completed check is shown separately from configured credentials. Existing logs and recipient/provider evidence should be used to investigate uncertain submissions; this feature deliberately has no bulk resend button.

## Deployment

Models are registered with the existing SQLAlchemy metadata and created by the existing application startup schema initialization. No existing member, purchase or attendance columns are rewritten.

Existing secrets/configuration are reused: `RESEND_API_KEY`, optional `RESEND_FROM_EMAIL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TNG_APP_URL` and `TNG_BACKEND_URL`. No credentials belong in source control. `MEMBERSHIP_REMINDERS_WORKER_ENABLED=0` disables the background worker; default is `1`. Tests always disable it and mock providers; never run the test database fixtures against production.

API: admin-only GET/PUT `/api/renewal-reminders`; signed Twilio POST `/api/renewal-reminders/sms-status?delivery_id=...`.

## Expired membership text notices

SMS-only expired notices are enabled by default in the same admin workspace (Text when membership expires). One notice per expiration date is sent after the recorded term ends, with up to three Central calendar days of catch-up. Older expired records are not bulk-texted. Expired notices reuse the same consent, opt-out, shared-contact, quiet-hour and submission safeguards. Manual inactive, suspended and cancelled accounts are excluded. Renewing before submission cancels an outdated expiration notice. This setting is stored in a separate additive table; existing reminder settings and recipient history are retained.
