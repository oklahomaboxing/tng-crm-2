# TNGOS Command Center foundation — development preview

Branch: `feature/command-center-foundation`. This is Phase 1A/1B plus the first read-only bracket integration. Production deployment branches are not changed by this work.

## Architecture audit

The application uses React 19.2.7, Vite 8.1.6, Material UI 9, Emotion, Lucide/MUI icons, Recharts and hash-based role-aware workspace navigation. `App.jsx` lazy-loads workspaces. `AppShell.jsx` already provides Standard/Command styling, module navigation, preferences and a module launcher. Existing FastAPI APIs use the current bearer-token authentication and server-side role guards. The existing dashboard, account/session flow and operational modules are retained.

There is no new backend API, database schema, payment flow or production data migration. No messages are sent. The production APIs already restrict both operations and briefing snapshots to administrators. New frontend workspace access is admin-only; tournament access continues to use its existing role and roster controls.

## Implemented

- Admin workspace `/#/command-center`, with alias `/#/admin/command-center` (the application uses hash routes).
- Scoped command tokens, dark glass-style panels, cyan accents, searchable workspace buttons, fullscreen toggle, Oklahoma City date/time and reduced-motion-aware Motion entrance transitions.
- Read-only membership, attendance, selected event ticket-payment and fight-card summaries; real work queues; upcoming events and navigation to existing venue/tournament/revenue tools.
- GET `/api/operations/overview` supplies membership counts, queues, event summaries and configuration flags. GET `/api/assistant/snapshot` supplies saved attendance, current-event orders and card information. This GET does not start a voice or paid-model request.
- Configuration is labeled **configured, not verified**; errors, loading and unavailable values remain visible. Refresh is user-driven. The clock updates once per minute and skips rendering while hidden. No perpetual GPU animation or 3D engine is installed.
- A clearly labeled, static AI visual placeholder; no microphone or assistant is connected in this new preview.
- Lazy-loaded React Flow bracket map in Amateur Matchmaker → tournament planner → Tournament view → Bracket map. Uses the selected plan's existing `nodes`, source references, saved corner labels and recorded results. No graph editing, reconnection, deletion or result submission. Existing planner screens retain all approvals and mutations. Changed division entries retain a review warning.
- Optional, disabled-by-default Sentry rendering-error integration. Initialization is lazy; no session replay, tracing, automatic integrations, network/console breadcrumbs or automatic session tracking. Error content is allowlisted: generic exception description, static code-file path and line/column only; original messages, URLs/query strings, user details, request bodies, tags and arbitrary context are stripped. A failed telemetry setup cannot stop the application.

## Dependencies

Exact versions: `motion@14.14.0`, `@xyflow/react@12.12.1`, `@sentry/react@11.16.0`. Lockfile updated. React Flow 12 is used to avoid the newer release's CSS-layer dependency on older Android/WebView targets. Existing Recharts remains the chart system; no additional animation engine, chart engine or 3D framework was added.

Official package READMEs, source/types and examples were inspected for compatibility. Direct documentation-site access is restricted in this cloud environment. Reference documentation: [Motion accessibility](https://motion.dev/docs/react-accessibility), [React Flow interaction controls](https://reactflow.dev/learn/customization/interaction-props), [Sentry options](https://docs.sentry.io/platforms/javascript/guides/react/configuration/options/).

## Preview

From `frontend`:

```sh
npm ci
npm run dev -- --port 5176
```

Actual application: `http://127.0.0.1:5176/#/admin/command-center`. Use an administrator login against your approved development/staging backend (`VITE_API_URL`). Do not supply production credentials to the fixture preview.

No-login design fixture: `http://127.0.0.1:5176/tests/browser/command-center.html`. This route clearly labels all values as synthetic and replaces fetch locally for the fixture only. It is not an application entry and is not included in the production build. Add `?bracket` to see the bracket fixture; `?unavailable` tests failed-report states. Fixture navigation records its target without opening operational tools. These localhost URLs are available on the machine running Vite, not public deployment links.

Screenshots, both explicitly labeled synthetic:

- [Command Center](docs/previews/command-center-fixture.png)
- [Tournament map](docs/previews/tournament-map-fixture.png)

## Optional monitoring configuration

Only after configuring an approved Sentry project, set both build variables:

```dotenv
VITE_ERROR_MONITORING_ENABLED=true
VITE_SENTRY_DSN=https://YOUR_PUBLIC_PROJECT_DSN
```

No DSN or account has been added. Default builds send no Sentry events. Do not enable replay/tracing or add customer/payment payloads to telemetry without reviewing that separate change.

## Validation

- 56 Node tests pass, covering workspace-role isolation/alias, graph source edges and non-mutation, opt-in monitoring and removal of sensitive error content.
- Production build passes with the existing Chrome 83 JavaScript target. Existing large-chunk warnings remain; Motion, React Flow and Sentry are split into optional chunks.
- Browser checks pass: synthetic-data labeling, GET-only report access, navigation, provider-status wording, unavailable-report states, 390px layout with no page overflow, reduced-motion rendering, three saved bracket nodes/two source edges and disabled node dragging.
- Dependency audit after the final compatible dependency selection reports zero known vulnerabilities. Physical Android/iPad testing and staging-account end-to-end verification remain release checks.

## Remaining phases

The AI placeholder is not a conversational or voice assistant. Public-safe Event Mode, custom fighter intelligence profiles, advanced notification history, an optional verified startup sequence and any 3D graphics remain future work. Sentry requires an approved configured project. No public preview hosting service is configured in this environment. Review the branch/screenshots and test against approved staging data before merging or publishing production, as requested in the supplied brief.

## Files

New: `CommandCenterPreview.jsx`, `commandTokens.js`, `components/command/{command.css,TournamentFlow.jsx,tournamentGraph.js}`, `services/monitoring/{index.js,privacy.js}`, `commandFoundation.test.mjs`, development-only `tests/browser/command-center.*`, this document and preview images.

Updated: `App.jsx`, `Sidebar.jsx`, `WorkspaceBoundary.jsx`, `navigation/workspaces.js`, `AmateurTournament.jsx`, `workspaces.test.mjs`, `package.json`, `package-lock.json`.
