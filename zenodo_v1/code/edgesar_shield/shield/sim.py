"""
The episode simulator (plan section 5; M2).

Two worlds that never mix:
  RUNTIME  everything a deployed system may use: the report, its own belief table, the UAV states, the map, head probabilities,
           the allocator, the budget left.  A policy gets only a `View` of this.
  HIDDEN   `HiddenTruth`: which incidents are real, where, which camera they need, their true deadlines, and the gold record.
           Only the engine (to decide what a UAV finds on arrival) and the scorer open it. Any other access raises `TruthLeak`.
           The verifier is the one deliberate door: it returns the gold record `d_v` seconds after the request and costs budget.

Time and money are real in the simulation:
  * a verification request costs one unit of the budget and the answer arrives `d_v` seconds later;
  * every allocator run a policy makes (what-if runs included) costs `alloc_cost_s` seconds of simulated decision time:
    the committed table is applied only after that delay;  measured wall-clock time is logged as well;
  * a decision that needs more than `decision_timeout_s` is labelled TIMEOUT.

Same-second order of events: a visit arrives < a visit ends < a verification answer arrives < a decision is applied < a report arrives.

Overlay mode (development with saved vectors): a ReportEvent carries `open_before`, the open table of that pilot case. At the report time those
incidents enter BOTH the belief and the truth (their clocks start then), the policy reads the report, and the gold record is applied to the truth.
An incident that the gold record closes in the same second it appeared was never real and is not counted (V1 convention).
Chain mode (fresh episodes): `open_before` is None; the tables carry over from event to event.
"""
import heapq
import math
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from . import alloc as alloc_mod
from .core import AFTER_LAST_S, DEADLINE_S, DWELL_S, Agent, Problem, Task, landmarks, req_of, sensor_of, uav_specs


# =====================================================================================================================
# the wall
# =====================================================================================================================
class TruthLeak(RuntimeError):
    """Raised when code outside the engine and the scorer tries to open the hidden truth or a gold record."""


_ACCESS = [0]


@contextmanager
def truth_access():
    _ACCESS[0] += 1
    try:
        yield
    finally:
        _ACCESS[0] -= 1


def _need_access(what):
    if _ACCESS[0] <= 0:
        raise TruthLeak("%s opened outside the engine/scorer" % what)


def next_new_id(ids):
    k = 1
    while "N%d" % k in ids:
        k += 1
    return "N%d" % k


@dataclass
class TInc:
    ns: str
    iid: str
    landmark: str
    sensor: str
    pri: int
    created: float
    deadline: float
    verified_at: float = None
    closed_at: float = None
    never_real: bool = False


class HiddenTruth:
    """The real incidents. Every method needs `with truth_access():`."""

    def __init__(self):
        self._inc = {}           # (ns, iid) -> TInc

    def add_open(self, ns, rows, t, deadlines):
        _need_access("HiddenTruth")
        for r in rows:
            self._inc[(ns, r["id"])] = TInc(ns, r["id"], r["landmark"], r["sensor"], r["priority"], t, t + deadlines[r["priority"]])

    def apply_gold(self, ns, norm, t, deadlines, same_instant):
        """Apply the gold record at time t."""
        _need_access("HiddenTruth")
        a = norm["action"]
        if a == "CREATE_VERIFICATION":
            iid = next_new_id({i for (n, i) in self._inc if n == ns})
            self._inc[(ns, iid)] = TInc(ns, iid, norm["landmark"], norm["sensor"], norm["priority"], t, t + deadlines[norm["priority"]])
        elif a == "UPDATE_INCIDENT":
            inc = self._inc.get((ns, norm["incident"]))
            if inc is not None and inc.closed_at is None:
                new_p = norm["priority"]
                if new_p > inc.pri:
                    inc.deadline = min(inc.deadline, t + deadlines[new_p])
                inc.landmark, inc.sensor, inc.pri = norm["landmark"], norm["sensor"], new_p
        elif a == "CLOSE_INCIDENT":
            inc = self._inc.get((ns, norm["incident"]))
            if inc is not None and inc.closed_at is None:
                if inc.created == t and norm["incident"] in same_instant and inc.verified_at is None:
                    inc.never_real = True
                inc.closed_at = t

    def visit(self, ns, landmark, uav_sensors, finish):
        """What a UAV finds at this landmark: 'verified' (some incident it can serve), 'failed' (incidents here, none it can serve), 'empty'."""
        _need_access("HiddenTruth")
        hit = [i for i in self._inc.values()
               if i.ns == ns and i.landmark == landmark and i.closed_at is None and i.verified_at is None and not i.never_real]
        if not hit:
            return "empty"
        ok = [i for i in hit if req_of(i.sensor) <= uav_sensors]
        for i in ok:
            i.verified_at = finish
        return "verified" if ok else "failed"

    def incidents(self):
        _need_access("HiddenTruth")
        return list(self._inc.values())


