# Bulk recording of existing SMS permission

Marketing Center → New member text → select the intended contacts → **Record signup SMS permission for selected**. Review the common consent evidence once, then press **Record permission for all selected**. The signup Subscribe selection must explicitly cover SMS; email-only subscriptions are not SMS permission.

This records a staff attestation of permission already given. It does not send a text or automatically select every CRM contact. The batch is limited to 5,000 selected IDs and applies to all selected contacts even when only the first 100 are displayed. Staff may still record permission individually.

Results report newly recorded, already recorded, opted-out, invalid-number, inactive and missing contacts. STOP suppression applies by normalized phone, including duplicate contact rows and the global hashed suppression list. A bulk or individual action cannot override a STOP. The member must opt back in through START before new permission is recorded. Repeating the same action does not duplicate consent changes or audit entries.

Each batch audit records the staff user, timestamp, affected contact IDs, evidence and counts. Existing consent is not transferred to a changed phone number; existing audience-sync protection remains.

Twilio message-purpose approval remains independent. Recording permission does not approve promotional campaigns or change a sender's approved use case. Actual campaign sends retain the existing review step and maximum of 500 recipients per campaign.

All application-generated outgoing SMS now use the same ending: **Reply STOP to unsubscribe.** This covers the generic sender, ticket texts, renewal/expired reminders and marketing campaigns. Existing standard STOP lines are normalized so the footer appears once. Recording permission sends no message.
