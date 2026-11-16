# Commission boxing results and judges totals

Open an event → **Fight Night & Results**. Authorized admin/staff can upload the Oklahoma commission results workbook. All matching is by saved BoxRec ID and the exact current-card pairing; date and entire card coverage must agree. The source's column is labeled FED ID, but its values are matched only against the existing BoxRec IDs; no identity numbers, DOBs, locations or weights are overwritten.

Imports save each bout result, official order, winner, method, round/time, supplied final judge totals, source comments, source-record and current-record snapshots. Both red and blue corner identities/names are frozen at import so future card edits cannot rewrite a completed result. Bouts become completed and follow official bout order. Event ticket-sales settings and finances are unchanged.

Career records are **review only**, as directed for the November 14 workbook. No pro record is incremented or replaced. Conflicting or impossible reported records (such as 0–0 for a winner) are flagged. Imported TNG wins/losses appear separately in the fighter's result history. Suspension comments are preserved for review; they do not automatically clear or change medical eligibility.

The provided workbook has final totals for Jason Esparza–David De Leon and Kevin Conrad–Theodore Morse, not round-by-round cards. All three named judges' final totals are displayed under the correct red/blue corners. UD is derived from those three agreeing totals. Stoppages retain KO/TKO, round and elapsed time without fabricated judging scores.

The exact original XLSX is stored with SHA-256 and an import audit log. Re-importing identical bytes is idempotent. A changed workbook cannot silently overwrite existing results. Source downloads are staff-only because the workbook contains all participants' identity and other details. No workbook text is executed or treated as instructions.

Fighter profiles and portals show bout results and scorecards. Fighters can access only their own bout history and their own record-review/comments; opponent medical notes and the full workbook are not exposed. Event staff/matchmakers can view event results. Admin/staff alone can import or download the source.
