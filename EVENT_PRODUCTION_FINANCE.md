# Event production and concessions financial reporting

## Announcer and DJ
Admin/staff open Boxing & Events → Announcer & DJ, or the show-plan shortcut on an event. Admin can prepare any event immediately. Create separate Announcer or DJ accounts in User Management, then assign selected events under Show profiles & access. No accounts or invites are created automatically. Assigned roles see only public fight-card details, production scripts, team profiles and walkout music; member/customer identities, medical records, contracts and purses are excluded.

Run of show holds ordered, timed/triggered cues with an owner (announcer, DJ or both). Announcement templates include welcome, concessions, bar, sponsor recognition, headphone reminder and closing. Sponsor names come only from committed/paid event sponsors; price mentions come only from a published concessions menu. Fighter introductions and walkout cues can be drafted from the current bout card. Drafts require admin/staff approval before presenter mode/completion. Completion is manual and versioned; editing reopens a cue for review. The workspace refreshes every 12 seconds and exports a run-of-show PDF. It does not play audio or make external announcements automatically.

Music includes title, artist, reference URL, start offset, clean-version status, confirmation and DJ notes. DJ/admin/staff can edit songs for current-card fighters; announcers have read access. Song-reference links never trigger server downloads. Profiles can be edited by admin or their own announcer/DJ user. Revoking an assignment removes the next API access immediately.

## Concessions / bar and expense sheet
Admin/staff open the event's Concessions → Sales & profit. Review the Oklahoma City time window before Read Clover sales. Default is event date 00:00 through next morning 06:00, with an exclusive end. Read-only Clover requests fetch paginated orders and catalog categories; a complete snapshot replaces prior data atomically. An order cannot be attributed to two events. Provider failures, truncation or overlarge windows preserve the prior report.

Only fully paid, reconciled orders count. Recorded item sales exclude taxes and tips. Known line discounts/modifiers are applied; basket-level discounts are allocated proportionally using exact integer-cent allocation. Unpaid, refunded, exchanged, service-charge, truncated and unexplained/malformed orders are excluded and counted for review. Paid lines Clover labels non-revenue are counted from actual receipts and flagged for configuration review. This is a sales snapshot, not a card-settlement ledger; processing fees must be recorded separately.

Beer, mixed drinks and shots are suggested as Bar; clear food/soft-drink items and eligible Clover categories as Concessions. Ticket/membership items are excluded; ambiguous manual/custom items require staff classification. Staff can change classifications and save them before export. Unknown amounts are never invented. Categories update event recaps and investor income; matching source-backed food/bar sale rows are excluded from the separate sales ledger to avoid mirrors being counted twice.

Operating expenses reuse BoxingEventFee, so the same beer/alcohol purchase appears once in the event recap. Staff can add idempotent actual receipt expenses and allocate them to concessions, bar, shared event cost, review or exclusion. Existing excluded duplicate/fighter-pay/ticket-commission treatments cannot be overridden in this sheet. Shopping plans and unit costs are not automatically added as cash expenses. Fighter compensation remains in the full event recap.

Net sales minus recorded allocated costs is labeled contribution. Confirmed section profit/loss requires explicit staff confirmation that complete costs are recorded, no unclassified sales or unresolved source discrepancies, and no missing allocated expense amounts. Shared overhead must be reviewed; a checkbox is a staff assertion, not proof of a bank balance. PDF results and itemized expense PDF/CSV show the basis, window, reviewed exclusions, unpaid statuses and missing amounts. Save allocations before export.

## Welcome letter
All newly generated event letters include: No loud music. Please bring headphones if you want to listen to music. Shared preparation and warm-up areas must remain quiet. Previously submitted emails are not resent automatically; changed preview hashes require staff to review the updated letter before sending.

## Budget and forecast
Event staff open Budget & Forecast in More event tools or the event header/recap. Prior events must have a completed calendar date and recorded paid tickets. The default reference is the most recent eligible event; incomplete historical records remain flagged. Current recorded operating amounts take precedence over prior references; prior excluded placeholders are not copied as cost estimates. Current card purses/allowances use both corners. With no current fighters, prior purse costs are explicitly an unbooked planning reference. Venue/rent, insurance and processor allowances stay missing until entered or explicitly zeroed.

