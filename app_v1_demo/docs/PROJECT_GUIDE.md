# EdgeSAR Lab — complete project guide

Source inspection date: 16 October 2026. Project root: `D:\1 Samadhi UNI\aFYP\implementation\V1`.

This guide describes the implementation present in this directory, distinguishes working functionality from future research plans, and explains every application/configuration/documentation file. Generated dependencies and caches are grouped rather than expanded into thousands of third-party files. This is a source inspection; tests, builds, Docker, and browser acceptance were not rerun for this guide.

## 1. What this project does

**EdgeSAR Lab** is a local web application for observing and controlling a deterministic, multi-UAV search-and-rescue mission simulation. UAV means unmanned aerial vehicle, or drone. The current application version is **0.1.0**, implementing the Phase 1 simulator foundation.

The user opens a mission-control dashboard, sees a synthetic disaster area, and watches three simulated aircraft follow predefined routes to five predefined task points. The application displays position, heading, battery, distance flown, task progress, mission time, and an ordered event history. Run, Pause, Step, Reset, map selection, layer toggles, and audit export are implemented.

The longer-term research objective is to examine whether differences in quantized language-model decisions affect task allocation and mission outcomes. **There is currently no language model, quantization comparison, semantic decision engine, CBBA allocator, or automatic path planner running in this project.** Those are future phases, explicitly marked as deferred in the documentation.

It is a mission-level simulator, not a flight dynamics simulator or operational UAV control station. No real aircraft, camera, thermal sensor, autopilot, or telemetry service is connected.

## 2. Complete project structure

```text
V1/
|-- .dockerignore                    Files excluded from Docker build contexts
|-- .env.example                     Frontend API URL and backend CORS examples
|-- .gitignore                       Dependency/build/cache/local-env exclusions
|-- README.md                        Setup, usage, architecture and limitations
|-- CHANGELOG.md                     Version history and recorded verification
|-- package.json                     Root npm workspace and command forwarding
|-- package-lock.json                Locked JavaScript dependency tree
|-- pyproject.toml                   Python metadata, dependencies and pytest setup
|-- requirements.lock                Frozen Python installation requirements
|-- docker-compose.yml               API and frontend container configuration
|
|-- apps/
|   |-- api/
|   |   |-- Dockerfile               Python API container
|   |   |-- app/
|   |   |   |-- main.py              FastAPI lifecycle, REST, WebSocket and CORS
|   |   |   |-- models.py            Domain/state contracts and world validation
|   |   |   |-- repository.py        Loads the committed scenario JSON
|   |   |   `-- service.py           Async ticking, command lock and revisions
|   |   `-- tests/
|   |       |-- test_api.py          HTTP, commands, WebSocket and export tests
|   |       `-- test_engine.py       Determinism, movement and validation tests
|   |
|   `-- web/
|       |-- Dockerfile               Node frontend build and runtime container
|       |-- package.json             Frontend dependencies and commands
|       |-- tsconfig.json            Strict TypeScript and @/* import alias
|       |-- next-env.d.ts            Next.js generated type declarations
|       |-- playwright.config.ts     Browser acceptance-test configuration
|       |-- app/
|       |   |-- layout.tsx           HTML wrapper, metadata and global CSS imports
|       |   |-- page.tsx             / route, renders MissionControl
|       |   |-- globals.css          Custom responsive mission-dashboard styling
|       |   `-- simulator/
|       |       `-- page.tsx         /simulator route, reuses the root page
|       |-- components/
|       |   |-- MissionControl.tsx   Dashboard composition and mission controls
|       |   |-- MissionMap.tsx       MapLibre layers, markers and map interactions
|       |   `-- Panels.tsx           Fleet, task, inspector and event-log UI
|       |-- hooks/
|       |   `-- useMission.ts        Fetch, WebSocket, reconnect, commands, export
|       |-- lib/
|       |   |-- types.ts             Frontend TypeScript protocol/domain types
|       |   `-- geo.ts               Local-metre conversion and GeoJSON features
|       |-- scripts/
|       |   `-- copy-map-worker.mjs  Copies MapLibre modules into local public assets
|       |-- public/
|       |   `-- maplibre/
|       |       |-- maplibre-gl-worker.mjs  Generated/copied map worker
|       |       `-- maplibre-gl-shared.mjs  Generated/copied shared map module
|       |-- tests/
|       |   `-- mission.spec.ts      End-to-end desktop/mobile workflow test
|       |-- .next/                   Generated Next.js build/development output
|       |-- test-results/            Generated browser-test results
|       `-- tsconfig.tsbuildinfo     Generated incremental TypeScript cache
|
|-- packages/
|   `-- simulation/
|       `-- engine.py                Deterministic fixed-tick mission executor
|
|-- scenarios/
|   |-- urban-disaster.json          Committed default scenario and authored routes
|   `-- scenario.schema.json         Generated structural JSON Schema
|
|-- scripts/
|   |-- create_scenario.py           Authors/overwrites the default scenario fixture
|   |-- generate_schema.py           Generates JSON Schema from the Python model
|   `-- dev.ps1                      Starts local backend and frontend together
|
|-- docs/
|   |-- PROJECT_GUIDE.md             This consolidated project explanation
|   |-- PHASE_1_DESIGN.md            Design, milestones and acceptance criteria
|   |-- ARCHITECTURE.md              Responsibilities and application data flow
|   |-- API.md                       REST/WebSocket contracts
|   |-- SIMULATION_MODEL.md          Time, movement, service and battery semantics
|   |-- REPRODUCIBILITY.md           Deterministic runs and export limitations
|   |-- SEMANTIC_ENGINE.md           Future semantic-engine boundary; deferred
|   |-- CBBA.md                      Future allocation work; deferred
|   |-- EXPERIMENTS.md               Future experiment work; deferred
|   |-- mission-desktop.png          Saved desktop acceptance screenshot
|   `-- mission-mobile.png           Saved mobile acceptance screenshot
|
|-- .venv/                           Local Python environment and installed packages
|-- node_modules/                    Installed npm workspace dependencies
`-- pytest-cache-files-a_oo691r/      Temporary pytest-related directory
```

