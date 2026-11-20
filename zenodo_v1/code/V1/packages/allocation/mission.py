"""Step 5: fly one mission and measure what happened.

Inputs
  table : the task table the allocator works from (made from ONE arm: gold, FP16 or Q4)
  truth : the real victims = {landmark: camera that is really needed}. We take it from the gold table.

Rules (all of them are choices we must write in the report)
  - All tasks are known at time 0. UAVs fly in straight lines (no obstacles) at constant speed.
  - A visit takes DWELL seconds. The victim counts as verified when the visit ends.
  - The camera must work: needed THERMAL -> the UAV must carry THERMAL. Needed RGB -> must carry RGB.
    Needed ANY -> any UAV works. Wrong camera = the UAV sees nothing, the task goes back to the
    waiting list, and that UAV may not try that task again.
  - A task where nobody is really there = a wasted visit (a false alarm).
  - A victim with no task in the table is never visited (missed).
"""
from packages.allocation.cbba import allocate
from packages.allocation.world import LANDMARKS, travel_time

DWELL = 12.0       # seconds per visit (same as the service time in V1)
HORIZON = 600.0    # seconds. A victim not verified by then is MISSED.


def sees(uav, needed):
    return needed == "ANY" or needed in uav.sensors


def run_mission(uavs, table, truth, horizon=HORIZON):
    pending = {t["id"]: t for t in table}          # tasks waiting for a UAV
    banned = {}                                    # task_id -> set of UAV ids that failed there
    position = {u.id: u.start for u in uavs}
    free_at = {u.id: 0.0 for u in uavs}
    requeue = []                                   # (time, task) failed visits that come back
    verified = {}                                  # landmark -> time of verification
    visits = []                                    # log of every flight
    now = 0.0
    while now <= horizon:
        for item in [r for r in requeue if r[0] <= now]:      # failed tasks come back
            requeue.remove(item)
            pending[item[1]["id"]] = item[1]
        free = [u for u in uavs if free_at[u.id] <= now]
        if free and pending:
            assignment, _ = allocate(free, list(pending.values()), position, now, banned)
            for u in free:
                task_id = assignment[u.id]
                if task_id is None:
                    continue
                task = pending.pop(task_id)
                spot = task["landmark"]
                arrive = now + travel_time(u, position[u.id], LANDMARKS[spot])
                finish = arrive + DWELL
                if spot not in truth or spot in verified:
                    result = "empty"                                 # nobody there (or already found)
                elif sees(u, truth[spot]):
                    result = "verified"
                    verified[spot] = finish
                else:
                    result = "failed"                                # wrong camera
                    banned.setdefault(task_id, set()).add(u.id)
                    requeue.append((arrive, task))
                visits.append({"uav": u.id, "task": task_id, "landmark": spot, "start": now,
                               "arrive": arrive, "finish": finish, "result": result})
                position[u.id] = LANDMARKS[spot]
                free_at[u.id] = finish
        later = [t for t in list(free_at.values()) + [r[0] for r in requeue] if t > now]
        if not later or (not pending and not requeue):
            break
        now = min(later)
    times = {spot: verified.get(spot) for spot in truth}
    score = [t if t is not None else horizon for t in times.values()]
    return {
        "verify_time": times,                                         # None = missed
        "missed": sum(t is None for t in times.values()),
        "rmivt": sum(score) / len(score) if score else 0.0,           # mean verification time, missed = horizon
        "wasted": sum(v["result"] in ("empty", "failed") for v in visits),
        "visits": visits,
    }