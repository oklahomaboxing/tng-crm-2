# Event Check-In

Admin and staff accounts have **Event Check-In** in the main sidebar next to Front Desk. Choose an event, confirm its displayed name/date/venue, then use the existing Fight Night Door Scanner. Opening the page or choosing an event performs no admission. Upcoming events appear before past events, and the scanner is unavailable until an event is explicitly chosen. Switching events remounts the scanner and clears the previous result.

The page uses the same authenticated ticket-admission endpoint as the event Tickets dashboard, preserving paid-ticket, activation, wrong-event, refund/void, and duplicate-scan checks. Member, fighter, manager, matchmaker and representative accounts do not get this shortcut; backend ticket admission remains restricted to admin/staff.

For gym members, continue using **Front Desk**. Fight participants' registration, medical clearance and weigh-in processes are separate from admitting ticket holders.

Browser verification uses mocked API calls to check sidebar access, required event selection, correct event ID in a scan submission, clearing results when events change, and no automatic admissions from navigation. No customer ticket is consumed by verification.

## Scan to activate a paper cash sale

Select the event, choose **Activate paper ticket**, and scan its QR. Lookup only displays the ticket, seller and saved face value; it does not activate or admit anyone. After collecting cash, select **Cash received — activate ticket** and confirm the amount. The existing staff cash-sale flow records one order and commission, preserving the same QR. Repeated submissions do not duplicate sales. Return to **Door check-in** for actual admission. Returned/deleted, wrong-event, unknown, already-sold and digital tickets cannot be newly activated through lookup. Digital purchases use verified-payment issuance automatically.

## Owner-authorized offline stock

An administrator can explicitly release a known batch for offline sales, checking its expected quantity. Release marks unsold tickets `released`, preserving their QR codes and inventory reservations. It creates no paid orders, commissions or cash receipts. Released tickets can admit once; a successful scan changes them to `offline_used` and records an admission audit event. Repeat scans fail. Event check-in totals include these admissions, while cash sales and commissions remain separate until staff records actual payment.

The paper-batch panel distinguishes inactive stock, admission-enabled stock without recorded cash, and admitted tickets awaiting cash reconciliation. Recording cash later creates the ordinary paid sale and commission, carrying an earlier admission forward as used so reconciliation never permits a second entry. Unadmitted stock can be returned; admitted stock cannot be returned as unsold. The normal QR activation flow still requires cash confirmation; only administrator-released stock has admission enabled before reconciliation.

The main **TNG BOXING EVENTS** sidebar entry opens an event list and the existing event workspace directly. Upcoming events appear first by default, with search and an option to include past/other events.
