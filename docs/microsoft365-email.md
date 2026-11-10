# Microsoft 365 welcome-letter email

TNGOS supports an optional Microsoft 365 connection for fighter welcome emails. Before connection, the existing Resend sender remains active. The connection does not migrate marketing campaigns, membership reminders, ticket email or invitations.

## Administrator setup

1. Sign in at https://entra.microsoft.com as the Microsoft 365 administrator. Open **App registrations → New registration**, name **TNGOS Mail**, and select **Accounts in this organizational directory only**.
2. Add a **Web** redirect URI exactly:
   `https://sea-lion-app-2-gxyfr.ondigitalocean.app/api/mail/microsoft365/callback`
3. Under **API permissions**, add **delegated Microsoft Graph** permissions `Mail.Send`, `User.Read` and `offline_access`, and grant administrator consent for the organization. TNGOS does not request Mail.Read or Mail.ReadWrite.
4. Under **Certificates & secrets**, create a client secret and copy its **Value**, not its Secret ID.
5. In TNGOS → **System Overview → Microsoft 365 email**, enter the Directory (tenant) ID, Application (client) ID and secret Value in the password field. Never paste secrets into chat.
6. Click **Save & connect Microsoft 365**, sign in to **marketing@tngboxinggym.com**, and accept the permissions. TNGOS verifies the connected mailbox matches this exact address. A shared mailbox without its own sign-in requires a separate delegated Send As setup and is not accepted as another user's account.
7. The card turns connected and new fighter welcome letters use Microsoft 365. Sent messages are saved in the mailbox's **Sent Items**. Connecting itself does not send a test email or bulk letter.

The client secret and refresh/access tokens are encrypted at rest using a purpose-specific key derived from the existing backend SECRET_KEY. They are never returned by the API or stored in frontend browser storage. Changing that key requires re-saving credentials and reconnecting.

OAuth uses authorization code + PKCE, short-lived random state, a one-time browser handoff, an HttpOnly Secure SameSite=Lax cookie and a stored administrator credential marker. The top-level handoff sets its cookie on the backend's own domain, avoiding third-party cookie dependence. Callback verifies current administrator role, credential generation, mailbox identity and delegated Mail.Send scope. App configuration changes and disconnect invalidate outstanding authorization links.

## Sending and recovery

Each new welcome submission snapshots its provider. Microsoft is selected only after successful sign-in. Old Resend submissions keep their original provider, and no unknown submission silently falls back to another service.

Graph sendMail is submitted once per persisted delivery key, with the PDF attached, reply address set to marketing@tngboxinggym.com and saveToSentItems enabled. A 202 response is provider acceptance, not proof of inbox delivery. The stored Microsoft request correlation ID is not a delivered-message receipt.

Microsoft does not provide Resend-style send idempotency. Therefore uncertain Graph requests are **not replayed**, even by the generic recovery button. Staff must review Outlook Sent Items for uncertain sends. Definite rejections can be retried after correcting the connection; no automatic retry or cross-provider fallback occurs. Existing accepted welcome emails are skipped.

**Disconnect Microsoft — use Resend for new welcome emails** clears stored Microsoft access and refresh tokens. It preserves historical submission routes and does not recall sent mail. Microsoft app permissions can also be revoked in the Microsoft administrator portal.

No Microsoft credentials, consent or live email sends are fabricated during testing. Tests mock the provider, verify encrypted storage, admin authorization, PKCE/callback replay protection, exact mailbox matching, PDF attachment construction, provider routing and uncertain-send protection.

## Explicit recovery of rejected Resend attempts

When Microsoft is connected and the unchanged letter has rejected Resend submissions, the welcome-letter dialog offers **Send N rejected emails through Microsoft**. This is an explicit staff-selected provider change, not automatic fallback. Accepted entries, unknown/in-flight entries and recipients never attempted are excluded. The previous Resend payload and rejection are archived with the acting user before switching the selected submission to Microsoft. The three-state distinction matters: a later rejection cannot prove an earlier unconfirmed attempt never arrived, so the screen warns that another copy is possible. The standard send button is disabled when every recipient already has an accepted or review submission, preventing misleading zero-send results.
