# Amateur roster upload and local matched-bout proposals

Open **Boxing & events → Amateur Matchmaker** (admin, staff or matchmaker). Use **Roster actions → Upload amateur roster** for CSV/XLSX intake. The core matching views are: **Boxer roster**, **Event setup**, **Match proposals**, and **Rules & reference**. Tournament, Clubs and Officials have their own sections; see [Amateur event operations](AMATEUR_EVENT_OPERATIONS.md). On phones, choose a view from the Workspace view dropdown. In Event setup, choose a TNG event or standalone competition date and save; this opens Match proposals, where **Auto-match roster** generates proposals. Roster filters and matching preferences fold away. The Match view dropdown separates proposed bouts (20 per page) from unmatched/excluded boxers. Boxer editing separates Profile, Boxing details, and Club & coach into tabs, preserving edits between tabs. Roster entries remain separate from professional fighters, member accounts, ticket sales and actual bout cards.

The supplied `singleday_all.csv` has 93 rows. A temporary-database trial parsed all 93 without data-review errors. The live import intentionally leaves the competition date and event unassigned. An event date must be selected before any live proposals are generated.

## Source edition

The owner explicitly requested the **2026** rulebook as the current reference after supplying links labelled 2026. It is not called a 2027 rulebook. The reviewed source is:

- USA Boxing National Rulebook, revised January 1, 2026; Appendix F page 53 (the chart itself is labelled revised January 1, 2025), Rule 9.1 and Appendix H.
- Official PDF: https://assets.contentstack.io/v3/assets/blteb7d012fc7ebef7f/blt5ff28f6e78e9624d/695ed2d8b45570d8a64b74b9/USA_Boxing_Rule_Book_Revisions_-_1.1.2026.pdf
- SHA-256: `39c1d0c67b266cacb3341b2bcc23842da4d5ca6c57fc59eccb60380333faa28a`

The image-only matching chart was rendered and visually transcribed. `rules_2026.py` records the transcription and version. A reviewed-rule database record identifies its reference edition and applicable competition year. Unknown/disabled sources block generation; a future edition requires a new source review and implementation. The 2026 reference is authorized here for the 2026 and 2027 competition years.

## Official constraints and TNG preferences

This implementation supports **local matched bouts**, not advancing tournament seeding or developmental bouts.

- Match ages by actual date of birth with mutual Appendix F age ranges. For a pair involving ages 8–17, enforce an exact maximum 24-month birth-date difference. Do not substitute national-tournament calendar-year ages. The roster shows both ages to help review.
- Minimum actual age eight. Masters match only other Masters, age 35+, within ten years by birth date. Ages 35–40 require their registered Elite/Masters/Both classification before proposals can use them.
- Apply the lower-age division's rules. For declared weight proposals, enforce both boxers' applicable tolerance from the chart, conservatively. Actual weigh-in weights still need checking.
- Same-sex proposals by default. A staff preference optionally permits the explicitly allowed local Pee Wee mixed-sex case, both ages 8–10.
- Show three rounds and the maximum duration for the lower-age division; Masters maximum two minutes.
- **Total-bout gap is a TNG preference, not a USA Boxing rule.** Default maximum gap five; staff can change it. Avoid same-club proposals by default. In weight bands where Appendix F has no limit, TNG defaults to a 20 lb proposal gap cap; it is labelled as a preference.

Rule 9.1 requires consideration of total bouts and winning percentages, both coaches' discretion and final approval by the Official in Charge. This file contains total bouts but no wins. Proposals therefore flag missing winning percentages. Other combat-sport experience, current membership/passbooks, physicals/medical restrictions, actual weights, Masters registration and equipment approval are not established by an imported spreadsheet.

**Proposals are preliminary.** Generation sends no offers or messages, signs no contracts and makes no changes to actual fight cards. CSV exports repeat the proposal/review status. Use the supplied certified-equipment memo and sanction manual when organizing the event; this matching tool does not certify sanction/equipment compliance.

## Data and matching behavior

- UTF-8 CSV / XLSX, maximum 5 MB, 1,000 boxer rows and bounded expanded spreadsheet size. Leading-zero member IDs survive CSV import. For XLSX, store IDs as text to preserve zeros that spreadsheet software would otherwise discard.
- Required fields: USA Boxing member ID, first/last names, DOB, sex, declared weight, total bouts and club. Coach/location fields are kept when supplied; optional wins and age classification can be added in boxer review.
- Bad and duplicate-ID rows are preserved with review flags and excluded from matching until corrected. Staff can withdraw a boxer using Exclude. No medical clearance or verified membership status is inferred.
- SHA-256 retry detection reopens the existing roster rather than duplicating it. PostgreSQL advisory locks serialize concurrent uploads. Changes use optimistic versions; roster row locks serialize edits and generation.
- Up to 200 available, unflagged boxers per generation. A binary optimization maximizes the number of disjoint bouts, then prefers smaller weight, bout-count and age gaps. A ten-second solver limit is disclosed if only a feasible result is returned. No boxer appears twice.
- Saved runs retain the rule-source version, date, preferences and roster fingerprint. Reopening restores current proposals. Changes invalidate displayed proposals and warn that regeneration is required. Unmatched/excluded boxers are retained with reasons.
- Private authenticated APIs, no-store responses, audited changes and spreadsheet-formula escaping in CSV exports. No roster or DOB data is exposed on public facility/ticket pages.

## Validation

`backend/tests/test_amateur_rosters.py` covers CSV/XLSX, leading zeros, retries, invalid/duplicate row preservation, permissions, stale edits, exclusions, source/date gates, disjoint saved proposals, and age/weight/Masters/coed/preference boundaries. The isolated PostgreSQL run covers simultaneous identical uploads. Browser fixtures cover upload, event date, preferences, proposal warnings, exclusion invalidation and mobile layout. Full-file trials use only a temporary database and do not assign the production roster to an assumed event date.
