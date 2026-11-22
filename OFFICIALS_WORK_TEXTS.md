# USA Boxing Officials work communication

Administrators and staff can open **USA Boxing Officials** from the dashboard or Boxing & events sidebar. The direct route is `/#/usa-boxing-officials`.

The workspace reuses directory contacts and the private Text Inbox. Staff can add an official, record documented work-text permission, select recipients, compose a message, preview the exact text and recipients, and confirm its work-related purpose before submitting. Adding a contact does not certify their assignment roles or grant texting permission. Event-specific availability and qualification checks remain in Amateur Matchmaker.

Messages use the existing approved notification service, include a STOP footer, respect global opt-outs, and share existing delivery callbacks and inbound conversations. Provider acceptance does not establish delivery. Conversations are available from each contact and Text Inbox.

Submission keys and message records are persisted before provider calls. Replaying a submission returns its recorded status without sending again, including uncertain submissions. Review unknown/submitting messages against provider records before considering a new submission. Limits are 50 selected recipients and 50 outgoing messages per staff member per hour. Contacts and permission are checked again before each provider call.

No new database tables, account creation, or contact certification changes are required. Automated tests mock provider calls; production verification must not send messages or infer permission.

## New replies and the shared inbox

Admin and staff screens show a Messages shortcut with the shared unread SMS count. While TNGOS is visible, it checks `/api/messages/summary` every 15 seconds and refreshes on focus, returning to the tab, or marking a conversation read. The summary returns counts and the latest unread ID only. New unread replies produce an in-app alert with an Open inbox action; pre-existing unread messages also alert on sign-in. Failed checks are shown as unavailable instead of silently implying no new messages.

Text Inbox contains all SMS threads, refreshes every 15 seconds, and supports unread-only filtering. Mark conversation read clears the shared unread state through the displayed message ID, leaving later arrivals unread. These are in-app notifications while TNGOS is open, not background phone push notifications. Reading or checking counts does not send texts.
