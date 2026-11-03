# TNG Assistant

Open TNGOS and choose **TNG Assistant** under Command. It is the default admin landing page unless **Open TNG Assistant automatically after login** is switched off. It reports live saved membership totals, today's attendance in Central Time, paid ticket quantities and gross paid totals, pending checkouts, paper tickets awaiting recorded sales, saved fight-card progress and the operations work queue. Select an event or mention its exact saved name. No provider reconciliation runs simply by asking a question.

Type a question, select a suggested question or press **Ask by voice**. For hands-free questions, press **Enable “Hey TNG”**, allow microphone access, then say **Hey TNG, how are we today?** The first microphone permission requires browser interaction. An enabled assistant stays mounted while navigating admin workspaces; the floating TNG Assistant button shows its listening state. It pauses recognition when the browser tab is hidden, avoids reading its own answers back as questions and stops on logout. Screen-locked/background listening is not guaranteed by browser speech APIs. Chrome on a computer or Android is recommended; typing works without speech recognition. No native always-listening application is installed or substituted for InBody software.

The browser's speech services may process audio. TNGOS does not store recordings or question transcripts. Speech replies use the device/browser text-to-speech service. Voice opt-in and assistant landing/audio preferences stay on this device. Standard report questions do not require an AI API call. For unfamiliar wording, the configured `OPENAI_ASSISTANT_MODEL` (default `gpt-4.1-mini`) selects a report topic; numbers and narrative facts are generated from server-side reports, not model-written financial claims. Missing paid-ticket quantities are flagged rather than guessed. The assistant is admin-only and reports information; it has no customer messaging, purchasing, billing or record-editing tools. Requests are limited to 20 per account per minute.

## Stay signed in

The login form defaults **Stay signed in on this trusted device until I log out** on. Uncheck it on shared devices. Existing signed-in users can enable the same setting inside the assistant without logging out first. Turning it off rotates back to the standard 30-minute session.

Remembered sessions are signed, credential-bound JWTs with a 100-year technical expiration and a separate revocable device identifier stored as a SHA-256 hash. They are not extended to unauthenticated users and do not bypass MFA. Explicit logout revokes the remembered token on the server; password or role changes, account deactivation and Security Center session revocation still invalidate access. Expiration handling avoids JavaScript timer overflow on long-lived tokens. Other open tabs clear their UI after logout. Logout clears cached private data while retaining device preferences and any separate restricted kiosk pairing.

No existing production login is silently replaced. To retain an existing session, enable **Stay signed in** in Assistant & device settings. Next logins can use the checked login option. A device may still lose its session if browser storage is cleared.

Session conversion preserves the credential binding validated on the incoming request, so a concurrent password change or session revocation cannot be bypassed by converting to remembered sign-in. MFA remains mandatory when enabled, including remembered-device password logins.

## API funding

Broader language routing requires a funded OpenAI API account. ChatGPT Plus does not include API credits. A provider `credit_balance_exhausted` or `insufficient_quota` response shows a clear in-app notice while standard live report questions continue to work. Add funding in the connected API organization's billing settings and retry an unfamiliar question; no application redeployment is required. Never paste API keys into chat.

## Validation

Backend regressions cover admin-only access, correct membership reporting, paid versus pending/refunded/paper ticket separation, model output isolation, provider failures, rate limiting, remembered-session logout and credential revocation. Browser tests use synthetic microphone/speech services and fixture responses to verify wake handling, navigation, stop behavior and persistent-token timing without speaking private data or mutating real customer records. Actual microphone recognition depends on the chosen physical device and browser.
