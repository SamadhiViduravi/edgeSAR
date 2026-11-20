"""Versioned scenario contract. All physical calculations use local metres."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import Polygon, LineString, Point as ShapePoint


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Point(Model):
    x: float
    y: float

    def xy(self) -> tuple[float, float]:
        return self.x, self.y


class Region(Model):
    id: str
    label: str
    kind: Literal["building", "water", "no_fly", "debris", "blocked_road"]
    polygon: list[Point] = Field(min_length=4)


class Sector(Model):
    id: str
    label: str
    polygon: list[Point] = Field(min_length=4)


class UAVDefinition(Model):
    id: str
    position: Point
    speed_mps: float = Field(gt=0, le=30)
    battery_percent: float = Field(gt=0, le=100)
    capabilities: list[str]
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class TaskDefinition(Model):
    id: str
    label: str
    type: Literal["AREA_SEARCH", "INFRASTRUCTURE_INSPECTION"]
    location: Point
    assigned_uav_id: str
    route: list[Point] = Field(min_length=2)
    service_seconds: float = Field(gt=0)
    sector_id: str | None = None


class Origin(Model):
    longitude: float = Field(ge=-170, le=170)
    latitude: float = Field(ge=-80, le=80)


class Scenario(Model):
    schema_version: Literal[1]
    id: str
    version: str
    name: str
    seed: int
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    origin: Origin
    base: Point
    sectors: list[Sector]
    regions: list[Region]
    uavs: list[UAVDefinition] = Field(min_length=1)
    tasks: list[TaskDefinition]

    @model_validator(mode="after")
    def validate_world(self):
        boundary = Polygon([(0, 0), (self.width_m, 0), (self.width_m, self.height_m), (0, self.height_m)])
        ids = [item.id for group in (self.sectors, self.regions, self.uavs, self.tasks) for item in group]
        if len(set(ids)) != len(ids):
            raise ValueError("Entity IDs must be globally unique")
        obstacles = []
        for item in [*self.regions, *self.sectors]:
            ring = [p.xy() for p in item.polygon]
            shape = Polygon(ring)
            if ring[0] != ring[-1] or not shape.is_valid or shape.area <= 0 or not boundary.covers(shape):
                raise ValueError(f"Invalid polygon: {item.id}")
            if isinstance(item, Region) and item.kind != "water":
                obstacles.append(shape.buffer(12))
        ends = {u.id: u.position for u in self.uavs}
        for p in [self.base, *ends.values()]:
            if not boundary.covers(ShapePoint(p.xy())) or any(o.intersects(ShapePoint(p.xy())) for o in obstacles):
                raise ValueError("Base/UAV start is outside navigable space")
        for task in self.tasks:
            if task.assigned_uav_id not in ends:
                raise ValueError("Unknown assigned UAV")
            if task.sector_id and task.sector_id not in {s.id for s in self.sectors}:
                raise ValueError("Unknown sector")
            if task.route[0] != ends[task.assigned_uav_id] or task.route[-1] != task.location:
                raise ValueError(f"Route endpoints do not match task sequence: {task.id}")
            line = LineString([p.xy() for p in task.route])
            if line.length == 0 or not boundary.covers(line) or any(line.intersects(o) for o in obstacles):
                raise ValueError(f"Route violates obstacle clearance or boundary: {task.id}")
            ends[task.assigned_uav_id] = task.location
        return self


class UAVState(UAVDefinition):
    status: Literal["AVAILABLE", "EN_ROUTE", "EXECUTING", "DONE"] = "AVAILABLE"
    heading_deg: float = 0
    distance_m: float = 0
    current_task_id: str | None = None


class TaskState(TaskDefinition):
    status: Literal["PENDING", "EN_ROUTE", "IN_PROGRESS", "COMPLETED"] = "PENDING"
    service_elapsed: float = 0


class Event(Model):
    sequence: int
    simulation_time: float
    type: str
    entity_ids: list[str]
    message: str


class WorldState(Model):
    tick: int = 0
    simulation_time: float = 0
    mission_status: Literal["READY", "RUNNING", "PAUSED", "COMPLETED"] = "READY"
    uavs: list[UAVState]
    tasks: list[TaskState]
    events: list[Event] = Field(default_factory=list)
