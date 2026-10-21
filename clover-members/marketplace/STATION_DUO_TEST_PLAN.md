# Station Duo acceptance test

Use an approved test/private installation, a staging backend and synthetic members. Hardware tests are outstanding until actually performed; compiling an APK does not validate Clover scanner services.

- Install the app with the registered package and test release. Launch from the Clover launcher and return to Register without affecting a sale.
- Sign in as test staff. Invalid credentials and locked/inactive staff accounts must be rejected. Relaunch must retain a valid encrypted session; expired sessions must show login. Sign-out must clear the local session.
- Search by full/partial name, short number and legacy member number. Page through the results. Confirm retail-only customers do not appear.
- Open a member profile and verify status, expiry, waiver status, contact information and ten most recent visits. Confirm financial/medical data is absent.
- Update contact details. Invalid email/name must fail without changing membership eligibility or billing.
- Show the member QR card and verify the credential matches the member's existing phone/printed card.
- Scan using the customer-facing camera, then the merchant-facing camera. Confirm native preview, one attendance record per scan and correct member identity. Verify cancellation and retry after closing the scanner.
- Enter a short member number, submit with the onscreen button and with a handheld keyboard scanner's Enter key. Blank/unknown numbers must not create attendance.
- Scan two different members in succession. Repeated frames of the same card must not trigger repeated submissions.
- Try an expired/inactive member. No attendance may be created.
- Disconnect the internet during submission. The app must explain that status is unconfirmed and must not automatically retry. Reconnect and inspect the member's recent visits before deciding whether to resubmit.
- Background the app, switch to Register, rotate the merchant display if supported, and return. Scanner resources must be released. Verify member profiles do not appear on the customer-facing display.
- Test both hardware generations separately before claiming both Station Duo and Station Duo 2 support.

Record device model, Android/Clover ROM version, app version, tester, date, outcome and any issue for each test. Attach only synthetic-data screenshots.

Customer display: launch “Open customer check-in screen” on the merchant display when Clover is idle. Verify the welcome page, its own numeric keypad, customer-facing QR request, green active/check-in success and generic staff-review message for expired or unknown members. Verify automatic clearing of the previous member’s feedback. Browse profiles on the staff display while another member checks in. Return to Register during an idle period and confirm the customer app closes without resetting or interfering with a payment. Verify sign-out/expired staff session closes the customer activity.
