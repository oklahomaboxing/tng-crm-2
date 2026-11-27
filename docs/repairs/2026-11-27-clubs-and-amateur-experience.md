# Clubs inbox and amateur experience

Club Inbox now opens a searchable Oklahoma club directory, including clubs without messages. Message club opens the work composer filtered to that contact; existing conversations remain a separate inbox view. Opening the inbox after composing goes directly to conversations. Existing SMS permission, STOP handling, preview and submission checks remain in place. Browser verification used a mock club without message history and made only GET requests.

TNG local experience preference: Novice 0–10 reported bouts; Open 11+. Novices with 0–7 bouts cannot be proposed against Open athletes. With the consideration switch enabled, 8–10-bout novices may be proposed against Open athletes, visibly flagged for approval, while all other compatibility checks remain mandatory. At equal maximum card size the solver prefers same-class pairings before minimizing gaps. This preference does not modify the verified 2026 source rules. Previous cached proposals become stale and must be regenerated.

Validation: 21 amateur backend tests (20 passed, one optional database test skipped); 7 club messaging tests passed; 114 frontend tests passed; production frontend build passed; mocked browser flow verified directory → club composer → conversations → directory. No real messages sent.