class ReportEvent:
    """One incoming report. The gold record is behind the same wall as the truth."""
    __slots__ = ("t", "ns", "case_id", "open_before", "_gold")

    def __init__(self, t, ns, case_id, open_before, gold):
        self.t, self.ns, self.case_id, self.open_before, self._gold = t, ns, case_id, open_before, gold

    @property
    def gold(self):
        _need_access("the gold record")
        return self._gold


@dataclass
class Episode:
    id: str
    events: list
    level: str = ""

    @property
    def t_end(self):
        return max(e.t for e in self.events) + AFTER_LAST_S


# =====================================================================================================================
# configuration and decisions
# =====================================================================================================================
@dataclass
class Decision:
    kind: str                  # 'COMMIT' | 'ESCALATE'
    outcome: str               # label for the logs: COMMIT, ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, ...
    table: list = None         # COMMIT: the complete table of this namespace after the decision (dict id, landmark, sensor, priority, [req, cover])
    record: dict = None
    diag: dict = field(default_factory=dict)


@dataclass
class SimConfig:
    dwell: float = DWELL_S
    d_v: float = 60.0                      # verification answer delay (s)
    alloc_cost_s: float = 0.02             # simulated decision time per allocator run (s)
    deadlines: dict = field(default_factory=lambda: dict(DEADLINE_S))
    budget_fraction: float = 0.10          # verification requests per report; hard cap per episode = floor(b * reports + 0.5)
    decision_timeout_s: float = 5.0        # a decision that needs more simulated time than this is a TIMEOUT
    audit_gold_plan: bool = True           # evaluation only: compare the committed plan with the plan the gold record would give


class _CountingAllocator:
    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.runs = 0
        self.ms = 0.0

    def plan(self, prob):
        t0 = time.perf_counter()
        p = self.inner.plan(prob)
        self.ms += (time.perf_counter() - t0) * 1000.0
        self.runs += 1
        return p


@dataclass
class BTask:
    key: str
    ns: str
    iid: str
    landmark: str
    req: frozenset
    pri: int
    created: float
    deadline: float
    state: str = "open"          # open | done | closed
    cover: bool = False


@dataclass
class UavRt:
    spec: object
    pos: tuple
    busy: tuple = None           # (task key, arrive, finish, destination landmark)
    dist: float = 0.0


def apply_record(table, norm):
    """Pilot/V1 semantics (decisions.py apply_decision) on a table of dicts {id, landmark, sensor, priority}. Returns a new list.
    A record that names an incident that is not in the table changes nothing (the pilot validator turns it into NO_ACTION)."""
    out = [dict(t) for t in table]
    a = norm["action"]
    if a == "CLOSE_INCIDENT":
        out = [t for t in out if t["id"] != norm["incident"]]
    elif a == "UPDATE_INCIDENT":
        for t in out:
            if t["id"] == norm["incident"]:
                t["landmark"], t["sensor"], t["priority"] = norm["landmark"], norm["sensor"], norm["priority"]
    elif a == "CREATE_VERIFICATION":
        out.append({"id": next_new_id({t["id"] for t in out}), "landmark": norm["landmark"], "sensor": norm["sensor"],
                    "priority": norm["priority"]})
    return out


