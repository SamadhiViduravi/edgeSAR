# API v1

Base: `http://127.0.0.1:8000`. Interactive OpenAPI at `/docs`.

- `GET /api/health`: version and service health.
- `GET /api/scenario`: validated scenario definition.
- `GET /api/scenario/schema`: authoritative Pydantic-generated JSON Schema.
- `GET /api/state`: current world envelope.
- `POST /api/control/run`: starts or resumes; idempotent while running/completed.
- `POST /api/control/pause`: pauses a running mission.
- `POST /api/control/step`: advances one tick while ready/paused; no-op when running/completed.
- `POST /api/control/reset`: restores initial world including events.
- `GET /api/export`: exact scenario, hash, engine configuration, current state/events.
- `WS /ws`: immediate state then snapshots every 250 ms. Browser origins restricted to CORS_ORIGINS.

Envelope:

```json
{
  "schema_version": 1,
  "type": "world_state",
  "revision": 0,
  "scenario_id": "urban-disaster",
  "state": {
    "tick": 0,
    "simulation_time": 0,
    "mission_status": "READY",
    "uavs": [],
    "tasks": [],
    "events": []
  }
}
```

Empty arrays above illustrate the schema only; the service sends all entities. Scenario contract is in `scenarios/scenario.schema.json`. Runtime fields are in `models.py`. Event: sequence, simulation_time, type, entity_ids, message. Full snapshots repair missing updates after reconnect. Revisions are monotonic within a process; reconnect resets the browser's revision cursor to accept a restarted backend.

One local mission is shared across tabs. Commands are serialized, but there is no multi-user session ownership or authorization. API state and audit exports are read atomically on the event loop. Event log is bounded by this finite scenario; generalized indefinite simulations will require pagination/backpressure.
