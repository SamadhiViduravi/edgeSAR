"""
Allocators behind ONE stable interface:   allocator.plan(Problem) -> Plan

  BoundedCBBA       a bounded Consensus-Based Bundle Algorithm (the allocator for all main results)
  LegacyGreedyS1    the V1 "CBBA" wrapped without change. The audit showed it makes the same decisions as a simple greedy
                    auction (one task per UAV, one shared table, no messages). It is NOT called CBBA anywhere in the outputs.

Sources read for BoundedCBBA (checked 13 Nov 2026, text of the sources, not the IEEE article itself):
  [Brunet 2008]  L. Brunet, "Consensus-Based Auctions for Decentralized Task Assignment", MIT master's thesis.
                 Section 3.2: Algorithm 2 (bundle phase), Eq. 3.10 (marginal score), Eq. 3.14 (timestamps), Eq. 3.15 (release),
                 Table 3.1 (conflict resolution). This is the same material as Table I of Choi, Brunet and How (2009),
                 "Consensus-Based Decentralized Auctions for Robust Task Allocation", IEEE Trans. Robotics 25(4).
  [Johnson 2012] Johnson, Choi, Ponda, How, "Allowing non-submodular score functions in distributed task allocation",
                 Section III-B, Eq. 6 ("bid warping"): warped bid = min(own score, bids already in the bundle). The raw score ranks the
                 tasks; the warped bid is the one shared with the others.
  The 17 rows of the conflict table are implemented in `_resolve` and numbered as in the thesis table.

What is bounded (on purpose):
  * bundle length L_t (default 3) per auction; if more tasks wait, further auctions are run on the rest ("passes"), each UAV
    continuing from the end of its path, so one call returns a complete plan;
  * synchronous rounds on a communication graph (default fully connected), reliable messages, a round cap (non-convergence is logged);
  * the score is  S_i(path) = sum_j value(priority_j) * exp(-0.01 * arrival time_j)  with travel + dwell + the UAV's busy time.
    Deadlines are NOT in the score (they are checked afterwards by the requirement check).

Convergence claim (only under these assumptions): a static task set during one call, a connected graph with synchronous reliable
messages, deterministic tie-breaking (lower agent id wins), identical task and agent data for every agent, and bid warping.
The 50 % optimality statement of the CBBA paper is NOT used; the ratio to brute force is measured on small instances instead.
"""
import math
import sys
from types import SimpleNamespace

from . import paths
from .core import DWELL_S, PRIORITY_VALUE, TIME_DISCOUNT, Plan, Problem, req_of

EPS = 1e-12
NONE = -1


# =====================================================================================================================
# shared helpers
# =====================================================================================================================
def path_score(agent, path_tasks, now, landmarks, dwell=DWELL_S, discount=TIME_DISCOUNT):
    """Score of one UAV's ordered path (list of Task). Also used by tests and the brute-force check."""
    t = agent.avail - now
    pos = agent.pos
    total = 0.0
    for tk in path_tasks:
        p = landmarks[tk.landmark]
        t += math.dist(pos, p) / agent.speed
        total += PRIORITY_VALUE[tk.pri] * math.exp(-discount * t)
        t += dwell
        pos = p
    return total


def timeline(agent, keys, tasks_by_key, landmarks, dwell):
    """Arrival and finish times along a path (absolute times)."""
    t = agent.avail
    pos = agent.pos
    out = []
    for k in keys:
        p = landmarks[tasks_by_key[k].landmark]
        t += math.dist(pos, p) / agent.speed
        out.append((k, t, t + dwell))
        t += dwell
        pos = p
    return out


def _finish_plan(prob, agents_sorted, tasks_by_key, path_keys, unassigned, info):
    paths_out, arrive, finish, owner = {}, {}, {}, {}
    for a in agents_sorted:
        ks = path_keys[a.id]
        paths_out[a.id] = list(ks)
        for k, ta, tf in timeline(a, ks, tasks_by_key, prob.landmarks, prob.dwell):
            arrive[k], finish[k], owner[k] = ta, tf, a.id
    return Plan(paths_out, arrive, finish, owner, sorted(unassigned), info)


