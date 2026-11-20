"""Step 7: package the 5 demo cases x 3 arms as plain data, so the frontend can draw them."""
from functools import lru_cache

from packages.allocation.decisions import ARMS, apply_decision, load_case, load_decision
from packages.allocation.mission import DWELL, HORIZON, run_mission
from packages.allocation.world import BASE, LANDMARKS, UAVS

CASES = ["c0618", "c0119", "c1189", "c0093", "c0047"]
UAV_COLORS = {"UAV-01": "#51dec5", "UAV-02": "#bb9bff", "UAV-03": "#ffc66d"}   # same colours as V1

ASSUMPTIONS = [
    "Mechanism POC on 5 selected cases. This is an illustration, not statistical evidence.",
    "All tasks are known at time 0. The final study will create tasks while the mission runs.",
    "Simplified CBBA: each UAV holds one task, and all UAVs hear each other perfectly.",
    "UAVs fly in straight lines at constant speed. Obstacles are ignored.",
    "Truth = the gold table (POC shortcut). The final study needs its own hidden truth per case.",
    "A 'cannot confirm' report is treated as a real person. Chosen after seeing POC results.",
    "A UAV that arrives with the wrong camera is banned from that task. Other UAVs may still try.",
    "RMIVT here = mean verification time, with a missed victim counted as the 600 s horizon.",
]


def _truth(case):
    gold_table = apply_decision(case, load_decision("gold", case))
    return {t["landmark"]: t["sensor"] for t in gold_table}


@lru_cache(maxsize=1)
def build_demo():
    cases = []
    for case_id in CASES:
        case = load_case(case_id)
        truth = _truth(case)
        arms = {}
        for arm in ARMS:
            decision = load_decision(arm, case)
            table = apply_decision(case, decision)
            arms[arm] = {"decision": decision, "table": table, "result": run_mission(UAVS, table, truth)}
        cases.append({"id": case_id, "text": case["text"], "open": case["open"], "truth": truth, "arms": arms})
    return {
        "landmarks": {name: list(pos) for name, pos in LANDMARKS.items()},
        "base": list(BASE),
        "uavs": [{"id": u.id, "speed": u.speed, "sensors": list(u.sensors), "start": list(u.start),
                  "color": UAV_COLORS[u.id]} for u in UAVS],
        "dwell": DWELL,
        "horizon": HORIZON,
        "assumptions": ASSUMPTIONS,
        "cases": cases,
    }
