import asyncio
import hashlib
import json
import os
from contextlib import asynccontextmanager, suppress
from typing import Literal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .models import Scenario
from .repository import load_scenario
from .service import SimulationService
from .allocation_routes import router as allocation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.simulation = SimulationService(load_scenario())
    runner = asyncio.create_task(app.state.simulation.run())
    yield
    runner.cancel()
    with suppress(asyncio.CancelledError):
        await runner


app = FastAPI(title="EdgeSAR Lab", version="0.1.0", lifespan=lifespan)
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(allocation_router)

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0", "mode": "single-operator"}


@app.get("/api/scenario")
def scenario():
    return app.state.simulation.engine.scenario


@app.get("/api/scenario/schema")
def schema():
    return Scenario.model_json_schema()


@app.get("/api/state")
async def state():
    return app.state.simulation.envelope()


@app.post("/api/control/{action}")
async def control(action: Literal["run", "pause", "step", "reset"]):
    return await app.state.simulation.command(action)


@app.get("/api/export")
async def export():
    service = app.state.simulation
    async with service.lock:
        definition = service.engine.scenario.model_dump()
        snapshot = service.envelope()
        canonical = json.dumps(definition, sort_keys=True, separators=(",", ":"))
        return {"format_version": 1, "simulator_version": "0.1.0", "scenario_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                "scenario": definition, "snapshot": snapshot,
                "execution": {"dt_seconds": 0.25, "assignment": "scenario-defined", "planner": "authored", "battery_percent_per_m": 0.002}}


@app.websocket("/ws")
async def updates(socket: WebSocket):
    if socket.headers.get("origin") not in [*origins, None]:
        await socket.close(code=1008)
        return
    await socket.accept()
    try:
        while True:
            await socket.send_json(app.state.simulation.envelope())
            await asyncio.sleep(0.25)
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
