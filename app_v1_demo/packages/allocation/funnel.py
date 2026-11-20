"""Step 8: the exact rules for "what changed" between two arms that start from the SAME situation.

Arm A is the reference (FP16), arm B is the test arm (Q4). Everything here is a plain, mechanical comparison.

  L0  decision change      the normalised decisions differ (action, incident, landmark, sensor, priority)
  L1  task change          the task tables differ (landmark, sensor, priority). Task ids are ignored.
  L2  assignment change    the set of (landmark, UAV) pairs that were visited differs.
                           Two kinds are counted: a task added or removed, and the same task given to another UAV.
  L3  route change         some UAV's ORDERED list of landmarks differs. A route can change while L2 does not
                           (only the order changed). That case is called route_only.
  L4  verification change  for a real incident, the verification time differs by more than EPS seconds,
                           or it is verified in one arm and missed in the other.

Rule that must always hold: if the task tables are the same, L2, L3 and L4 are all unchanged (the simulator is
deterministic). Any violation is a bug. test_funnel.py checks this on all 1,400 pilot cases.

Harm is judged PER INCIDENT, not on the mean:
  new miss      a real victim is verified in A but missed in B
  worse         a real victim is verified at least HARM_SECONDS later in B
  harmful       a new miss, or at least one victim that is worse
  mixed         one victim is worse and another is better by at least HARM_SECONDS
  hidden_harm   harmful, although the mean delay change is zero or negative (the mean hides it)

POC values: EPS and HARM_SECONDS were chosen by me after seeing the pilot cases. The final study must fix them
BEFORE any held-out run. A missed victim counts as HORIZON seconds only so that a delay can be computed.
Misses are always reported separately.
"""
import statistics

from packages.allocation.mission import HORIZON

EPS = 0.5               # seconds: verification times closer than this are "the same"
HARM_SECONDS = 30.0     # POC value, see above

_KEYS = ("action", "incident", "landmark", "sensor", "priority")


def decision_changed(a, b):
    """L0."""
    return tuple(a.get(k) for k in _KEYS) != tuple(b.get(k) for k in _KEYS)


def task_key(table):
    return sorted((t["landmark"], t["sensor"], t["priority"]) for t in table)


def task_changed(table_a, table_b):
    """L1."""
    return task_key(table_a) != task_key(table_b)


def visit_pairs(result):
    return {(v["landmark"], v["uav"]) for v in result["visits"]}


def routes(result):
    """For each UAV, the landmarks it visited, in the order it visited them."""
    out = {}
    for v in sorted(result["visits"], key=lambda v: (v["start"], v["uav"])):
        out.setdefault(v["uav"], []).append(v["landmark"])
    return out


def delay(result, landmark, horizon=HORIZON):
    t = result["verify_time"].get(landmark)
    return horizon if t is None else t


def compare(table_a, res_a, table_b, res_b, truth, harm_seconds=HARM_SECONDS, eps=EPS):
    """Compare arm B with arm A. `truth` = {landmark: sensor} of the real victims."""
    pairs_a, pairs_b = visit_pairs(res_a), visit_pairs(res_b)
    lands_a = {l for l, _ in pairs_a}
    lands_b = {l for l, _ in pairs_b}
    reassigned = any({u for l2, u in pairs_a if l2 == l} != {u for l2, u in pairs_b if l2 == l}
                     for l in lands_a & lands_b)
    assignment_changed = pairs_a != pairs_b
    route_changed = routes(res_a) != routes(res_b)

    delays = {l: delay(res_b, l) - delay(res_a, l) for l in truth}
    verified_a = {l for l in truth if res_a["verify_time"].get(l) is not None}
    verified_b = {l for l in truth if res_b["verify_time"].get(l) is not None}
    new_misses = sorted(verified_a - verified_b)
    fixed_misses = sorted(verified_b - verified_a)
    worse = sorted(l for l, x in delays.items() if x >= harm_seconds)
    better = sorted(l for l, x in delays.items() if x <= -harm_seconds)
    mean_delay = statistics.mean(delays.values()) if delays else 0.0
    harmful = bool(new_misses or worse)
    return {
        "task_changed": task_changed(table_a, table_b),
        "assignment_changed": assignment_changed,
        "added_or_removed": lands_a != lands_b,
        "reassigned": reassigned,
        "route_changed": route_changed,
        "route_only": route_changed and not assignment_changed,
        "verification_changed": bool(new_misses or fixed_misses or any(abs(x) > eps for x in delays.values())),
        "new_misses": new_misses,
        "fixed_misses": fixed_misses,
        "delays": delays,
        "worst_delay": max(delays.values(), default=0.0),
        "best_delay": min(delays.values(), default=0.0),
        "mean_delay": mean_delay,
        "worse": worse,
        "better": better,
        "harmful": harmful,
        "mixed": bool(worse and better),
        "hidden_harm": harmful and mean_delay <= 0,
    }