Python `__pycache__/` directories also occur under Python source directories. They contain generated bytecode, not project logic. The temporary pytest directory could not be enumerated because filesystem access was denied; its contents are not included above. No `AGENTS.md` appeared in the accessible project search. No `.git` directory was visible in the root listing.

## 3. Technology stack

### Frontend

- **Next.js 16.4.2:** application framework and App Router. Both `/` and `/simulator` show the mission dashboard.
- **React 19.2.4 / React DOM 19.2.4:** components and reactive UI updates.
- **TypeScript, declared `^5.9.3`:** compile-time contracts; strict checking is enabled.
- **MapLibre GL JS, declared `^6.14.0`:** browser WebGL map rendering.
- **Lucide React, declared `^0.577.0`:** interface icons.
- **Custom CSS:** layout, styling, responsive behavior and map-marker appearance.
- **Native browser Fetch and WebSocket:** communication with FastAPI.
- **React hooks:** local UI and transport state, without a separate state-management library.

There is no implemented Tailwind, shadcn, Zustand, React Query, or charting layer. Dependency ranges above are manifest declarations; `package-lock.json` locks resolved versions.

### Backend and simulation

- **Python >=3.12:** backend and executor language.
- **FastAPI 0.135.1:** HTTP routes, WebSocket endpoint and API documentation.
- **Uvicorn 0.41.0:** ASGI application server.
- **Pydantic 2.12.5:** scenario validation, typed models and schema generation.
- **Shapely 2.1.2:** polygon/line geometry and obstacle-clearance validation.
- **websockets 16.0:** WebSocket runtime dependency.
- **asyncio:** background scheduling and command/tick serialization.
- **Python standard library:** file paths, JSON, hashing and movement mathematics.

There is no SQL/NoSQL database, ORM, Redis, message queue, Celery worker, GPU dependency, PyTorch, Transformers, or llama.cpp integration in this implementation.

### Tooling and packaging

- **npm workspaces:** the root delegates JavaScript commands to `apps/web`.
- **pytest 9.0.2 and httpx 0.28.1:** backend tests and FastAPI TestClient support.
- **Playwright, declared `^1.58.2`:** browser acceptance tests.
- **Prettier, declared `^3.8.1`:** optional frontend formatting.
- **Docker / Docker Compose:** separate API and frontend containers.
- **PowerShell:** local Windows launcher.
- **Dependency locks:** reproducible installation inputs for both ecosystems.

The README specifies Node.js 22+ and a WebGL-capable browser. Docker uses Node 22 slim and Python 3.12 slim.

## 4. Architecture and data flow

