# EdgeSAR Lab

**Multi-UAV Search-and-Rescue Simulation and Quantized Semantic Decision Evaluation Platform**

Phase 1 is a runnable, map-first mission simulator: Next.js + FastAPI + MapLibre, one 2 km × 2 km synthetic scene, three UAVs, six sectors, twelve buildings, floodplain, no-fly zone, two debris fields, blocked road, base and five static tasks.

The long-term research question is whether changes in a quantized model's semantic decisions propagate through decentralized allocation into measurable mission consequences. **This phase contains no CBBA, Llama, semantic decisions or precision comparison.** Its routes and assignments are authored explicitly in the scenario.

## Run locally (Windows PowerShell)

Prerequisites: Node.js 22+, Python 3.12+, WebGL-capable browser. Run commands from this V1 repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
npm ci
```

If your environment forces offline installation, allow network access and set `$env:PIP_NO_INDEX='0'` for pip or use `npm ci --offline=false`. If Python's bundled ensurepip is unavailable, create the environment with `python -m venv --without-pip .venv`, then use `python -m pip --python .venv install -r requirements.lock`.

Terminal 1:

```powershell
.\.venv\Scripts\python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm run dev
```

Open http://127.0.0.1:3000 (also `/simulator`). API docs: http://127.0.0.1:8000/docs. For macOS/Linux, use `.venv/bin/python` in place of the Windows interpreter path. Keep one API worker: this local phase owns one in-memory shared mission.

Optional Windows launcher: `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1`. It runs both services, waits for Ctrl+C, and stops its backend on exit.

## Operate the mission

The default scenario loads automatically from `scenarios/urban-disaster.json`. Before running, inspect the five dashed planned routes. Colors match the UAV cards; labels and numbered markers distinguish entities independently of color. Hard obstacles have a 12 m route clearance. Water permits overflight. Click an aircraft or task to inspect its state and highlight its routes. Use map zoom, drag, Fit area and layer checkboxes.

Run starts fixed 0.25-second ticks at 1× wall-clock rate. Pause freezes simulated time; Step advances exactly one tick while ready/paused; Reset restores the initial state. All five tasks finish automatically in roughly four minutes. Solid route segments show distance flown. Task service is at a point, **not a sector coverage algorithm**. UAVs remain at their final task locations; automatic return-to-base is not implemented.

Export audit JSON downloads the exact scenario, scenario SHA-256, execution configuration, state and event history. Restarting the backend resets memory. Export is an audit snapshot, not an implemented restore/replay system.

## Checks

```powershell
.\.venv\Scripts\python -m pytest -q
npm run check
npm run build
```

Browser acceptance (start both services first):

```powershell
npx playwright install chromium
npm run test:e2e
```

On this Windows machine the acceptance test was verified with installed Edge:
```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
```

Production frontend: `npm run build` then `npm run start --workspace apps/web`. Docker alternative: `docker compose up --build`. The browser-facing backend URL defaults to `http://127.0.0.1:8000`; configure `NEXT_PUBLIC_API_URL` at frontend build time if necessary. Set `CORS_ORIGINS` to the exact frontend origin(s). No map tiles, map keys, cloud services or external fonts are needed at runtime.

## Architecture and responsibility boundaries

- `apps/web`: presentation, selection, WebSocket recovery and GeoJSON conversion; no simulation logic.
- `apps/api/app`: validated domain contracts, file repository, serialized simulation service, REST/WebSocket boundary.
- `packages/simulation`: deterministic executor without wall clock or network dependencies.
- `scenarios`: versioned local-metre JSON and generated JSON Schema.
- `docs/PHASE_1_DESIGN.md`: all eight design deliverables, milestones and acceptance criteria written before implementation.

Future semantic engines propose **what** tasks should exist, CBBA determines **which** UAV performs them, a planner determines **how** to reach them, and the executor follows approved routes. None of these future components is represented as implemented today.

## Reproducibility and limitations

Identical scenario + command sequence produces identical state and event history. The seed is stored for future stochastic extensions; this phase consumes no random numbers. Distances use Cartesian metres; latitude/longitude is only a display transform. Battery consumption is an illustrative 0.002 percentage points/metre and is not field-calibrated. The engine is mission-level, with no aerodynamic, sensor, flight-safety or real-world validation, no UAV-to-UAV deconfliction, no authentication and no persistent experiment database. Bind locally; shared/public deployment needs a separate security and session design.

Pilot experiments, llama.cpp configuration, GGUF registration, scenario editing, CBBA and snapshot restore are later phases and have no runnable commands yet. Future models receive structured text observations; imagery would require a separate perception adapter. No research conclusions about FP16/Q8/Q4 are claimed.

See `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/SIMULATION_MODEL.md`, `docs/REPRODUCIBILITY.md` and `CHANGELOG.md`.
