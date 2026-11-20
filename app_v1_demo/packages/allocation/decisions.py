"""Step 2: turn a pilot case + one model decision into a task table.
A task table is the list of verification tasks that CBBA will later share between the UAVs."""
import json
import sys
from pathlib import Path

PILOT_DIR = Path(r"D:\1 Samadhi UNI\aFYP\Claude\edgesar_pilot")

sys.dont_write_bytecode = True        # do not write cache files into the frozen pilot folder
sys.path.insert(0, str(PILOT_DIR))
import common                          # the SAME parser and validator that the pilot used

# arm name -> run file made by the pilot (None = the answer key)
ARMS = {"gold": None, "FP16": "f16_P1", "Q4": "q4_P1"}


def load_case(case_id):
    for case in common.load_cases(PILOT_DIR / "data" / "cases.jsonl"):
        if case["id"] == case_id:
            return case
    raise KeyError(case_id)


def load_decision(arm, case):
    """The decision (a dict) that this arm made for this case."""
    if arm == "gold":
        return common.gold_norm(case)
    run_file = PILOT_DIR / "runs" / (ARMS[arm] + ".jsonl")
    with open(run_file, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["case_id"] == case["id"]:
                obj, _ = common.parse_decision(row["text"])
                norm, _status = common.validate(obj, case)   # bad answers become NO_ACTION
                return norm
    raise KeyError(case["id"])


def apply_decision(case, norm):
    """Return the task table after the decision. Each task is a dict."""
    table = [dict(t) for t in case["open"]]        # copy, so the case itself is not changed
    action = norm["action"]
    if action == "CLOSE_INCIDENT":
        table = [t for t in table if t["id"] != norm["incident"]]
    elif action == "UPDATE_INCIDENT":
        for t in table:
            if t["id"] == norm["incident"]:
                t["landmark"] = norm["landmark"]
                t["sensor"] = norm["sensor"]
                t["priority"] = norm["priority"]
    elif action == "CREATE_VERIFICATION":
        table.append({"id": "NEW", "landmark": norm["landmark"],
                      "sensor": norm["sensor"], "priority": norm["priority"]})
    return table


if __name__ == "__main__":
    from packages.allocation.world import LANDMARKS
    assert set(LANDMARKS) == set(common.LANDMARKS), "landmark names differ from the pilot"
    for case_id in ["c0618", "c0119", "c1189", "c0093", "c0047"]:
        case = load_case(case_id)
        print(f"\n=== {case_id}: {case['text']}")
        for arm in ARMS:
            norm = load_decision(arm, case)
            table = apply_decision(case, norm)
            print(f"  {arm:5s} {norm['action']}")
            for t in table:
                print(f"        {t['id']:4s} {t['landmark']:16s} {t['sensor']:8s} priority {t['priority']}")