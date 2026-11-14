# Commission reports and display modes

In an event's Ticketing → Reports section, the commission panel sits beside Email Seller Reports. Administrators can configure verified To/CC recipients and the report schedule in America/Chicago. Settings do not affect seller cutoffs or ticket purchases.

Fall Brawl 6 (event 2): Heather.Turner@osac.ok.gov, CC Diana.Fletcher@osac.ok.gov, confirmed by the owner. Unsent alert begins Sunday November 15, 2026 at 00:00 CT (06:00 UTC). Normal report submission closes Monday November 16 at 01:00 CT (07:00 UTC). Late reports remain possible with explicit acknowledgement. These are report submission times, not ticket sale times.

Send All Ticket Reports attaches the master ticket PDF and a ZIP of master and every seller's PDF/CSV, including inactive sellers. The existing paid-subtotal 5% calculation and reconciliation notes are preserved. Review paper stock, partial refunds and issuance discrepancies before submitting. This sends reports; it does not pay the commission.

Microsoft 365 sends from marketing@tngboxinggym.com, saves Sent Items and includes CC. Provider acceptance is recorded separately from inbox delivery. Durable snapshot signatures prevent duplicate submissions. A changed report requires a new submission; uncertain submissions block replay and require review in Outlook Sent Items. There is no automatic midnight email. Requests exceeding the 3 MB encoded package limit must be submitted through Outlook using downloaded reports. Administrator authorization is required for configuration, reports and sending.

Enabled unsent reports produce a prominent alert across admin screens after their deadline. Server time is used for the browser clock, with a one-minute refresh for report changes. The alert remains after closing until the current snapshot is accepted. It cannot appear on a closed/offline browser.

The header Standard / Command toggle stores a preference in the browser. Standard retains the familiar interface. Command applies dark glass panels, cyan accents, interactive live-report tiles, transitions and a read-only briefing assistant to the authenticated workspace. Public/member/kiosk entry routes retain their existing presentation. Command visual effects respect reduced-motion settings. The visual design makes no additional security assurance.

Command briefings use saved TNGOS reports with deterministic topic routing, without paid AI-model requests. Optional press-to-talk starts only on a user action and depends on browser speech support; typed questions always work. Read-aloud is opt-in. The voice indicator animates only while actually listening or speaking. This does not enable speech recognition on the telephone menu, which remains keypad-only.

Validation: commission authorization, Central/UTC deadlines, complete report packet, CC and attachment MIME serialization, snapshot changes, duplicate send prevention, uncertain/rejected handling, late acknowledgement, and no paid AI routing. PostgreSQL integration tests use a separate local disposable database; provider requests are mocked, never live email.