```text
scenarios/urban-disaster.json
             |
             v
repository.py -> models.py validates definitions and geometry
             |
             v
SimulationService -> Engine -> WorldState + ordered events
       ^                           |
       |                           v
REST control requests       REST snapshots / WebSocket /ws
       ^                           |
       |                           v
Browser buttons <------ useMission.ts
                                  |
                                  v
                  MissionControl + Panels + MissionMap
                                             |
                                             v
                                  geo.ts -> GeoJSON / markers
```

**The backend is authoritative.** The browser displays the server state and sends commands; it does not independently advance the mission. A browser disconnect does not pause the running server mission. Reconnecting retrieves the scenario and receives a complete current state again.

The Python executor is separate from network and timing code. It imports the domain models from `apps/api/app/models.py`, so it is not a fully independent installed domain package, but its execution logic has no network calls or wall-clock dependency.

All tabs connected to one API process share one mission. There are no separate user sessions or independent mission IDs selected through the UI. Run one API worker: separate workers would each hold their own divergent in-memory mission.

## 5. Backend files in detail

### `main.py`: application boundary

FastAPI's lifespan handler loads the scenario, creates a `SimulationService`, stores it on `app.state.simulation`, and starts its asynchronous runner. Shutdown cancels the runner.

This file defines all application endpoints, configures CORS, checks WebSocket origins, and assembles audit exports. The export hash uses SHA-256 of the validated scenario serialized as sorted, compact JSON. It identifies normalized scenario content rather than the original file's whitespace or byte layout.

### `repository.py`: scenario storage adapter

Resolves the project root from the Python file location, reads `scenarios/urban-disaster.json`, and calls `Scenario.model_validate_json`. The filename is fixed. There is no scenario list, upload endpoint, editor API, or runtime switching facility.

Changing the scenario file requires reloading/restarting the backend to load it. Reset resets the already loaded scenario; it does not reread the file.

### `service.py`: scheduling and concurrency

Owns one `Engine`, one `asyncio.Lock`, and a revision counter. Commands and automatic ticks acquire the same lock. The runner waits 0.25 wall-clock seconds and advances the engine only while the mission is running.

Every command increments the revision, including a command that produces no engine state change. Every automatic advancement also increments it. Reset clears world state and events but preserves the service's increasing transport revision.

The scheduler targets approximately real-time execution. It does not compensate for delays or skip simulation ticks if the machine is busy.

### `models.py`: contracts and validation

Definitions include `Point`, `Region`, `Sector`, `UAVDefinition`, `TaskDefinition`, `Origin`, and `Scenario`. Runtime models include `UAVState`, `TaskState`, `Event`, and `WorldState`.

Unknown fields are forbidden and non-finite numeric values are rejected. Additional checks enforce:

- Globally unique IDs across sectors, regions, UAVs and tasks.
- Closed, valid, positive-area polygons inside the scenario boundary.
- Base and aircraft starting positions inside navigable space.
- Existing aircraft and sector references for tasks.
- Route starts matching each UAV's initial position or previous task destination.
- Route ends matching task locations.
- Nonzero routes fully inside the world boundary.
- Entire route segments avoiding hard obstacles buffered by 12 metres.

Water is excluded from hard-obstacle checks. JSON Schema documents structural constraints; custom Shapely checks still require Python validation. Schema-only validation cannot reproduce all world/geometry checks.

## 6. API reference

Default base URL: `http://127.0.0.1:8000`. Commands require no JSON request body.

- **`GET /api/health`** — returns `status: "ok"`, version `0.1.0`, and mode `single-operator`. This is a simple application health response, not a deep dependency diagnostic.
- **`GET /api/scenario`** — returns the validated static scenario: dimensions, origin, regions, sectors, UAV definitions, tasks and routes.
- **`GET /api/scenario/schema`** — generates the current `Scenario` JSON Schema directly from Pydantic.
- **`GET /api/state`** — returns the current world-state envelope.
- **`POST /api/control/run`** — starts a ready mission or resumes a paused one. Running/completed missions are unchanged by the engine.
- **`POST /api/control/pause`** — changes a running mission to paused; other states are unchanged.
- **`POST /api/control/step`** — advances exactly one 0.25-second tick from ready/paused and leaves the mission paused unless it completes. No advancement while running/completed.
- **`POST /api/control/reset`** — restores initial runtime entities, time and event history. Returns a fresh state envelope.
- **`GET /api/export`** — returns format/simulator versions, scenario hash, full scenario, state snapshot including events, and execution configuration.
- **`WS /ws`** — sends a full world envelope immediately and approximately every 250 ms, even while paused. This is outbound state streaming; controls use HTTP.
- **`GET /docs`** — FastAPI interactive Swagger UI.
- **`GET /redoc`** and **`GET /openapi.json`** — standard FastAPI documentation/schema routes enabled by the default application configuration.