def plan_signature(plan, tasks):
    """What the plan DOES, with names and numbers left out: the set of active tasks (landmark, cameras) and each UAV's ordered list
    of such tasks. Task ids, bids and priority numbers are not in it: priority matters only through the plan it produces."""
    by_key = {t.key: t for t in tasks}

    def attr(k):
        t = by_key[k]
        return (t.landmark, tuple(sorted(t.req)))

    active = tuple(sorted(attr(k) for k in by_key))
    routes = tuple(sorted((a, tuple(attr(k) for k in ks)) for a, ks in plan.paths.items() if ks))
    left = tuple(sorted(attr(k) for k in plan.unassigned))
    return (active, routes, left)


def check_requirements(plan, tasks, deadlines, agents, tolerance=1e-9):
    """Requirements under the system's own belief (plan section 4.4).
       R1  every planned task is on a UAV that carries its cameras
       R2  every task's predicted completion is no later than its believed deadline
       R3  no active task is left without a UAV
       Returns (ok, details) with the list of tasks that break each requirement."""
    by_key = {t.key: t for t in tasks}
    cams = {a.id: a.sensors for a in agents}
    r1 = [k for k, u in plan.owner.items() if not by_key[k].req <= cams[u]]
    r2 = [k for k in plan.owner if plan.finish[k] > deadlines[k] + tolerance]
    r3 = list(plan.unassigned)
    return (not r1 and not r2 and not r3), {"R1": r1, "R2": r2, "R3": r3}


