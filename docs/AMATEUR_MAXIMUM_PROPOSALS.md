# Maximum amateur proposal card and boxer comparisons

TNG Promotions → Amateur Matchmaker → Match proposals now offers **Find maximum bouts** / **Rebuild maximum card**. It builds the largest disjoint set of candidate pairings, with one proposed bout per available boxer. A maximum-weight blossom solver prioritizes maximum cardinality first, then minimizes the existing weight/experience/DOB gap penalty. It handles non-bipartite graphs and has no MILP time-limit fallback. NetworkX 3.4.2 is pinned as a backend dependency. The existing 200-available-boxer limit remains and is shown before generating an oversized run.

Candidate eligibility logic is unchanged: the installed, hash-verified 2026 rulebook/Appendix F local matched-bout reference, birthday ages, weight tolerances, Masters and sex-class rules, plus staff's TNG preferences. Same-club exclusions, reported-bout gap caps and unlimited-class weight caps can reduce the maximum; they are labeled TNG preferences rather than USA Boxing rules. This does not certify membership, medical clearance, winning-percentage suitability or full combat-sport experience. Both coaches and the Official in Charge still review and approve. Tournament brackets remain separate.

The response includes maximum_bouts, matched_boxers, available_boxers, unmatched_available, solver and maximum_basis. The solver version is part of the roster fingerprint so old timed-solver caches become stale and must be regenerated. Historical runs are preserved. No actual card, offers, contracts or messages are created.

Each proposal shows red and blue boxer panels with reported DOB, birthday age at the event, bouts, wins, declared weight, gym, city/state, coach, LBC, sex category and USA Boxing ID. Leading zeros are preserved in IDs. Missing wins/details remain marked Not reported. Boxer review opens the existing versioned roster editor. Unmatched boxers also get profile details with their reason. Search works across names, clubs, states, cities and IDs; proposals and unmatched lists paginate 20 per page.

## Validation

17 amateur/backend tests: 16 passed and one PostgreSQL-only upload-concurrency test skipped without an isolated TEST_DATABASE_URL. Exact matching was checked against exhaustive solutions for 84 small random graphs, an odd cycle, a greedy trap, and a dense 200-boxer graph yielding 100 disjoint bouts. Existing 2026 age, weight, sex, Masters, source-verification and preference tests remain intact. All 108 frontend tests and the production build pass.

An isolated browser/API run generated two bouts for five sample boxers, verified profile fields and leading-zero IDs, searched a boxer, viewed the unmatched profile, and checked phone width with no captured browser errors. Screenshots use sample data. No production roster was regenerated, no boxer records were changed, and nobody was contacted during testing.