Unsupported control names receive HTTP 422 from FastAPI's `Literal` validation. Valid but currently inapplicable actions are engine no-ops, not HTTP errors.

Envelope shape:

```text
schema_version: 1
type: "world_state"
revision: increasing integer for this service instance
scenario_id: "urban-disaster"
state:
  tick: integer
  simulation_time: seconds
  mission_status: READY | RUNNING | PAUSED | COMPLETED
  uavs: full aircraft runtime records
  tasks: full task runtime records
  events: complete ordered event history
```

An event contains `sequence`, `simulation_time`, `type`, `entity_ids`, and `message`. Implemented event types are `SCENARIO_LOADED`, `SIMULATION_STARTED`, `SIMULATION_PAUSED`, `TASK_DISPATCHED`, `TASK_STARTED`, `TASK_COMPLETED`, and `MISSION_COMPLETED`.

Example PowerShell requests, with the API running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/control/step
Invoke-RestMethod http://127.0.0.1:8000/api/state
```

## 7. Simulation mechanics

`packages/simulation/engine.py` defines `DT = 0.25` seconds.

For every tick, each UAV selects its first incomplete assigned task in scenario-array order. It dispatches a pending task, moves along its route, then accumulates service time at the destination. Separate UAVs progress during the same simulation tick, while each UAV's tasks remain sequential.

Movement budget is `speed_mps × 0.25`. A tick can traverse several short waypoint segments. Position changes by straight-line interpolation; heading is measured clockwise from north. Distances use local Cartesian metres, never geographic-coordinate distances.

On reaching a task, the task becomes `IN_PROGRESS` and the aircraft becomes `EXECUTING`. Service accrues on subsequent ticks; leftover movement budget is not converted to service time. After service completes, the aircraft can dispatch its next task on the following tick. The mission finishes once all tasks are complete, and all aircraft become `DONE`.

Mission states: `READY → RUNNING ↔ PAUSED → COMPLETED`, with Reset returning to `READY` and Step allowing advancement from `READY` or `PAUSED`.

Task states: `PENDING → EN_ROUTE → IN_PROGRESS → COMPLETED`.

Aircraft states: `AVAILABLE → EN_ROUTE → EXECUTING → AVAILABLE`, repeating for further tasks, then `DONE`.

Battery decreases by **0.002 percentage points per metre**, clamped to zero. Thus 1,000 m consumes 2 percentage points. No battery is consumed during service, and reaching zero does not implement emergency landing, stopping, or return-to-base behavior.

The engine contains no randomness. Seed 42 is metadata for future extensions. Identical scenario and command sequences produce deterministic simulated results; wall-clock scheduling and cross-platform floating-point bit identity are separate concerns.

## 8. Default scenario

The default scenario is `urban-disaster`, version `1.0.0`, named **Urban Disaster Search**.

- Area: 2,000 × 2,000 m, or 4 km².
- Display origin: longitude 79.86, latitude 6.92. Geometry is synthetic, not a surveyed map of that location.
- Six sectors: A1, A2, B1, B2, C1, C2.
- Twelve buildings, one floodplain, one no-fly zone, two debris fields and one blocked road.
- One base at local position `(220, 80)`.
- Three aircraft starting near the base at y = 140 m.

Aircraft definitions:

- **UAV-01:** starts `(160,140)`, speed 18 m/s, initial battery 85%, RGB capability metadata.
- **UAV-02:** starts `(220,140)`, speed 16 m/s, initial battery 75%, RGB and THERMAL capability metadata.
- **UAV-03:** starts `(280,140)`, speed 20 m/s, initial battery 90%, RGB capability metadata.

Task assignments and sequence:

- **TASK-01 / Search A1:** UAV-01, destination `(550,450)`, 12 seconds service.
- **TASK-02 / Search B1:** UAV-02, destination `(1050,850)`, 12 seconds service.
- **TASK-03 / Search C1:** UAV-03, destination `(1750,600)`, 12 seconds service.
- **TASK-04 / Inspect bridge:** UAV-01 after TASK-01, destination `(1150,1450)`, 20 seconds service.
- **TASK-05 / Search C2:** UAV-02 after TASK-02, destination `(1750,1550)`, 12 seconds service.

The four search tasks use type `AREA_SEARCH`; bridge inspection uses `INFRASTRUCTURE_INSPECTION`. These labels do not implement perception, victim detection, image processing, or full-area search. Completion means dwelling at a point for the configured duration. UAV capability strings are displayed metadata, not an allocation/feasibility algorithm.

## 9. Frontend implementation

### Page composition

`layout.tsx` supplies document metadata and loads global and MapLibre CSS. `page.tsx` renders `MissionControl`; `/simulator` re-exports that page.

`MissionControl.tsx` is a client component. It connects the transport hook to the header, controls, summary, fleet panel, map, task panel, event log, errors and loading state. It holds selected-entity state. The map is dynamically loaded with server rendering disabled.

`Panels.tsx` defines `FleetPanel`, `UAVCard`, `TaskPanel`, `TaskCard`, `EventLog`, and a clock-formatting helper. The inspector shows the selected aircraft or task. Events appear newest first in the UI although they are stored in chronological order.

### Transport and recovery

`useMission.ts` fetches the scenario and opens the WebSocket. It checks envelope version/type and ignores revisions older than its current revision. On connection, it resets its revision cursor so a restarted backend can be accepted.

Reconnect attempts use exponential delays of approximately 1, 2, 4 and then at most 8 seconds. HTTP requests have an 8-second timeout. Errors are displayed, and mission controls are disabled when connection/state/busy conditions require it. There is no HTTP polling fallback or offline simulator.

Export fetches `/api/export`, creates a browser Blob, and downloads `edgesar-audit.json`. It does not save server-side experiment records.

### Map and geography

`MissionMap.tsx` creates a flat MapLibre map with locally provided GeoJSON. Layers include boundary, sectors, buildings, water, debris, blocked road, hatched no-fly area, planned routes, flown tracks and selected-route highlighting. HTML markers label UAVs, tasks, hazards, sectors and base.

The user can pan, zoom, fit the area, select aircraft/tasks, and toggle sectors, hazards and routes. Telemetry updates move markers and update track data without rebuilding the map or resetting its camera. Map creation depends on scenario ID/version. WebGL failure produces an error message.

`geo.ts` converts local metres to display longitude/latitude using a small-area approximation around the scenario origin. It builds static GeoJSON and reconstructs flown tracks from authored routes, task state and accumulated distance. It is rendering logic, not a second mission executor.

No map tiles, map API keys, external font service, or basemap provider is needed for the mission screen at runtime. The map worker/shared modules are copied from the installed package before development/build. Initial package installation still needs available dependencies, and FastAPI's default documentation pages are separate from this frontend offline-runtime claim.

`types.ts` manually mirrors backend contracts; it is not generated from OpenAPI. Some frontend status fields are broad strings, and its scenario entities reuse runtime-oriented types. Keep these definitions synchronized when modifying Python contracts.

## 10. Storage, export and reproducibility

Persistent project inputs are JSON files. Active world state, waypoint cursors and events live only in Python memory. Restarting the backend starts a fresh mission. No database migrations, database credentials or database service are needed.

Audit export includes:

- Format version and simulator version.
- Canonical scenario SHA-256.
- Full validated scenario, including seed/version/routes.
- Current envelope, runtime entities and all events.
- Fixed timestep, scenario-defined assignment mode, authored planner label and battery rate.

Export is an inspectable audit snapshot. Import, restore, replay, snapshot branching, experiment persistence and model provenance are not implemented. Internal engine waypoint cursors are not provided as a supported restoration contract.

## 11. Running locally

From the project root, install dependencies if needed:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
npm ci
```

