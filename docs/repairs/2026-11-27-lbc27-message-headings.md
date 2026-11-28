# LBC 27 work-message headings

New outgoing club work texts use `LBC 27 Boxing Clubs: `; official work texts use `LBC 27 Boxing Officials: `. Preview and send share the same content builder. Inbox replies use the corresponding label from the conversation's server-resolved folder, including saved routing overrides. Gym and venue replies retain their existing TNG Boxing heading. UI composer/reply guidance reflects the label.

The existing STOP footer is appended as before. No message history, contact permission, opt-outs, routing assignments or provider configuration is rewritten, and no contacts were messaged as part of this change. Existing open previews whose content hash includes an old heading need a refreshed preview before submission.

Verification: 31 work-text/inbox tests passed with mocked Twilio. Assertions cover club and official preview and send headings, corresponding inbox reply labels, preserved gym/venue labels, STOP footer, permissions, stale previews, idempotency and uncertain provider submissions. Production frontend build passed.
