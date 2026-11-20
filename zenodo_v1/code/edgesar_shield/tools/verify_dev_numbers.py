"""
Independent check of the headline numbers.

It reads ONLY the raw record files (records_<level>_s<seed>.json.gz). It does not use devrun.arm_table / paired / certificate_check / gate_quality,
so a mistake in the analysis code cannot hide here. It compares what it recomputes with the numbers printed in DEV_<tag>.json (or FRESH_<tag>.json).

    python tools/verify_dev_numbers.py                      (results/dev/main)
    python tools/verify_dev_numbers.py --tag raw
    python tools/verify_dev_numbers.py --base fresh --tag main

Counts and rates must be EQUAL. Bootstrap intervals and sign-flip p-values are recomputed with another random seed and 20,000 draws;
they must agree within bootstrap noise (interval ends 0.12 percentage points, p-values 0.012).
Exit code 0 = every check passed; 1 = at least one check failed (they are listed).
"""
import argparse
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import paths                                          # noqa: E402

CI_TOL_PP = 0.12
P_TOL = 0.012
B = 20000
SEED = 20261113


def load_level(folder, level):
    units = collections.defaultdict(dict)                                 # (seed, episode) -> arm -> record
    n_files = 0
    for f in sorted(folder.glob("records_%s_s*.json.gz" % level)):
        n_files += 1
        for r in json.load(gzip.open(f, "rt")):
            units[(r["seed"], r["episode"])][r["arm"]] = r
    return units, n_files


def is_flagged(outcome):
    return outcome == "ESCALATE" or outcome.startswith("FALLBACK")


class Checker:
    def __init__(self):
        self.bad = []
        self.n = 0

    def eq(self, what, got, want, tol=0.0):
        self.n += 1
        ok = (got == want) if tol == 0.0 else (abs(got - want) <= tol)
        if not ok:
            self.bad.append("%s: recomputed %r, report says %r" % (what, got, want))
        return ok

    def true(self, what, cond):
        self.n += 1
        if not cond:
            self.bad.append(what)
        return cond


def arm_numbers(units, arm):
    inc = late = unv = on_time = ext = reqs = reps = wasted = cov = covw = runs = 0
    dist = hold = 0.0
    for u in units.values():
        r = u[arm]
        cls = collections.Counter(i[8] for i in r["inc"])
        inc += len(r["inc"])
        late += cls["late"]
        unv += cls["unverified"]
        on_time += cls["on_time"]
        ext += cls["resolved_external"]
        c = r["cost"]
        reqs += c["requests"]
        reps += c["reports"]
        wasted += c["wasted"]
        cov += c["cover_visits"]
        covw += c["cover_wasted"]
        runs += c["policy_runs"]
        dist += c["dist"]
        hold += c["hold_s"]
    return {"incidents": inc, "late": late, "unverified": unv, "on_time": on_time, "resolved_external": ext, "requests": reqs, "reports": reps,
            "wasted": wasted, "cover_visits": cov, "cover_wasted": covw, "U": (late + unv) / inc, "request_rate": reqs / reps,
            "wasted_per_report": wasted / reps, "runs_per_report": runs / reps, "dist_per_report": dist / reps, "hold_per_report": hold / reps}


def per_unit(units, arm):
    keys = sorted(units)
    miss = np.array([sum(1 for i in units[k][arm]["inc"] if i[8] in ("late", "unverified")) for k in keys], dtype=float)
    unv = np.array([sum(1 for i in units[k][arm]["inc"] if i[8] == "unverified") for k in keys], dtype=float)
    n = np.array([len(units[k][arm]["inc"]) for k in keys], dtype=float)
    return miss, unv, n


