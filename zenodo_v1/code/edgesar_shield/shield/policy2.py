"""
Iteration 1 (docs/ITERATION1_PROTOCOL.md): the revised Shield and the equal-footing gate.  Runtime code: a policy sees only a `View` and the readout `Service`.
The old arms (policy.py) are NOT changed.

ShieldV2(strict, mass_guard, cost_aware)
  strict      every candidate's plan is checked against ITS OWN task (priority -> its own deadline, camera -> its own R1);
              certified needs one execution signature AND one feasibility status for all candidates
  mass_guard  certified also needs the conformal set's score mass >= 1 - alpha (agreement inside an incomplete set is not proof of safety).
              Low mass with agreeing plans cannot be repaired by a cover: escalate while the cap allows, else UNSUPPORTED_COMMIT (visible, unresolved)
  cost_aware  a fallback is chosen by its predicted effect on ALL pending incidents (runtime information only):
              n_bad(option) = |R1 U R2 U R3| fleet-wide under the believed deadlines;
              full cover if n_bad(full) <= n_bad(r-hat), else location cover if n_bad(loc) <= n_bad(r-hat), else COVER_DECLINED (commit r-hat)
GateFB   confidence gate with the SAME fallback machinery and the same verification cap (equal footing)
"""
from dataclasses import dataclass, field

from .candidates import conformal_set
from .cover import build_cover, uncovered_rows
from .policy import Observer, ShieldPolicy, asks
from .service import uniform01
from .sim import Decision, apply_record, canon_table


@dataclass
class Assessment2:
    members: list
    rkey: object
    r_in_set: bool
    certified: bool
    reason: str                       # "" | EMPTY | OVERSIZE | RHAT_OUT | DIFFERENT_PLANS | FEASIBILITY_DIFFERS | LOW_MASS
    risk: tuple
    mass: float
    sigs: dict = field(default_factory=dict)
    feas: dict = field(default_factory=dict)       # candidate key -> own requirements met under that candidate's own task
    evs: dict = field(default_factory=dict)
    n_distinct_sigs: int = 0


def n_bad(ev):
    """Fleet-wide predicted unmet requirements (believed deadlines): distinct tasks breaking R1, R2 or R3."""
    d = ev.details
    return len(set(d["R1"]) | set(d["R2"]) | set(d["R3"]))


