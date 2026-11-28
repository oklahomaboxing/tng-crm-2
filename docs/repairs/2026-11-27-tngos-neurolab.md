# TNG NeuroLab in TNGOS

The user's instruction to add NeuroLab to TNGOS authorizes a TNGOS entry point while preserving the separate standalone research project. This integration is a working **browser simulation lab**, not deployment of the standalone Python backend inside production CRM services.

## Access

Admin only: `#/tng-neurolab`, the dedicated TNG NEUROLAB sidebar section, or Dashboard → Overview → Open TNG NeuroLab. Role menus, URL resolution, search and rendering all restrict the page to admin. Members, fighters, staff and partners are not given access. No new backend endpoints, database tables, production dependencies or customer-record reads.

## Functionality

Eight synthetic channels at a nominal 250 samples/s, 50-sample packets every 200ms. Browser Welch PSD uses periodic Hann 256-sample windows with 128 overlap over at most 500 recent samples. Relative powers use half-open bands delta .5–4, theta 4–8, alpha 8–13, beta 13–30, gamma 30–45 Hz. Drawing retains 1000 samples/channel and clips display amplitude only to ±100 µV. These are sample-time signals, not hard real-time hardware measurements.

The baseline classifies the dominant spectral band, explicitly **not PyTorch** and not a human mental-state/intent model. Artifact checks flag flatline (<.2 µV standard deviation), high amplitude (>120 µV absolute), abrupt steps (>100 µV difference), and 49–61 Hz interference (>25% PSD-bin total). Score=max(0,100−35×flags). Any flagged channel causes baseline abstention. No medical or performance inference.

Virtual control requires explicit arming, live simulation, clean quality and dominant relative fraction above .85; at most one command/second. Alpha/left, beta/right, theta/up, clamped to arena. Leaving the sandbox, disconnecting, playback or withdrawing consent disarms control. No OS, hardware or CRM commands.

## Data and consent

Explicit simulation consent before streaming/recording. Consent applies to the page instance only. Recordings are **React page memory only**, up to 60 seconds each and latest five sessions. Internal research-view changes retain them; leaving the TNGOS module, refreshing or logging out discards them. JSON export is explicit and includes `TNGOS_BROWSER_SIMULATED` provenance. There is no IndexedDB/localStorage/server retention and no upload/import path. Export before navigating away. Withdrawal stops activity and clears samples/recordings; previously downloaded files remain on device. The 100-entry local activity list is temporary and is not a durable server audit log.

## Standalone service boundary

`/workspace/tng-neurolab` remains an independent project. Its FastAPI/PostgreSQL, BrainFlow, PyTorch, server recording, account consent and durable audit functions are **not connected** to TNGOS by this change. The browser page states this explicitly. An optional build-time `VITE_NEUROLAB_URL` enables a link to a reviewed HTTPS deployment with no URL credentials. It opens separately with `noopener noreferrer` and never forwards TNGOS auth tokens. It requires its own sign-in. Without a configured URL there is no broken service-launch button; the local browser lab still works.

## Verification

120 frontend tests passed, including six new tests covering synthetic spectral classification, provenance, artifact abstention, finite-window handling, bounded virtual movement, role restrictions and HTTPS service link validation. Production frontend build passed. Browser verification at 1450px and 390px covered consent gate, live signals, recording, downloaded JSON provenance, replay, virtual movement, artifact suppression and withdrawal clearing recordings. Zero JavaScript exceptions and zero `/api/` requests from the lab. Existing standalone repository and TNGOS backend source unchanged.

## Dedicated main section follow-up

Moved NeuroLab out of Gym & Members into its own TNG NEUROLAB main navigation group and added a separate dark research card on the main Dashboard Overview. Removed the gym-dashboard shortcut so research has its own home. Admin-only route/access unchanged. 121 frontend tests and the production build passed. Browser checks verified both menu and dashboard-card navigation, absence of the research section for staff, and no JavaScript exceptions. No backend changes in this navigation follow-up.