def paired_numbers(units, x, y, rng):
    mx, ux, nx = per_unit(units, x)
    my, uy, ny = per_unit(units, y)
    d = mx - my
    E = len(d)
    diff = d.sum() / nx.sum()
    idx = rng.randint(0, E, size=(B, E))
    boots = d[idx].sum(1) / nx[idx].sum(1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    signs = rng.choice([-1.0, 1.0], size=(B, E))
    perm = (signs * d).mean(1)
    p = (np.sum(np.abs(perm) >= abs(d.mean()) - 1e-12) + 1) / (B + 1)
    return {"diff": diff, "ci": (lo, hi), "p": p, "miss_x": int(mx.sum()), "miss_y": int(my.sum()), "unv_x": int(ux.sum()), "unv_y": int(uy.sum()),
            "wins_x": int((mx < my).sum()), "wins_y": int((mx > my).sum()), "ties": int((mx == my).sum()), "same_incidents": bool(np.array_equal(nx, ny))}


def certificate_numbers(units, arm):
    n = cert = wrong = 0
    sizes = collections.Counter()
    for u in units.values():
        for rep in u[arm]["reports"]:
            n += 1
            if rep["o"] in ("ACCEPT", "ACCEPT_INFEASIBLE"):
                cert += 1
                sizes[str(rep["sz"])] += 1
                wrong += rep["rpg"] is False
    return {"reports": n, "certified": cert, "wrong": wrong, "sizes": dict(sizes)}


def gate_numbers(units, arm):
    n = flagged = flagged_wrong = wrong = 0
    for u in units.values():
        for rep in u[arm]["reports"]:
            n += 1
            w = rep["rpg"] is False
            f = is_flagged(rep["o"])
            wrong += w
            flagged += f
            flagged_wrong += (w and f)
    return {"reports": n, "wrong_plan": wrong, "flagged": flagged, "flagged_wrong": flagged_wrong, "accepted_wrong": wrong - flagged_wrong}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="dev")
    ap.add_argument("--tag", default="main")
    a = ap.parse_args()
    folder = paths.RESULTS / a.base / a.tag
    jf = folder / (("DEV_%s.json" if a.base == "dev" else "FRESH_%s.json") % a.tag)
    if not jf.exists():
        sys.exit("No %s. Run tools/analyze_dev.py first." % jf.name)
    J = json.load(open(jf))
    C = Checker()
    rng = np.random.RandomState(SEED)
    print("Independent check of %s  (raw records only; %d bootstrap and sign-flip draws, seed %d)\n" % (jf.relative_to(paths.RESULTS.parent), B, SEED))
    for level in J["levels"]:
        L = J["levels"][level]
        units, nf = load_level(folder, level)
        print("== Level %s: %d record files, %d (seed, episode) units" % (level, nf, len(units)))
        arms = sorted(next(iter(units.values())).keys())
        # --- 1. invariants on every record
        for k, u in units.items():
            sizes = {len(r["inc"]) for r in u.values()}
            C.true("level %s unit %s: arms disagree on the number of incidents %s" % (level, k, sizes), len(sizes) == 1)
            for r in u.values():
                c = r["counts"]
                cls = collections.Counter(i[8] for i in r["inc"])
                C.true("level %s %s %s: counts do not add up" % (level, k, r["arm"]),
                       c["n"] == len(r["inc"]) == c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"]
                       and all(cls[x] == c[x] for x in ("on_time", "late", "unverified", "resolved_external")))
                C.true("level %s %s %s: 20 reports expected" % (level, k, r["arm"]), len(r["reports"]) == r["cost"]["reports"])
        # --- 2. per-arm numbers
        for arm, rep in L["arms"].items():
            if arm not in arms:
                continue
            m = arm_numbers(units, arm)
            t = "level %s %s " % (level, arm)
            C.eq(t + "incidents", m["incidents"], rep["incidents"])
            C.eq(t + "late", m["late"], rep["late"])
            C.eq(t + "unverified", m["unverified"], rep["unverified"])
            C.eq(t + "on_time", m["on_time"], rep["on_time"])
            C.eq(t + "resolved_external", m["resolved_external"], rep["resolved_external"])
            C.eq(t + "U_deadline", m["U"], rep["U_deadline"], 1e-12)
            C.eq(t + "requests", m["requests"], rep["requests"])
            C.eq(t + "request_rate", m["request_rate"], rep["request_rate"], 1e-12)
            C.eq(t + "wasted trips per report", m["wasted_per_report"], rep["wasted_per_report"], 1e-12)
            C.eq(t + "cover visits", m["cover_visits"], rep["cover_visits"])
            C.eq(t + "cover wasted", m["cover_wasted"], rep["cover_wasted_visits"])
            C.eq(t + "allocator runs per report", m["runs_per_report"], rep["allocator_runs_per_report"], 1e-12)
            C.eq(t + "distance per report", m["dist_per_report"], rep["distance_per_report_m"], 1e-6)
        # --- 3. paired comparisons
        for p in L["paired"]:
            if p["x"] not in arms or p["y"] not in arms:
                continue
            r = paired_numbers(units, p["x"], p["y"], rng)
            t = "level %s %s-%s " % (level, p["x"], p["y"])
            C.true(t + "arms see different incidents", r["same_incidents"])
            C.eq(t + "miss_x", r["miss_x"], p["miss_x"])
            C.eq(t + "miss_y", r["miss_y"], p["miss_y"])
            C.eq(t + "unverified_x", r["unv_x"], p["unverified_x"])
            C.eq(t + "unverified_y", r["unv_y"], p["unverified_y"])
            C.eq(t + "diff_U", r["diff"], p["diff_U"], 1e-12)
            C.eq(t + "episodes won by x", r["wins_x"], p["wins_x"])
            C.eq(t + "episodes won by y", r["wins_y"], p["wins_y"])
            C.eq(t + "tied", r["ties"], p["ties"])
            C.eq(t + "CI low (pp)", 100 * r["ci"][0], 100 * p["ci"][0], CI_TOL_PP)
            C.eq(t + "CI high (pp)", 100 * r["ci"][1], 100 * p["ci"][1], CI_TOL_PP)
            C.eq(t + "sign-flip p", r["p"], p["p_signflip"], P_TOL)
            sig_here, sig_rep = r["p"] < 0.05, p["p_signflip"] < 0.05
            C.true(t + "significance at 0.05 differs (%.4f vs %.4f)" % (r["p"], p["p_signflip"]), sig_here == sig_rep or abs(r["p"] - 0.05) < 0.01)
        # --- 4. certificate (Shield, plan arm)
        if "A8" in arms:
            c = certificate_numbers(units, "A8")
            ce = L["certificate"]
            C.eq("level %s certified reports" % level, c["certified"], ce["certified"])
            C.eq("level %s certified AND wrong plan" % level, c["wrong"], ce["certified_wrong_plan"])
            C.eq("level %s certified set sizes" % level, c["sizes"], {k: v for k, v in ce["certified_set_sizes"].items()})
        # --- 5. which reports does each method flag
        for arm, g in L["gate_quality"].items():
            if arm not in arms:
                continue
            m = gate_numbers(units, arm)
            t = "level %s %s gate " % (level, arm)
            for k in ("reports", "wrong_plan", "flagged", "flagged_wrong", "accepted_wrong"):
                C.eq(t + k, m[k], g[k])
        # --- headline lines for people
        if "A6" in arms and "A8" in arms:
            r = paired_numbers(units, "A8", "A6", rng)
            m6, m8, m1, m0 = (arm_numbers(units, x) for x in ("A6", "A8", "A1", "A0"))
            print("   U_deadline: gold %.2f%%  Q4 commit %.2f%%  confidence gate %.2f%%  Shield (A8) %.2f%%" % (100 * m0["U"], 100 * m1["U"], 100 * m6["U"], 100 * m8["U"]))
            print("   A8 minus A6: %+.2f pp (95%% CI %+.2f to %+.2f), sign-flip p %.4f  [recomputed here]" % (100 * r["diff"], 100 * r["ci"][0], 100 * r["ci"][1], r["p"]))
        if "A8c" in arms and "A6" in arms:
            r = paired_numbers(units, "A8c", "A6", rng)
            print("   A8c minus A6: %+.2f pp (95%% CI %+.2f to %+.2f), sign-flip p %.4f  [recomputed here]" % (100 * r["diff"], 100 * r["ci"][0], 100 * r["ci"][1], r["p"]))
        print()
    print("%d checks run." % C.n)
    if C.bad:
        print("FAILED: %d check(s):" % len(C.bad))
        for b in C.bad[:60]:
            print("  - " + b)
        sys.exit(1)
    print("ALL CHECKS PASSED: every count, rate and difference equals the report; intervals and p-values agree within bootstrap noise.")


if __name__ == "__main__":
    main()
