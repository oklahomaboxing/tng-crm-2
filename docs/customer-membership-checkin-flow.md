# Customer accounts, memberships and member check-in

## Accounts

Members opens gym memberships by default. The Contacts and All Contacts & Members filters retain the combined directory. Profiles without a name and usable email are excluded from gym membership totals even if they have a saved active flag. Fight-ticket purchases never create a gym membership, including miscategorized ticket products. Clover sales sync requires a recognized, explicitly configured gym product; unknown orders and amounts matching membership prices are not sufficient. Existing sales and ticket records remain available.

Contacts with a name, usable email and telephone number receive a restricted, active member-portal account. Account access is separate from gym membership eligibility. Existing passwords, disabled accounts and non-member staff/fighter/admin roles are preserved. Shared emails and matching names/phones across different profiles require ownership review. A unique contact must not take over another person's login.

New prepared accounts have a random unusable password. Customers choose their own password via **First time here or forgot your password?** on the login page, or the staff **Send Password Setup** action. Bulk account preparation does not send bulk emails. Admin creation has an explicit password-setup email checkbox. Existing valid invitation links continue to work for unclaimed prepared accounts; claimed accounts and password changes invalidate the claim path. No default passwords are distributed.

Customer-directory reconciliation prepares accounts automatically in small committed batches. **Connect Customer Accounts** prepares existing profiles immediately and honors existing recorded nonstandard monthly rates. Account creation never marks a customer as a paid gym member.

**Members → Merge Duplicates** shows matching profiles after sync. Email matching ignores spaces/case; telephone matching ignores formatting and the US country prefix. Review the two cards and press **Merge** once, with no confirmation popup. Matching email, telephone or Clover identity permits the administrator's explicit merge even when names or birthdates differ. Sync does not silently merge shared-family contact details. Alternate buttons choose which profile's contact details to keep.

Merges retain sales, attendance, Clover purchase details, old member numbers and Clover customer aliases. The later recorded membership term and its applicable agreed rate survive without creating sales or adding time. Both member login identities retain their passwords and reach the combined profile. Disabling the primary portal account also blocks alternate login access. Superseded photos, setup markers and rates are retained in database audit snapshots. Unused invitations from the former profile are invalidated to prevent them claiming the kept login; customers can use password reset. The merge is transactional and retrying the same completed pair does not merge twice. Only administrators can merge profiles.

## Admin-created memberships and agreed rates

**Add Member → Create Active Member** creates the profile, member number, account access and active term in one action. Staff enter plan, agreed rate and months. Default is $150 for 30 days; other amounts and multi-month terms are supported. This administrative assignment records no sale and charges no card. Money received is recorded separately in Sales. Recording the first payment for a newly admin-activated term covers that term rather than adding a free extra month; later renewals extend normally.

**Member Profile → Membership & Rate** assigns a negotiated rate and can explicitly activate a term. Leaving activation unchecked preserves existing expiration dates. The assigned plan/rate is stored server-side and shown in the member's renewal checkout; customer-supplied prices are ignored. Assigned members cannot switch product IDs to bypass their agreed plan. Existing recorded custom monthly rates are preserved without guessing from order totals, extending terms or replaying payments. Cash/retail purchases do not become memberships merely because the customer has an account.

Configured plans retain their explicit term, including plans whose names include “Annual” but are billed monthly. Zero-price assigned memberships are managed at the front desk rather than submitting zero-value Clover charges. Existing external Clover subscriptions are managed separately; this feature controls TNGOS renewal checkouts.

## Purchases

Customer **Purchase History** and staff **Payments** show saved Clover item descriptions and quantities, payment totals and refund metadata. Background reconciliation caches descriptions from merchant orders without altering payment, amount or sale-product records. Unnamed Clover items are explicitly labeled; no invented purchase description replaces them. Orders split across different member profiles are not cached as one person's complete order. Portal endpoints only return the signed-in member's records. Older item descriptions fill progressively as Clover orders are read; available saved TNGOS product descriptions remain visible meanwhile.

## Check-in

**Member Check-In** replaces the old Front Desk workspace. Authenticated staff use the new number keypad and signup QR with their existing staff authorization; no device pairing is needed for this staff workspace. Staff sessions are retained. The old `#/front-desk` bookmark resolves to the new workspace.

Both `/check-in` and `/kiosk/checkin` use the new public entrance kiosk. The signup QR is visible even before pairing. The physical public device uses its restricted one-time pairing, never an administrator login. The old camera scanner component has been removed. Fight-night ticket scanning remains separate.

The same attendance service records manual staff check-ins and paired device check-ins, with duplicate protection. Success clears after 8 seconds and errors after 5. Only inactive/expired membership errors receive the membership-inactive message. Public success shows only first name and status. No camera permission is requested by the new member check-in page.