Backend terminal:

```powershell
.\.venv\Scripts\python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
npm run dev
```

Open `http://127.0.0.1:3000` or `/simulator`. API documentation is at `http://127.0.0.1:8000/docs`.

Optional combined Windows launcher:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

The launcher checks for the local Python executable, starts the backend in a hidden process, runs the frontend, and stops its backend process when the frontend command exits.

Production frontend commands:

```powershell
npm run build
npm run start --workspace apps/web
```

Configuration:

- `NEXT_PUBLIC_API_URL`: browser-visible backend URL; defaults to `http://127.0.0.1:8000`. Put a local override in `apps/web/.env.local`; production builds capture this value at build time.
- `CORS_ORIGINS`: comma-separated allowed frontend origins in the backend process environment. Defaults to `http://localhost:3000,http://127.0.0.1:3000`.

`.env.example` is explanatory; the backend does not explicitly load it or automatically load an arbitrary `.env` file.

Docker alternative:

```powershell
docker compose up --build
```

Compose publishes API port 8000 and frontend port 3000 on host loopback. Containers bind their own servers to `0.0.0.0`. The frontend URL points to the host address because requests originate in the user's browser. `depends_on` establishes startup ordering; no healthcheck/readiness policy is defined. There is no database container or persistent mission volume.

