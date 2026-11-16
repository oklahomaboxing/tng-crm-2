# Fighter bout cost and ticket sales

The **Bout cost & ticket sales** panel appears in:

- Promoter → edit a fighter profile (administrator/staff financial access).
- The fighter's own portal, immediately above Ticket Sales & Commission.

Choose an event to keep the profile compact. Each assigned event shows paid ticket quantity and sales credited to that fighter, recorded direct bout costs, and ticket contribution. Expand Cost breakdown for gross purse, travel/per diem, deductions, net obligation, recorded purse payments and ticket commission cost.

The calculation reuses the event recap's current-card fighter row:

`paid ticket sales − (net purse/allowance obligation or higher recorded purse payment) − (earned ticket commission or higher recorded commission payment)`

A positive figure means sales exceeded recorded direct costs; a negative figure means sales fell below them. The display uses neutral above/below-cost descriptions. It excludes venue, officials, insurance, state assessments and separately recorded vendor costs, so it is not the final event profit. Pending and refunded orders are not counted as paid sales. Partial refunds, missing issuance, unsigned terms and unrecorded purse payments receive review notes.

Cancelled/removed bouts are excluded, consistent with the current-card recap. Completed bouts remain part of event history if still on the event card. Restoring a fighter to a card restores their saved contribution data. Changes to existing purse or commission records appear on refresh; this panel itself is read-only and sends no messages or payments.

`GET /api/events/fighters/{fighter_id}/contribution` allows admin/staff or the fighter login linked to that exact fighter ID. Other fighters, managers, members, reps and anonymous visitors cannot access it. Responses include no opponent finances, customer contacts, QR tokens, private payment notes or event-wide financial totals. All responses are private/no-store; event history is paginated, 20 events by default, at most 50 per request.

## Both-corner comparison

The profile now compares the fighter's own credited ticket sales with the **combined costs of both red and blue corners**. The breakdown shows own direct cost, aggregate opponent direct cost, and combined bout cost. This aggregate opponent cost is intentionally visible to that bout's fighter as requested; other opponents' private payout notes or individual contract details are not returned.

The original per-fighter accounting fields remain available for compatibility. New fields `combined_bout_cost_cents`, `combined_bout_contribution_cents`, and `combined_bout_outcome` drive the new display. The response advertises `cost_scope: both_corners` and `ticket_sales_scope: this_fighter`. The frontend waits for this scope before showing the updated calculation during deployment.

Both participant profiles may show the same bout cost. Do not sum those profile comparisons into event expenses. The event recap continues counting each fighter's costs once. If an opponent also has unrelated bouts on the same event, combined costs are left unallocated rather than overstating this bout's cost; the display asks for allocation review.
