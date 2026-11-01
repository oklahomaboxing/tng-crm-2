# Membership directory and contact consolidation

The Members list defaults to recorded gym memberships. Customer-only profiles remain accessible under **Contacts** and **All Contacts & Members**. “Pending” is no longer a membership filter or roster badge. Internal checkout/profile activation states are retained; no contact is granted paid membership access simply to remove a label.

- **Active** includes current active memberships, including those expiring soon.
- **Expiring** is the subset of Active ending within the next seven days. Do not add Active and Expiring together.
- **Expired** means the saved membership end timestamp has passed, including less than one day ago.
- **Inactive** means a recorded membership disabled/cancelled without a past end timestamp.
- **Contacts** have no confirmed membership record; importing a Clover customer is not a membership payment.
- **Membership review** covers a saved paid/recorded membership whose current status needs staff verification.

Membership evidence comes from non-refunded paid membership-product sales or explicitly recorded membership start and term/plan. Bare legacy “active” defaults without membership evidence do not count. The directory, member details, dashboard and System Overview use the same server-side reporting function. Naive stored timestamps are interpreted as UTC in the browser; display dates use the browser's local timezone.

**Consolidate Contacts** only merges unambiguous customer-only duplicates into an existing profile: matching complete name and normalized phone; matching email or a missing canonical email; no conflicting birthdate; exactly one eligible target; no linked source records. Conflicting emails, different family members sharing contacts, paid duplicate profiles, portal accounts and linked histories require individual Duplicate Review.

Original profile snapshots and card/Clover identifiers are retained in `consolidated_member_contacts`. Old member numbers and QR values resolve to the canonical member, old staff profile URLs resolve to it, and subsequent Clover customer imports and sales sync use the saved Clover aliases. Canonical numbers and populated contact fields are preserved. A consolidation creates no sales, invitations, customer messages or check-ins.

Individual same-person merges preserve payment, attendance, invitation, InBody and other member-linked records by moving their foreign keys within one transaction. Two portal accounts or other conflicting unique records block the merge. Conflicting birthdates or different names also block it. The later recorded membership term is retained without replaying sales or adding invented membership time. Both profile snapshots and moved row IDs are archived, and the action is recorded in the security log. Merging does not refund payments, recreate them or change user passwords.
