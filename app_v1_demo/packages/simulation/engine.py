"""Pure fixed-tick executor. No wall clock, I/O, random globals or allocation logic."""
import math
from apps.api.app.models import Event, Point, Scenario, TaskState, UAVState, WorldState

DT = 0.25


class Engine:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario.model_copy(deep=True)
        self.reset()

    def reset(self):
        self.state = WorldState(
            uavs=[UAVState(**u.model_dump()) for u in self.scenario.uavs],
            tasks=[TaskState(**t.model_dump()) for t in self.scenario.tasks],
        )
        self.waypoints: dict[str, int] = {}
        self.emit("SCENARIO_LOADED", [], "Scenario loaded · authored routes / fixed assignments")

    def emit(self, kind: str, ids: list[str], message: str):
        self.state.events.append(Event(sequence=len(self.state.events) + 1,
            simulation_time=self.state.simulation_time, type=kind, entity_ids=ids, message=message))

    def command(self, action: str):
        if action == "reset":
            self.reset()
        elif action == "run" and self.state.mission_status in ("READY", "PAUSED"):
            self.state.mission_status = "RUNNING"
            self.emit("SIMULATION_STARTED", [], "Mission running")
        elif action == "pause" and self.state.mission_status == "RUNNING":
            self.state.mission_status = "PAUSED"
            self.emit("SIMULATION_PAUSED", [], "Mission paused")
        elif action == "step" and self.state.mission_status in ("READY", "PAUSED"):
            self.state.mission_status = "PAUSED"
            self.advance()

    def advance(self):
        if self.state.mission_status not in ("RUNNING", "PAUSED"):
            return
        self.state.tick += 1
        self.state.simulation_time = self.state.tick * DT
        for uav in self.state.uavs:
            task = next((t for t in self.state.tasks if t.assigned_uav_id == uav.id and t.status != "COMPLETED"), None)
            if task is None:
                uav.status = "DONE"
                uav.current_task_id = None
                continue
            uav.current_task_id = task.id
            if task.status == "PENDING":
                task.status = "EN_ROUTE"
                uav.status = "EN_ROUTE"
                self.waypoints[task.id] = 1
                self.emit("TASK_DISPATCHED", [uav.id, task.id], f"{uav.id} → {task.label} (fixed assignment)")
            if task.status == "IN_PROGRESS":
                task.service_elapsed = min(task.service_seconds, task.service_elapsed + DT)
                if task.service_elapsed >= task.service_seconds:
                    task.status = "COMPLETED"
                    uav.current_task_id = None
                    uav.status = "AVAILABLE"
                    self.emit("TASK_COMPLETED", [uav.id, task.id], f"{task.label} · point service complete")
                continue
            remaining = uav.speed_mps * DT
            while remaining > 0 and self.waypoints[task.id] < len(task.route):
                target = task.route[self.waypoints[task.id]]
                dx, dy = target.x - uav.position.x, target.y - uav.position.y
                distance = math.hypot(dx, dy)
                if distance < 1e-9:
                    self.waypoints[task.id] += 1
                    continue
                travel = min(remaining, distance)
                uav.heading_deg = math.degrees(math.atan2(dx, dy)) % 360
                uav.position = Point(x=uav.position.x + dx * travel / distance, y=uav.position.y + dy * travel / distance)
                uav.distance_m += travel
                # Explicit illustrative energy model; no field-calibrated battery claims.
                uav.battery_percent = max(0, uav.battery_percent - travel * 0.002)
                remaining -= travel
                if travel >= distance:
                    uav.position = target.model_copy()
                    self.waypoints[task.id] += 1
            if self.waypoints[task.id] == len(task.route):
                task.status = "IN_PROGRESS"
                uav.status = "EXECUTING"
                self.emit("TASK_STARTED", [uav.id, task.id], f"{uav.id} servicing {task.label}")
        if all(t.status == "COMPLETED" for t in self.state.tasks):
            for uav in self.state.uavs:
                uav.status = "DONE"
                uav.current_task_id = None
            self.state.mission_status = "COMPLETED"
            self.emit("MISSION_COMPLETED", [], "All five task points serviced · mission complete")
