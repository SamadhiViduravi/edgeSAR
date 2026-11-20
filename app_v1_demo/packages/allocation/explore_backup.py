r"""EXPLORATORY ONLY. Backup numbers for questions from your supervisor. Not for the paper.
Run from the V1 folder:
    .\.venv\Scripts\python -m packages.allocation.explore_backup

It never calls a model. It reads the saved pilot answers (FP16, Q8, Q4, and the FP16 restart) and runs all 1,400
pilot cases through the POC mission simulator. It prints:
  1. Q4 vs FP16 and Q8 vs FP16: how many task tables change, and how many of those are harmful
  2. the FP16 restart (must be 0 everywhere)
  3. how the harmful count changes with the harm threshold (10 s ... 120 s)
  4. each model against the correct answer (gold)
Same POC rules as before: truth = gold table, all tasks known at t = 0, harmful = new miss or one victim >= threshold later.
"""
import json
import sys
sys.dont_write_bytecode = True

from packages.allocation import funnel
from packages.allocation.decisions import PILOT_DIR, apply_decision
from packages.allocation.mission import run_mission
from packages.allocation.world import UAVS
import common

RUNS = {"FP16": "f16_P1", "Q8": "q8_P1", "Q4": "q4_P1", "FP16 restart": "f16_P1_rerun"}


def _texts(run_name):
    with open(PILOT_DIR / "runs" / (run_name + ".jsonl"), encoding="utf-8") as f:
        return {r["case_id"]: r["text"] for r in map(json.loads, f)}


def _norm(text, case):
    obj, _ = common.parse_decision(text)
    return common.validate(obj, case)[0]


def build():
    cases = common.load_cases(PILOT_DIR / "data" / "cases.jsonl")
    texts = {arm: _texts(run) for arm, run in RUNS.items()}
    rows = []
    for c in cases:
        gold_table = apply_decision(c, common.gold_norm(c))
        truth = {t["landmark"]: t["sensor"] for t in gold_table}
        arms = {"gold": (gold_table, run_mission(UAVS, gold_table, truth))}
        for arm in RUNS:
            table = apply_decision(c, _norm(texts[arm][c["id"]], c))
            arms[arm] = (table, run_mission(UAVS, table, truth))
        rows.append((truth, arms))
    return rows


def compare_all(rows, ref, test, **kw):
    return [funnel.compare(*arms[ref], *arms[test], truth, **kw) for truth, arms in rows]


def summary(rows, ref, test, **kw):
    changed = [x for x in compare_all(rows, ref, test, **kw) if x["task_changed"]]
    n = len(changed)
    return {
        "table_changed": n,
        "assignment_changed": sum(x["assignment_changed"] for x in changed),
        "route_changed": sum(x["route_changed"] for x in changed),
        "verification_changed": sum(x["verification_changed"] for x in changed),
        "harmful": sum(x["harmful"] for x in changed),
        "new_miss": sum(bool(x["new_misses"]) for x in changed),
        "fixed_miss": sum(bool(x["fixed_misses"]) for x in changed),
    }


def main():
    rows = build()
    print("cases:", len(rows))
    print("\n1) task-table changes against FP16 (harmful = new miss or a victim >= %d s later)" % funnel.HARM_SECONDS)
    for arm in ("Q4", "Q8", "FP16 restart"):
        s = summary(rows, "FP16", arm)
        pct = 100 * s["harmful"] / s["table_changed"] if s["table_changed"] else 0
        print("  %-13s table changed %3d | assignment %3d | route %3d | verification %3d | harmful %3d (%.0f%%) | new miss %2d | fixed miss %2d"
              % (arm, s["table_changed"], s["assignment_changed"], s["route_changed"], s["verification_changed"],
                 s["harmful"], pct, s["new_miss"], s["fixed_miss"]))
    print("\n2) the FP16 restart must be 0 everywhere (see the line above)")
    print("\n3) Q4 vs FP16: how the harmful count depends on the threshold")
    for t in (10, 15, 30, 60, 120):
        s = summary(rows, "FP16", "Q4", harm_seconds=t)
        print("  %3d s -> %2d of %d (%.1f%%)" % (t, s["harmful"], s["table_changed"], 100 * s["harmful"] / s["table_changed"]))
    print("\n4) each model against the correct answer (gold), all %d cases" % len(rows))
    for arm in ("FP16", "Q8", "Q4"):
        out = compare_all(rows, "gold", arm)
        print("  %-5s harmful in %3d cases | has at least one victim missed that gold verifies: %3d"
              % (arm, sum(x["harmful"] for x in out), sum(bool(x["new_misses"]) for x in out)))


if __name__ == "__main__":
    main()