## 12. Tests and verification

Backend tests cover scenario counts/schema roundtrip, completion, exact repeated-run/reset results, commands, movement limits, battery accounting, obstacle intersections, service duration, assignment order, malformed scenarios, HTTP state/export, WebSocket handshake and WebSocket origin rejection.

`test_engine.py` includes a five-case parameterized validation test. Together with API tests, the checked-in suite accounts for the 12 backend tests recorded in the changelog.

```powershell
.\.venv\Scripts\python -m pytest -q
npm run check
npm run build
```

`npm run check` runs TypeScript only; it is not an ESLint command.

Browser acceptance requires both services already running. Playwright does not start them through a `webServer` configuration. The test resets shared mission state, checks map/entities/selection/layers, starts and pauses, verifies export, resets again, and writes desktop/mobile screenshots. It also checks mobile horizontal overflow and browser page errors.

```powershell
npx playwright install chromium
npm run test:e2e
```

Installed Edge can be selected with:

```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
```

The changelog records backend/type/build/browser checks passing on the implementation machine, using Edge for browser acceptance. It records Docker as not executed. These are existing recorded results, not fresh verification performed while writing this guide.

## 13. Current boundaries and implementation details to remember

- Assignments and routes are authored, not optimized or decided at runtime.
- No automatic route planning, A*, CBBA, bids, consensus or task reassignment exists.
- No model loading, prompts, inference API, GGUF files or FP16/Q8/Q4 experiments exist.
- There is no dynamic incident discovery, scenario editor or real perception pipeline.
- Buildings, debris, blocked roads and no-fly polygons are conservatively treated as 2D flight obstacles; altitude is not modeled.
- Static obstacle clearance is checked, but UAV-to-UAV collision avoidance is absent.
- Aircraft stop at final task positions; there is no automatic return-to-base.
- Search service does not measure sector coverage or rescue success.
- Battery is illustrative and has no operational depletion policy.
- CORS and WebSocket origin checks are not authentication. WebSocket clients without an Origin header are allowed. There are no user accounts, access tokens, ownership checks or rate limits.
- Every snapshot includes the full event history. Longer/unbounded missions would need a different history/streaming strategy.
- Several labels are specific to the default scenario: three aircraft, five tasks, seed 42, a 2 km map extent, and the engine's final "All five task points" message. Generalizing scenario data also requires reviewing these assumptions.
- A task's sector reference must exist, but validation does not enforce that the task point lies inside that sector or matches aircraft capabilities.
- Lockfiles and recorded checks improve reproducibility; they do not establish real-world flight safety or validate future research conclusions.

## 14. Where to make future changes

- **Dashboard/layout/style:** `MissionControl.tsx`, `Panels.tsx`, `globals.css`.
- **Map visualization:** `MissionMap.tsx`, `geo.ts`.
- **Browser networking or reconnect:** `useMission.ts`.
- **API endpoints or export:** `main.py`.
- **Command scheduling or revisions:** `service.py`.
- **Schema and validation:** `models.py`, then regenerate `scenario.schema.json` and update frontend `types.ts`.
- **Movement/task execution/battery:** `packages/simulation/engine.py` and its tests.
- **Scenario geometry, routes and initial entities:** `urban-disaster.json`; update `create_scenario.py` too if it remains the fixture authoring source.
- **New storage mechanism:** extend the repository/service boundary rather than introducing database calls into movement logic.
- **Future research pipeline:** separate semantic task proposals, allocation, route planning and execution. Current docs describe these boundaries but contain no implemented plugins for them.

Generate the structural schema from the root with `python -m scripts.generate_schema`. Run `python -m scripts.create_scenario` only when intentionally regenerating the committed default scenario; it overwrites that fixture.

For an efficient source walkthrough, read `README.md`, `models.py`, `engine.py`, `service.py`, `main.py`, `useMission.ts`, `MissionControl.tsx`, then `MissionMap.tsx` and the tests.