# =====================================================================================================================
# the bounded CBBA
# =====================================================================================================================
class BoundedCBBA:
    name = "cbba_bounded"

    def __init__(self, bundle_len=3, graph="full", warp=True, discount=TIME_DISCOUNT, round_cap=None, max_passes=40, adjacency=None):
        self.bundle_len = bundle_len
        self.graph = graph
        self.warp = warp
        self.discount = discount
        self.round_cap = round_cap
        self.max_passes = max_passes
        self.adjacency = adjacency        # {agent id: [agent ids]} for graph == "custom"
        self.last_stats = None
        self.trace = None                  # set to a list to record every round (debugging and tests)

    # ------------------------------------------------------------------ public
    def plan(self, prob):
        agents = sorted(prob.agents, key=lambda a: a.id)
        tasks = sorted(prob.tasks, key=lambda t: t.key)                # order of the input never matters
        tasks_by_key = {t.key: t for t in tasks}
        st = {"rounds": 0, "passes": 0, "releases": 0, "warps": 0, "bids": 0, "placed": 0, "nonconverged": 0, "repaired": 0,
              "max_rounds_one_auction": 0}
        cur = {a.id: (a.pos, a.avail) for a in agents}
        path_keys = {a.id: [] for a in agents}
        remaining = list(range(len(tasks)))
        for _ in range(self.max_passes):
            if not remaining:
                break
            ag = [type(a)(a.id, a.speed, a.sensors, cur[a.id][0], cur[a.id][1]) for a in agents]
            sub = [tasks[j] for j in remaining]
            res = self._auction(ag, sub, prob, st)
            st["passes"] += 1
            got = 0
            taken = set()
            for i, a in enumerate(ag):
                for lj in res[i]:
                    path_keys[a.id].append(sub[lj].key)
                    taken.add(sub[lj].key)
                    got += 1
                if res[i]:
                    last = sub[res[i][-1]]
                    # the UAV is free again after the last visit of this pass
                    t_end = timeline(a, [sub[lj].key for lj in res[i]], {t.key: t for t in sub}, prob.landmarks, prob.dwell)[-1][2]
                    cur[a.id] = (prob.landmarks[last.landmark], t_end)
            if got == 0:
                break
            remaining = [j for j in remaining if tasks[j].key not in taken]
        unassigned = [tasks[j].key for j in remaining]
        info = dict(st)
        info["converged"] = st["nonconverged"] == 0
        self.last_stats = info
        return _finish_plan(prob, agents, tasks_by_key, path_keys, unassigned, info)

    # ------------------------------------------------------------------ graph
    def _neighbors(self, ag):
        n = len(ag)
        if self.graph == "full":
            nbr = [[k for k in range(n) if k != i] for i in range(n)]
        elif self.graph == "line":
            nbr = [[k for k in (i - 1, i + 1) if 0 <= k < n] for i in range(n)]
        elif self.graph == "custom":
            idx = {a.id: i for i, a in enumerate(ag)}
            nbr = [sorted(idx[x] for x in self.adjacency[a.id]) for a in ag]
        else:
            raise ValueError("unknown graph %r" % self.graph)
        # diameter by breadth-first search (a disconnected graph is not allowed)
        diam = 0
        for s in range(n):
            dist = {s: 0}
            q = [s]
            while q:
                u = q.pop(0)
                for v in nbr[u]:
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        q.append(v)
            if len(dist) < n:
                raise ValueError("the communication graph is not connected")
            diam = max(diam, max(dist.values()))
        return nbr, max(diam, 1)

    # ------------------------------------------------------------------ one auction (<= bundle_len tasks per UAV)
    def _auction(self, ag, tasks, prob, st):
        n, m = len(ag), len(tasks)
        if n == 0 or m == 0:
            return [[] for _ in ag]
        now, dwell, disc, Lt, warp = prob.now, prob.dwell, self.discount, self.bundle_len, self.warp
        land = prob.landmarks
        pts = [land[t.landmark] for t in tasks]
        Dtt = [[0.0] * m for _ in range(m)]
        for a in range(m):
            for b in range(a + 1, m):
                Dtt[a][b] = Dtt[b][a] = math.dist(pts[a], pts[b])
        D0 = [[math.dist(a.pos, pts[j]) for j in range(m)] for a in ag]
        spd = [a.speed for a in ag]
        t0 = [a.avail - now for a in ag]
        val = [PRIORITY_VALUE[t.pri] for t in tasks]
        compat = [[(tasks[j].req <= ag[i].sensors) and (ag[i].id not in prob.banned.get(tasks[j].key, ())) for j in range(m)]
                  for i in range(n)]
        nbr, diam = self._neighbors(ag)
        exp = math.exp

        def pscore(i, path):
            t = t0[i]
            tot = 0.0
            prev = -1
            sp = spd[i]
            for j in path:
                t += (D0[i][j] if prev < 0 else Dtt[prev][j]) / sp
                tot += val[j] * exp(-disc * t)
                t += dwell
                prev = j
            return tot

        bundle = [[] for _ in range(n)]
        path = [[] for _ in range(n)]
        y = [[0.0] * m for _ in range(n)]          # winning bids this UAV believes in (0 = none)
        z = [[NONE] * m for _ in range(n)]         # winner this UAV believes in
        s = [[0] * n for _ in range(n)]            # timestamps: last time this UAV heard (directly or not) from each UAV

        def beats(c, i, yj, zj):
            if zj == NONE:
                return c > EPS
            if c > yj + EPS:
                return True
            return abs(c - yj) <= EPS and i < zj

        def build(i):
            """Phase 1 (Brunet Alg. 2): add tasks to the bundle, best marginal score first, while any task can still be won."""
            added = False
            while len(bundle[i]) < Lt:
                base = pscore(i, path[i])
                minbid = min((y[i][b] for b in bundle[i]), default=float("inf"))
                best = None
                inpath = set(path[i])
                for j in range(m):
                    if not compat[i][j] or j in inpath:
                        continue
                    p = path[i]
                    bc, bpos = -1.0, 0
                    for pos in range(len(p) + 1):
                        c = pscore(i, p[:pos] + [j] + p[pos:]) - base
                        if c > bc + 1e-15:
                            bc, bpos = c, pos
                    cw = min(bc, minbid) if warp else bc          # bid warping [Johnson 2012, Eq. 6]
                    st["bids"] += 1
                    if beats(cw, i, y[i][j], z[i][j]):
                        if best is None or bc > best[0] + 1e-15 or (abs(bc - best[0]) <= 1e-15 and j < best[1]):
                            best = (bc, j, bpos, cw)
                if best is None:
                    break
                bc, j, bpos, cw = best
                bundle[i].append(j)
                path[i].insert(bpos, j)
                y[i][j] = cw
                z[i][j] = i
                st["placed"] += 1
                if cw < bc - 1e-15:
                    st["warps"] += 1
                added = True
            return added

        def gt(yk, zk, yi, zi):
            """The sender's bid beats the receiver's belief (equal bids: lower winner id)."""
            if yk > yi + EPS:
                return True
            return abs(yk - yi) <= EPS and zk < zi

        def resolve(i, k, j, Yk, Zk, Sk, Si):
            """Rows 1-17 of the conflict table [Brunet 2008, Table 3.1]; i = receiver, k = sender, m = a third UAV."""
            zk, zi, yk, yi = Zk[j], z[i][j], Yk[j], y[i][j]
            upd = False
            rst = False
            if zk == k:                                   # sender thinks it holds the task
                if zi == i:                               # 1: update if the sender's bid is higher
                    upd = gt(yk, zk, yi, zi)
                elif zi == k:                             # 2: update
                    upd = True
                elif zi != NONE:                          # 3: update if the sender's news about m is newer, or its bid is higher
                    upd = Sk[zi] > Si[zi] or gt(yk, zk, yi, zi)
                else:                                     # 4: update
                    upd = True
            elif zk == i:                                 # sender thinks the receiver holds the task
                if zi == i:                               # 5: leave
                    pass
                elif zi == k:                             # 6: reset
                    rst = True
                elif zi != NONE:                          # 7: reset if the sender's news about m is newer
                    rst = Sk[zi] > Si[zi]
                else:                                     # 8: leave
                    pass
            elif zk != NONE:                              # sender thinks a third UAV m holds the task
                mm = zk
                if zi == i:                               # 9: update if news about m is newer and the sender's bid is higher
                    upd = Sk[mm] > Si[mm] and gt(yk, zk, yi, zi)
                elif zi == k:                             # 10: update if the news about m is newer, else reset
                    if Sk[mm] > Si[mm]:
                        upd = True
                    else:
                        rst = True
                elif zi == mm:                            # 11: update if the news about m is newer
                    upd = Sk[mm] > Si[mm]
                else:
                    if zi != NONE:                        # 12: the receiver thinks another UAV n holds it
                        nn = zi
                        if Sk[mm] > Si[mm] and Sk[nn] > Si[nn]:
                            upd = True
                        elif Sk[mm] > Si[mm] and gt(yk, zk, yi, zi):
                            upd = True
                        elif Sk[nn] > Si[nn] and Si[mm] > Sk[mm]:
                            rst = True
                    else:                                 # 13: update if the news about m is newer
                        upd = Sk[mm] > Si[mm]
            else:                                         # sender thinks nobody holds the task
                if zi == i:                               # 14: leave
                    pass
                elif zi == k:                             # 15: update
                    upd = True
                elif zi != NONE:                          # 16: update if the sender's news about n is newer
                    upd = Sk[zi] > Si[zi]
                else:                                     # 17: leave
                    pass
            if upd:
                if y[i][j] != yk or z[i][j] != zk:      # count only real changes, otherwise the loop never looks quiet
                    y[i][j], z[i][j] = yk, zk
                    return True
                return False
            if rst:
                if y[i][j] != 0.0 or z[i][j] != NONE:
                    y[i][j], z[i][j] = 0.0, NONE
                    return True
            return False

        def release(i):
            """Eq. 3.15: the first bundle task that is no longer ours is dropped together with every later task."""
            b = bundle[i]
            for idx, j in enumerate(b):
                if z[i][j] != i:
                    for jj in b[idx + 1:]:
                        if z[i][jj] == i:
                            z[i][jj], y[i][jj] = NONE, 0.0
                    gone = set(b[idx:])
                    bundle[i] = b[:idx]
                    path[i] = [p for p in path[i] if p not in gone]
                    st["releases"] += 1
                    return True
            return False

        dirty = [True] * n
        quiet = 0
        cap = self.round_cap or (6 * (m + n) + 24)
        converged = False
        rounds_here = 0
        for rnd in range(1, cap + 1):
            rounds_here += 1
            st["rounds"] += 1
            changed = False
            for i in range(n):
                if dirty[i] and len(bundle[i]) < Lt:
                    if build(i):
                        changed = True
                dirty[i] = False
            built = [b[:] for b in bundle] if self.trace is not None else None
            snapY = [row[:] for row in y]
            snapZ = [row[:] for row in z]
            snapS = [row[:] for row in s]
            for i in range(n):
                Si = snapS[i]
                ch = False
                for k in nbr[i]:
                    Yk, Zk, Sk = snapY[k], snapZ[k], snapS[k]
                    for j in range(m):
                        if resolve(i, k, j, Yk, Zk, Sk, Si):
                            ch = True
                # timestamps: direct neighbours = now; others = newest news any neighbour has [Brunet Eq. 3.14]
                for o in range(n):
                    if o == i:
                        continue
                    if o in nbr[i]:
                        s[i][o] = rnd
                    else:
                        s[i][o] = max([snapS[i][o]] + [snapS[k][o] for k in nbr[i]])
                if release(i):
                    ch = True
                if ch:
                    dirty[i] = True
                    changed = True
            if self.trace is not None:
                self.trace.append({'round': rnd, 'built': built, 'bundle': [b[:] for b in bundle], 'z': [r[:] for r in z], 'y': [[round(v, 4) for v in r] for r in y], 'changed': changed})
            quiet = 0 if changed else quiet + 1
            if quiet >= diam + 1:
                converged = True
                break
        st["max_rounds_one_auction"] = max(st["max_rounds_one_auction"], rounds_here)
        if not converged:
            st["nonconverged"] += 1
        # --- final paths. After convergence every task is in at most one path. If the cap was hit, keep one owner per task
        out = [[] for _ in range(n)]
        owner = {}
        for i in range(n):
            for j in path[i]:
                if z[i][j] != i:
                    continue
                if j in owner:
                    st["repaired"] += 1
                    o = owner[j]
                    if (y[i][j], -i) > (y[o][j], -o):         # higher bid wins, then lower id
                        out[o] = [p for p in out[o] if p != j]
                        owner[j] = i
                        out[i].append(j)
                else:
                    owner[j] = i
                    out[i].append(j)
        # order inside each UAV's path is the order in path[i]
        final = []
        for i in range(n):
            keep = set(out[i])
            final.append([p for p in path[i] if p in keep])
        return final


