# EdgeSAR Lab — Phase 1 design

## Assessment and scope

V1 starts empty. Node 22 and Python 3.12 are installed. This phase delivers a local, single-operator mission simulator, not an operational flight system. There is no CBBA, semantic engine, incident discovery, experiment comparison or learned perception. Fixed assignments and authored routes are explicitly labelled. Route following is included to make Run/Pause meaningful; general path planning belongs to Phase 2.

## 1. Exact frontend component tree

```
RootLayout
└── SimulatorPage (client boundary)
    └── MissionControl
        ├── MissionHeader (identity, scenario, connection, Run/Pause/Step/Reset)
        ├── MissionSummary (clock, tasks complete, fleet distance, mission state)
        ├── FleetPanel → UAVCard × 3
        ├── MissionMap (MapLibre instance; authoritative state → GeoJSON)
        │   ├── map navigation + fit controls
        │   ├── HTML entity labels (UAVs/tasks/base/sectors/hazards)
        │   └── MapLegend (layer visibility)
        ├── TaskPanel → TaskCard × 5 + selected entity detail
        └── EventLog (ordered events, entity selection, JSON audit export)
```

One transport hook owns initial fetch, WebSocket reconnect and command requests. React owns selection/layer visibility; the server owns simulation. No simulation advancement in React. Map initializes once and updates sources without resetting camera. No remote tiles, fonts or map API keys.

## 2. Backend domain models

Pydantic v2 strict-extra models: Point(x,y metres); Region(id,label,kind,polygon); Sector(id,label,polygon); UAVDefinition(id,position,speed_mps,battery_percent,capabilities,color); TaskDefinition(id,label,type,location,assigned_uav_id,route,service_seconds,sector_id optional); Scenario(schema_version,id,version,name,seed,width_m,height_m,origin,base,sectors,regions,uavs,tasks).

Runtime: UAVState adds status, heading_deg, distance_m, current_task_id and position; TaskState adds status and service_elapsed; WorldState contains tick, simulation_time, mission_status, UAV/task arrays and ordered events. Event records contain sequence, simulation_time, type, entity_ids and message. A simulation service owns a pure deterministic engine and a command lock. No module-global mutable world state; lifespan owns the service. A repository loads and validates scenario files.

## 3. Scenario JSON schema

Canonical schema is generated from Scenario.model_json_schema() into scenarios/scenario.schema.json and exposed at GET /api/scenario/schema. Coordinates are local metres, east/north, within [0,2000]². Polygons are closed simple rings. IDs are unique, assignments reference existing UAVs, sector references exist, endpoints equal task locations. Routes are ordered per UAV in task array order, begin at the preceding destination, and must clear blocked polygons by 12 m. Buildings, debris, blocked-road and no-fly regions block navigation. Water is an overflight-permitted visual hazard, never an implicit aerial obstacle. Definition validation rejects invalid geometry and unsafe routes before the server starts.

## 4. GeoJSON layer strategy

Convert local metres to geographic coordinates around the scenario origin; this is a small-area visualization transform, never used for physical distance. Backend uses Cartesian metres. Render bottom to top: background; six sector fills/outlines; boundary; flood fill/outline; buildings fill/outline; debris and blocked-road fill/outline; no-fly translucent red fill with diagonal stripes and strong dashed border; route dark casing then UAV-colored route line; traveled tracks; task circles; UAV heading markers; base marker. HTML labels avoid network glyph dependencies. Task numbers and UAV IDs supplement color. Route casing preserves contrast over every obstacle. Selection highlights a route and its task/UAV. Legend controls hazards, sectors and routes independently. Fit extent restores the complete 2 km square.

## 5. WebSocket and HTTP contract

GET /api/scenario, /api/scenario/schema, /api/state, /api/health, /api/export. POST /api/control/{run|pause|step|reset}. WS /ws emits `{schema_version:1,type:"world_state",revision:number,scenario_id:string,state:WorldState}` immediately on connection, then at 4 Hz. Full snapshots are intentionally small and self-healing; revision increases monotonically, including reset. Events are ordered by deterministic sequence. Reset resets simulation tick/events, not transport revision. Browser ignores stale revisions and reconnects with bounded exponential backoff. Controls are serialized with ticks. Errors use HTTP error responses, surfaced visibly; failed sockets never produce invented state. State is in memory; export saves scenario + current snapshot + all events. Restart resets the session.

## 6. Folder structure

```
apps/api/app/{main.py,models.py,repository.py,service.py}
apps/api/tests/{test_engine.py,test_api.py}
apps/web/{app,components,lib,hooks,tests}
packages/simulation/engine.py
scenarios/{urban-disaster.json,scenario.schema.json}
scripts/{generate_schema.py,dev.ps1}
docs/{PHASE_1_DESIGN.md,ARCHITECTURE.md,SIMULATION_MODEL.md,API.md,REPRODUCIBILITY.md}
README.md, CHANGELOG.md, pyproject.toml, package.json, docker-compose.yml
```

Future allocation, planning and semantic packages are separate interfaces when implemented, not fake empty integrations today.

## 7. Milestones

1. Commit design artifact, schemas and reproducible project setup.
2. Validate synthetic scenario: 12 buildings, flood, no-fly, two debris regions, blocked road, six sectors, base, three UAVs and five tasks.
3. Implement deterministic 0.25-second ticks, fixed assignment execution, service duration, pause/step/reset and audit events.
4. Implement REST/WebSocket boundary and contract tests.
5. Implement map-first responsive UI with high-contrast routes, labels, obstacle patterns, panels, selection and reconnect/error states.
6. Run backend tests, TypeScript/build checks and browser workflow checks; document local/Docker commands and limitations.

## 8. Acceptance criteria

- Fresh installs run using README commands; backend health and frontend return HTTP 200.
- Initial map shows a 2 km square, all six labelled sectors, 12 buildings, water, no-fly, two debris regions, blocked road, base, three UAVs and five numbered tasks.
- All five routes are visible before Run and avoid inflated hard obstacles. Water is labelled overflight allowed.
- Map pans/zooms, fits extent, toggles layers and selects UAVs/tasks without losing camera.
- Run advances authoritative time and position; Pause freezes it; Step advances exactly one tick while paused; Reset restores initial entities and deterministic event history.
- All tasks eventually complete in explicit scenario assignment order; mission stops automatically. Completion means servicing a task point, not full sector coverage.
- Repeated executions yield identical state/event output; route segment safety and service duration tests pass.
- Disconnect is visible; reconnection restores current state and controls report failures.
- Audit JSON includes exact scenario, seed, current state and ordered event log. No fabricated research metrics.
- Panels remain usable at laptop and narrow screen sizes; controls have accessible labels, focus states and status text.

## Dependencies and risks

Next.js/React/TypeScript, MapLibre and Lucide for UI; FastAPI/Pydantic/Uvicorn/Shapely for API and geometry; pytest/httpx for backend; Playwright for browser acceptance. Lock npm dependencies and freeze Python versions. Deliberately defer charting, DB, ML and allocation dependencies. Risks: WebGL availability (show error), socket interruption (reconnect), unsafe authored routes (startup validation), accidental wall-clock nondeterminism (fixed ticks), and misleading sector coverage (point-service semantics explicitly shown).
