import asyncio
from packages.simulation.engine import DT, Engine


class SimulationService:
    def __init__(self, scenario):
        self.engine = Engine(scenario)
        self.lock = asyncio.Lock()
        self.revision = 0

    def envelope(self):
        return {"schema_version": 1, "type": "world_state", "revision": self.revision,
                "scenario_id": self.engine.scenario.id, "state": self.engine.state.model_dump()}

    async def command(self, action):
        async with self.lock:
            self.engine.command(action)
            self.revision += 1
            return self.envelope()

    async def run(self):
        while True:
            await asyncio.sleep(DT)
            async with self.lock:
                if self.engine.state.mission_status == "RUNNING":
                    self.engine.advance()
                    self.revision += 1
