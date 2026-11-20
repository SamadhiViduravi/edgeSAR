"""
The policies (arms) and the Shield (plan sections 4.3-4.7 and 7).  Runtime code: a policy sees only a `View` and the readout `Service`.

Arms
  CommitPolicy      A1-A5   commit the pilot-style record of the readout (which readout is the service's business)
  RiskGate          A6, A6b, A7   ask for verification when a risk score is above a threshold chosen on CAL reports (budget matching); else commit
  ShieldPolicy      A8-A11  calibrated candidate set -> execution signatures -> certify / verify / cover
  Observer          commits the pilot-style record and logs every gate's risk score (used on CAL episodes to set the thresholds)

Risk scores are tuples (compared in order).  A threshold is (theta, xi) found on CAL so that the expected request rate is b:
    ask when risk > theta, or risk == theta and u < xi   (u is a fixed pseudo-random number of the report)
and a hard cap of b x reports per episode is enforced by the simulator.
"""
from dataclasses import dataclass, field

from .alloc import plan_signature
from .candidates import conformal_set
from .cover import build_cover, uncovered_rows
from .service import uniform01
from .sim import Decision, apply_record


# =====================================================================================================================
# thresholds for budget matching
# =====================================================================================================================
def rate_threshold(risks, b):
    """(theta, xi) such that  P(risk > theta) + xi * P(risk == theta) = b  on the given calibration risks.  Risks may be tuples."""
    n = len(risks)
    m = b * n
    order = sorted(risks, reverse=True)
    j = int(m)                                    # floor
    if j >= n:
        return None, 1.0                          # ask about everything
    theta = order[j]                              # the (j+1)-th largest
    c_gt = sum(1 for r in risks if r > theta)
    c_eq = sum(1 for r in risks if r == theta)
    xi = (m - c_gt) / c_eq
    return theta, xi


def asks(risk, u, theta, xi):
    if theta is None:
        return True
    return risk > theta or (risk == theta and u < xi)


# =====================================================================================================================
# the baselines
# =====================================================================================================================
class CommitPolicy:
    """A1-A5: commit the readout's pilot-style record. No gate."""
    label = "COMMIT"

    def __init__(self, service):
        self.svc = service

    def on_report(self, view):
        rec = self.svc.pilot_record(view.case_id)
        return Decision("COMMIT", "COMMIT", table=apply_record(view.open_table, rec["norm"]), record=rec["norm"],
                        diag={"conf": self.svc.confidence(view.case_id), "top_score": rec["score"]})


class RiskGate:
    """A6 (risk = 1 - pilot confidence), A6b (risk = 1 - score of the committed record), A7 (risk = a fixed random number)."""

    def __init__(self, service, kind, theta, xi, seed=0):
        self.svc, self.kind, self.theta, self.xi, self.seed = service, kind, theta, xi, seed

    def risk(self, rid):
        if self.kind == "conf":
            return (1.0 - self.svc.confidence(rid),)
        if self.kind == "topscore":
            return (1.0 - self.svc.pilot_record(rid)["score"],)
        if self.kind == "random":
            return (uniform01(self.seed, "gate:" + rid),)
        raise ValueError(self.kind)

    def on_report(self, view):
        rid = view.case_id
        rec = self.svc.pilot_record(rid)
        r = self.risk(rid)
        u = uniform01(self.seed, "tie:" + rid)
        if view.budget_left > 0 and asks(r, u, self.theta, self.xi):
            return Decision("ESCALATE", "ESCALATE", record=rec["norm"], diag={"risk": r[0]})
        return Decision("COMMIT", "COMMIT", table=apply_record(view.open_table, rec["norm"]), record=rec["norm"], diag={"risk": r[0]})


# =====================================================================================================================
# the Shield
# =====================================================================================================================
@dataclass
class Assessment:
    members: list                     # the candidate set that was assessed (dicts key, norm, score)
    rkey: object                      # key of the committed (pilot-style) record
    r_in_set: bool
    certified: bool
    rho: float                        # share of the set's mass that leads to a different execution than the committed record
    risk: tuple
    sigs: dict = field(default_factory=dict)      # key -> signature
    ev_r: object = None               # Evaluation of the committed record (None when not computed)
    reason: str = ""                  # why not certified: EMPTY | OVERSIZE | RHAT_OUT | DIFFERENT_PLANS | SINGLETON_ONLY
    n_distinct_sigs: int = 0
    timeout: bool = False