class ShieldV2(ShieldPolicy):
    def __init__(self, service, q, K=8, theta=None, xi=1.0, seed=0, alpha=0.10, mass_guard=True, cost_aware=True):
        super().__init__(service, q, K, "shield", True, theta, xi, seed)
        self.alpha, self.mass_guard, self.cost_aware = alpha, mass_guard, cost_aware

    # ------------------------------------------------------------------ the assessment
    def assess2(self, view, free=False):
        rid = view.case_id
        cands, rec, S, _ = self._members(rid)
        rkey = rec["key"]
        keys = [c["key"] for c in S]
        r_in = rkey in keys
        top_res = 1.0 - rec["score"]
        mass = sum(m["score"] for m in S)
        if len(S) == 0 or len(S) > self.K or not r_in:
            reason = "EMPTY" if len(S) == 0 else ("OVERSIZE" if len(S) > self.K else "RHAT_OUT")
            return Assessment2(S, rkey, r_in, False, reason, (1.0, top_res), mass)
        evaluate = (lambda tb: view.evaluate(tb, free=True)) if free else view.evaluate
        base = view.open_table
        order = [m for m in S if m["key"] == rkey] + [m for m in S if m["key"] != rkey]
        sigs, feas, evs = {}, {}, {}
        for m in order:
            e = evaluate(apply_record(base, m["norm"]))
            sigs[m["key"]], evs[m["key"]] = e.sig, e
            feas[m["key"]] = self._own_requirements(view, e)[0]       # this candidate's own task, its own deadline and camera
        same_plan = all(sigs[k] == sigs[rkey] for k in keys)
        same_feas = all(feas[k] == feas[rkey] for k in keys)
        low_mass = self.mass_guard and mass < 1.0 - self.alpha - 1e-12
        cert = same_plan and same_feas and not low_mass
        reason = "" if cert else ("DIFFERENT_PLANS" if not same_plan else ("FEASIBILITY_DIFFERS" if not same_feas else "LOW_MASS"))
        good = sum(m["score"] for m in S if sigs[m["key"]] == sigs[rkey] and feas[m["key"]] == feas[rkey])
        rho = 0.0 if cert else max(1.0 - good, 1e-12)
        return Assessment2(S, rkey, r_in, cert, reason, (rho, top_res), mass, sigs, feas, evs, len(set(sigs.values())))

    def runs_needed(self, view):
        cands, rec, S, _ = self._members(view.case_id)
        early = len(S) == 0 or len(S) > self.K or rec["key"] not in [c["key"] for c in S]
        return (0 if early else len(S)) + (3 if early else 2)          # r-hat + full cover + location cover is the upper bound

    # ------------------------------------------------------------------ the fallback (shared with the gate)
    def fallback(self, view, members, partial, ev_r, rec, table_r, diag):
        base = view.open_table
        tag = int(round(view.now * 1000))
        rows_f, info_f = build_cover(base, members, tag=tag, rhat=rec["norm"])
        ev_f = view.evaluate(rows_f)
        rows, info, ev, choice = rows_f, info_f, ev_f, "full"
        diag["n_bad_r"], diag["n_bad_full"] = n_bad(ev_r), n_bad(ev_f)
        if self.cost_aware and n_bad(ev_f) > n_bad(ev_r):
            rows_l, info_l = build_cover(base, members, tag=tag, rhat=rec["norm"], camera="rhat", priority="rhat")
            if canon_table(rows_l) == canon_table(rows_f):
                ev_l = ev_f
            else:
                ev_l = view.evaluate(rows_l)
            diag["n_bad_loc"] = n_bad(ev_l)
            if n_bad(ev_l) <= n_bad(ev_r):
                rows, info, ev, choice = rows_l, info_l, ev_l, "location"
            else:
                diag["fallback_choice"] = "declined"
                return Decision("COMMIT", "COVER_DECLINED", table=table_r, record=rec["norm"], diag=diag)
        ok, bad = self._own_requirements(view, ev)
        miss = {}
        for m in members:
            u = uncovered_rows(rows, apply_record(base, m["norm"]))
            if u:
                miss[str(m["key"])] = u
        complete = (not miss) and (not partial)
        diag.update({"cover": info, "partial_cover": partial, "cover_complete": complete, "cover_unserved_candidates": len(miss),
                     "fallback_choice": choice})
        if not ok:
            diag["uncovered"] = {k: v for k, v in bad.items() if v}
            return Decision("COMMIT", "FALLBACK_UNRESOLVED", table=rows, record=rec["norm"], diag=diag)
        if complete:
            return Decision("COMMIT", "FALLBACK_COVERED", table=rows, record=rec["norm"], diag=diag)
        return Decision("COMMIT", "FALLBACK_PARTIAL", table=rows, record=rec["norm"], diag=diag)

    def _fallback_members(self, view, a):
        cands = self.svc.candidates(view.case_id)
        if len(a.members) == 0 or len(a.members) > self.K:
            return cands[:self.K], True
        return a.members, False

    # ------------------------------------------------------------------ the decision
    def on_report(self, view):
        rid = view.case_id
        rec = self.svc.pilot_record(rid)
        base = view.open_table
        table_r = apply_record(base, rec["norm"])
        if self.runs_needed(view) > view.runs_available():
            return Decision("COMMIT", "TIMEOUT", table=table_r, record=rec["norm"], diag={"needed_runs": self.runs_needed(view)})
        a = self.assess2(view)
        diag = {"set_size": len(a.members), "certified": a.certified, "rho": a.risk[0], "r_in_set": a.r_in_set, "reason": a.reason,
                "distinct_sigs": a.n_distinct_sigs, "mass": round(a.mass, 4)}
        if a.certified:
            if a.feas[a.rkey]:
                return Decision("COMMIT", "ACCEPT", table=table_r, record=rec["norm"], diag=diag)
            diag["unmet"] = {k: v for k, v in self._own_requirements(view, a.evs[a.rkey])[1].items() if v}
            return Decision("COMMIT", "ACCEPT_INFEASIBLE", table=table_r, record=rec["norm"], diag=diag)
        u = uniform01(self.seed, "tie:" + rid)
        if view.budget_left > 0 and asks(a.risk, u, self.theta, self.xi):
            return Decision("ESCALATE", "ESCALATE", record=rec["norm"], diag=diag)
        if a.reason == "LOW_MASS":                                 # plans and feasibility agree: a cover would change nothing
            return Decision("COMMIT", "UNSUPPORTED_COMMIT", table=table_r, record=rec["norm"], diag=diag)
        members, partial = self._fallback_members(view, a)
        ev_r = a.evs.get(a.rkey) or view.evaluate(table_r)
        return self.fallback(view, members, partial, ev_r, rec, table_r, diag)


