# Event recap and payment records

Open an event, choose **Business → Event Recap** (also on the Finance home card).
Only administrators and staff can access this financial workspace and its API/exports.

- **Paid Purses:** enter the total already paid to each fighter for this event, an optional payment date and a note/reference. Save again to correct the cumulative total. These entries do not edit a signed contract or transfer money. Blank means payment status has not been recorded; enter zero to explicitly record no payment.
- **Ticket Commissions:** a separate cumulative payment record per seller. Saving appends a payout snapshot and updates the existing seller payout balance. Historical snapshots are retained, not added together as if they were separate transfers.
- **Expenses:** edit actual amounts in the existing Expenses page. Recap treatment can identify costs already counted in purses/commissions, or exclude an amount, without changing its source record.
- **PDF / CSV:** download the recap, payment information and review notes. Downloads do not email anyone.

The result uses recorded paid ticket subtotals and PAID sponsor/vendor receipts, minus net purse obligations (including travel/per diem and deductions), earned seller commissions, the state assessment and actual expenses. If recorded payments exceed an obligation, the higher payment is counted as cost. Customer checkout fees are displayed separately. The state assessment defaults to the existing 5% calculation until an actual assessment is entered; it is an estimate, not a filing determination.

Unsigned drafts, missing expenses, unreconciled paper sales and partial refunds produce review notices. Cancelled bouts do not automatically incur a full purse; recorded payments remain included. Review cancellation settlements separately. Hotel/medical deductions reduce the net fighter payment; related vendor costs must be entered separately once.

This is a recorded event result, not a bank balance or a guarantee that all costs are present. No historical purse payments are inferred from the contract's calculated `boxer_paid` field. All new payment and expense-classification writes create security audit entries and reject stale versions with HTTP 409.
