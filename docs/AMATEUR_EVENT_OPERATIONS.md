# Amateur events: tournament, clubs and officials

The Amateur Matchmaker workspace now includes **Tournament**, **Clubs** and **Officials** views, alongside roster, event setup, match proposals and rule reference. Existing 93-boxer roster records and professional fight cards remain separate.

## Two-day tournament planning

Create a plan using a Saturday date. Configure Saturday AM/PM and Sunday PM; Sunday AM can be Auto, Always or Off. In Auto, the planner compares three- and four-session allocations and adds Sunday AM only when it reduces unscheduled bouts. Times use America/Chicago. Bout-slot estimates default to 15 minutes and session capacities to 20; edit times/capacities to fit the show. Overlapping sessions and slots extending beyond midnight are rejected.

Add draft divisions with 1–16 available roster entries in the staff-selected draw/seed order. Brackets use single elimination, power-of-two sizing and first-round byes. Unopposed divisions remain labelled for official review; a title is not awarded automatically. A boxer cannot be placed in two divisions of the same tournament.

**This is a draft planner, not an official draw or automatic tournament eligibility certification.** The 2026 Rule 12 source says the OIC and event Fact Sheet determine the official draw, which must be public. National-tournament age classification and event-specific classes must not be replaced by the local matched-bout Appendix F logic. Staff must verify division classifications, entry requirements and seed order with the OIC/Fact Sheet. Mixed-sex local matched-bout exceptions are not assumed for tournament divisions.

TNG's conservative planning defaults are **one bout per boxer per day and 12 hours between potential bouts**. These are explicitly labelled TNG planning policy, not invented universal USA Boxing rules. Scheduling checks all possible participants in winner placeholders and all earlier bracket rounds. Larger brackets can require more competition days even with Sunday AM enabled. Unscheduled bouts are retained with reasons; the planner does not force them into an unsafe or infeasible slot.

Record a confirmed official winner only after earlier rounds resolve. Winner identity advances in the draft bracket but does not establish medical clearance or change pro career records. Later recorded results must be cleared before changing an earlier result. Recorded results protect the existing event's settings/schedule. Draw/roster changes invalidate old schedules. CSV export includes draft status, session times, both corners and unresolved/unscheduled bouts.

## Club and people imports

The seven supplied exports represent five distinct byte-level sources, including HTML-based `.xls` exports and flattened TXT exports. A temporary-database import trial produced **83 club identities and 510 people** from 516 membership rows. All seven filenames are retained as source aliases. A Non-Athlete membership label (161 people in these sources) does not establish official/coach role or current certification.

Sources are private, archived with their original text, and retain row observations, alternate emails/phones, source membership types/statuses and conflicting identity flags. Person identity merges use USA Boxing member IDs; club identities use normalized club name/city/state. Shared family phone numbers are not used to collapse different athletes. Duplicate source bytes are idempotent. Source imports do not create gym memberships, logins, availability, SMS permission or official qualifications.

A flattened export with broken tab boundaries is repaired only if its non-whitespace content exactly matches a previously imported structured Excel export. Otherwise it is retained for review rather than guessed. Import Excel exports first; the multi-file UI orders them first automatically. Review source history and original rows through the private directory UI.

## Officials and communication

1. In Officials, choose the single-day roster event or a tournament plan.
2. In People & officials directory, review Non-Athlete contacts or add a person. Staff explicitly select verified roles/current credentials. Add the verified official to this event's availability list.
3. Preview the request before pressing Send, or copy its scoped reply link. Importing, adding to a show, or previewing sends nothing.
4. The public reply form shows only that official's event/session details and their own response. Links use high-entropy tokens in URL fragments; only token hashes and encrypted token material are stored. They expire after 30 days. Event detail changes invalidate old responses/links until staff reissue the request; reissuing clears prior availability/confirmed assignments.
5. Availability and confirmed assignments are distinct. A confirmed official counts in only one verified role per session and must be available. A later unavailability reply removes affected confirmations. Staffing targets are entered by staff/OIC, not inferred as official minimums. Optional Sunday AM coverage is identified separately.

One-to-one email uses the configured Microsoft 365/Resend route. SMS uses a verified notification messaging service, recorded phone permission, shared STOP suppression and a STOP footer. Send requests are idempotent; unknown provider submissions are not automatically replayed or silently sent via another provider. Provider acceptance is displayed as acceptance, not delivery proof.

Staff notes, send attempts and reply-link responses are kept in communication history. Email replies arrive in the connected mailbox; freeform SMS replies use the existing TNGOS Text Inbox. They are not falsely presented as automatically imported email conversations. No additional mailbox read permission is requested.

## Security and checks

Private event/directory APIs require admin, staff or matchmaker access; investor/sponsor/concessions/manager/member roles do not receive these directories. Public reply APIs are token scoped, rate limited, no-store and contain no roster, email, phone, home-address, billing or other official-contact records. Changes and role/permission decisions are audited. No providers are contacted by import or schedule generation.

Tests cover brackets, byes, infeasible three-round/two-day paths, Sunday overflow, duplicate assignments, versions, winner dependencies, source imports/recovery, role verification, private public replies, staffing shortages, withdrawals, opt-outs, STOP text, provider idempotency and unknown submission handling. Browser tests run against an isolated local API with fake providers and synthetic contacts, covering tournament creation, bracket/schedule/result workflow, directory verification, request preview, public reply, confirmed coverage and mobile views. No real officials are messaged by testing.
