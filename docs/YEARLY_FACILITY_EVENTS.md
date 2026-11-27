# Yearly Events and linked promotions bookings

Facility Management → Venue & Event Bookings → Yearly Events is a separate screen from the monthly calendar and request inbox. Choose a year, month and record type, or search. The list groups dated TNG events and facility reservations/blockouts by month. It reads the existing yearly calendar endpoint; no second annual list is copied or maintained. Undated TNG events are not assigned an invented year.

Use Edit planning event for uncommitted planning/draft events. Names, dates and venue details update the actual BoxingEvent and use a schedule fingerprint to reject stale saves. Events with live status, a linked facility booking, bouts, contracts, ticketing configuration/orders or paper batches are protected. Administrators can open the full event workspace; linked booking changes use Edit / review linked booking. Facility name edits remain versioned and cannot silently change an issued quote's event details.

## Manual booking → TNG Promotions

In Add booking / blockout, select **Also create a TNG Promotions boxing event**. Saving creates the booking and one linked planning BoxingEvent in the same database transaction. The success panel provides **Open event / build show** for administrators. The same link remains in booking review, and the event appears in TNG Promotions. Ticketing, fight cards and contracts are configured in that existing workspace; saving the booking does not send messages, collect payment or issue tickets.

The linkage is stored in the new venue_booking_promotions table (one event per booking, one booking per linked event), created through the existing startup metadata process. Existing booking/event records are not bulk-converted. Request-key retries return the same event rather than creating duplicates. Public customers cannot create a promotions event.

TNG facility events reserve the full start day, while booking confirmation/payment remain separate. Full-day conflicts are checked before either record is committed. Linked booking confirmation and quote acceptance exclude their own event from overlap checks. Planning-only name/date changes stay synchronized through booking review; cancellation/reopening also synchronizes the linked planning event. Live obligations block calendar-driven changes or cancellation. Multi-day bookings retain the normal booking interval, while the linked BoxingEvent uses the booking's start date.

The yearly view displays a linked pair once, with both booking-review and event actions. A carryover booking can still appear when its linked event's start date is in a different year. Existing unlinked bookings continue to work normally.

## Validation

23 backend booking/quote/yearly tests: 22 passed; one PostgreSQL-only concurrency test skipped without an isolated TEST_DATABASE_URL. Coverage includes annual/leap-year ranges, roles, stale edits, live ticketing locks, booking title edits, linked creation/retry, public creation rejection, atomic conflict rollback, self-overlap exclusion, quote acceptance, cancellation and reopening. All 108 frontend tests and the production build pass.

An isolated browser/API walk-through edited a planning event, verified protected editing was disabled, created a manual linked boxing booking, verified one annual entry and the build-show navigation, and checked phone width with no captured browser errors. Sample screenshots contain fixture data. No live events/bookings or customer messages were changed during testing.
