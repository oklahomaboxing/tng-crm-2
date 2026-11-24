# Oklahoma Boxing Clubs

Administrators and staff open **Oklahoma Boxing Clubs** from its own dashboard card, beside USA Boxing Officials, or the Boxing & events sidebar. Direct route: `/#/oklahoma-boxing-clubs`.

This workspace reuses the club directory. It shows Oklahoma clubs, accepting both OK and Oklahoma in saved state values. Each club shows its contact person and existing phone/email links. **Edit club / contact** updates the contact person/head coach and contact details; **Add club** starts a new club with OK selected. Search includes contact names. Clubs without a saved state do not have a location inferred.

The optional directory API state filter applies before pagination; existing unfiltered consumers retain all-state results. The existing contact_name detail field is reused, including imported contacts. Explicitly clearing that field is supported; omitted fields and original imported observations are retained. This does not create membership accounts, grant texting permission, verify credentials, or send messages.

## Club work messages and replies

The workspace now has **Club contacts**, **Message clubs**, and **Club inbox** tabs. Each directory card includes **Message club**, which opens the composer for that contact. Record documented work-text permission, select up to 50 eligible clubs, compose event/availability/logistics text, review recipients and the exact STOP-footer message, and confirm its work-related purpose before sending. Some imported numbers are office lines; staff must confirm SMS capability and permission. Importing contacts never opts them in.

Club texts reuse the existing work-text engine, approved notification service, durable InboxMessage records, opt-out suppression, callbacks and shared staff rate limit. Scope `clubs` restricts recipient selection, permission changes and history to Oklahoma club records. Submission keys and audits distinguish club batches from official batches. Unknown submissions are not retried by replaying the batch.

Club Inbox filters conversations by normalized phone numbers stored on Oklahoma clubs. It shows club names without treating an organization number as authenticated personal identity. Names/club searches and manual read controls remain available. A number shared by a club and an official remains one SMS conversation and may appear in both relevant views; no history is copied or split. Club conversations also remain available in the general inbox. Switching club tabs is disabled during submission to avoid losing an in-progress send or reply.

The main dashboard also has a **Venue & Event Bookings** card that opens the existing booking workspace.
