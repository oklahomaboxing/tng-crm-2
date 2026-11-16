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

## Concessions / chef accounts

Create a **Concessions / Chef** user in User Management. Its title and contact phone are stored separately from member and sales-representative records. Assign events and publish service/menu coordination notes through **Partner & concessions access**. The chef signs in at `https://tngos.tngboxinggym.com/#/concessions-portal` and sees only assigned event details and concessions updates. This is a restricted coordination login, not POS/payment processing or inventory management. Concessions accounts cannot receive investor financial summaries or access member records, customer orders, contracts, or administrative APIs. Use the existing password setup/reset flow; do not share an administrator login.

## Chef & Concessions workspace

**Dashboard → Chef & Concessions** opens the event kitchen for administrators. Chef accounts land on this same module and see their assigned events. All concessions tools are available to both roles: menu items and selling prices; food costs and planned margins; planned/sold/waste quantities; a shopping checklist grouped by CHEF’STORE, Walmart, Sam’s Club and Other; prep/service notes; menu ideas; printable published menu PDF; and store order-list CSV.

An event created through the TNGOS event API or existing event import automatically receives concessions-only grants for every active chef account. The grants are created in the same transaction as the event. Disabled chefs, sponsors and investors are excluded. Administrators retain access to every event without a grant. Grant revocation remains effective; renaming an event does not recreate revoked grants. Existing events can be assigned through User Management.

Menu and shopping edits use versions to prevent one person silently overwriting another's changes. Blank food costs remain unknown, so no false margin is displayed. Planned food margin excludes tax, labor, transport and overhead. Shopping estimates and manually entered receipts do not place orders or charge payments; serving counts are not reconciled Clover transactions.

**Generate menu ideas** uses the existing configured OpenAI connection, with a bounded request timeout. If no connection is configured or it fails, a clearly labeled starter template is returned. Draft suggestions are reviewed and editable before import; importing adds items alongside existing ones and is idempotent. AI output cannot mark purchases as paid, assert actual receipts, record sales/waste or verify allergen information. Chef-verified ingredients, allergen labeling, supplier prices and food-service requirements remain the chef's responsibility.

**Review & publish menu** creates a customer-facing snapshot containing names, descriptions, selling prices and allergen notes only. Its PDF excludes food costs, shopping information, internal prep notes and receipt values. Later edits stay draft until republished. Downloads and all workspace APIs require authorized event access.