Editable assumptions cover total expected paid tickets, average net ticket price, food/bar sales per paid ticket, sponsorship/vendor revenue, total purse/allowances, itemized operating costs, ticket commission percentage, assessment percentage/minimum and processing allowance. Historical paid tickets are a proxy, not verified attendance. The three scenarios use 80%, 100% and 120% ticket volume; operating/purse costs are fixed, commissions/assessment/processing vary with receipts. Recorded current commissions are a floor. A monotone search provides the modeled minimum break-even count up to 100,000 paid tickets, or reports it unattainable under the assumptions. Inputs missing from the calculation are explicitly flagged, even though their arithmetic contribution is zero. Source review flags persist.

Preview recalculates without saving. Save persists only the separate, versioned budget assumptions; it never creates actual sales, receipts, payouts or contracts. The reviewed saved forecast exports to PDF. Forecasts are estimates, not guaranteed demand or an investment return.

## November 19 financial presentation and OSAC rule
The OSAC calculation is the greater of 5% of paid ticket subtotals or $450 per event. Recorded assessments above that amount remain honored; amounts recorded below the required calculation remain visible and create a review warning instead of reducing the liability. Reports, recap totals and forecast scenarios share this rule. Existing saved budget minima below $450 are normalized when read/saved; no order, ticket or fighter commission is fabricated to adjust the aggregate.

The event statement presents paid ticket revenue, classified Clover concessions and bar receipts, sponsor/vendor receipts, total income, and costs separately. Charts use those same numeric summary fields and exclude unpaid checkouts and excluded expense placeholders. The investor default selects the latest held-date event with paid ticket sales rather than an upcoming event; the overview links to its full statement. Unimported food/bar snapshots display as not recorded. Expense composition distinguishes operating expenses, purses, seller commissions and state assessment. Itemized expenses have their own top-level recap view; paid markers, source dates and provisional status remain visible.

## November 19 navigation and reconciliation update

The sidebar uses compact rows, explicit group icons and a single selected-page highlight; Daily Tools no longer duplicates navigation. Event finance has Overview, Revenue, All Expenses, Paid Purses and Commissions views. All expense entries are visible together, with no second collapsed expense list. Investor event expenses are expanded and finance view selectors are tabs on desktop and mobile.

Forecasts retain recorded receipts and obligations as floors. Blank historical inputs cannot make an event with paid ticket sales display zero income. Both corners remain included and the $450 assessment minimum remains enforced.

Paper stock can be explicitly marked complimentary without creating paid orders, customer messages, revenue or commissions. Previously scanned stock stays used; reprints retain QR identities and four-per-page layout. Sold/order-linked/returned stock cannot be converted. Complimentary stock remains included in paper inventory capacity and attendance totals.

Assigned sponsors may receive a cost-only statement with explicit admin sharing. Event access checks protect JSON/PDF endpoints. It includes category obligations, recorded payments and flat expense entries; no individual fighter contracts, buyer records or global business accounts are shared. Investors retain their existing scoped permissions. Unknown payments are labeled unrecorded, not assumed paid or unpaid.

POS exclusion of a previously counted ticket receipt requires an exact payment reference and exact whole-order subtotal match. Unclassified receipts remain visible for review; legitimate exclusions and open orders alone do not produce a generic financial error. Deduction guidance is informational and does not invent vendor expenses.

Tournament defaults are Saturday Noon / PM and optional Sunday Noon / PM. Existing saved morning times are labeled honestly and recorded results are preserved.

## Direct comparison and minimum pro-show worksheet

Fight Recap is available on the admin dashboard and in Boxing & Events for admin/staff only. Its direct URL is `/#/fight-recap`. Up to four event summaries can be compared in aligned columns, with full-recap links and horizontal scrolling inside the comparison on phones. Recorded income sources, both-corner purse costs, commissions, assessment, operating expenses and paid amounts use the existing recap API.

The event budget includes a separate, saved minimum pro-show planning worksheet: $10,000 total professional purses, $1,750 inclusive athletic commission allowance, $400 EMSA, $50 event permit, $255 state liquor license and $255 ABLE liquor license. Known listed baseline is $12,710 plus fighter insurance (price not supplied). This worksheet is included in the budget PDF. It does not create actual expenses or payments and does not replace the complete event forecast; unlisted event costs remain separate. Fall Brawl liquor-license actual costs are recorded separately from the existing promoter/matchmaker/event/sport permit entries, per owner confirmation.
