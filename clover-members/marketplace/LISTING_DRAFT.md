# Clover App Market listing draft — TNG Members

Status: owner review / developer registration required; not submitted or approved.

**Name:** TNG Members

**Short description:** Manage TNG Boxing member profiles and attendance directly on Clover Station Duo.

**Description:** TNG Members puts the gym's front-desk member workflow on its Clover POS. Authorized TNG staff can find a member by name or short member number, view membership status and recent attendance, update basic contact information, display a QR membership card, and check members in using the Station Duo's native scanner or typed number. Membership eligibility and attendance stay synchronized with TNGOS. An active TNG staff or admin account and an internet connection are required.

**Initial supported device:** Clover Station Duo. Station Duo 2 compatibility requires its own hardware validation before listing it as supported.

**Intended merchant:** TNG Boxing. This build is connected to TNG's existing single-gym backend. It is not a multi-merchant CRM service. Start with a designated test/private merchant installation; do not advertise general support for unrelated merchants.

**Support:** marketing@tngboxinggym.com · +1 405-959-5823

**Website:** https://tngos.tngboxinggym.com

**Price / billing plan:** Owner decision required. No Clover app subscription or charge is implemented by this preview.

**Privacy policy:** Draft at `PRIVACY_DRAFT.md`. Publish an owner-approved HTTPS page before submission; do not substitute the ticket-only privacy policy without reviewing its coverage.

**Permissions:** Internet; native scanner services through Clover SDK. No card processing or Clover payments permissions are requested by this implementation. Verify the final merged manifest and developer dashboard permissions against the submitted release build.

**Screenshots needed:** Login, member search, member profile, QR card and successful check-in. Use synthetic profiles, not real customer data.

**Reviewer access:** Owner must supply a test staff account and a synthetic-data backend. Do not share real production staff credentials or live member records with reviewers.

**Release signing:** Owner-controlled production signing certificate required. Preserve its key securely for future updates.
