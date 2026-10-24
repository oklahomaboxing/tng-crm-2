# Local sponsor finder

Find Sponsors previously required a paid OpenAI web-search call. Live diagnosis returned HTTP 429 `credit_balance_exhausted`; the button surfaced the failure without a usable discovery result. It also searched around the event venue instead of the gym address requested by the owner.

The finder now uses sourced public business-directory records. Its editable default center is **8416 NW Expressway, Oklahoma City, OK 73162**, using an approximate U.S. Census geocoder result (35.56871056141, -97.66325776497). This is a business-search center, not an approved member geofence pin. Other U.S. addresses use the Census geocoder and are not silently replaced with Oklahoma City if geocoding fails.

## Sources and coverage

- The gym's initial results use a bundled OpenStreetMap extract retrieved from the documented map API URL in `backend/app/revenue/data/nw_okc_businesses.json`. The file contains 64 named map records before business filtering. Church and other nonbusiness amenities are excluded from returned leads.
- The API filters by category and approximate distance, selects the closest mapped location per business name, sorts by distance, and returns up to the requested limit (maximum 30). The UI requests 20.
- **Refresh from public map** retrieves a bounded map extract. Responses are cached in process for 24 hours. The extract samples at most an approximately two-mile box radius; requested distance is a hard result filter, not a guarantee of exhaustive coverage throughout a wider radius.
- If the map provider is unavailable near this gym, the labeled saved snapshot remains usable. Other locations get an actionable error instead of unrelated Oklahoma City leads.
- Directory retrieval dates, source links, OpenStreetMap attribution, approximate distances, listed addresses, and public contact details where present are shown. This does not verify that a business remains open or that a contact is current.
- No interest, marketing budget, sponsorship history, or personal relationship is inferred as fact. Those fields remain unknown/zero absent evidence. Directory results display distance rather than an invented sponsor heat score.

## Pipeline and outreach

**Add to Pipeline** saves the selected lead, its sources, and available public contact/location fields. It no longer invokes the auto-outreach endpoint. Existing verified sponsorship history, relationship notes, and populated contact fields are preserved when a map lead matches an existing organization. Sending requires the separate existing outreach controls. This change does not alter previously configured follow-up jobs.

The finder itself does not create organizations/prospects, send messages, or call paid AI services. AI proposal/contact-research tools remain subject to their existing provider availability.

## License

The bundled business-directory extract is OpenStreetMap data, © OpenStreetMap contributors, available under the Open Database License (ODbL). See https://www.openstreetmap.org/copyright and the extract's `source_url` and `retrieved_at` fields. This data attribution does not assert a license change for the application code.

## Validation

Seven backend regressions cover offline gym search, category/distance limits, source attribution and unknown sponsorship status, provider outages, wrong-city rejection, URL safety, authorization, and pipeline saves without outreach or loss of established sponsor evidence. Frontend build and browser fixture checks verify the gym center instead of an unrelated event venue, source/distance/contact display, and saving without an auto-outreach request. Live verification searches only; no business is contacted or added to the live pipeline by the check.
