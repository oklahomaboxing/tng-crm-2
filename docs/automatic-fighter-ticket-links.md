# Automatic fighter ticket links

Creating an event bout now creates missing active fighter seller links for both assigned fighters in the same database transaction. Assignment changes and reactivation of a bout also create missing links. The SQLAlchemy mapper hooks cover the app's normal booking, accepted-offer booking, and ORM import paths without duplicating logic across routes. Bouts without an event and cancelled, void, withdrawn, or completed records do not create selling links; completed/archived/cancelled events are skipped.

Existing seller codes, sales records, payouts, commission settings, contact data, and explicit inactive settings are preserved. Unique `(event_id, seller_type, seller_ref_id)` upserts prevent duplicate seller rows on repeated bookings or updates. Registration is idempotent. A rollback of the bout transaction also rolls back new seller rows. The existing production PostgreSQL unique constraint was verified before deployment.

New links are available in staff Ticket Sales and the linked fighter's portal Ticket Sales section. Fighters can share their event-specific link; paper batches can use the same seller. No ticket email, SMS, invitation, paid order, or admission QR is created by this automation. Customers still receive admission tickets only through the existing verified-payment or authorized paper cash-sale flow.

Event ticket types and prices must be configured once by staff; the automation does not invent prices or new ticket types. Existing booked-bout commission rules apply when purchases are created or paper sales are recorded.

The old activation button remains as **Repair Fighter Ticket Links** for manual backfill and deliberate reactivation of disabled sellers. Automatically creating missing links does not override a staff member's explicit seller disablement. Removing a fighter or cancelling a bout does not delete their historical seller or sales records.

Validation: six automation regressions verify API booking and fighter-portal visibility, import/assignment paths, repeated registration and updates, transaction rollback, cancelled/unassigned bouts, preservation of disabled sellers and existing codes, and public-checkout fighter attribution. The 32 ticketing and seven paper-ticket regressions also pass, along with the frontend production build.