def canon_table(table):
    """A table without ids: sorted (landmark, cameras, priority, is_cover). Two tables with the same canon lead to the same missions."""
    rows = []
    for r in table:
        req = tuple(sorted(r["req"])) if "req" in r else tuple(sorted(req_of(r["sensor"])))
        rows.append((r["landmark"], req, r["priority"], bool(r.get("cover", False))))
    return tuple(sorted(rows))


@dataclass
class Evaluation:
    sig: tuple
    ok: bool
    details: dict
    plan: object
    prob: object


class View:
    """What a policy may see at a decision. Built from the belief and the UAV states only."""

    def __init__(self, sim, ns, case_id, t):
        self._sim = sim
        self.now = t
        self.ns = ns
        self.case_id = case_id

    @property
    def open_table(self):
        return self._sim.open_table(self.ns)

    @property
    def budget_left(self):
        return self._sim.budget_left

    @property
    def cfg(self):
        return self._sim.cfg

    @property
    def runs_so_far(self):
        return self._sim.policy_alloc.runs - self._sim._runs0

    def runs_available(self):
        """How many more allocator runs fit before the decision timeout."""
        c = self._sim.cfg
        if c.alloc_cost_s <= 0:
            return 10 ** 9
        return max(0, int(math.floor(c.decision_timeout_s / c.alloc_cost_s + 1e-9)) - self.runs_so_far)

    def evaluate(self, table, free=False):
        """Run the allocator on the situation if this namespace's table were `table`. Costs one allocator run (simulated decision time),
        unless free=True, which is for calibration-time observation only (the run is then not charged).
        Returns the execution signature, the requirement check (R1-R3 under the system's own belief) and the plan."""
        prob, dl = self._sim._problem(self.now, self.ns, table, self.now)
        plan = (self._sim.engine_alloc if free else self._sim.policy_alloc).plan(prob)
        sig = alloc_mod.plan_signature(plan, prob.tasks)
        ok, det = alloc_mod.check_requirements(plan, prob.tasks, dl, prob.agents)
        return Evaluation(sig, ok, det, plan, prob)


