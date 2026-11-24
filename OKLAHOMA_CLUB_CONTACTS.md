# Oklahoma Boxing Clubs

Administrators and staff open **Oklahoma Boxing Clubs** from its own dashboard card, beside USA Boxing Officials, or the Boxing & events sidebar. Direct route: `/#/oklahoma-boxing-clubs`.

This workspace reuses the club directory. It shows Oklahoma clubs, accepting both OK and Oklahoma in saved state values. Each club shows its contact person and existing phone/email links. **Edit club / contact** updates the contact person/head coach and contact details; **Add club** starts a new club with OK selected. Search includes contact names. Clubs without a saved state do not have a location inferred.

The optional directory API state filter applies before pagination; existing unfiltered consumers retain all-state results. The existing contact_name detail field is reused, including imported contacts. Explicitly clearing that field is supported; omitted fields and original imported observations are retained. This does not create membership accounts, grant texting permission, verify credentials, or send messages.
