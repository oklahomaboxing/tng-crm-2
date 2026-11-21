# USA Boxing Officials work communication

Administrators and staff can open **USA Boxing Officials** from the dashboard or Boxing & events sidebar. The direct route is `/#/usa-boxing-officials`.

The workspace reuses directory contacts and the private Text Inbox. Staff can add an official, record documented work-text permission, select recipients, compose a message, preview the exact text and recipients, and confirm its work-related purpose before submitting. Adding a contact does not certify their assignment roles or grant texting permission. Event-specific availability and qualification checks remain in Amateur Matchmaker.

Messages use the existing approved notification service, include a STOP footer, respect global opt-outs, and share existing delivery callbacks and inbound conversations. Provider acceptance does not establish delivery. Conversations are available from each contact and Text Inbox.

Submission keys and message records are persisted before provider calls. Replaying a submission returns its recorded status without sending again, including uncertain submissions. Review unknown/submitting messages against provider records before considering a new submission. Limits are 50 selected recipients and 50 outgoing messages per staff member per hour. Contacts and permission are checked again before each provider call.

No new database tables, account creation, or contact certification changes are required. Automated tests mock provider calls; production verification must not send messages or infer permission.
