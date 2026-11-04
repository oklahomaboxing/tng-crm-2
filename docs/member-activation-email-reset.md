# Correct and resend an unactivated member invitation

Open Members, select the member, and choose **Reset email & resend activation**. Enter the corrected address (or keep the same one), then choose **Save email & send activation**. Admin/staff access is required. The control is only offered for unactivated accounts or prepared portal accounts still awaiting password setup. Activated accounts must use the existing account-management/password-reset workflows.

The server checks for another member/profile/login using the normalized email, updates the member and their own prepared login together, expires previous unused links, and sends a new seven-day invitation using the existing sender. There is no seven-day wait to correct or resend an invitation. Memberships, custom rates, purchases and attendance remain untouched. The browser prevents repeat submits while processing. A provider rejection rolls back the corrected email and old-link invalidation. The action is audited without storing addresses or activation tokens in the security log. Activation and invitation reset lock the member first to serialize competing requests.

Tests mock email delivery; no real customer's invitation was reset or sent during verification.