# =====================================================================================================================
# the engine
# =====================================================================================================================
class Sim:
    def __init__(self, allocator, cfg=None):
        self.cfg = cfg or SimConfig()
        self.raw_alloc = allocator
        self.policy_alloc = _CountingAllocator(allocator)        # runs a policy asks for (charged as decision time)
        self.engine_alloc = _CountingAllocator(allocator)        # replans on events (not charged)
        self.land = landmarks()
        self.specs = uav_specs()
        self._runs0 = 0

    # ------------------------------------------------------------------ belief helpers
    def open_table(self, ns):
        return [{"id": b.iid, "landmark": b.landmark, "sensor": sensor_of(b.req), "priority": b.pri}
                for b in self.belief.values() if b.ns == ns and b.state == "open" and not b.cover]

    def _merge_times(self, t_ref, ns, table):
        """Created time and deadline for each row of a table: what the belief already knows, otherwise counted from t_ref."""
        out = {}
        D = self.cfg.deadlines
        for r in table:
            key = "%s:%s" % (ns, r["id"])
            old = self.belief.get(key)
            if old is not None and old.state != "closed":
                created, dl = old.created, old.deadline
                if r["priority"] > old.pri:
                    dl = min(dl, t_ref + D[r["priority"]])
            else:
                created, dl = t_ref, t_ref + D[r["priority"]]
            out[key] = (created, dl)
        return out

    def _problem(self, now, ns=None, table=None, t_ref=None):
        """The planning problem now, with this namespace's table replaced by `table` when given. Returns (Problem, believed deadlines)."""
        t_ref = now if t_ref is None else t_ref
        agents = []
        for u in self.uavs.values():
            if u.busy is not None:
                _, _, fin, dest = u.busy
                agents.append(Agent(u.spec.id, float(u.spec.speed), frozenset(u.spec.sensors), self.land[dest], fin))
            else:
                agents.append(Agent(u.spec.id, float(u.spec.speed), frozenset(u.spec.sensors), u.pos, now))
        tasks, dls = [], {}
        table_keys = set()
        if table is not None:
            table_keys = {"%s:%s" % (ns, r["id"]) for r in table}
        for b in self.belief.values():
            if b.state != "open" or b.key in self.locked or b.key in table_keys:
                continue
            if table is not None and b.ns == ns and not b.cover:
                continue
            tasks.append(Task(b.key, b.landmark, b.req, b.pri))
            dls[b.key] = b.deadline
        if table is not None:
            times = self._merge_times(t_ref, ns, table)
            for r in table:
                key = "%s:%s" % (ns, r["id"])
                old = self.belief.get(key)
                if old is not None and (old.state == "done" or key in self.locked):
                    continue                                    # already served or being served: not a planning task
                req = frozenset(r["req"]) if "req" in r else req_of(r["sensor"])
                tasks.append(Task(key, r["landmark"], req, r["priority"]))
                dls[key] = times[key][1]
        banned = {k: set(v) for k, v in self.banned.items()}
        return Problem(now, tuple(agents), tuple(tasks), banned, self.cfg.dwell, self.land), dls

    def install(self, ns, table, t_ref):
        """Make `table` the belief of this namespace. Rows that are no longer listed (and are still open, not cover) are closed."""
        times = self._merge_times(t_ref, ns, table)
        seen = set()
        for r in table:
            key = "%s:%s" % (ns, r["id"])
            seen.add(key)
            created, dl = times[key]
            req = frozenset(r["req"]) if "req" in r else req_of(r["sensor"])
            cover = bool(r.get("cover", False))
            old = self.belief.get(key)
            if old is not None and old.state != "closed":
                if old.state == "done":
                    continue
                if old.landmark != r["landmark"] or old.req != req:
                    self.banned.pop(key, None)
                old.landmark, old.req, old.pri, old.deadline, old.cover = r["landmark"], req, r["priority"], dl, cover
            else:
                self.belief[key] = BTask(key, ns, r["id"], r["landmark"], req, r["priority"], created, dl, "open", cover)
        for key, b in self.belief.items():
            if b.ns == ns and key not in seen and b.state == "open" and not b.cover:
                b.state = "closed"

    # ------------------------------------------------------------------ the run
    def run(self, episode, policy, label="", oracle=False):
        cfg = self.cfg
        self.belief = {}
        self.banned = {}
        self.locked = {}
        self.uavs = {u.id: UavRt(u, tuple(u.start)) for u in self.specs.values()}
        self.truth = HiddenTruth()
        R = len(episode.events)
        self.budget_cap = int(math.floor(cfg.budget_fraction * R + 0.5))
        self.budget_left = self.budget_cap
        self.t_end = episode.t_end
        self.events = []
        self.seq = 0
        self.log = {"reports": [], "visits": [], "requests": [], "replans": 0, "wasted": 0, "empty": 0, "failed": 0, "dist": 0.0,
                    "hold_s": 0.0, "decision_s": 0.0, "wall_ms_policy": 0.0, "wall_ms_total": 0.0, "eval_runs": 0, "policy_runs": 0}
        self.policy_alloc.runs = 0
        self.policy_alloc.ms = 0.0
        self.engine_alloc.runs = 0
        self.engine_alloc.ms = 0.0
        t_wall = time.perf_counter()
        for ev in episode.events:
            self._push(ev.t, 4, "report", ev)
        while self.events:
            t, _, _, kind, data = heapq.heappop(self.events)
            if t > self.t_end + 1e-9:
                continue
            if kind == "arrive":
                self._on_arrive(t, *data)
                self._replan(t)
            elif kind == "end":
                self._on_end(t, *data)
                self._replan(t)
            elif kind == "verify":
                self._on_verify(t, *data)
                self._replan(t)
            elif kind == "apply":
                self._on_apply(t, *data)
                self._replan(t)
            elif kind == "report":
                self._on_report(t, data, policy, oracle)
        self.log["wall_ms_total"] = (time.perf_counter() - t_wall) * 1000.0
        self.log["policy_runs"] = self.policy_alloc.runs
        self.log["policy_alloc_ms"] = self.policy_alloc.ms
        self.log["engine_runs"] = self.engine_alloc.runs
        self.log["engine_alloc_ms"] = self.engine_alloc.ms
        self.log["dist"] = sum(u.dist for u in self.uavs.values())
        return self._score(episode, label)

    def _push(self, t, order, kind, data):
        self.seq += 1
        heapq.heappush(self.events, (t, order, self.seq, kind, data))

    # ------------------------------------------------------------------ events
    def _on_report(self, t, ev, policy, oracle):
        cfg = self.cfg
        fresh = set()
        if ev.open_before is not None:
            rows = [dict(r) for r in ev.open_before]
            self.install(ev.ns, rows, t)
            with truth_access():
                self.truth.add_open(ev.ns, rows, t, cfg.deadlines)
            fresh = {r["id"] for r in rows}
        with truth_access():
            gold = ev.gold
        base = self.open_table(ev.ns)
        gold_table = apply_record(base, gold)
        runs, wall, timed_out = 0, 0.0, False
        if oracle:
            dec = Decision("COMMIT", "ORACLE", table=gold_table, record=dict(gold))
            delay = 0.0
        else:
            view = View(self, ev.ns, ev.case_id, t)
            self._runs0 = self.policy_alloc.runs
            w0 = time.perf_counter()
            dec = policy.on_report(view)
            wall = (time.perf_counter() - w0) * 1000.0
            runs = self.policy_alloc.runs - self._runs0
            delay = runs * cfg.alloc_cost_s
            timed_out = delay > cfg.decision_timeout_s + 1e-9
        self.log["decision_s"] += delay
        self.log["wall_ms_policy"] += wall
        row = {"ns": ev.ns, "case_id": ev.case_id, "t": t, "kind": dec.kind, "outcome": dec.outcome, "runs": runs, "decision_s": delay,
               "wall_ms": wall, "timeout": timed_out, "diag": dec.diag, "record": dec.record, "gold_record": dict(gold)}
        if timed_out and dec.kind == "COMMIT" and not dec.outcome.startswith("TIMEOUT"):
            row["outcome"] = "TIMEOUT_LATE:" + dec.outcome
        if dec.kind == "ESCALATE":
            if self.budget_left <= 0:
                raise RuntimeError("policy escalated with no budget left (policy bug)")
            self.budget_left -= 1
            tv = t + delay + cfg.d_v
            self.log["requests"].append({"ns": ev.ns, "case_id": ev.case_id, "t": t, "answer_at": tv})
            self.log["hold_s"] += cfg.d_v + delay
            self._push(t + delay, 3, "apply", (ev.ns, None, t))              # the old rows are planned now; the change waits for the answer
            self._push(tv, 2, "verify", (ev.ns, gold, t))
            row["table_equal_gold"] = None
            row["plan_equal_gold"] = None
        else:
            row["table_equal_gold"] = canon_table(dec.table) == canon_table(gold_table)
            if cfg.audit_gold_plan:
                row["plan_equal_gold"] = self._audit_plan(t, ev.ns, dec.table, gold_table)
            self._push(t + delay, 3, "apply", (ev.ns, dec.table, t))
        # evaluation only: would the policy's own best-guess record (r_hat) have given the gold plan?  (asked for every decision, so that
        # gates that verify or cover can be compared with each other on the same question)
        if cfg.audit_gold_plan and not oracle and dec.record is not None:
            rt = apply_record(base, dec.record)
            row["rhat_table_equal_gold"] = canon_table(rt) == canon_table(gold_table)
            if dec.kind == "COMMIT" and dec.table is not None and canon_table(dec.table) == canon_table(rt):
                row["rhat_plan_equal_gold"] = row["plan_equal_gold"]
            else:
                row["rhat_plan_equal_gold"] = self._audit_plan(t, ev.ns, rt, gold_table)
        with truth_access():
            self.truth.apply_gold(ev.ns, gold, t, cfg.deadlines, fresh)
        self.log["reports"].append(row)

    def _audit_plan(self, t, ns, committed, gold_table):
        """Evaluation only (never fed back): do the committed table and the gold table lead to the same plan from this state?"""
        self.log["eval_runs"] += 2
        pa, _ = self._problem(t, ns, committed, t)
        pb, _ = self._problem(t, ns, gold_table, t)
        sa = alloc_mod.plan_signature(self.raw_alloc.plan(pa), pa.tasks)
        sb = alloc_mod.plan_signature(self.raw_alloc.plan(pb), pb.tasks)
        return sa == sb

    def _on_apply(self, t, ns, table, t_ref):
        if table is not None:
            self.install(ns, table, t_ref)

    def _on_verify(self, t, ns, gold, t_ref):
        table = apply_record(self.open_table(ns), gold)
        self.install(ns, table, t_ref)

    def _replan(self, now):
        self.log["replans"] += 1
        if not any(u.busy is None for u in self.uavs.values()):
            return                                              # everybody is flying: nothing can start now
        prob, _ = self._problem(now)
        if not prob.tasks:
            return
        plan = self.engine_alloc.plan(prob)
        for u in self.uavs.values():
            if u.busy is None:
                ks = plan.paths.get(u.spec.id, [])
                if ks:
                    self._start(u, ks[0], now)

    def _start(self, u, key, now):
        b = self.belief[key]
        dest = b.landmark
        p = self.land[dest]
        d = math.dist(u.pos, p)
        arrive = now + d / u.spec.speed
        finish = arrive + self.cfg.dwell
        u.busy = (key, arrive, finish, dest)
        u.dist += d
        self.locked[key] = u.spec.id
        self._push(arrive, 0, "arrive", (u.spec.id, key, arrive, finish, dest))
        self._push(finish, 1, "end", (u.spec.id, key, dest))

    def _on_arrive(self, t, uav_id, key, arrive, finish, dest):
        u = self.uavs[uav_id]
        b = self.belief[key]
        with truth_access():
            res = self.truth.visit(b.ns, dest, frozenset(u.spec.sensors), finish)
        self.log["visits"].append({"uav": uav_id, "key": key, "landmark": dest, "arrive": arrive, "finish": finish, "result": res,
                                   "cover": b.cover})
        same = (b.landmark == dest and b.state == "open")
        if res == "failed":
            self.log["failed"] += 1
            self.log["wasted"] += 1
            if same:
                self.banned.setdefault(key, set()).add(uav_id)
            if self.locked.get(key) == uav_id:
                del self.locked[key]                            # back on the waiting list at the moment of arrival (V1 rule)
        else:
            if res == "empty":
                self.log["empty"] += 1
                self.log["wasted"] += 1
            if same:
                b.state = "done"
            elif self.locked.get(key) == uav_id:
                del self.locked[key]

    def _on_end(self, t, uav_id, key, dest):
        u = self.uavs[uav_id]
        u.pos = self.land[dest]
        u.busy = None
        if self.locked.get(key) == uav_id:
            del self.locked[key]

    # ------------------------------------------------------------------ scoring (opens the truth: allowed)
    def _score(self, episode, label):
        rows = []
        counts = {"n": 0, "on_time": 0, "late": 0, "unverified": 0, "resolved_external": 0}
        with truth_access():
            for inc in self.truth.incidents():
                if inc.never_real:
                    continue
                counts["n"] += 1
                v = inc.verified_at
                if v is not None and v <= self.t_end + 1e-9:
                    cls = "on_time" if v <= inc.deadline + 1e-9 else "late"
                elif inc.closed_at is not None:
                    cls = "resolved_external"
                else:
                    cls = "unverified"
                counts[cls] += 1
                rows.append({"episode": episode.id, "arm": label, "ns": inc.ns, "iid": inc.iid, "landmark": inc.landmark,
                             "sensor": inc.sensor, "priority": inc.pri, "created": inc.created, "deadline": inc.deadline,
                             "verified_at": v if (v is not None and v <= self.t_end + 1e-9) else None, "class": cls})
        return {"episode": episode.id, "arm": label, "counts": counts, "incidents": rows, "log": self.log,
                "budget_cap": self.budget_cap, "requests": len(self.log["requests"])}