class GateFB:
    """The equal-footing gate (G1): confidence trigger, same verification cap, same cost-aware fallback on the same conformal set."""

    def __init__(self, service, q, K, theta_esc, xi_esc, theta_fb, xi_fb, seed=0):
        self.svc, self.seed = service, seed
        self.th_esc, self.xi_esc, self.th_fb, self.xi_fb = theta_esc, xi_esc, theta_fb, xi_fb
        self.fb = ShieldV2(service, q, K, mass_guard=False, cost_aware=True, seed=seed)

    def on_report(self, view):
        rid = view.case_id
        rec = self.svc.pilot_record(rid)
        base = view.open_table
        table_r = apply_record(base, rec["norm"])
        risk = (1.0 - self.svc.confidence(rid),)
        u = uniform01(self.seed, "tie:" + rid)
        diag = {"risk": risk[0]}
        if view.budget_left > 0 and asks(risk, u, self.th_esc, self.xi_esc):
            return Decision("ESCALATE", "ESCALATE", record=rec["norm"], diag=diag)
        if not asks(risk, u, self.th_fb, self.xi_fb):
            return Decision("COMMIT", "COMMIT", table=table_r, record=rec["norm"], diag=diag)
        if 3 > view.runs_available():
            return Decision("COMMIT", "TIMEOUT", table=table_r, record=rec["norm"], diag={"needed_runs": 3})
        cands = self.svc.candidates(rid)
        S = conformal_set(cands, self.fb.q)
        members, partial = (cands[:self.fb.K], True) if (len(S) == 0 or len(S) > self.fb.K) else (S, False)
        ev_r = view.evaluate(table_r)
        return self.fb.fallback(view, members, partial, ev_r, rec, table_r, diag)


class ObserverV2(Observer):
    """CAL episodes: commits like A1 and logs every gate's risk, now including the two assessments of iteration 1 (free what-if runs)."""

    def __init__(self, service, q, K=8, alpha=0.10):
        super().__init__(service, q, K)
        self.s1 = ShieldV2(service, q, K, mass_guard=False, cost_aware=False, alpha=alpha)
        self.s2 = ShieldV2(service, q, K, mass_guard=True, cost_aware=False, alpha=alpha)

    def on_report(self, view):
        n0 = len(self.rows)
        dec = super().on_report(view)
        a1, a2 = self.s1.assess2(view, free=True), self.s2.assess2(view, free=True)
        self.rows[n0].update({"s1": a1.risk, "s2": a2.risk, "s1_flag": not a1.certified, "s2_flag": not a2.certified, "s2_reason": a2.reason})
        return dec
