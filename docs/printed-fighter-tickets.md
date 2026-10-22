# Printed fighter tickets

In Event Ticket Sales, use **Print paper tickets**. Choose an active fighter/seller, ticket type, and quantity (1–200), create the allocation, then download its PDF. Print US Letter at Actual Size / 100%; six tickets fit per page. Each ticket carries event information, its face value, seller, unique ticket number, and a private admission QR. Reprinting preserves all ticket numbers and QR codes. Copies cannot create additional admissions.

## Sales and returns

Printed tickets begin **unsold / inactive**. They do not create paid orders, admission tickets, or commissions. Staff must select the exact ticket numbers and record the full face-value cash sale before customers arrive. This is a staff attestation of customer cash payment, not a Clover verification or card charge. The same QR is activated by creating one paid `paper_cash` order and one valid issued ticket. Repeating a sale request creates no additional order, commission, or admission.

Customer payment to a fighter is not proof that the fighter remitted money to TNG. Keep remittance records separately; the batch totals are not a cash settlement or payout balance. Price and commission are snapshotted at allocation using existing negotiated fighter/bout rules.

Unsold tickets can be returned. Their QR codes become invalid permanently and they are excluded from later PDF downloads. Sold tickets cannot be returned through this flow. Handle refunds separately. The door scanner rejects inactive, wrong-event, returned, and duplicate tickets. The scanner now submits the selected event ID, which it previously omitted.

## Data and security

Only admin/staff operations accounts can create, print, sell, or return batches. Raw QR credentials are only included in the authenticated PDF; list/detail APIs do not expose them. PDFs are private and not cached. New allocation/sale/return actions are audited. Allocation requests use UUID idempotency keys; batch row locks serialize sales and returns. No email or SMS is automatically queued for paper cash sales.

Two new tables (`paper_ticket_batches`, `paper_tickets`) are registered before the existing startup metadata creation. Existing online tickets and signed contracts are unchanged. Creating a batch checks its configured inventory against currently valid/used tickets and unsold paper allocations. This change does not add a reservation/expiry system to the existing online checkout; monitor combined allocations for limited-capacity seating.

The order recovery dashboard identifies manual paper cash orders, includes recorded sales/commissions, and does not flag missing email/text delivery for a customer holding a paper ticket.

## Validation

Six paper-ticket regression tests plus 30 ticketing and 20 stabilization tests pass. The frontend production build passes. Browser fixtures verify allocation, exact selected sale totals, a single sale submission, the selected event in door scans, and decoding a QR from the rendered PDF. A seven-ticket sample spans two US Letter pages. All validation uses synthetic records; no live batch is created, cash sale recorded, or customer notification sent by deployment verification.