# =====================================================================================================================
# the V1 allocator, wrapped without change
# =====================================================================================================================
class LegacyGreedyS1:
    """V1 packages/allocation/cbba.py (one task per UAV, shared table). Called repeatedly in a roll-out: allocate to the UAVs that are free,
    advance to the next time a UAV becomes free, allocate again. That is exactly what V1 mission.py does when every visit succeeds."""
    name = "legacy_greedy_s1"

    def __init__(self):
        paths.add_v1_to_path()
        for rel in ("V1/packages/allocation/cbba.py", "V1/packages/allocation/bids.py", "V1/packages/allocation/world.py"):
            if paths.sha256_file(paths.ROOT / rel) != paths.PINS[rel]:
                raise SystemExit("%s is not the audited version. Stop." % rel)
        from packages.allocation import cbba as v1cbba          # noqa: E402
        self._allocate = v1cbba.allocate
        self.last_stats = None

    @staticmethod
    def _sensor_name(req):
        if not req:
            return "ANY"
        if len(req) == 1:
            return next(iter(req))
        return "THERMAL"          # two cameras: only a UAV with both can do it; in this fleet that is the THERMAL UAV

    def plan(self, prob):
        agents = sorted(prob.agents, key=lambda a: a.id)
        tasks = sorted(prob.tasks, key=lambda t: t.key)
        by_key = {t.key: t for t in tasks}
        uavs = [SimpleNamespace(id=a.id, speed=a.speed, sensors=tuple(sorted(a.sensors))) for a in agents]
        v1tasks = {t.key: {"id": t.key, "landmark": t.landmark, "sensor": self._sensor_name(t.req), "priority": t.pri} for t in tasks}
        pos = {a.id: a.pos for a in agents}
        free_at = {a.id: a.avail for a in agents}
        pending = dict(v1tasks)
        banned = {k: set(v) for k, v in prob.banned.items()}
        path_keys = {a.id: [] for a in agents}
        T = prob.now
        calls = 0
        guard = 0
        while pending and guard < 10 * (len(tasks) + len(agents)) + 10:
            guard += 1
            free = [u for u in uavs if free_at[u.id] <= T + 1e-9]
            if free:
                assignment, _ = self._allocate(free, list(pending.values()), pos, T, banned)
                calls += 1
                got = False
                for u in free:
                    tid = assignment[u.id]
                    if tid is None:
                        continue
                    task = pending.pop(tid)
                    p = prob.landmarks[task["landmark"]]
                    arrive = T + math.dist(pos[u.id], p) / u.speed
                    free_at[u.id] = arrive + prob.dwell
                    pos[u.id] = p
                    path_keys[u.id].append(tid)
                    got = True
                if got and pending:
                    nxt = [t for t in free_at.values() if t > T + 1e-9]
                    if not nxt:
                        break
                    T = min(nxt)
                    continue
            nxt = [t for t in free_at.values() if t > T + 1e-9]
            if not nxt:
                break
            T = min(nxt)
        info = {"rounds": calls, "passes": calls, "converged": True, "warps": 0, "releases": 0, "nonconverged": 0, "repaired": 0}
        self.last_stats = info
        return _finish_plan(prob, agents, by_key, path_keys, list(pending), info)


def make_allocator(name, **kw):
    if name in ("cbba_bounded", "bounded"):
        return BoundedCBBA(**kw)
    if name in ("legacy_greedy_s1", "legacy"):
        return LegacyGreedyS1()
    raise ValueError(name)
