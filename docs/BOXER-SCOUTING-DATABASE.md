# Nationwide boxer scouting database

Promoter → Boxer database is a separate prospect catalogue, not the active
boxing_fighters roster. Staff can browse, search, filter, review and shortlist
prospects without creating bookings, offers, contracts, or outreach messages.

## Coverage and growth

All 50 states plus DC are supported. The 19 research weight labels include
atomweight through heavyweight, plus bridgerweight; these are research buckets,
not a certification of the athlete's division or a commission's supported classes.
A prospect's actual reported weight and source excerpt remain visible. Unknown
weights are stored in the unknown bucket. Explicit single-weight mismatches and
BKFC/UFC/Sherdog record sources are excluded from automatic batch saves.

Find & save prospects searches one chosen group or sequentially searches all
groups, saving up to eight sourced results per request. A selected state narrows
research; otherwise the search is nationwide. Stop halts after the current request.
Already saved records remain if the page closes or the research stops. Re-running
skips the same normalized name/state/source identity without overwriting shortlist
status or staff notes. Different-source potential duplicates need human review;
this is not an exhaustive licensed registry or an automated current-record service.

## Choosing prospects

Filter by name, source-reported record, city/gym, state, research weight group,
review status, or presence of published contact information. Lists are paginated.
Shortlist records to select prospects. Open a row to read the original source,
set review status, record staff-confirmed availability, and add bout/follow-up notes.
Nothing in this workflow sends an email, text, offer or booking.

Only authenticated admin/staff/matchmaker roles can access the catalogue.
The table boxing_scouting_prospects is created by the existing application metadata
startup workflow. Existing fighter records and ticket/payment tables are unchanged.
Search uses the existing server-side web-search provider and source validation.
Contact details remain unverified research; unquoted contact strings are omitted.

## Validation

Regression tests cover role isolation, nationwide options, all research groups,
separation from the roster/bouts, URL and state validation, same-source duplicates,
pagination and filtering, manual shortlist/availability updates, contact evidence,
weight mismatches, and rejected non-boxing combat-sport source domains. Tests run
on SQLite and the dedicated local PostgreSQL database. Browser fixtures exercise
listing, shortlist persistence, review, sequential research and mobile overflow.
Live population must be reported with actual counts, empty groups and failed
requests; no test fixtures may be written into production.
