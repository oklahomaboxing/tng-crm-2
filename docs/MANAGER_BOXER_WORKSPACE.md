# Manager boxer workspace

Manager sign-ins open the boxer management workspace. Use the boxer tabs or Selected boxer menu to switch accounts. Each selection opens the existing fighter portal with that boxer's ticket sales, contribution, results, offers, contracts and media. Offers & availability retains the manager offer-response and scheduling workflow, filtered to the selected boxer.

## Roster changes

- **Add boxer** creates a canonical fighter-pool profile and an active manager assignment together. Provide a legal name and at least a BoxRec ID, email or complete phone number. Reported records are optional; medical and suspension approval remain staff-controlled.
- A matching existing pool profile produces a **roster link request**, rather than a duplicate fighter or immediate access. Staff review requests in **User Management → Roster requests**. Existing representation must be released before transferring a boxer to another manager.
- **Edit selected profile** updates contact, training, social and weight details on the shared fighter record. Optimistic version checks reject stale edits.
- **Remove from my roster** ends the assignment and access, including through already minted workspace tokens. It does not delete the fighter, personal account, tickets, bouts, contracts or history.
- Adding a represented boxer does not silently create a second login or send an activation email.

## Authorization

The normal manager login is never replaced. Selection creates a short-lived, memory-only JWT whose subject remains the manager, with a selected-fighter claim. The API rechecks active representation on each request and restricts the token to the existing fighter API plus the selected boxer's results and contribution endpoints. Remembered-device revocation and original token expiry apply to delegated tokens. Managers can review/download contracts and upload signed PDFs; personal electronic signatures and provider signing URLs remain restricted to the boxer.

New submissions and assignments commit together. Per-manager row locks and PostgreSQL identity advisory locks serialize concurrent saves. Idempotency keys prevent duplicate retries; reuse with a different identity is rejected. Administrative assignment and review serialize against the fighter row. Roster/profile changes are audited.

## Verification

`backend/tests/test_manager_workspace.py` covers roster isolation, scoped actor identity, personal-signature denial, cross-account denial, unchanged fighter login, device revocation, inactive managers, create/retry/identity conflicts, reviewed links, stale edits, release and offer-list revocation. With the isolated PostgreSQL fixture it also checks simultaneous submissions by different managers create only one pool boxer.

Browser checks use synthetic fixture data and intercept all API calls; they cover top tabs, reselecting the same boxer, fast switching, scoped portal requests, adding a boxer, removal explanations and a narrow mobile viewport. No actual messages or signing requests are sent by these checks.
