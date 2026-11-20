# Implementation progress

## 0.1.0 — 2026-10-16

Phase 0 and Phase 1 complete as a local research simulator foundation.

- Wrote the eight-part Phase 1 design before implementation.
- Added Next.js 16.4.2 frontend, FastAPI backend, domain contracts and JSON Schema.
- Added the 2 km square scenario with six sectors, three UAVs, five tasks, twelve buildings, floodplain, no-fly, debris, blocked road and base.
- Added map layers, high-contrast routes, flown tracks, numbered tasks, UAV headings, layer toggles, selection and fit extent.
- Added deterministic route following, fixed assignments, point service, battery/distance telemetry, Run/Pause/Step/Reset and ordered events.
- Added WebSocket reconnection, visible error states, audit JSON export and scenario hash.
- Upgraded MapLibre to 6.14.0 after dependency audit and packaged its worker/shared module locally for offline runtime.
- Added setup docs, dependency locks, Windows launcher and Docker configuration.

Verification: 12 backend tests passed; TypeScript passed; production build passed; Playwright acceptance passed using installed Microsoft Edge against the production build. Desktop and 390 px mobile screenshots inspected. npm dependency audit reported zero vulnerabilities. Python dependency consistency check passed. Starlette emits a deprecation warning for its httpx-based test client; tests pass. Docker build/run was not executed. Downloading the optional Playwright Chromium headless distribution was interrupted; Edge is the verified test browser.

Deferred: A* planning, CBBA, Llama/semantic decisions, dynamic incidents, scenario editing, full sector coverage, UAV collision avoidance, return-to-base, persistence, experiment management and snapshot restore/replay. No research results are fabricated.
