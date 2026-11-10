# Event sales reports and fighter welcome letter

## Sales exports and Oklahoma State Athletic Commission section

Event workspace → Tickets shows **Oklahoma State Athletic Commission — 5%**, paid ticket gross, calculated amount and reconciliation counts. The rate is the promoter's requested 5%. The calculation uses recorded paid order ticket subtotals before seller commissions, excluding fees, pending/failed orders and refunded/partially refunded orders. Partial refunds are flagged for review because a reliable net-refund amount is not stored. Paid orders missing issued tickets still count toward revenue and are flagged. Free tickets contribute zero dollars. Recorded paper cash sales count through their existing paid orders; merely printed or released stock does not.

Rounding is half up once on the aggregate event amount. This is a calculation/export; it does not remit payment or certify that unreconciled sales are final.

**Export all sales PDF / CSV**, **View / print PDF**, and the commission card download buttons use authenticated relative API paths. The old top buttons incorrectly doubled the backend URL; this is repaired. Blob URLs live for 60 seconds for browser download compatibility.

Both exports include event and seller totals, all order statuses, issued ticket ledger and unrecorded paper stock. The PDF includes a supplementary order-reference table, repeating table headers and page numbers. The CSV uses UTF-8 with BOM for Excel and escapes untrusted spreadsheet formulas. Buyer phone numbers, email addresses, QR tokens and ticket access tokens are excluded. Files are private/no-store and staff-only. No email is sent by exporting.

## Fighter welcome letter

In an event workspace, click **Fighter welcome letter**. Save weigh-in time/location, fighter arrival, contact information and additional instructions. Preview the letter, then download a PDF or click **Email letter to booked fighters**. Incomplete schedules may be downloaded as marked drafts but cannot be emailed.

The letter reuses event venue/date and saved doors/first-bout times. It includes general preparation guidance and the event ticket-sales cutoff. It does not change a bout contract, promise a specific purse, or invent missing schedule details.

Recipients are fighters actually assigned to non-cancelled bouts, with validated email addresses, deduplicated by normalized email. Missing contacts are listed for staff to fix. Each recipient gets an individual email with the PDF attached. No recipient list is exposed in another fighter's message.

A preview hash binds sending to the reviewed content and current recipients. Durable unique claims prevent repeat/concurrent sends of the same letter to the same address. Resend receives a stable idempotency key. Unknown submissions are retained for review and never automatically replayed. Provider acceptance is shown as acceptance, not guaranteed inbox delivery. A revised letter can be sent only through another explicit staff action.

Fall Brawl 6 details supplied by promoter: Friday November 13, 2026, 5 PM weigh-ins at TNG Boxing, 8416 NW Expressway, Oklahoma City, OK 73162. Saturday November 14 arrival 3:30 PM, no later than 4 PM. Existing event record: doors 5 PM, first bout 6 PM. All Oklahoma local time.

No live fighter emails are sent during development or verification.
