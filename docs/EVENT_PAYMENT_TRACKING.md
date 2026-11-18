# Event purse and commission payment records

Open an event's **Purses & recap**. Overview shows each current-card fighter's purse and ticket commission as separate statuses: Paid in full, Partially paid, Unpaid, Not recorded, On hold, Nothing due, or Overpaid / review. Commission costs and earned commissions are not proof of payment.

Select **Update purse** or **Update commission** to open the correct record directly. The payment tabs can be searched and filtered by payment status. Zero-due seller records are hidden by default and can be included using the filter.

- **Set total already paid** sets the cumulative total. It does not add that number to earlier records.
- **Add another payment** adds an actual payment to the previously known total. It is disabled when the starting total is unrecorded.
- **Use full amount due** fills the cumulative obligation; review and confirm only after the money was actually paid.
- Enter the actual payment date when known. A blank date stays unknown; the recorded-on timestamp is separate.
- Use the reference field for cash/check/bank details or correction explanations. No payment method is inferred from a note.

A confirmation identifies the fighter, payment kind, previous total, new cumulative total and actual payment date. Saving is bookkeeping only: no bank, Clover or other transfer is initiated. Concurrent edits are rejected using the existing purse version and commission snapshot checks.

**Place purse on hold** records a reason such as pending approval independently of both the contract and paid amount. Clearing the hold does not pay the purse. A fully paid purse with an active hold is flagged for review; existing payment history is preserved. Holds do not remove agreed obligations from event costs or increase the event's recorded profit.

**Payment history** shows cumulative revisions, actual payment dates when recorded, actor names when available and recorded-on times. Do not sum its cumulative totals as separate payments. Existing purse snapshots are preserved as a baseline before the first correction under this feature. Existing commission snapshots remain the source of commission history. The most recent 50 revisions are shown. PDF/CSV recap exports include a separate payment-status section.

The fighter's existing cost/ticket profile also shows their own recorded purse and commission statuses and paid amounts. It does not expose internal hold reasons, payment notes, staff history, other fighters' payment records or customer details. Payment editing and history endpoints remain staff/admin only.