class ShieldPolicy:
    """modes:  'shield' A8 / A10 (conformal set + signatures),  'nodown' A9 (singleton set only),  'top2' A11 (top two candidates + committed record, no conformal).
    cover=True: uncertified and not verified -> cover (A8, A9, A11);  cover=False -> UNCERTIFIED_COMMIT (A10)."""

    def __init__(self, service, q, K=8, mode="shield", cover=True, theta=None, xi=1.0, seed=0, cover_kw=None):
        self.svc, self.q, self.K, self.mode, self.cover = service, q, K, mode, cover
        self.theta, self.xi, self.seed = theta, xi, seed
        self.cover_kw = dict(cover_kw or {})            # development variants of the cover (default: the plan's cover)

    # ------------------------------------------------------------------ helpers
    def _members(self, rid):
        cands = self.svc.candidates(rid)
        rec = self.svc.pilot_record(rid)
        if self.mode == "top2":
            seen, out = set(), []
            for c in [rec] + cands[:2]:
                if c["key"] not in seen:
                    seen.add(c["key"])
                    out.append(c)
            return cands, rec, out, out
        S = conformal_set(cands, self.q)
        return cands, rec, S, S

    @staticmethod
    def _own_requirements(view, ev):
        own = view.ns + ":"
        det = ev.details
        bad = {k: [x for x in det[k] if x.startswith(own)] for k in ("R1", "R2", "R3")}
        return not any(bad.values()), bad

    # ------------------------------------------------------------------ the assessment (costs allocator runs unless free)
    def assess(self, view, free=False):
        rid = view.case_id
        cands, rec, S, _ = self._members(rid)
        rkey = rec["key"]
        keys = [c["key"] for c in S]
        r_in = rkey in keys
        top_res = 1.0 - rec["score"]
        evaluate = (lambda tb: view.evaluate(tb, free=True)) if free else view.evaluate
        base = view.open_table
        # --- cheap exits: no allocator run is needed to see that the set is unusable
        if self.mode != "top2" and (len(S) == 0 or len(S) > self.K or not r_in):
            reason = "EMPTY" if len(S) == 0 else ("OVERSIZE" if len(S) > self.K else "RHAT_OUT")
            return Assessment(S, rkey, r_in, False, 1.0, (1.0, top_res), reason=reason)
        if self.mode == "nodown":
            ev_r = evaluate(apply_record(base, rec["norm"]))
            cert = len(S) == 1
            return Assessment(S, rkey, r_in, cert, 0.0 if cert else 1.0, (0.0 if cert else 1.0, top_res), ev_r=ev_r,
                              reason="" if cert else "SINGLETON_ONLY", n_distinct_sigs=1 if cert else 0)
        # --- execution signature of every member (the committed record first)
        order = [m for m in S if m["key"] == rkey] + [m for m in S if m["key"] != rkey]
        sigs, ev_r = {}, None
        for m in order:
            e = evaluate(apply_record(base, m["norm"]))
            sigs[m["key"]] = e.sig
            if m["key"] == rkey:
                ev_r = e
        mass = sum(m["score"] for m in S)
        diff = sum(m["score"] for m in S if sigs[m["key"]] != sigs[rkey])
        rho = (diff / mass) if mass > 0 else 1.0
        cert = not any(sigs[m["key"]] != sigs[rkey] for m in S)
        return Assessment(S, rkey, r_in, cert, 0.0 if cert else rho, (0.0 if cert else max(rho, 1e-12), top_res), sigs=sigs, ev_r=ev_r,
                          reason="" if cert else "DIFFERENT_PLANS", n_distinct_sigs=len(set(sigs.values())))

    def runs_needed(self, view):
        cands, rec, S, _ = self._members(view.case_id)
        if self.mode != "top2" and (len(S) == 0 or len(S) > self.K or rec["key"] not in [c["key"] for c in S]):
            return 1 if self.cover else 0                    # only the cover run (partial cover is planned once)
        return (1 if self.mode == "nodown" else len(S)) + (1 if self.cover else 0)

    # ------------------------------------------------------------------ the decision
    def on_report(self, view):
        rid = view.case_id
        rec = self.svc.pilot_record(rid)
        base = view.open_table
        table_r = apply_record(base, rec["norm"])
        if self.runs_needed(view) > view.runs_available():
            return Decision("COMMIT", "TIMEOUT", table=table_r, record=rec["norm"], diag={"needed_runs": self.runs_needed(view)})
        a = self.assess(view)
        diag = {"set_size": len(a.members), "certified": a.certified, "rho": a.rho, "r_in_set": a.r_in_set, "reason": a.reason,
                "distinct_sigs": a.n_distinct_sigs}
        if a.certified:
            ev = a.ev_r
            ok, bad = self._own_requirements(view, ev)
            if ok:
                return Decision("COMMIT", "ACCEPT", table=table_r, record=rec["norm"], diag=diag)
            diag["unmet"] = {k: v for k, v in bad.items() if v}
            return Decision("COMMIT", "ACCEPT_INFEASIBLE", table=table_r, record=rec["norm"], diag=diag)
        # --- not certified
        u = uniform01(self.seed, "tie:" + rid)
        if view.budget_left > 0 and asks(a.risk, u, self.theta, self.xi):
            return Decision("ESCALATE", "ESCALATE", record=rec["norm"], diag=diag)
        if not self.cover:
            return Decision("COMMIT", "UNCERTIFIED_COMMIT", table=table_r, record=rec["norm"], diag=diag)
        # --- cover
        cands = self.svc.candidates(rid)
        partial = False
        if self.mode == "top2":
            members = a.members
        elif len(a.members) == 0 or len(a.members) > self.K:
            members, partial = cands[:self.K], True
        else:
            members = a.members
        rows, info = build_cover(base, members, tag=int(round(view.now * 1000)), rhat=rec["norm"], **self.cover_kw)
        ev = view.evaluate(rows)
        ok, bad = self._own_requirements(view, ev)
        # is every plausible candidate really served by the cover?  (the plan's cover is by construction; the development variants are not)
        miss = {}
        for m in members:
            u = uncovered_rows(rows, apply_record(base, m["norm"]))
            if u:
                miss[str(m["key"])] = u
        complete = (not miss) and (not partial)
        diag.update({"cover": info, "partial_cover": partial, "cover_complete": complete, "cover_unserved_candidates": len(miss)})
        if not ok:
            diag["uncovered"] = {k: v for k, v in bad.items() if v}
            return Decision("COMMIT", "FALLBACK_UNRESOLVED", table=rows, record=rec["norm"], diag=diag)
        if complete:
            return Decision("COMMIT", "FALLBACK_COVERED", table=rows, record=rec["norm"], diag=diag)
        return Decision("COMMIT", "FALLBACK_PARTIAL", table=rows, record=rec["norm"], diag=diag)


# =====================================================================================================================
# the observer (CAL episodes): commits the pilot-style record, logs every risk score
# =====================================================================================================================
class Observer:
    def __init__(self, service, q, K=8):
        self.svc = service
        self.shield = ShieldPolicy(service, q, K, "shield", True)
        self.nodown = ShieldPolicy(service, q, K, "nodown", True)
        self.top2 = ShieldPolicy(service, q, K, "top2", True)
        self.rows = []

    def on_report(self, view):
        rid = view.case_id
        rec = self.svc.pilot_record(rid)
        a8 = self.shield.assess(view, free=True)
        a9 = self.nodown.assess(view, free=True)
        a11 = self.top2.assess(view, free=True)
        self.rows.append({"id": rid, "conf": (1.0 - self.svc.confidence(rid),), "topscore": (1.0 - rec["score"],),
                          "a8": a8.risk, "a9": a9.risk, "a11": a11.risk, "a8_cert": a8.certified, "a8_size": len(a8.members),
                          "a8_reason": a8.reason})
        return Decision("COMMIT", "COMMIT", table=apply_record(view.open_table, rec["norm"]), record=rec["norm"])
