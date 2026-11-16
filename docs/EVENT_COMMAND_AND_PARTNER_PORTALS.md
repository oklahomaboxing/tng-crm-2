# Event command workflow and partner access

Open **TNG BOXING EVENTS → Saturday Night Fights**. Overview provides four steps:

1. **Matchmaking:** search fighters by name, record or location, or generate suggestions. Choose fighters and review terms before sending an offer. Sending one fighter an offer does not secure the opponent's agreement.
2. **Offers:** review negotiations and accepted offers. Review before adding an accepted offer to the card. A matching draft with identical weight, rounds and bout type is reused; the accepted fighter's corner is inferred from that card. Existing contracts are never overwritten by conversion. Mismatched terms or another opponent's booking require review.
3. **Fight Card:** review corners, terms and bout order.
4. **Contracts:** review prepared documents, send them and track signatures. Conversion prepares a contract; it does not send it.

Use **Matchmaker Desk** for the contact directory, open slots and staff-entered conversation history. Names can be saved before phone/email are known. Later, edit the contact and use Call, Text on device or Email. These links open the device's apps; delivery and replies are not automatically imported. Notes and agreed slot statuses do not create bouts or send offers.

Medicals, compliance, expenses, results, settings and other tools remain under **More event tools**. Event readiness and the fighter welcome letter are optional panels on Overview. Standard and Command modes use the same data and workflow; Command adds the existing dark cyan glass styling.

## Investor and sponsor logins

Administrators create an **Investor** or **Sponsor** account in **User Management → Create User** using the existing account creation flow. No real external accounts are created by this release.

In **Investor & sponsor access**, refresh partner accounts, select the account and event, write an update, and press **Save access & publish update**. Select an existing assignment to revise its update. Revoke event access to remove the event immediately. Disabling the account blocks the login.

Both partners sign in at the normal TNGOS URL. They land on their own portal:

- Investor: `https://tngos.tngboxinggym.com/#/investor-portal`
- Sponsor: `https://tngos.tngboxinggym.com/#/sponsor-portal`

Accounts initially see no events. Investors see financial summaries only when the administrator explicitly enables sharing on that event. Summaries contain aggregate recorded income, ticket sales, costs and gain/loss, with provisional labeling when incomplete; they are not bank balances. Sponsors never receive financial summaries. No private member/customer records, contracts, payout breakdowns or administrative controls are included.

External roles are restricted at the shared authentication dependency to their portal, their identity and account-security/session functions. Event assignments are enforced by the API, not just hidden menus. Use account security settings to revoke sessions when appropriate.

## Validation

The regression suite covers event-scoped access, revocation, disabled accounts, blank contact numbers, saved slots/notes, stale status updates, signed-contract protection and draft reuse. Isolated PostgreSQL tests also cover simultaneous offer conversion and transactional template creation. Browser checks use sample data and intercept writes; they do not send real offers or messages.
