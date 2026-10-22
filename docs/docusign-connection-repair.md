# DocuSign connection repair

The live OAuth JWT check returned `no_valid_keys_or_signatures` before envelope creation. The server currently uses DocuSign demo endpoints. Required configuration values are present and the private key parses, but the provider rejects authentication. Do not infer that demo credentials should be switched to production without confirming the integration's environment.

In an event's Contracts page, use **Check DocuSign connection**. This manually requests an OAuth token and reads `/oauth/userinfo`; it never creates or sends an envelope. It verifies that the sending user has the configured account and that `DOCUSIGN_BASE_URI` matches that account. Failure messages explain key mismatches, consent requirements, invalid identities, and connection failures without returning raw provider bodies or secrets.

For a key mismatch:

1. As a TNG admin, use **Download public key (TNG admin)** after the connection check.
2. A DocuSign administrator must open Apps and Keys in the matching environment and locate the configured integration (the check shows its final six characters).
3. Register the downloaded public RSA key under that integration. Keep existing keys unless their removal is separately authorized. Do not upload the private key or paste it into chat.
4. Run the check again. If consent is required, grant `signature impersonation` consent for the configured sending user through the normal DocuSign authorization flow.
5. Verify a ready connection before the owner sends a contract to an authorized recipient. A passing connection check does not itself validate envelope templates, signer behavior, or completed-PDF import.

The public-key endpoint derives only SubjectPublicKeyInfo PEM from the configured private key, requires admin access, and sets `Cache-Control: no-store`. It does not change provider keys or server secrets. No real envelopes were sent during this repair. The provider configuration cannot be fully repaired without access to the DocuSign integration settings.

Also corrected two DocuSign sync buttons incorrectly labeled “Sync Adobe.”

Validation: eight mocked-provider diagnostic tests, 20 existing stabilization tests, frontend build, and browser fixture checks of the diagnostic panel. Physical sending and signing are not claimed verified.
