"""
Core types shared by the allocator, the simulator and the Shield.

Fleet and map come from the V1 world.py (pinned by SHA-256). Sensors in the reports are RGB / THERMAL / ANY.
A task asks for a set of cameras:  ANY -> {} (every UAV can do it),  RGB -> {RGB},  THERMAL -> {THERMAL}.
A UAV can do a task when the task's cameras are a subset of the UAV's cameras (V1 rule, written as sets so a cover task
that must satisfy two candidates can ask for {RGB, THERMAL}, which only UAV-02 can do).
"""
import importlib.util
from dataclasses import dataclass, field
from functools import lru_cache

from . import paths

# ---- research constants (same values as V1 bids.py / mission.py; listed in the plan, section 6)
PRIORITY_VALUE = {1: 1.0, 2: 2.0, 3: 3.0}
TIME_DISCOUNT = 0.01          # per second
DWELL_S = 12.0                # seconds per visit
DEADLINE_S = {1: 480.0, 2: 360.0, 3: 240.0}     # plan section 5 defaults (frozen in M7)
AFTER_LAST_S = 600.0          # horizon = last report time + 600 s


def req_of(sensor):
    """'ANY' -> frozenset(), 'RGB' -> {'RGB'}, 'THERMAL' -> {'THERMAL'}."""
    return frozenset() if sensor == "ANY" else frozenset([sensor])


def sensor_of(req):
    """Back to a report-style name. A set with two cameras can only be met by a UAV that has both; name it by its parts."""
    if not req:
        return "ANY"
    return "+".join(sorted(req))


@dataclass(frozen=True)
class Task:
    key: str            # unique, e.g. "c0123:I3"
    landmark: str
    req: frozenset      # cameras that are needed
    pri: int            # 1..3  (3 = most urgent)


@dataclass(frozen=True)
class Agent:
    id: str
    speed: float
    sensors: frozenset
    pos: tuple          # where the UAV is when it becomes free
    avail: float        # absolute time when it becomes free


@dataclass
class Problem:
    now: float
    agents: tuple
    tasks: tuple
    banned: dict = field(default_factory=dict)        # task key -> set of agent ids that must not take it
    dwell: float = DWELL_S
    landmarks: dict = None


@dataclass
class Plan:
    paths: dict          # agent id -> [task key, ...] in execution order
    arrive: dict         # task key -> predicted arrival time (absolute)
    finish: dict         # task key -> arrival + dwell
    owner: dict          # task key -> agent id
    unassigned: list     # task keys nobody could take
    info: dict           # rounds, passes, converged, warps, releases, ...


@lru_cache(maxsize=1)
def v1_world():
    """The V1 world module (landmarks, UAVs, travel_time), loaded straight from its pinned file."""
    p = paths.V1 / "packages" / "allocation" / "world.py"
    want = paths.PINS["V1/packages/allocation/world.py"]
    if paths.sha256_file(p) != want:
        raise SystemExit("V1 world.py is not the audited version. Stop.")
    spec = importlib.util.spec_from_file_location("edgesar_v1_world", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def landmarks():
    return dict(v1_world().LANDMARKS)


def fleet(pos=None):
    """The three UAVs as planning agents, all free at time 0 at their start positions."""
    w = v1_world()
    return tuple(Agent(u.id, float(u.speed), frozenset(u.sensors), tuple(u.start), 0.0) for u in w.UAVS)


def uav_specs():
    return {u.id: u for u in v1_world().UAVS}


def travel(speed, a, b):
    import math
    return math.dist(a, b) / speed
