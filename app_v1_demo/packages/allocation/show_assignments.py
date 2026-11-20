"""Print who gets which task, for the 5 demo cases and the 3 arms (gold, FP16, Q4)."""
from packages.allocation.cbba import allocate
from packages.allocation.decisions import ARMS, apply_decision, load_case, load_decision
from packages.allocation.world import UAVS

START = {u.id: u.start for u in UAVS}

for case_id in ["c0618", "c0119", "c1189", "c0093", "c0047"]:
    case = load_case(case_id)
    print(f"\n=== {case_id}: {case['text']}")
    for arm in ARMS:
        table = apply_decision(case, load_decision(arm, case))
        assignment, rounds = allocate(UAVS, table, START)
        print(f"  {arm}  (agreed after {rounds} round(s))")
        for uav_id, task_id in assignment.items():
            task = next((t for t in table if t["id"] == task_id), None)
            what = f"{task['landmark']} / {task['sensor']} / priority {task['priority']}" if task else "nothing"
            print(f"      {uav_id} -> {what}")
        for t in table:
            if t["id"] not in assignment.values():
                print(f"      WAITING: {t['landmark']} / {t['sensor']} / priority {t['priority']}")