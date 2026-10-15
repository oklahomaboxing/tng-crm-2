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

### Research reliability repair

The default UI source is now **Official promoter profiles**, which reads public
Top Rank, Golden Boy, Matchroom and Red Owl directories and profiles without OpenAI credits.
Only source-reported US hometowns and recognized boxing weight labels are imported.
Hometowns do not establish current residence; profile presence does not establish
current activity or availability. General promoter office contacts are explicitly
identified in evidence. Golden Boy's zero placeholder counters are omitted; actual published animation target values supply records when present.
Existing same-name/state records retain their reviews. Public profiles are cached
for one hour per process; requests follow only the fixed publishers, without redirects.

Broader web research remains optional. It retains source citations before extracting
structured facts. Exhausted API credits return an actionable error without exposing
provider credentials. User research focus is preserved instead of being truncated
by the boilerplate prompt.

Research starts with HTTP 202 and runs in a background worker. Progress and errors
are stored in `boxing_scouting_research_jobs` and polled by the UI. One shared job
runs at a time; leaving the page does not cancel it. Stop takes effect after the
current group. Jobs interrupted by a deployment become visibly interrupted after
five minutes without progress; saved prospects remain intact. This is not a durable
queue that automatically resumes work after process termination.

Beginner (0–5 reported pro bouts) and developing (0–10) filters use explicit source-reported records, including documented debut results. Unknown records are excluded from these filters. The Texas / Oklahoma / New Mexico filter and Dallas/Houston city search narrow the view without deleting other findings.
