# InBody Touch member check-in

Kiosk URL: **https://tngos.tngboxinggym.com/kiosk/checkin**

## Set up the entrance screen

1. On your normal staff computer, sign in to TNGOS and open **Check-In Kiosk** in Gym Operations. Administrator and staff accounts can manage devices.
2. Select **Add check-in device**. Name it **InBody Touch — Entrance**. Leave confirmation at **8 seconds** and the duplicate window at **120 seconds**, or choose your preferred values and save.
3. Select **Generate pairing code**. On the InBody screen, open the kiosk URL and enter this staff-only code. It expires after 10 minutes and works once. Do not sign the entrance screen into an administrator account.
4. The welcome screen appears after pairing. Members enter the numeric portion of their existing member number, including any leading zeros, and touch **CHECK IN**. Existing `TNG-000001` cards are recognized as `000001`; ambiguous numbers are directed to staff.
5. Successful attendance shows only first name and Active status for 8 seconds. Errors clear after 5 seconds. **Next Member** resets immediately. Incomplete number entries clear after 30 seconds of inactivity.
The welcome screen also displays **Not a member yet? Scan to join TNG Boxing**. The QR code opens the existing **https://tngos.tngboxinggym.com/register** signup process on the visitor's own phone, including their information, emergency contact, waiver/consent, membership selection and payment. It contains no device credential or member data and uses the existing front-desk registration attribution. Visitors never leave the shared kiosk to enter private signup/payment details.

6. Test on the actual InBody screen using a consenting staff member's active membership. Confirm one attendance entry under that member's attendance history; immediately submitting again should show **Already checked in** without another record.

## Full screen and installation

Use an up-to-date Chrome browser or Android System WebView supported by your InBody device. Android 11 shipped with Chromium 83; the frontend build targets that syntax baseline. Updating the browser/WebView is still recommended for security and compatibility.

- Browser: open the URL and touch **Full screen**. The page requests Screen Wake Lock where supported. It reacquires it when the page becomes visible. Browser support and device power policies determine whether it can keep the display awake.
- PWA: Chrome menu → **Install app** or **Add to Home screen**. If Chrome offers it, the page also shows **Install kiosk**. Launch the installed **TNG Check-In** icon for a separate window without normal browser navigation.
- Optional Android APK: [Download TNG Check-In 1.0.0](https://tngos.tngboxinggym.com/kiosk/tng-checkin-1.0.0.apk). It is a separate app, package `com.tngboxing.checkinkiosk`, not a Clover marketplace APK. Install only if your InBody administrator/manufacturer permits additional apps. Android may require **Allow from this source** for the browser/file manager; disable that permission again after installation. The app has only Internet permission, keeps its screen awake, uses portrait immersive mode, and opens only the dedicated HTTPS kiosk URL. Android Home remains available. It does not remove or modify InBody software.
- APK SHA-256: `4c678c7fabce513dad75f635acb6785005f3e2ec75d5b282923bae638a941f33`.

Browser/PWA and APK have separate app storage. Pair the version you intend to use. Pairing a replacement rotates the old credential. Clearing browser/app storage or uninstalling requires pairing again. Staff can revoke device access at any time.

## Reopen after restarting

Pairing survives a normal restart. Open the **TNG Check-In** icon after Android starts and the keypad reconnects automatically. For unattended restart, use the InBody manufacturer's supported startup-app/kiosk setting or your Android device-management policy to launch the TNG PWA/APK after boot. Android 11 restricts apps starting a foreground activity from a boot receiver; this app does not claim to bypass those restrictions. Screen pinning alone does not automatically launch an app after reboot.

If the device provides no approved startup-app feature, staff must tap the icon after a restart. Do not factory-reset the device, replace the InBody launcher, root it, disable its services or change device-owner settings to enable this feature. Retain access to InBody's original software. Ask the device supplier to enable managed autostart if needed.

## Staff monitoring and security

The Check-In Kiosk workspace shows per-device enable/disable, confirmation duration (3–30 seconds), duplicate window (30–3600 seconds), pairing/revocation, heartbeat, Central Time daily outcome totals, and the latest 50 attempts for today. Click a member profile number to inspect its attendance in the existing Members workspace. Recorded attempts link internally to existing attendance rows. Disabled kiosks stop accepting new check-ins immediately on the server; the screen notices configuration updates within 30 seconds. Online means a heartbeat was received within 90 seconds, not an independent network probe.

A restricted device credential is stored only on the paired device; the database stores its SHA-256 hash. It cannot call CRM member/profile/admin APIs. Pairing is one-use, ten-minute, 48-bit random enrollment; invalid pairing attempts are limited to ten per minute per connection address. Number submissions are limited to thirty per minute per device, with an additional shared address limit. Database counters apply across application workers. Device attempts record outcome/device/member association without retaining the typed number, email, phone or billing details. Management changes are logged to the existing security log.

The kiosk cannot verify a person's identity from a membership number. Locate it physically at the entrance under staff supervision, and revoke access if it is lost or removed. Do not publish pairing codes or share an administrator login with it.

Attendance uses the existing member eligibility rules and `attendance` table. Writes lock the existing member row on PostgreSQL so concurrent kiosk/Front Desk/Clover check-ins cannot both insert within the duplicate window. Existing member cards, profile numbers, membership billing, Front Desk and Clover POS integrations are retained. Front Desk/Clover also use the shared 120-second guard. A previously saved check-in whose response was lost can be safely retried.

Internet is required. No offline attendance queue or member records are cached by the service worker. An offline check-in never claims to be recorded. Reconnect and retry or visit the front desk. No attendance is created just by opening the page, pairing, or sending heartbeats.

## Developer build

Source: `android-kiosk/`. Use JDK 17+, Android SDK 35 and Gradle 8.11.1 with `gradle assembleRelease lintRelease`, then zipalign and sign with the dedicated TNG kiosk release keystore using Android SDK apksigner. The signing keystore/password stay outside Git in secure runtime storage and need a secure owner backup for future APK updates. Never commit them, put them into APK assets or paste them into chat. The downloadable APK is release-signed with APK Signature Scheme v2/v3; the app minimum is Android 8 (API 26), covering Android 11. Physical InBody installation/fullscreen/restart still require an on-device acceptance test; cloud tests do not emulate proprietary InBody firmware restrictions.
