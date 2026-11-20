"""
Demo: the Shield, case by case, on real reports.  Development data (saved vectors), level M, arrival seed 1, the settings of the main development run.

    python demo.py                      all cases (one per outcome class, plus a failure case), about 1 minute
    python demo.py --list               only show which case was chosen for each class, and by which rule
    python demo.py --only ACCEPT FAILURE_CASE      chosen cases only

How the cases are chosen (the rule of STRENGTHENING_PLAN section 8.6, fixed before looking): for each outcome class, the FIRST episode (by episode id) in which the
arm shows that class, and in it the first report of that class; plus the first episode where the plan's Shield (A8) misses an incident that the confidence gate
(A6) verifies on time (the FAILURE CASE).  Nothing is hand-picked.  The FRESH demo uses the same rule on the fresh run, after the analysis.

For every case the demo prints: the report; the open incidents the system believes in; the candidate records with their scores; the execution plan each
candidate leads to; whether the set is certified (all plans equal); the decision and its reason; the cost; and, marked EVALUATION ONLY because the system
cannot see it, the gold record and what happened to the real incidents of the report, next to what the confidence gate (A6) and always-commit (A1) did.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shield import devrun, paths                                  # noqa: E402
from shield.devset import DevSet                                  # noqa: E402
from shield.sim import SimConfig                                  # noqa: E402

# (class, arm that shows it, run it is chosen from, note)
CLASS_CASES = [
    ("ACCEPT", "A8", "main", "Every candidate leads to the same plan and the requirements hold: commit the best record."),
    ("ACCEPT_INFEASIBLE", "A8", "main", "Certified, but the fleet cannot meet a requirement (for example a deadline). Verifying would not help: commit, raise an alarm, count it."),
    ("ESCALATE", "A8", "main", "Not certified and the verification budget has room: ask for verification; the change waits for the answer."),
    ("FALLBACK_COVERED", "A8", "main", "Not certified, no budget: plan the union (cover) of what the candidates imply; it is feasible and serves every candidate."),
    ("FALLBACK_UNRESOLVED", "A8", "main", "Not certified, no budget, and the cover itself breaks a requirement: commit it best-effort and count the incident as unresolved."),
    ("FALLBACK_PARTIAL", "A8c", "main", "Shown for A8c (location cover). The plan's cover (A8) has this class only for empty or oversized sets, which do not occur in this run. "
                                          "Here the cover keeps the best record's camera and priority, so it does not serve every plausible candidate."),
    ("UNCERTIFIED_COMMIT", "A10", "main", "Ablation arm A10 (Shield without any fallback): not certified, not verified, so it commits the best record anyway."),
    ("TIMEOUT", "A8", "ac10", "Same Shield, but one allocator run costs 1.0 s (limit 5 s per decision): the decision does not fit, so it commits the best record unassessed."),
]
SHOW_ARMS = ["A1", "A6"]


# ---------------------------------------------------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------------------------------------------------
def fmt_record(r):
    if r is None:
        return "-"
    a = r["action"]
    if a == "CREATE_VERIFICATION":
        return "CREATE %s %s p%s" % (r["landmark"], r["sensor"], r["priority"])
    if a == "UPDATE_INCIDENT":
        return "UPDATE %s -> %s %s p%s" % (r["incident"], r["landmark"], r["sensor"], r["priority"])
    if a == "CLOSE_INCIDENT":
        return "CLOSE %s" % r["incident"]
    return "NO_ACTION"


def fmt_open(rows):
    return "; ".join("%s %s %s p%s" % (r["id"], r["landmark"], r["sensor"], r["priority"]) for r in rows) or "(none)"


def fmt_sig(sig):
    active, routes, left = sig

    def t(x):
        lm, cams = x
        return "%s%s" % (lm, " [THERMAL]" if "THERMAL" in cams else "")
    parts = ["%s: %s" % (u, " > ".join(t(x) for x in path)) for u, path in routes]
    if left:
        parts.append("NOT ASSIGNED: " + ", ".join(t(x) for x in left))
    return " | ".join(parts) if parts else "(no task)"


def fmt_inc(i):
    ns, iid, lm, sensor, pri, created, deadline, ver, cls = i
    return "%s %s %s p%s: %s (deadline %.0f s%s)" % (iid, lm, sensor, pri, {"on_time": "verified ON TIME", "late": "verified LATE", "unverified": "NOT VERIFIED",
                                                    "resolved_external": "resolved externally"}.get(cls, cls),
                                                    deadline, "" if ver is None else ", verified at %.0f s" % ver)


# ---------------------------------------------------------------------------------------------------------------------
# selection by the fixed rule
# ---------------------------------------------------------------------------------------------------------------------
def load_records(tag, level, seed):
    f = paths.RESULTS / "dev" / tag / ("records_%s_s%d.json.gz" % (level, seed))
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def class_of(outcome):
    return "TIMEOUT_LATE" if outcome.startswith("TIMEOUT_LATE") else outcome.split(":")[0]


def select(level, seed):
    cases = []
    cache = {}
    for cls, arm, tag, note in CLASS_CASES:
        if tag not in cache:
            cache[tag] = load_records(tag, level, seed)
        found = None
        for r in sorted((x for x in cache[tag] if x["arm"] == arm), key=lambda x: x["episode"]):
            for rep in r["reports"]:                           # reports are in arrival order
                if class_of(rep["o"]) == cls:
                    found = (r["episode"], r["fold"], rep["id"])
                    break
            if found:
                break
        cases.append({"name": cls, "arm": arm, "tag": tag, "note": note, "found": found})
    # the failure case: A8 misses an incident that A6 verifies on time
    recs = cache.get("main") or load_records("main", level, seed)
    a6 = {r["episode"]: r for r in recs if r["arm"] == "A6"}
    found = None
    for r in sorted((x for x in recs if x["arm"] == "A8"), key=lambda x: x["episode"]):
        base = {(i[0], i[1]): i for i in a6[r["episode"]]["inc"]}
        for i in r["inc"]:
            j = base.get((i[0], i[1]))
            if j and j[8] == "on_time" and i[8] in ("late", "unverified"):
                found = (r["episode"], r["fold"], i[0], i[1])
                break
        if found:
            break
    cases.append({"name": "FAILURE_CASE", "arm": "A8", "tag": "main", "found": found,
                  "note": "A8 misses a real incident that the confidence gate A6 verifies on time (the first such incident by episode id)."})
    return cases


# ---------------------------------------------------------------------------------------------------------------------
# running the chosen episodes with a recorder around the policies
# ---------------------------------------------------------------------------------------------------------------------
class Recorder:
    """Wraps a policy: records what it saw and decided.  It changes nothing: the extra assessment is a free what-if (not charged, not fed back)."""

    def __init__(self, arm, policy, store):
        self.arm, self.p, self.store = arm, policy, store

    def on_report(self, view):
        rec = {"now": view.now, "open": [dict(r) for r in view.open_table], "budget_left": view.budget_left}
        if hasattr(self.p, "assess"):
            rec["assessment"] = self.p.assess(view, free=True)
        dec = self.p.on_report(view)
        rec["decision"] = dec
        self.store[(self.arm, view.case_id)] = rec
        return dec


def run_cases(ds, cases, level, seed):
    """Re-run the episodes of the chosen cases with the same settings and thresholds as the development run; return per-case material."""
    want = {}
    for c in cases:
        if c["found"]:
            want.setdefault(c["tag"], {}).setdefault(c["found"][1], set()).add(c["found"][0])
    out = {}
    for tag, by_fold in want.items():
        cfg = SimConfig(alloc_cost_s=1.0) if tag == "ac10" else SimConfig()
        for k, eps in sorted(by_fold.items()):
            store, keep = {}, {}
            devrun.run_fold(ds, k, level, seed=seed, cfg=cfg, arms=["A1", "A6", "A8", "A8c", "A10"], only_episodes=eps, wrap=lambda a, p: Recorder(a, p, store), keep=keep)
            for e in eps:
                out[(tag, e)] = {"store": store, "res": {a: keep[(e, a)] for a in ("A1", "A6", "A8", "A8c", "A10")}}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------------------------------------------------
def report_row(res, rid):
    return next(r for r in res["log"]["reports"] if r["case_id"] == rid)


def cover_trips(res, ns):
    v = [x for x in res["log"]["visits"] if x["key"].startswith(ns + ":") and x["cover"]]
    return len(v), sum(1 for x in v if x["result"] != "verified")


def incidents_of(res, ns):
    return [[i["ns"], i["iid"], i["landmark"], i["sensor"], i["priority"], i["created"], i["deadline"], i["verified_at"], i["class"]] for i in res["incidents"] if i["ns"] == ns]


def print_case(n, total, c, ds, mat, q, K):
    tag, (ep, fold, rid) = c["tag"], c["found"][:3]
    m = mat[(tag, ep)]
    arm = c["arm"]
    res = m["res"][arm]
    rec = m["store"][(arm, rid)]
    row = report_row(res, rid)
    case = next(x for x in ds.cases if x["id"] == rid)
    print("=" * 110)
    print("CASE %d of %d: %s    (arm %s: %s; episode %s, fold %d%s)" % (n, total, c["name"], arm, devrun.ARM_TEXT[arm], ep, fold,
                                                                 "; allocator run costs 1.0 s" if tag == "ac10" else ""))
    print("=" * 110)
    print("Why this class: " + c["note"])
    print("\nReport %s arrives at t = %.1f s   (source %s, time stamp %s). Verification budget left: %d of %d." % (rid, row["t"], case["source"], case["time"], rec["budget_left"], res["budget_cap"]))
    print('  Text: "%s"' % case["text"])
    print("  The system believes these incidents are open: %s" % fmt_open(rec["open"]))
    a = rec.get("assessment")
    if a is not None:
        print("\nCandidate records (conformal set, alpha 0.10, threshold q = %.3f, at most K = %d):  %d candidate(s)%s" % (q, K, len(a.members), "" if a.members else " - the set is EMPTY"))
        for m_ in a.members:
            star = "*" if m_["key"] == a.rkey else " "
            plan = fmt_sig(a.sigs[m_["key"]]) if m_["key"] in a.sigs else "(no plan computed)"
            print("  %s score %.3f  %-46s -> plan: %s" % (star, m_["score"], fmt_record(m_["norm"]), plan))
        print("  (* = the record the readout would commit, r-hat%s)" % ("" if a.r_in_set else "; it is NOT in the set"))
        if a.certified:
            print("Distinct plans: %d  ->  CERTIFIED: every candidate leads to the same plan." % a.n_distinct_sigs)
        else:
            why = {"EMPTY": "the set is empty", "OVERSIZE": "the set has more than K candidates (never truncated)", "RHAT_OUT": "the best record is not in the set",
                   "DIFFERENT_PLANS": "%d different plans (risk rho = %.2f = share of the set's score mass that leads to another plan than r-hat)" % (a.n_distinct_sigs, a.rho),
                   "SINGLETON_ONLY": "the set is not a single record"}[a.reason]
            print("Distinct plans: %d  ->  NOT certified: %s." % (a.n_distinct_sigs, why))
    dec = rec["decision"]
    d = dec.diag or {}
    if dec.outcome.startswith("TIMEOUT") and a is not None:
        print("  NOTE: the candidates and plans above were computed by this demo outside the time limit (a free what-if). The real decision did not have them.")
    print("\nDecision: %s  (%s)" % (dec.outcome, "ask for verification, the change waits 60 s" if dec.kind == "ESCALATE" else "commit"))
    if dec.outcome == "ACCEPT_INFEASIBLE":
        print("  Unmet requirements under the system's own belief: %s" % d.get("unmet"))
    if "cover" in d:
        cv = d["cover"]
        print("  Cover: %d task(s), %d of them new; complete cover (serves every candidate): %s; partial because of the set size: %s; candidates left unserved: %d" %
              (cv.get("n_tasks", 0), cv.get("n_new", 0), d.get("cover_complete"), d.get("partial_cover"), d.get("cover_unserved_candidates", 0)))
        if d.get("uncovered"):
            print("  The cover itself breaks: %s" % d["uncovered"])
    if dec.outcome.startswith("TIMEOUT"):
        print("  The assessment needed %s allocator runs; at 1.0 s each that is over the 5 s limit, so the best record is committed without assessment." % d.get("needed_runs"))
    ct, cw = cover_trips(res, rid)
    print("Cost of this report: %d allocator run(s) = %.2f s of decision time; %d cover trip(s) flown (%d wasted)." % (row["runs"], row["decision_s"], ct, cw))
    print("\nEVALUATION ONLY (hidden from the system at run time):")
    print("  Gold record: %s.   The best record r-hat is %s;  the plan of r-hat is %s the plan of the gold record." %
          (fmt_record(row["gold_record"]), "RIGHT" if row.get("rhat_table_equal_gold") else "WRONG (as a table)", "the same as" if row.get("rhat_plan_equal_gold") else "DIFFERENT from"))
    if class_of(row["outcome"]) in devrun.FLAGGED:
        print("  The Shield flagged this report (verification or cover). Was it needed? %s" %
              ("NO - false alarm: the plan of the best record was already the gold plan." if row.get("rhat_plan_equal_gold") else
               "YES - true alarm: the plan of the best record was not the gold plan."))
    print("  What happened to the real incident(s) of this report:")
    for aa in [arm] + [x for x in SHOW_ARMS if x != arm]:
        r2 = m["res"][aa]
        incs = incidents_of(r2, rid)
        r2row = report_row(r2, rid)
        text = "; ".join(fmt_inc(i) for i in incs) if incs else "no real incident"
        print("    %-3s %-20s %s" % (aa, "[" + class_of(r2row["outcome"]) + "]", text))


def print_failure(n, total, c, ds, mat, q, K):
    ep, fold, ns, iid = c["found"]
    m = mat[("main", ep)]
    print("=" * 110)
    print("CASE %d of %d: FAILURE CASE    (episode %s, fold %d)" % (n, total, ep, fold))
    print("=" * 110)
    print("Why this case: " + c["note"])
    print("\nThe incident: %s in report %s." % (iid, ns))
    for aa in ("A6", "A8", "A1"):
        incs = [i for i in incidents_of(m["res"][aa], ns) if i[1] == iid]
        print("  %-3s %s" % (aa, fmt_inc(incs[0]) if incs else "-"))
    print("\nThe decisions on this report:")
    for aa in ("A6", "A8"):
        row = report_row(m["res"][aa], ns)
        ct, cw = cover_trips(m["res"][aa], ns)
        print("  %-3s %-22s allocator runs %d, cover trips %d (%d wasted)" % (aa, class_of(row["outcome"]), row["runs"], ct, cw))
    print("\nWhat the whole episode cost under each arm (all %d reports share the fleet):" % len(m["res"]["A8"]["log"]["reports"]))
    for aa in ("A1", "A6", "A8"):
        lg = m["res"][aa]["log"]
        cvt = sum(1 for v in lg["visits"] if v["cover"])
        cvw = sum(1 for v in lg["visits"] if v["cover"] and v["result"] != "verified")
        print("  %-3s missed incidents (late + unverified): %d of %d; verification requests: %d; wasted trips: %d; cover trips: %d (%d wasted); distance %.0f m" %
              (aa, m["res"][aa]["counts"]["late"] + m["res"][aa]["counts"]["unverified"], m["res"][aa]["counts"]["n"], len(lg["requests"]), lg["wasted"], cvt, cvw, lg["dist"]))
    rec = m["store"][("A8", ns)]
    a = rec.get("assessment")
    if a is not None:
        print("\nThe Shield's view of report %s (as in the other cases):" % ns)
        for m_ in a.members:
            print("  %s score %.3f  %-46s -> plan: %s" % ("*" if m_["key"] == a.rkey else " ", m_["score"], fmt_record(m_["norm"]),
                                                          fmt_sig(a.sigs[m_["key"]]) if m_["key"] in a.sigs else "(no plan computed)"))
        print("  Distinct plans: %d; certified: %s" % (a.n_distinct_sigs, a.certified))
    def margin(aa):
        i = [x for x in incidents_of(m["res"][aa], ns) if x[1] == iid][0]
        return None if i[7] is None else i[6] - i[7]
    m6, m8 = margin("A6"), margin("A8")
    print("\nReading: under A6 the incident was reached %s its deadline; under A8 %s. The two arms differ in more than this one decision (they share the fleet "
          "with 19 other reports, and A8 flew %d cover trips in this episode), so the case shows the cost side of the cover; it does not prove that this single "
          "decision was the only cause. The totals in IMPLEMENTATION_EVIDENCE.md show the same cost side over many episodes." %
          ("%.0f s before" % m6 if m6 is not None and m6 >= 0 else "%.0f s after" % -m6 if m6 is not None else "never before",
           "%.0f s before" % m8 if m8 is not None and m8 >= 0 else "%.0f s after" % -m8 if m8 is not None else "never before",
           sum(1 for v in m["res"]["A8"]["log"]["visits"] if v["cover"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="M")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    cases = select(a.level, a.seed)
    if a.only:
        cases = [c for c in cases if c["name"] in a.only]
    print("EdgeSAR Shield demo (development data, saved vectors; level %s, arrival seed %d). Cases are chosen by a fixed rule, not by hand.\n" % (a.level, a.seed))
    if a.list:
        for c in cases:
            print("%-20s %-4s %s" % (c["name"], c["arm"], c["found"]))
        return
    ds = DevSet()
    mat = run_cases(ds, [c for c in cases if c["found"]], a.level, a.seed)
    man = json.loads((paths.RESULTS / "dev" / "main" / "manifest.json").read_text(encoding="utf-8"))
    n = 0
    for c in cases:
        n += 1
        if not c["found"]:
            print("CASE %d: %s - no such case in this run (the class did not occur)\n" % (n, c["name"]))
            continue
        k = c["found"][1]
        q = ds.q_hat(k, "q4", man["args"]["alpha"])
        if c["name"] == "FAILURE_CASE":
            print_failure(n, len(cases), c, ds, mat, q, man["args"]["K"])
        else:
            print_case(n, len(cases), c, ds, mat, q, man["args"]["K"])
        print()


if __name__ == "__main__":
    main()
