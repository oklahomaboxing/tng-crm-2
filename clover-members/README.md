# TNG Members for Clover Station Duo

Native Android preview app for TNG Boxing's member services. This is a separate app, not a browser wrapper or a copy of the full CRM.

## Included

- TNG staff/admin sign-in on the Clover; a separate tablet is not needed.
- Encrypted Android Keystore session storage, eight-hour POS sessions, sign-out.
- Search members by name or short member number, with pagination.
- Member profile, membership eligibility and expiry, waiver status, contact details, recent attendance.
- Edit first/last name, email and phone; display the existing member QR credential.
- Separate customer-facing Clover check-in activity: welcome screen, QR scan request, onscreen member-number keypad and brief membership/check-in feedback. Staff profiles and recent check-in status stay on the merchant display. The customer display closes when leaving this app for Register; it never resets an active payment.
- Native Clover QR scanner with customer-facing and merchant-facing controls, plus number entry.
- Reuses existing check-in eligibility/attendance flow. Retail customers are not promoted to members by this app.
- POS session tokens are rejected by ordinary CRM endpoints, and ordinary CRM tokens are rejected by the POS API.

## What is not connected yet

- Clover developer app registration, signed marketplace upload, private/test installation and App Market review.
- Clover single sign-on. This preview uses TNG staff login on the Clover itself. It does not trust a client-supplied Clover merchant ID.
- Automatic billing, plan activation, refunds, purchases, marketing, fighter data and commissions are outside this app.
- Actual Station Duo hardware testing is required. The native scanner uses Clover SDK 341; an emulator without Clover's scanner services cannot validate either device camera.
- The pending web geofence work is on a separate branch, awaiting the gym's location pin. It is not included or silently enabled here. If the shared check-in route later enforces location, this app must supply a location reading as part of that coordinated rollout.

## Build

Requirements: JDK 21, Android SDK platform 35 and build tools 35.0.0. `local.properties` may contain `sdk.dir=/your/sdk/path` and is ignored. Gradle wrapper is pinned to 8.11.1 with the official distribution SHA-256.

```sh
./gradlew assembleDebug assembleRelease lintDebug testDebugUnitTest
```

Windows PowerShell:

```powershell
.\gradlew.bat assembleDebug assembleRelease lintDebug testDebugUnitTest
```

`app/build/outputs/apk/debug/app-debug.apk` is a debug-signed test build. `app/build/outputs/apk/release/app-release-unsigned.apk` must be signed with the owner's permanent release key before uploading. Do not upload the debug APK for production review or commit signing keys/passwords.

The default backend is TNG's existing production backend. For sandbox/review, use a separate TNG staging backend with synthetic members:

```sh
./gradlew assembleRelease -PtngApiBaseUrl=https://YOUR-STAGING-BACKEND
```

The API origin must be HTTPS. No API keys, passwords or Clover tokens are embedded in the APK. A network interruption during check-in is not automatically retried, because attendance may already have been recorded; staff should verify recent visits before retrying.

## Installation and release

1. Owner creates a Clover developer account and a new **Android** app named **TNG Members**. Android package: `com.tngboxing.members`.
2. Configure and approve the developer business account as required by Clover. Preserve the production signing key for all subsequent versions.
3. Install through Clover's documented sandbox/test-merchant or private-app workflow. Do not enable debugging on a live payment device without following Clover's supported procedure.
4. Run `marketplace/STATION_DUO_TEST_PLAN.md` with test members, including customer-facing scanning and return to Register.
5. Supply the marketplace listing, privacy URL, screenshots, supported devices, reviewer test credentials on a synthetic-data environment, pricing/distribution choices and signed release APK.
6. Submit through Clover's Developer Dashboard. Only Clover can approve and list the app. A successful build or backend deployment is not a marketplace installation or approval.

Official sources:

- https://docs.clover.com/dev/docs/gdp-create-new-app
- https://docs.clover.com/dev/docs/gdp-manage-android-app-releases
- https://docs.clover.com/dev/docs/gdp-submit-your-app-for-approval
- https://docs.clover.com/dev/docs/setting-android-sdk-versions
- https://docs.clover.com/dev/docs/building-apps-for-station-pro
- https://docs.clover.com/dev/docs/build-apps-for-station-duo-2
- https://github.com/clover/clover-android-sdk

## Private preview 0.2.0

The supplied private-test APK is release-mode and signed with a preview certificate, not the owner’s final public-release certificate. The preview signing material is stored outside the checkout and is never embedded in the APK or committed. Keep this build for private testing. A future production signing-key change requires reinstalling this preview; server member records are unaffected because the app stores no member database locally.

Customer display implementation follows Clover’s Customer Facing Platform using `RemoteDeviceConnector`, `CloverCFPActivityHelper` and `CloverCFPCommsHelper`. The Android `GET_ACCOUNTS` permission is used only to obtain the installed Clover account for that connector; TNG credentials and member-directory data are not sent to the customer activity. This must be tested on Station Duo before claiming working dual-display hardware support.

Clover upload requires the V1 (JAR) APK signature scheme. When signing the release APK, explicitly pass `--v1-signer-name CERT --v1-signing-enabled true --v2-signing-enabled false --v3-signing-enabled false --v4-signing-enabled false` to `apksigner sign`. Run `apksigner verify --verbose` and confirm `Verified using v1 scheme (JAR signing): true` before uploading. Preserve the same signing certificate for updates.

Clover also requires the exact ZIP entry `META-INF/CERT.RSA` (and its `META-INF/CERT.SF` companion). Set `--v1-signer-name CERT` rather than renaming entries after signing; verify both entries and the V1 signature in the final APK. This preserves the signing certificate.
