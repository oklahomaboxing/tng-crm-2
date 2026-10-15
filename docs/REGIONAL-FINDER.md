# Regional fighter, gym and manager finder

Open **Promoter → Regional finder**. The default region is Oklahoma, Texas,
Kansas, Arkansas, Missouri, Colorado and New Mexico. Choose pro boxers, gyms,
or managers; narrow the state selection and enter a city, name or gym.
Fighter searches optionally include weight criteria and a required bout date.
The bout-date filter excludes results with missing, invalid, future, or older
source-reported dates. It does not certify records or current availability.

Searches use the backend's existing OPENAI_API_KEY with the Responses web-search
tool. FIGHTER_DISCOVERY_MODEL optionally overrides the default gpt-4.1 model.
Authenticated admin, staff, and matchmaker roles can search and manage leads.
A missing key returns a clear 503; provider failures return a sanitized 502.
Each search is user initiated, limited to eight leads and a 55-second provider timeout.

The finder accepts source URLs only when they match web-search source/citation
URLs, ignoring only UTM tracking parameters and fragments. Results must match the
selected entity type and state. Business contact fields are shown only if their
exact text is included in the returned source evidence. These remain unverified
research leads; staff must review the original source and confirm contact details.
The system does not infer professional activity from an event location or infer
availability from a recent bout. AI research can omit or misinterpret information.

Save a result to retain its source, evidence and research timestamp in
boxing_discovery_leads. Saves deduplicate by entity type, name and source URL.
Track Not contacted / Contacted / Interested / Negotiating / Declined, notes,
and explicitly confirmed availability. Availability changes record a check time;
updates record the staff user. Saved leads are shared within boxing operations.
They are not automatically added as verified fighter records or booked into bouts.

Research links open Google, Maps, Fight Fax and BoxRec in a separate tab.
There is no licensed Fight Fax / BoxRec feed, bulk scraping, automatic outreach,
or automatic enrolment in SMS. Access to those external sites may require accounts.
No messages are sent by searching, saving, or changing a follow-up status.

Verification: backend regressions cover permissions, malformed URLs, cited source
matching, contact evidence, optional activity dates, duplicate saves and follow-up
persistence. SQLite and PostgreSQL use temporary/dedicated local test databases.
Browser checks use labeled UI fixtures for search/save/follow-up and mobile layout.
A separate live provider probe returned cited regional research leads without
writing them to production or contacting anyone.

### Search without API credits

Regional Finder defaults to `source=catalog`: it searches the saved scouting
prospects and saved leads by entity kind, state, name/city/gym, reported weight,
record profile and documented bout date. No OpenAI request is made. Fighter
results can be saved into the outreach lead list without changing the active
roster or booking a bout. The original research timestamp is retained.

`source=official_rosters` fetches the public promoter profiles for fighters.
`source=public_web` remains an explicit paid-provider option. Gyms/managers can
be searched among saved leads, or researched using the direct public links and
the optional provider. These are distinct sources; a saved-catalogue search is
not presented as a fresh search of the entire web. Results return a match count
and show up to 50 candidates. Publication dates do not qualify as bout dates.

Both Regional Finder and Boxer Database offer losing (losses greater than wins),
at least one loss, even and winning record filters. Unknown records remain
unknown and are excluded from record-specific filters. Beginner/developing and
record filters can be combined. Regional losing-record quick selection clears
the experience filter so experienced losing-record prospects are not hidden.
