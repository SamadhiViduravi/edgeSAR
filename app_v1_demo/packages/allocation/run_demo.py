"""Step 6: run 5 cases x 3 arms and print one result table."""
from packages.allocation.decisions import ARMS, apply_decision, load_case, load_decision
from packages.allocation.mission import run_mission
from packages.allocation.world import UAVS

CASES = ["c0618", "c0119", "c1189", "c0093", "c0047"]


def truth_of(case):
    """The real victims: every task in the GOLD table has a person at its landmark."""
    gold_table = apply_decision(case, load_decision("gold", case))
    return {t["landmark"]: t["sensor"] for t in gold_table}


print(f"{'case':6s} {'arm':5s} {'victims':>7s} {'missed':>6s} {'wasted':>6s} {'RMIVT(s)':>9s}   verification time per victim")
for case_id in CASES:
    case = load_case(case_id)
    truth = truth_of(case)
    for arm in ARMS:
        table = apply_decision(case, load_decision(arm, case))
        out = run_mission(UAVS, table, truth)
        times = ", ".join(f"{spot} {('%.0fs' % t) if t is not None else 'MISSED'}"
                          for spot, t in out["verify_time"].items())
        print(f"{case_id:6s} {arm:5s} {len(truth):7d} {out['missed']:6d} {out['wasted']:6d} {out['rmivt']:9.1f}   {times}")
    print()