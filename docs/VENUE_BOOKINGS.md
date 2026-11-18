# Facility booking workspace

Admins open **Boxing & events → Venue & Event Bookings**. No coordinator account is created automatically. When someone is assigned, create an **Event Coordinator** account under User Management; they share the same calendar and inbox with admin, with access restricted to booking tools and their own account security.

Public request link: `https://tngos.tngboxinggym.com/venue/book` (hash fallback: `/#/venue-booking`). The form requires event details, local Oklahoma City start/end times, organizer name/email/phone, expected guests and an acknowledgement that submitting is not confirmation. It returns a reference, without creating a member, ticket sale or login. No payment is collected or email sent by submission or review.

## Calendar and review

- Month/day calendar, TNG event entries, request inbox, shareable link and public-form on/off switch.
- Admin/coordinator can add an internal request for a rental, TNG event or maintenance blockout, then review it to place a hold or confirm.
- Requested dates are not reserved. **On hold** and **Confirmed** reserve the interval. Declined and Cancelled release it.
- Review shows contact details, event needs, staff notes and editable start/end times. Rescheduling and status changes use optimistic versions and repeat overlap checks.
- Existing non-cancelled boxing events at TNG Boxing / 8416 NW Expressway block the facility for their date. Other/unspecified venues appear for planning without reserving the gym. A later change in the boxing-event editor can create a conflict with an existing facility booking; the coordinator should review the shared calendar when changing TNG event dates or venue.
- No rental price, capacity approval, refund policy or payment status is inferred. Staff agree pricing, permitted attendance and terms with the organizer.

All input times use America/Chicago, independent of the device timezone. Stored times are UTC, with explicit display in Oklahoma City time. Invalid or ambiguous daylight-saving times are rejected.

Public availability exposes occupied intervals only; organizer contacts, event names and staff notes require admin/coordinator authorization. Requests are rate limited using atomic database counters. A honeypot and idempotency keys reduce spam and duplicate submissions. PostgreSQL calendar advisory locks serialize holds, approvals and settings changes; competing confirmations cannot both reserve overlapping time. Internal changes are audited. Existing fight records, memberships and ticket workflows are reused without altering their records.

## Checks

`backend/tests/test_venue_bookings.py` covers privacy, coordinator isolation, public shutdown, retry keys, holds, cancellation, overlap prevention, stale updates, venue-aware boxing events, rescheduling, validation, throttling and admin-only coordinator account creation. The isolated PostgreSQL run additionally tests simultaneous confirmations. Browser fixtures cover calendar/inbox review, Oklahoma City times, public submission/reference and mobile layout; no real bookings or messages are created by these tests.
