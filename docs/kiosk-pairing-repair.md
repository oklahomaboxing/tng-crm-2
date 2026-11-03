# Kiosk pairing repair

Open **Check-In Kiosk**, select the named entrance device, and use **Connect screen**. A connected kiosk does not need another code. For a new/replacement connection, create a code and either enter it on `/kiosk/checkin` or copy the setup link to the physical entrance device. Press **Connect kiosk** there. Using the current browser for the kiosk will sign it out of administration; device authorization remains limited to check-in.

Codes are single-use, expire after ten minutes, and are displayed only in the selected device's setup panel. The countdown uses the server expiration. A setup link carries the code in a URL fragment, not a query string; the kiosk removes the fragment after loading and waits for explicit submission. A failed replacement does not erase a previously saved kiosk credential. Clipboard-disabled devices can use the displayed code. Spaces and hyphens in copied codes are accepted by the server.

Creating a replacement code does not revoke a working device. Redeeming it rotates the device credential. Admin status polling distinguishes a pending pairing from the old device's continuing heartbeat, and reports completion only after the pairing code is consumed. Paused devices must be enabled in Settings before issuing a code. Revoked credentials no longer appear online just because their old heartbeat was recent. Newly added devices require a distinct, nonblank name; existing records and attendance are retained.

Settings and today's activity are separate from setup. All attendance times use Central Time. Network errors and timeouts are visible. Staff can disconnect a device explicitly from Settings, with an explanation that reconnection will require a new code.

The kiosk rate limiter uses atomic database upserts. The previous update/check/insert sequence could return a false 429 if another concurrent request created the bucket between checks. Limits are unchanged, while concurrent valid requests no longer encounter that race. PostgreSQL regressions cover concurrent kiosk/front-desk attendance and single-record duplicate protection.

No production kiosk has to be revoked or re-paired merely to install this repair. Existing paired screens continue using their saved restricted credentials. Browser tests use fixture codes and credentials; real staff pairing secrets are not printed in logs or documentation.
