# Clover developer app registration

- App name: TNG Members
- App ID: `55ZJ8M8JZA8JT` (public identifier, not a credential)
- Type: Android
- Intended distribution: private gym installation / test
- Android package: `com.tngboxing.members`
- Owner-reported status: Draft
- Initial hardware target: Station Duo. Remove Mini (2nd Gen) from the device selection until it is tested.

No App Secret is embedded in the Android app or committed to this repository. The current native scanner and TNG staff authentication do not require exposing an App Secret on the POS.

Webhooks and receipt customization are not used by this version. It does not request Clover payment data or write payment transactions. Review any developer-dashboard permission choices against the actual app capabilities.
