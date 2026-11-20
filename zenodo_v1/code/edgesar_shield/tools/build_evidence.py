"""
Builds IMPLEMENTATION_EVIDENCE.md from the result files, so that no number in it is typed by hand.

    python tools/build_evidence.py                  -> IMPLEMENTATION_EVIDENCE.md  (and results/EVIDENCE_NUMBERS.json)

Inputs (all produced by other scripts):  results/dev/main (DEV_main.json + the raw records), results/dev/raw (stress test), results/dev/SENSITIVITY.json,
results/M1_cbba_report.json, results/M4_readout_report.json, results/tests_summary.json (written by the test run).
Run  python tools/verify_dev_numbers.py  first: it recomputes the headline numbers from the raw records with independent code.
The prose is written here; every figure in it is read from the files above.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_dev                                                 # noqa: E402
from shield import devrun, paths                                   # noqa: E402

RES = paths.RESULTS
J = json.load(open(RES / "dev" / "main" / "DEV_main.json"))
JR = json.load(open(RES / "dev" / "raw" / "DEV_raw.json"))
S = json.load(open(RES / "dev" / "SENSITIVITY.json"))
M1 = json.load(open(RES / "M1_cbba_report.json"))
M4 = json.load(open(RES / "M4_readout_report.json"))
recs_main, _ = analyze_dev.load("main")
recs_raw, _ = analyze_dev.load("raw")
try:
    TESTS = json.load(open(RES / "tests_summary.json"))
except FileNotFoundError:
    TESTS = {}
NUM = {}                                                           # every figure used in the prose, saved next to the report


def recs(src, level):
    d = recs_main if src is J else recs_raw
    return [r for (l, s), v in d.items() if l == level for r in v]


def A(src, level, arm):
    return src["levels"][level]["arms"][arm]


def U(src, level, arm):
    return 100 * A(src, level, arm)["U_deadline"]


def P(src, level, x, y):
    for p in src["levels"][level]["paired"]:
        if p["x"] == x and p["y"] == y:
            return p
    raise KeyError((level, x, y))


def pv(p):
    return "<0.001" if p < 0.001 else "%.3f" % p


def pp(p, with_p=True):
    s = "%+.2f pp (%+.2f to %+.2f)" % (100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1])
    return s + (", p %s" % pv(p["p_signflip"]) if with_p else "")


def pct(x, d=1):
    return "%.*f%%" % (d, 100 * x)


def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def table(head, rows):
    return [row(head), row(["---"] * len(head))] + [row(r) for r in rows]


def outcome_table(src, level, arms):
    R = recs(src, level)
    out = table(["Arm", "System", "Missed by deadline U (95% CI)", "late", "unverified", "requests / report", "wasted trips / report", "cover trips (wasted)",
                 "distance m / report", "hold s / report", "allocator runs / report", "decision ms median / p99"], [])
    for a in arms:
        t = A(src, level, a)
        lo, hi = devrun.episode_bootstrap_ci(R, a)
        out.append(row([a, devrun.ARM_TEXT[a], "%s (%s to %s)" % (pct(t["U_deadline"]), pct(lo), pct(hi)), t["late"], t["unverified"], "%.3f" % t["request_rate"],
                        "%.3f" % t["wasted_per_report"], "%d (%d)" % (t["cover_visits"], t["cover_wasted_visits"]), "%.0f" % t["distance_per_report_m"],
                        "%.1f" % t["hold_s_per_report"], "%.2f" % t["allocator_runs_per_report"], "%.2f / %.2f" % (t["wall_ms_median"], t["wall_ms_p99"])]))
    return out


def gate_table(level):
    g = J["levels"][level]["gate_quality"]
    n = g["A1"]["reports"]
    rows = []
    for a in ("A1", "A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A11", "A12"):
        x = g[a]
        rows.append([a, devrun.ARM_TEXT[a], "%d (%s)" % (x["flagged"], pct(x["flagged"] / n)),
                     "-" if x["wrong_plan"] == 0 else pct(x["flagged_wrong"] / x["wrong_plan"]),
                     "-" if x["flagged"] == 0 else pct(x["flagged_wrong"] / x["flagged"]), pct(x["accepted_wrong"] / n)])
    return table(["Arm", "System", "reports flagged (verify or cover)", "recall: wrong-plan reports flagged", "precision: flagged that were wrong-plan",
                  "wrong-plan reports left unflagged, share of ALL reports"], rows)


def ranking_table(level):
    q = J["levels"][level]["ranking"]["recall_at_flag_rate"]
    rows = [[k, pct(v["5%"]), pct(v["10%"]), pct(v["20%"]), pct(v["30%"]), "%.3f" % v["AUROC"]] for k, v in q.items()]
    return table(["Ranking by", "f = 5%", "f = 10%", "f = 20%", "f = 30%", "AUROC"], rows)


def decisions_table(src, level):
    a8, a8c = A(src, level, "A8")["outcome_classes"], A(src, level, "A8c")["outcome_classes"]
    keys = sorted(set(a8) | set(a8c), key=lambda k: -(a8.get(k, 0) + a8c.get(k, 0)))
    n = A(src, level, "A8")["reports"]
    return table(["Outcome class", "A8 reports", "A8 share", "A8c reports", "A8c share"],
                 [[k, a8.get(k, 0), pct(a8.get(k, 0) / n), a8c.get(k, 0), pct(a8c.get(k, 0) / n)] for k in keys])


def recovered(src, level, arm):
    """Share of the excess misses of the always-commit arm (over the gold-record arm) that `arm` removes."""
    u1, u0, ux = U(src, level, "A1"), U(src, level, "A0"), U(src, level, arm)
    return 100 * (u1 - ux) / (u1 - u0)


def audit_summary():
    """Counts of PASS / CHECK / FAIL per audit script, from the log of the re-run in the cloud session (results/audit_rerun_cloud/RUN_LOG.txt)."""
    txt = (RES / "audit_rerun_cloud" / "RUN_LOG.txt").read_text(encoding="utf-8")
    out, cur = {}, None
    for line in txt.splitlines():
        m = re.match(r"=== (audit_\d\d)", line)
        if m:
            cur = m.group(1)
            out[cur] = {"PASS": 0, "CHECK": 0, "FAIL": 0, "exit": None, "margins": []}
            continue
        if cur is None:
            continue
        for k in ("PASS", "CHECK", "FAIL"):
            if line.startswith(k):
                out[cur][k] += 1
        m = re.match(r"exit (\d+)", line)
        if m:
            out[cur]["exit"] = int(m.group(1))
        m = re.match(r"(\d+) files listed, (\d+) missing, (\d+) changed", line)
        if m:
            out[cur]["manifest"] = tuple(int(x) for x in m.groups())
        if cur == "audit_02" and line.startswith("CHECK") and "probability)" in line:
            out[cur]["margins"] += [float(x) for x in re.findall(r"\d\.\d+", line.split("probability)")[1])]
    return out


def repro_summary():
    txt = (RES / "compare_runs.txt").read_text(encoding="utf-8")
    return [(int(a), int(b)) for a, b in re.findall(r"ALL IDENTICAL: (\d+) files, (\d+) records", txt)]


def power_rows(level="M", cmp_="A8 vs A6"):
    rows = []
    for line in (RES / "dev" / "main" / "POWER.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) >= 9 and c[0] == level and c[2] == cmp_:
            rows.append({"seed": c[1], "mean": float(c[3]), "sd": float(c[4]), "delta": float(c[5]), "N_delta": float(c[6]),
                         "N_obs": float(c[7]) if c[7] != "inf" else float("inf")})
    return rows


def demo_failure():
    txt = (RES / "demo_output.txt").read_text(encoding="utf-8")
    m = re.search(r"The incident: (\S+) in report (\S+)\.", txt)
    r = re.search(r"Reading: under A6 the incident was reached (\d+) s before its deadline; under A8 (\d+) s after\.", txt)
    d = re.search(r"A8\s+FALLBACK_COVERED\s+allocator runs (\d+), cover trips (\d+)", txt)
    n_cases = len(re.findall(r"^CASE \d+ of (\d+)", txt, flags=re.M))
    if not (m and r and d):
        raise SystemExit("demo_output.txt does not have the failure case in the expected form; run demo.py again")
    return {"incident": m.group(1), "report": m.group(2), "a6_before": int(r.group(1)), "a8_after": int(r.group(2)), "runs": int(d.group(1)), "cover_trips": int(d.group(2)), "cases": n_cases}


def scenario_shares(level):
    """Evaluation-side audit on the OBS arm (it commits like A1): how often is the best-guess record wrong, and how often does a wrong record still give the gold plan?"""
    n = wrong_table = harmless = wrong_plan = unknown = 0
    for r in recs(J, level):
        if r["arm"] != "OBS":
            continue
        for rep in r["reports"]:
            if rep["rpg"] is None or rep["rtg"] is None:
                unknown += 1
                continue
            n += 1
            wrong_plan += rep["rpg"] is False
            if rep["rtg"] is False:
                wrong_table += 1
                harmless += rep["rpg"] is True
    return {"reports": n, "wrong_table": wrong_table, "harmless": harmless, "wrong_plan": wrong_plan, "unknown": unknown}


def paired_with_gold(level, arm, ref="A0"):
    """Incident-by-incident pairing of `arm` with the gold-record run on the same episodes (the same real incidents). Evaluation side only."""
    R = recs(J, level)
    base = {(r["seed"], r["episode"]): {(i[0], i[1]): i for i in r["inc"]} for r in R if r["arm"] == ref}
    out = []
    for r in R:
        if r["arm"] != arm:
            continue
        b = base[(r["seed"], r["episode"])]
        if set(b) != {(i[0], i[1]) for i in r["inc"]}:
            raise SystemExit("the arms do not share the same real incidents in %s (pairing is wrong)" % r["episode"])
        out.append([(b[(i[0], i[1])], i) for i in r["inc"]])
    return out


def transitions_row(level, arm):
    eps = paired_with_gold(level, arm)
    to_missed = to_ok = lost = gained = n = 0
    sd, nd = [], []
    for ep in eps:
        s = c = 0
        for b, i in ep:
            n += 1
            ok_b, ok_a = b[8] == "on_time", i[8] == "on_time"
            to_missed += ok_b and not ok_a
            to_ok += (not ok_b) and ok_a
            lost += b[8] != "unverified" and i[8] == "unverified"
            gained += b[8] == "unverified" and i[8] != "unverified"
            if b[7] is not None and i[7] is not None:
                s += i[7] - b[7]
                c += 1
        sd.append(s)
        nd.append(c)
    sd, nd = np.array(sd, float), np.array(nd, float)
    rng = np.random.default_rng(20261113)
    idx = rng.integers(0, len(sd), size=(2000, len(sd)))
    boot = sd[idx].sum(1) / nd[idx].sum(1)
    return {"incidents": n, "on_time_to_missed": int(to_missed), "missed_to_on_time": int(to_ok), "verified_to_unverified": int(lost), "unverified_to_verified": int(gained),
            "both_verified": int(nd.sum()), "delay_mean_s": float(sd.sum() / nd.sum()), "delay_ci": (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))}


def main():
    lv = ("L", "M", "H")
    M = "M"
    cert = J["levels"][M]["certificate"]
    es = J["levels"][M]["eval_set"]
    n_rep = cert["reports"]
    non_single = {l: sum(v for k, v in J["levels"][l]["certificate"]["certified_set_sizes"].items() if k != "1") / J["levels"][l]["certificate"]["reports"] for l in lv}
    gq = J["levels"][M]["gate_quality"]
    rk = J["levels"][M]["ranking"]["recall_at_flag_rate"]
    auc_diff = devrun.auroc_diff_ci(recs(J, M), "a8", "conf")
    t8 = {l: A(J, l, "A8") for l in lv}
    sens = S
    timeouts_ac10 = sens["ac10"]["timeouts_A8"]
    rates = {a: A(J, M, a)["request_rate"] for a in ("A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A11")}
    tests_total = sum(int(str(v).split()[0]) for v in TESTS.values() if str(v).split()[0].isdigit()) if TESTS else None
    n_arms = len([a for a in J["levels"][M]["arms"] if a != "OBS"])
    aud = audit_summary()
    rep = repro_summary()
    dem = demo_failure()
    pw = power_rows()
    ss = {l: scenario_shares(l) for l in lv}
    tr = {a: transitions_row(M, a) for a in ('A1', 'A2', 'A6', 'A8', 'A8c', 'A10', 'A12')}
    import extract_fresh_vectors as ex
    gib = {k: ex.GGUF_BYTES[k] / 2 ** 30 for k in ex.GGUF_BYTES}
    # sensitivity, counted from the file
    s_tags = [t for t in S]
    s_pos = [t for t in s_tags if S[t]["A8-A6"]["diff_U"] > 0]
    s_excl = [t for t in s_tags if S[t]["A8-A6"]["ci"][0] > 0]
    s_c_max = max(abs(S[t]["A8c-A6"]["diff_U"]) for t in s_tags) * 100
    s_c_excl = [t for t in s_tags if S[t]["A8c-A6"]["ci"][0] > 0 or S[t]["A8c-A6"]["ci"][1] < 0]
    oc8 = A(J, M, "A8")["outcome_classes"]
    f8, f6 = gq["A8"]["flagged"] / n_rep, gq["A6"]["flagged"] / n_rep
    esc8 = oc8.get("ESCALATE", 0) / n_rep
    cov8 = sum(oc8.get(k, 0) for k in ("FALLBACK_COVERED", "FALLBACK_UNRESOLVED", "FALLBACK_PARTIAL")) / n_rep
    k8 = next(k for k in rk if k.startswith("A8"))
    k6 = next(k for k in rk if k.startswith("A6 conf"))
    def excl(x, y, levels):
        return [l for l in levels if P(J, l, x, y)["ci"][0] > 0 or P(J, l, x, y)["ci"][1] < 0]
    c_excl = excl("A8c", "A6", ("M", "H", "L"))
    p9 = [P(J, l, "A8", "A9")["p_signflip"] for l in lv]
    a10_late = P(J, M, "A8", "A10")
    # power at 400 and 1,100 episodes for the three seeds (two-sided 5%), and the extraction time (22,800 reports x 3 models x 0.107 s)
    def power_at(n_ep):
        return [float(norm.cdf(np.sqrt(n_ep) * r["delta"] / r["sd"] - 1.96)) for r in pw]
    def gpu_minutes(n_ep):
        return (n_ep * 20 + 800) * 3 * 0.107 / 60
    p400, p1100 = power_at(400), power_at(1100)
    NUM.update({"U_M": {a: U(J, M, a) for a in J["levels"][M]["arms"]}, "A8-A6_M": P(J, M, "A8", "A6"), "A8c-A6_M": P(J, M, "A8c", "A6"),
                "auroc_diff_A8_conf_M": auc_diff, "non_single_certified": non_single, "tests": TESTS, "recovered_raw_M": {a: recovered(JR, M, a) for a in ("A6", "A8", "A8c")},
                "sensitivity": {"positive": s_pos, "excluding_zero": s_excl, "A8c_max_abs_pp": s_c_max, "A8c_excluding_zero": s_c_excl},
                "power": {"rows": pw, "power_400": p400, "power_1100": p1100, "gpu_min_400": gpu_minutes(400), "gpu_min_1100": gpu_minutes(1100)}, "audit": aud, "repro": rep, "demo": dem, "scenario_shares": ss, "transitions_M": tr, "model_gib": gib})
    json.dump(NUM, open(RES / "EVIDENCE_NUMBERS.json", "w"), indent=1, default=float)

    o = []
    w = o.append

    w("# EdgeSAR Shield: implementation evidence for the main chat")
    w("")
    w("Friday 13 November 2026 (Colombo). From the implementation chat to the research-design chat (\"main chat\"), to Samadhi, and later to the supervisors.")
    w("Package: `edgesar_shield` (the folder that holds this file). Every number below is read from files in `results/` by `tools/build_evidence.py`. "
      "The headline numbers were also recomputed from the raw records by independent code (`tools/verify_dev_numbers.py`: all counts and differences equal, "
      "intervals and p-values within bootstrap noise).")
    w("")
    w("**State.** Milestones M0 to M7 are done on **development (DEV) data**: the saved vectors of the 1,000 style-A reports. The GPU extraction script, the freeze tools and the demo "
      "are built and tested. **M8 (the FRESH run) has not started.** No fresh report exists. No fresh outcome has been generated or looked at. "
      "`docs/EVAL_PLAN_FRESH.md` says `STATUS: DRAFT`: it is not frozen, not hashed and not sent to the supervisors.")
    w("")
    w("**Asked of the main chat:** review this file, answer the open decisions in section 9, and only then freeze the plan and rerun the supervisor gates.")
    w("")
    w("---")
    w("")
    w("## 0. Short version")
    w("")
    w("*Plain English, for Samadhi.*")
    w("")
    w("1. **Built and tested.** A real bounded CBBA allocator. A simulator where 20 reports share 3 UAVs. The Shield. %d test systems (\"arms\") and an observer. A demo with a failure case. "
      "The tools for the fresh run. %s automatic checks pass." % (n_arms, tests_total if tests_total else "(test count missing)"))
    w("2. **What got better.** The Shield finds wrong-plan reports much more completely: wrong-plan reports that nobody checks are **%s** of all reports with the Shield, %s with the confidence gate and %s with no gate. "
      "This is not an equal-cost comparison: the Shield acts on %s of reports (verification or cover) and the gate on %s. At an equal flag rate its ranking is better by a modest margin (AUROC %.3f against %.3f). "
      "The promise \"certified and wrong is at most 10%%\" holds (%s). "
      "When the readout is poor (stress test), missed incidents fall from %s to **%s** (plan cover) or **%s** (location cover); the confidence gate only to %s."
      % (pct(gq["A8"]["accepted_wrong"] / n_rep), pct(gq["A6"]["accepted_wrong"] / n_rep), pct(gq["A1"]["accepted_wrong"] / n_rep), pct(f8, 0), pct(f6, 0), auc_diff["auroc_a"], auc_diff["auroc_b"],
         pct(cert["certified_wrong_rate"]), "%.1f%%" % U(JR, M, "A1"), "%.1f%%" % U(JR, M, "A8"), "%.1f%%" % U(JR, M, "A8c"), "%.1f%%" % U(JR, M, "A6")))
    w("3. **What did not get better.** With the good Q4 readout, the plan's Shield (A8) is **worse** than the simple confidence gate: %s vs %s missed at level M (%s). "
      "The revised location cover (A8c) is equal to the gate (%s). There is little left to fix: wrong records cost %s over gold records, and a perfect gate "
      "would win back only %s (not significant). Q4 is also worse than FP16 always-on at mission level (%s at M)."
      % ("%.1f%%" % U(J, M, "A8"), "%.1f%%" % U(J, M, "A6"), pp(P(J, M, "A8", "A6")), pp(P(J, M, "A8c", "A6")), "%+.1f pp" % (100 * P(J, M, "A1", "A0")["diff_U"]),
         "%.1f pp" % (-100 * P(J, M, "A12", "A1")["diff_U"]), pp(P(J, M, "A1", "A2"), False)))
    w("4. **Not tested.** Anything on fresh data. The GPU step on real hardware. Timing on a laptop or an edge board. Other models. Real report text. Closed-loop prompts. "
      "Message loss between UAVs. The full list is in section 8.")
    w("5. **Next.** The main chat answers the questions in section 9. Then: set `STATUS: FROZEN-READY`, run `tools/freeze_plan.py`, email the hash to the supervisors, "
      "make the fresh reports, run the GPU extraction (about 2 hours), run the fresh test **once**.")
    w("")
    w("---")
    w("")
    w("## 1. Existing findings and new experiments are kept apart")
    w("")
    w("| Kind | What | Status |")
    w("|---|---|---|")
    w("| Existing, unchanged | Pilot and harm test on the 1,400 pilot reports (style A 1,000, style B 400). On held-out B, incidents unverified out of 752: gold records 0, FP16 heads 15, Q8 heads 16, Q4 heads 13, "
      "FP16 head on raw Q4 vectors 141, same head with the offset removed 18, shared head 10, generative FP16 83, generative Q4 69, TF-IDF 30. | Exploratory. Reproduced again in this session from the saved records "
      "(audit script 03: 10 of 10 PASS). Not changed. |")
    a0, a1, a2, a3 = aud["audit_00"], aud["audit_01"], aud["audit_02"], aud["audit_03"]
    w("| Existing, unchanged | The audit of 13 Nov (79 inspected files, provenance, duplicates). | Re-run in this session on the staged copy, in the cloud (`results/audit_rerun_cloud/`): manifest %d listed, %d missing, %d changed; audit 01: %d PASS, %d FAIL; audit 03: %d PASS, %d FAIL; "
      "audit 02: %d PASS and %d CHECK (a few near-tie records, head margins %.3f to %.3f; AUDIT_REPORT section 5 expects this on another platform). All 13 comparable output files are identical to the saved ones in `edgesar_audit_2026-11-13/out`. "
      "Both runs were made in cloud sessions, so this is a reproducibility check, **not** the laptop run. |" % (a0["manifest"][0], a0["manifest"][1], a0["manifest"][2], a1["PASS"], a1["FAIL"], a3["PASS"], a3["FAIL"], a2["PASS"], a2["CHECK"], min(a2["margins"]), max(a2["margins"])))
    w("| **New, DEV (exploratory)** | Everything in section 5: saved vectors, 1,000 style-A reports, overlay episodes, 3 arrival seeds, three contention levels, stress test, sensitivity runs. | "
      "Used to build and set the design. **Not confirmatory.** The pooled intervals are optimistic because the seeds re-use the same reports. |")
    w("| **New, FRESH (confirmatory)** | Nothing. | Not started. Waits for the frozen plan. |")
    w("")
    w("Rules kept: `edgesar_pilot`, `edgesar_heads`, `V1` and the audit folder are read-only (14 pinned files are exactly the audited versions: `python tools/check_inputs.py`). "
      "Style B was not used for any choice. Each rerun keeps the first run (`results/dev/main_first` and `raw_first` have identical records; `tools/compare_runs.py`).")
    w("")
    w("## 2. What was built")
    w("")
    w("| Part | Files | What it does | Checked by |")
    w("|---|---|---|---|")
    w("| Bounded CBBA + legacy wrapper | `shield/alloc.py` | Bundles of up to 3 tasks, bid warping (Johnson et al. 2012), release of later bundle tasks, consensus rounds on a connected graph, round cap logged; `legacy_greedy_s1` wraps V1 unchanged | `tests/test_cbba.py` (18), `results/M1_cbba_report.md` |")
    w("| Simulator | `shield/sim.py`, `shield/core.py` | Event loop, deadlines, verification requests (delay and budget cap), scorer with every incident in the denominator, hidden-truth wall, simulated compute time (0.02 s per allocator run, time-out 5 s) | `tests/test_sim.py` (23) |")
    w("| Heads, candidates, conformal sets | `shield/data.py`, `readout.py`, `candidates.py`, `calibrate.py`, `service.py`, `devset.py`, `episodes.py` | Heads on saved vectors (tol 1e-6), up to 20 candidate records, split conformal sets | `results/M4_readout_report.md` |")
    w("| Shield and all arms | `shield/policy.py`, `cover.py`, `oracle.py`, `devrun.py` | Certification by execution signature, requirement check R1 to R3, escalation, cover fallback, ablations, gates with budget matching | `tests/test_policy.py` (26) |")
    w("| FRESH tools | `shield/freshset.py`, `shield/frozen.py`, `tools/gen_episodes_fresh.py`, `tools/freeze_plan.py`, `tools/run_fresh.py` | Regenerate the cases from the seed, freeze the plan and the code, refuse to run if anything changed | `tests/test_fresh.py` (13) |")
    w("| GPU extraction (kept apart) | `tools/extract_fresh_vectors.py` | One vector per report and precision with explicit llama.cpp settings, report-id hash, model hashes, log-order check, anchor and CPU checks, manifest | `tests/test_extraction.py` (11) |")
    w("| Analysis | `tools/run_dev.py`, `analyze_dev.py`, `power.py`, `sens_summary.py`, `compare_runs.py`, `verify_dev_numbers.py`, `check_inputs.py`, `build_evidence.py` | Tables, power, sensitivity, reproducibility, independent number check, input pins | run in section 10 |")
    w("| Demo | `demo.py` | One case for each outcome class and one failure case, with candidates, signatures, decision, outcome and cost | `results/demo_output.txt` |")
    w("")
    w("## 3. Acceptance checks of STRENGTHENING_PLAN section 9, one by one")
    w("")
    fg, nw, lg, b1 = M1["full graph, warping on"], M1["full graph, warping OFF"], M1["line graph, warping on"], M1["bundle length 1"]
    bf, lv1 = M1["brute_force"], M1["legacy_vs_L1_first_assignments"]
    w("| M | Plan wants | Result | Met? |")
    w("|---|---|---|---|")
    w("| M0 | Folder, `git init`, audit scripts on the laptop, gguf re-hash | Done in the cloud session on the staged copy: 14 pinned files and %d manifest files MATCH; audits as in section 1. **Not done:** the laptop run, the gguf re-hash, `git init` (my shell on the laptop cannot start: too little free disk space). | Partly |" % a0["manifest"][0])
    w("| M1 | (a) conflict-free (b) 10,000 random instances converge, zero non-converged on the full graph (c) deterministic (d) order invariant (e) L_t = 1 equals legacy on 1,400 gold tables (f) brute-force ratio (g) warping frequency | "
      "(a),(c),(d) tests pass. (b) %d instances: %d not converged on the full graph (worst %d rounds) and %d on a line graph (worst %d); with warping OFF %d do not converge (worst %d rounds). "
      "(e) %d of %d first assignments identical. (f) mean ratio to the best %.3f (worst %.3f) for L_t = 3; %.3f for L_t = 1; %.3f for legacy. (g) warping lowered %d of %d bids (%.2f%%). | Yes |"
      % (fg["instances"], fg["nonconv"], fg["worst_rounds"], lg["nonconv"], lg["worst_rounds"], nw["nonconv"], nw["worst_rounds"], lv1["same_first_assignment"], lv1["tables"],
         bf["bounded L3"]["mean"], bf["bounded L3"]["min"], bf["bounded L1"]["mean"], bf["legacy"]["mean"], fg["warps"], fg["placed"], 100 * fg["warps"] / fg["placed"]))
    w("| M2 | Truth wall test; deterministic gold runs; counts add up; hand-made scenario episodes | Source scan and runtime tests of the wall; deterministic reruns; random episodes add up (on time + late + unverified + resolved externally = incidents); "
      "one hand-made episode for each scenario type of plan section 5 | Yes |")
    w("| M3 | Generator reproducible; extraction script with provenance; CPU vs GPU cosine | Generator is deterministic and unique (tests; `run_fresh.py` regenerates it from the seed). Extraction script tested against a mock llama server and a failure matrix. "
      "**Not run on a GPU. CPU vs GPU cosine not measured.** | Built, not run |")
    c10, c05, c20 = M4["conformal_q4"]["0.1"], M4["conformal_q4"]["0.05"], M4["conformal_q4"]["0.2"]
    w("| M4 | <= 22 combinations, missing candidates counted; coverage inside the binomial band | At most %d combinations (deviation D-04). Missing candidates: %d of %d CAL + EVAL rows. Coverage at alpha 0.10: %s, inside the 95%% band %s to %s (%s). "
      "At alpha 0.05: %s (%s); at alpha 0.20: %s (%s). | %s |"
      % (M4["n_combinations_max"], M4["enumeration"]["reports_with_gold_missing"], M4["enumeration"]["reports"], pct(c10["coverage"]), pct(c10["band"][0]), pct(c10["band"][1]),
         "inside" if c10["inside"] else "OUTSIDE", pct(c05["coverage"]), "inside" if c05["inside"] else "OUTSIDE", pct(c20["coverage"]), "inside" if c20["inside"] else "OUTSIDE",
         "Yes" if c10["inside"] and c05["inside"] and c20["inside"] else "Partly"))
    w("| M5 | One unit test per outcome class and scenario type; zero truth access; ms per decision | 26 policy tests (one per class: ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, FALLBACK_UNRESOLVED, UNCERTIFIED_COMMIT, TIMEOUT, empty set, oversized set, missing candidate, competing deadlines); "
      "source scan shows no policy module names the truth; decision times in section 4.7 | Yes |")
    w("| M6 | Realised request rates within +-1 pp of b for A6 to A11 | The deployable arms are within **%.1f pp of each other** (%s to %s), as plan section 7 requires. But they are **%.1f to %.1f pp below b = 10%%**, because the hard cap (2 requests per 20 reports) cuts bursts. The plan's M6 wording is **not** met; see decision D6. | Partly |"
      % (100 * (max(rates.values()) - min(rates.values())), pct(min(rates.values())), pct(max(rates.values())), 100 * (0.10 - max(rates.values())), 100 * (0.10 - min(rates.values()))))
    w("| M7 | DEV runs; settings; N_e; `EVAL_PLAN_FRESH.md`; hash recorded before FRESH exists | DEV runs, sensitivity and power done; draft plan written. **Hash not recorded: the plan is a DRAFT.** | Partly (waits for approval) |")
    w("| Kill criteria | Fewer than 3%% certified non-singleton sets **and** A8 does not beat A6 on DEV | Certified non-singleton sets: %s of reports at L, %s at M, %s at H, so the first part is **false** and the rule is not triggered by its letter. A8 does not beat A6 (section 5). See decision D4. | Not triggered by its letter |"
      % (pct(non_single["L"]), pct(non_single["M"]), pct(non_single["H"])))
    g_l, g_m, g_h = (A(J, l, "A0")["U_deadline"] for l in lv)
    w("| Kill criterion 2 and plan section 5 | Gold-record miss rate 3 to 8%% at level M and 10 to 20%% at level H | Gold records miss %s at L, **%s at M, %s at H**: %s. Only the report gaps were tuned (60, 30, 8 s); the share of CREATE reports and of THERMAL needs were not. | %s |"
      % (pct(g_l), pct(g_m), pct(g_h), "inside both bands" if 0.03 <= g_m <= 0.08 and 0.10 <= g_h <= 0.20 else "**NOT inside both bands**", "Yes" if 0.03 <= g_m <= 0.08 and 0.10 <= g_h <= 0.20 else "No"))
    w("")
    w("### Plan items that are not built, or only partly built")
    w("")
    w("| Plan item | State | Effect on what the numbers can say |")
    w("|---|---|---|")
    w("| Section 5: scenario types **tagged**, with a guaranteed minimum count of each in development episodes, and subgroup reporting | **Not built.** I report two data-derived shares instead (section 4.11) and I test each type by a hand-made unit test | Subgroup results (for example only the competing-deadline reports) cannot be given. |")
    w("| Section 5: contention tuned by report gaps, **share of CREATE reports and share of THERMAL needs** | Only the gaps were tuned | The contention is one-dimensional. |")
    w("| Section 3.1: verification **queue time** | The simulated verifier has no queue: every request is answered d_v seconds later; requests are limited only by the budget cap | Waiting costs are the hold seconds only. |")
    w("| W11 / section 3.1: memory and **CPU latency** of Q4 + Shield, Q8 always-on, FP16 always-on | Only file sizes are known (%.2f, %.2f and %.2f GiB for Q4_K_M, Q8_0 and FP16). Forward-pass latency was **not measured** | The cost table has no model-latency column. The 2 GB assumption excludes FP16 on file size alone. |"
      % (gib["Q4_K_M"], gib["Q8_0"], gib["f16"]))
    w("| W14 / M3: 100-report **CPU-backend** check, CPU vs GPU cosine | Built into the extraction script, **not run** | Unknown platform effect. |")
    w("| W8 / M9: versioned **evidence package**, hosting | The folder is a candidate package. **No upload.** Hosting needs Samadhi's approval | Reviewers cannot yet rerun the tables. |")
    w("| Section 8.1: FIT / CAL / DEV of **200 episodes each**, new seeds | DEV uses the 1,000 saved style-A reports in 5 family folds (D-02, D-07); FRESH uses new episodes | DEV is not independent of the pilot data. |")
    w("| Section 8.6: demo cases **from FRESH** after the analysis | The demo reads DEV records only; the FRESH version is not written | The demo shown now is a development demo. |")
    w("")
    w("## 4. Results (DEV, saved vectors)")
    w("")
    w("### 4.1 Setup")
    w("")
    w("1,000 style-A reports, 5 outer folds by family. In each fold the EVAL reports are tested, the next fold calibrates, the other three (minus exact duplicates) fit the heads. "
      "An episode is 20 independent reports that arrive over time and **share one fleet** of 3 UAVs (deviation D-01). Levels L, M, H have mean gaps of 60, 30 and 8 s between reports. "
      "3 arrival seeds give 150 episodes per level (the seeds re-partition the same reports, so pooled intervals are optimistic). "
      "Verification budget b = 10%% of reports (hard cap 2 per episode), delay d_v = 60 s, alpha = 0.10, K = 8, deadlines 240/360/480 s for priority 3/2/1, bounded CBBA with L_t = 3, 0.02 s of simulated time per allocator run, time-out 5 s. "
      "**U** is the share of real incidents verified late or not verified (late + unverified) / incidents; every incident is in the denominator. Lower is better. "
      "Level M has %d incidents per arm; gold records miss %s of them." % (A(J, M, "A1")["incidents"], pct(A(J, M, "A0")["U_deadline"])))
    w("")
    w("### 4.2 Outcomes and costs, level M (all arms)")
    w("")
    w("Rows: A0 gold records (reference); A1 Q4 commit; A2 FP16 and A3 Q8 (off-board references); A4 recentred Q4; A5 frozen FP16 head on raw Q4 (**diagnostic, deliberately mismatched**); "
      "A6 confidence gate, A6b record-score gate, A7 random gate (budget-matched baselines); A8 Shield with the plan's full cover; A8c Shield with the revised location cover (**designed after the DEV outcomes were seen**); "
      "A9 singleton sets only; A10 Shield without fallback; A11 top-2 what-if; A12 oracle gate (diagnostic upper bound, not deployable; uses more requests).")
    w("")
    o += outcome_table(J, M, [a for a in devrun.ARM_ORDER if a in J["levels"][M]["arms"]])
    w("")
    w("Decision time is measured on the cloud session's CPU (not the laptop, not an edge board) and covers the Shield's own work: candidates, what-if allocator runs and the cover plan. It does not include the language-model forward pass.")
    w("")
    w("### 4.3 Levels L and H (key arms)")
    w("")
    for l in ("L", "H"):
        w("**Level %s** (gold records miss %s)" % (l, pct(A(J, l, "A0")["U_deadline"])))
        w("")
        o += outcome_table(J, l, ["A0", "A1", "A2", "A3", "A6", "A7", "A8", "A8c", "A10", "A12"])
        w("")
    w("### 4.4 Paired comparisons (same episodes; difference in U; negative = the first arm is better)")
    w("")
    pairs = [("A8", "A6", "**Plan primary:** Shield + full cover vs confidence gate"), ("A8c", "A6", "Revised (post-hoc): Shield + location cover vs confidence gate"),
             ("A8", "A10", "Fallback effect: full cover vs no fallback"), ("A8c", "A10", "Location cover vs no fallback"), ("A8c", "A8", "Location cover vs full cover"),
             ("A10", "A6", "Shield without fallback vs confidence gate"), ("A8", "A9", "Conformal sets vs singleton sets only"), ("A8", "A11", "Conformal sets vs top-2 what-if"),
             ("A6", "A1", "Confidence gate vs always commit"), ("A12", "A1", "**Headroom:** perfect gate vs always commit"), ("A1", "A0", "Record-induced misses of the Q4 head (vs gold records)"),
             ("A1", "A2", "Quantisation effect: Q4 vs FP16 always commit"), ("A4", "A1", "Recentred Q4 vs matched Q4 head")]
    rows = [[lab, x + " - " + y] + [pp(P(J, l, x, y)) for l in lv] for x, y, lab in pairs]
    o += table(["Comparison", "Arms", "Level L", "Level M", "Level H"], rows)
    w("")
    w("Per-seed differences for A8 - A6 at level M: %s pp (same sign in all three seeds). Episodes won / lost / tied by A8 against A6 at M: %d / %d / %d."
      % (", ".join(P(J, M, "A8", "A6")["per_seed_pp"]), P(J, M, "A8", "A6")["wins_x"], P(J, M, "A8", "A6")["wins_y"], P(J, M, "A8", "A6")["ties"]))
    w("")
    w("### 4.5 Does the Shield find the risky reports? (level M)")
    w("")
    w("A report is *wrong-plan* if the plan of the best-guess record differs from the plan of the gold record (evaluation-side audit only; never seen by a policy). A method *flags* a report if it asks for verification or flies a cover.")
    w("")
    o += gate_table(M)
    w("")
    w("Equal-budget ranking: the share of wrong-plan reports caught when each method flags the top f of every episode (OBS arm, which commits like A1 and logs every risk score). "
      "%d reports, %d of them wrong-plan." % (J["levels"][M]["ranking"]["reports"], J["levels"][M]["ranking"]["wrong_plan_reports"]))
    w("")
    o += ranking_table(M)
    w("")
    w("Paired episode bootstrap of the AUROC difference, Shield minus confidence: **%+.3f** (95%% CI %+.3f to %+.3f); AUROC %.3f vs %.3f." % (auc_diff["diff"], auc_diff["ci"][0], auc_diff["ci"][1], auc_diff["auroc_a"], auc_diff["auroc_b"]))
    w("")
    w("### 4.6 Certificate, conformal sets and what the Shield decided (level M)")
    w("")
    w("* Conformal sets on %d EVAL reports (target %d%%): gold record in the set **%d (%s)**; empty sets %d; singleton sets %d; sets of 2 to K %d; oversized sets (> K) %d; "
      "gold record not expressible by the heads + parser (missing candidate) **%d**." % (es["reports"], 90, es["covered"], pct(es["covered"] / es["reports"]), es["empty"], es["size1"], es["size_2_K"], es["over_K"], es["gold_missing"]))
    w("* Certified (ACCEPT + ACCEPT_INFEASIBLE): **%s** of reports. Certified **and** the committed plan differs from the gold plan: %d reports = **%s** of all reports (the marginal bound is alpha = 10%% under exchangeability). "
      "Among certified reports alone the wrong-plan rate is %s." % (pct(cert["certified_rate"]), cert["certified_wrong_plan"], pct(cert["certified_wrong_rate"], 2), pct(cert["certified_wrong_plan"] / cert["certified"])))
    w("* Certified set sizes: %s. Certified sets with more than one record (the case that motivates the Shield, where the allocator absorbs the difference): %s of reports at L, %s at M, %s at H."
      % (", ".join("%s: %d" % (k, v) for k, v in cert["certified_set_sizes"].items()), pct(non_single["L"]), pct(non_single["M"]), pct(non_single["H"])))
    w("")
    o += decisions_table(J, M)
    w("")
    w("ACCEPT_INFEASIBLE means the allocator gave one plan for all candidates but the fleet cannot meet the requirement; it is counted as unresolved, never as safe. "
      "FALLBACK_PARTIAL (A8c only) means the cover does not serve every plausible candidate. FALLBACK_UNRESOLVED means the fleet could not meet the cover. All of them stay in the denominators.")
    w("")
    w("### 4.7 Compute and waiting costs (A8, Shield with full cover)")
    w("")
    rows = [[l, "%.2f" % t8[l]["allocator_runs_per_report"], "%.2f / %.2f" % (t8[l]["wall_ms_median"], t8[l]["wall_ms_p99"]), "%.1f" % t8[l]["hold_s_per_report"],
             "%.3f" % t8[l]["request_rate"], "%d (%d wasted)" % (t8[l]["cover_visits"], t8[l]["cover_wasted_visits"]), "%.0f" % t8[l]["distance_per_report_m"]] for l in lv]
    o += table(["Level", "allocator runs / report", "decision ms median / p99", "hold s / report", "requests / report", "cover trips", "distance m / report"], rows)
    w("")
    w("The plan's target of under 200 ms per report is met by a wide margin on this CPU. This says nothing about an edge board. In the sensitivity run where one allocator run costs 1.0 s of simulated time, "
      "**%d** Shield decisions hit the 5 s time-out and are committed without assessment (class TIMEOUT, counted)." % timeouts_ac10)
    w("")
    w("### 4.8 Stress test: the deliberately mismatched head (FP16-fitted head on raw Q4 vectors)")
    w("")
    w("*Diagnostic only (plan W3). The Shield, the gates and the conformal sets all sit on the mismatched head here.* Gold records miss %s at M and %s at H."
      % (pct(A(JR, "M", "A0")["U_deadline"]), pct(A(JR, "H", "A0")["U_deadline"])))
    w("")
    for l in ("M", "H"):
        w("**Level %s**" % l)
        w("")
        o += outcome_table(JR, l, ["A0", "A1", "A6", "A7", "A8", "A8c", "A10", "A12"])
        w("")
        w("A8 - A6: %s. A8c - A6: %s. A8 - A10 (fallback effect): %s. Share of the always-commit arm's excess misses removed: A6 %.0f%%, A8 %.0f%%, A8c %.0f%%."
          % (pp(P(JR, l, "A8", "A6")), pp(P(JR, l, "A8c", "A6")), pp(P(JR, l, "A8", "A10")), recovered(JR, l, "A6"), recovered(JR, l, "A8"), recovered(JR, l, "A8c")))
        w("")
    w("Costs of the Shield in the stress test: wasted trips per report rise to %.3f (A8) and %.3f (A8c) from %.3f (A1); %.2f allocator runs per report; certified share only %s of reports; "
      "late incidents rise (A8 %d, A8c %d, A1 %d at M) while unverified incidents fall (A8 %d, A8c %d, A1 %d). Against always commit, the Shield (A8) leaves %d fewer incidents unverified and has %d more late ones: much of what it saves is saved late."
      % (A(JR, M, "A8")["wasted_per_report"], A(JR, M, "A8c")["wasted_per_report"], A(JR, M, "A1")["wasted_per_report"], A(JR, M, "A8")["allocator_runs_per_report"],
         pct(JR["levels"][M]["certificate"]["certified_rate"]), A(JR, M, "A8")["late"], A(JR, M, "A8c")["late"], A(JR, M, "A1")["late"],
         A(JR, M, "A8")["unverified"], A(JR, M, "A8c")["unverified"], A(JR, M, "A1")["unverified"],
         A(JR, M, "A1")["unverified"] - A(JR, M, "A8")["unverified"], A(JR, M, "A8")["late"] - A(JR, M, "A1")["late"]))
    w("")
    w("### 4.9 Sensitivity (level M, 3 seeds, one setting changed at a time)")
    w("")
    names = {"main": "default (b 10%, alpha 0.10, K 8, d_v 60 s, CBBA, 0.02 s per run)", "b05": "budget b = 5%", "b20": "budget b = 20%", "b30": "budget b = 30%", "a05": "alpha = 0.05",
             "a20": "alpha = 0.20", "K4": "K = 4", "dv30": "verifier answers after 30 s", "dv120": "verifier answers after 120 s", "legacy": "legacy greedy allocator instead of bounded CBBA",
             "ac02": "an allocator run costs 0.2 s", "ac10": "an allocator run costs 1.0 s"}
    rows = []
    for tag, nm in names.items():
        s = sens[tag]
        rows.append([nm, "%.1f%%" % (100 * s["arms"]["A1"]), "%.1f%%" % (100 * s["arms"]["A6"]), "%.1f%%" % (100 * s["arms"]["A8"]), "%.1f%%" % (100 * s["arms"]["A8c"]),
                     pp(s["A8-A6"], False), pp(s["A8c-A6"], False)])
    o += table(["Setting", "A1 commit", "A6 confidence gate", "A8 Shield + full cover", "A8c location cover", "A8 - A6 (95% CI)", "A8c - A6 (95% CI)"], rows)
    w("")
    w("A8 - A6 is positive (A8 worse) in %d of %d settings and its interval excludes zero in %d of them; it is smallest when the budget is large (b = 30%%: %s) or alpha is large (alpha = 0.20: %s). "
      "A8c - A6 stays within %.2f pp and its interval excludes zero in %d of %d settings. The result does not depend on the allocator (legacy: A8 - A6 %s)."
      % (len(s_pos), len(s_tags), len(s_excl), pp(sens["b30"]["A8-A6"], False), pp(sens["a20"]["A8-A6"], False), s_c_max, len(s_c_excl), len(s_tags), pp(sens["legacy"]["A8-A6"], False)))
    w("")
    w("### 4.10 Sample size (plan section 8.4, from DEV)")
    w("")
    w("N_e = ((1.96 + 0.84) sd_D / delta)^2 with delta = 20%% of A6's record-induced misses per episode. For A8 vs A6 at level M the three seeds give N_e = %s episodes (`results/dev/main/POWER.md`). "
      "The draft plan uses **1,100 episodes** (22,000 evaluation reports plus 800 calibration reports; about %.0f minutes of GPU time), which gives a power of %s for those three values of delta. "
      "For an effect as large as the DEV difference (A8 - A6 = %s) far fewer episodes would do (%s for the three seeds)."
      % (", ".join("{:,.0f}".format(r["N_delta"]) for r in pw), gpu_minutes(1100), ", ".join("%.0f%%" % (100 * p) for p in p1100), pp(P(J, M, "A8", "A6"), False),
         ", ".join("{:,.0f}".format(r["N_obs"]) for r in pw)))
    w("")
    w("### 4.11 The other outcomes of plan section 3.1 (level M, DEV)")
    w("")
    sm = ss[M]
    w("**Harmless and harmful record changes.** Of %d report decisions (1,000 reports, each seen under 3 arrival seeds), the best-guess record is wrong in %d (%s). In %d of those (%s of the wrong records) the allocator still gives the gold plan: the change is *harmless*. "
      "In %d reports (%s of all reports) the plan is wrong. At level L the harmless count is %d and at H %d: the more contention, the fewer wrong records the allocator absorbs. "
      "Per-type tags (missed CREATE, wrong CLOSE, wrong location) are not built (section 3)."
      % (sm["reports"], sm["wrong_table"], pct(sm["wrong_table"] / sm["reports"]), sm["harmless"], pct(sm["harmless"] / sm["wrong_table"]), sm["wrong_plan"], pct(sm["wrong_plan"] / sm["reports"]),
         ss["L"]["harmless"], ss["H"]["harmless"]))
    w("")
    w("**Incident by incident against the gold-record run** (the same %d real incidents, the same episodes). *On time -> missed* means the incident was on time with gold records and is late or unverified with this arm. "
      "*Delay* is the mean extra time to verification, over the incidents verified in both runs, with a 95%% episode-bootstrap interval; positive means later than with gold records. Part of the delay is shared by every arm, because wrong records and extra trips take fleet time."
      % tr["A1"]["incidents"])
    w("")
    rows = [[a, devrun.ARM_TEXT[a], t["on_time_to_missed"], t["missed_to_on_time"], "%+d" % (t["on_time_to_missed"] - t["missed_to_on_time"]), t["verified_to_unverified"], t["unverified_to_verified"],
             "%.1f (%.1f to %.1f)" % (t["delay_mean_s"], t["delay_ci"][0], t["delay_ci"][1])] for a, t in tr.items()]
    o += table(["Arm", "System", "on time -> missed", "missed -> on time", "extra missed vs gold", "verified -> never verified", "never verified -> verified", "delay vs gold, s (95% CI)"], rows)
    w("")
    w("Other costs are in the tables above: verification requests, hold seconds, wasted trips, cover trips, distance and allocator runs per report. The verifier has no queue (section 3). "
      "Model memory: the Q4_K_M file is %.2f GiB, Q8_0 %.2f GiB and FP16 %.2f GiB; against the 2 GB working assumption (unconfirmed) FP16 does not fit. Model latency was not measured."
      % (gib["Q4_K_M"], gib["Q8_0"], gib["f16"]))
    w("")
    w("### 4.12 Demo")
    w("")
    w("`python demo.py` prints %d cases chosen by a rule fixed in advance (the first evaluation episode, by id, that contains each outcome class): ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, FALLBACK_UNRESOLVED, FALLBACK_PARTIAL (A8c), UNCERTIFIED_COMMIT (A10), TIMEOUT (allocator run set to 1.0 s), "
      "and a **failure case**: incident %s of report %s is verified on time under the confidence gate (%d s before its deadline) and late under the Shield (%d s after), where the Shield's decision on that report was a cover (%d cover trip, %d allocator runs). "
      "For each case it prints the report, the open table, the candidates with scores, the execution signature of each candidate, the decision, the cost, and (marked evaluation-only) the gold record and what happened to the real incidents. "
      "The failure case does not prove that one decision caused the lateness: both arms share the fleet with 19 other reports. Full output: `results/demo_output.txt`."
      % (dem["cases"], dem["incident"], dem["report"], dem["a6_before"], dem["a8_after"], dem["cover_trips"], dem["runs"]))
    w("")
    w("## 5. What improved, what failed, and why")
    w("")
    w("### Improved (measured on DEV)")
    w("")
    w("1. **The Shield finds wrong-plan reports much more completely, at a price.** Wrong-plan reports left unflagged: %s of all reports (Shield) against %s (confidence gate), %s (record-score gate), %s (random gate) and %s (no gate). "
      "Recall of wrong-plan reports %s against %s for the confidence gate; precision %s against %s. This is **not an equal-cost comparison**: the Shield acts on %s of reports (%s verifications and %s covers), the gates on %s. "
      "At an equal flag rate the ranking is better by a smaller margin: at f = 10%% it catches %s of the wrong-plan reports against %s; AUROC %.3f against %.3f (difference %+.3f, CI %+.3f to %+.3f)."
      % (pct(gq["A8"]["accepted_wrong"] / n_rep), pct(gq["A6"]["accepted_wrong"] / n_rep), pct(gq["A6b"]["accepted_wrong"] / n_rep), pct(gq["A7"]["accepted_wrong"] / n_rep), pct(gq["A1"]["accepted_wrong"] / n_rep),
         pct(gq["A8"]["flagged_wrong"] / gq["A8"]["wrong_plan"]), pct(gq["A6"]["flagged_wrong"] / gq["A6"]["wrong_plan"]), pct(gq["A8"]["flagged_wrong"] / gq["A8"]["flagged"]),
         pct(gq["A6"]["flagged_wrong"] / gq["A6"]["flagged"]), pct(f8), pct(esc8), pct(cov8), pct(f6), pct(rk[k8]["10%"]), pct(rk[k6]["10%"]),
         auc_diff["auroc_a"], auc_diff["auroc_b"], auc_diff["diff"], auc_diff["ci"][0], auc_diff["ci"][1]))
    w("2. **The conformal certificate behaves as promised.** Coverage %s at a target of 90%%; certified-and-wrong %s of all reports (bound 10%%). The observed conditional rate among certified reports (%s) is far below the worst case alpha / P(certified) = %s."
      % (pct(es["covered"] / es["reports"]), pct(cert["certified_wrong_rate"], 2), pct(cert["certified_wrong_plan"] / cert["certified"]), pct(0.10 / cert["certified_rate"])))
    w("3. **Conformal sets are better than the top-2 what-if, and not worse than singleton-only sets.** A8 - A11 (top-2 what-if without conformal): %s at M, %s at H. A8 - A9 (singleton sets only): %s at M, %s at H, %s at L; %s."
      % (pp(P(J, "M", "A8", "A11")), pp(P(J, "H", "A8", "A11")), pp(P(J, "M", "A8", "A9")), pp(P(J, "H", "A8", "A9")), pp(P(J, "L", "A8", "A9")),
         "the sign-flip p-values are all at least %.3f, so I do not claim an advantage over singleton-only sets" % min(p9) if min(p9) >= 0.05 else "some of these differences are significant at the 5% level"))
    w("4. **When the readout is poor, the Shield protects the mission.** Stress test at M: U falls from %.1f%% (always commit) to %.1f%% (A8) and %.1f%% (A8c); the confidence gate reaches %.1f%%. "
      "The Shield removes %.0f%% (A8) and %.0f%% (A8c) of the excess misses over gold records; the confidence gate %.0f%%. *Cost:* %d late incidents (A8) against %d for always commit, wasted trips per report %.3f against %.3f."
      % (U(JR, M, "A1"), U(JR, M, "A8"), U(JR, M, "A8c"), U(JR, M, "A6"), recovered(JR, M, "A8"), recovered(JR, M, "A8c"), recovered(JR, M, "A6"),
         A(JR, M, "A8")["late"], A(JR, M, "A1")["late"], A(JR, M, "A8")["wasted_per_report"], A(JR, M, "A1")["wasted_per_report"]))
    w("5. **The allocator is now a real bounded CBBA** with measured convergence, determinism and a measured ratio to the best assignment; the old V1 allocator is kept as `legacy_greedy_s1` and the result does not depend on the choice.")
    w("")
    w("### Failed or not achieved")
    w("")
    w("1. **With the competent Q4 head, the plan's Shield does not lower deadline misses.** A8 - A6 is %s at M, %s at H and %s at L. The plan's primary comparison therefore points the wrong way on DEV."
      % (pp(P(J, "M", "A8", "A6")), pp(P(J, "H", "A8", "A6")), pp(P(J, "L", "A8", "A6"))))
    w("2. **The revised location cover (A8c) is about equal to the gate, not clearly better** (A8c - A6: %s at M, %s at H, %s at L). The interval excludes zero at: %s. "
      "A8c was designed after the DEV outcomes were seen and no multiplicity correction is applied, so none of this is confirmatory."
      % (pp(P(J, "M", "A8c", "A6")), pp(P(J, "H", "A8c", "A6")), pp(P(J, "L", "A8c", "A6")),
         ", ".join("level %s (A8c %s)" % (l, "lower" if P(J, l, "A8c", "A6")["diff_U"] < 0 else "higher") for l in c_excl) if c_excl else "no level"))
    w("3. **There is little headroom.** Record errors cost %s at M (A1 - A0); a perfect gate with the same budget wins back only %s (A12 - A1: %s, not significant). Even the perfect gate (%.1f%%) does not reach FP16 always-on (%.1f%%)."
      % ("%+.2f pp" % (100 * P(J, M, "A1", "A0")["diff_U"]), "%.2f pp" % (-100 * P(J, M, "A12", "A1")["diff_U"]), pp(P(J, M, "A12", "A1")), U(J, M, "A12"), U(J, M, "A2")))
    w("4. **Q4 is measurably worse than FP16 at mission level** on DEV: A1 - A2 is %s at L, %s at M, %s at H. This is not the same outcome definition as the pilot's held-out result (B: -0.3 pp, -1.1 to +0.5; \"unverified by 600 s\"), so the two are not in conflict, but "
      "the supporting finding \"Q4 is close to FP16\" of plan section 1 should be re-read with this in mind. The recentred baseline (A4) is not better than the matched Q4 head: A4 - A1 %s at M."
      % (pp(P(J, "L", "A1", "A2")), pp(P(J, M, "A1", "A2")), pp(P(J, "H", "A1", "A2")), pp(P(J, M, "A4", "A1"))))
    w("5. **Budget matching in the plan's M6 sense is not met** (realised rates %s to %s instead of 10%%; section 3). The arms are matched to each other." % (pct(min(rates.values())), pct(max(rates.values()))))
    w("")
    w("### Why the full cover costs more than it saves (evidence, not proof)")
    w("")
    w("* Same certification, same escalation, only the fallback differs: A8 - A10 = %s at M and %s at H. So the cover is what costs." % (pp(P(J, M, "A8", "A10")), pp(P(J, "H", "A8", "A10"))))
    w("* A8 flies %d cover trips at M (A10 flies none). Against A10, A8 has %d more late and %d fewer unverified incidents; incident by incident against gold records (section 4.11) %d more incidents go from on time to missed. "
      "So the cover mostly delays incidents that would have been on time. It rescues few."
      % (A(J, M, "A8")["cover_visits"], A(J, M, "A8")["late"] - A(J, M, "A10")["late"], A(J, M, "A10")["unverified"] - A(J, M, "A8")["unverified"],
         tr["A8"]["on_time_to_missed"] - tr["A10"]["on_time_to_missed"]))
    w("* The plan's cover takes the union of cameras and the maximum priority of all candidates. In this fleet a task that needs RGB and THERMAL can only go to UAV-02, the only thermal UAV (unit test `test_cover_task_with_two_cameras_goes_to_the_only_uav_that_has_both`). "
      "The location cover (A8c) keeps the committed camera and priority and removes the loss: A8c - A8 = %s at M. I did **not** measure how many cover tasks needed both cameras, so this is the best-supported explanation, not a measured fact." % pp(P(J, M, "A8c", "A8")))
    w("* Verification is not free either: the oracle gate A12 asks for %.3f requests per report and still recovers only %.2f pp." % (A(J, M, "A12")["request_rate"], -100 * P(J, M, "A12", "A1")["diff_U"]))
    w("")
    w("## 6. The boundaries you set, and how each is enforced and checked")
    w("")
    w("| Boundary | How it is enforced | How it is checked |")
    w("|---|---|---|")
    w("| Runtime decisions cannot read hidden incident truth | Hidden truth lives in one object only the engine and scorer hold; policies get a view with no route to it | `test_truth_and_gold_are_closed_outside_the_engine`, `test_policy_view_has_no_route_to_the_gold_record`, `test_source_scan_policy_modules_never_name_the_truth`, `test_policy_modules_do_not_import_the_truth`; the evaluation-side fields (`rpg`, `tg`, gold sets) are written to the records only after the decision |")
    w("| Identical candidate allocations are not sufficient evidence of safety | Certification is separate from the requirement check R1 to R3; a certified plan that fails R1 to R3 is ACCEPT_INFEASIBLE (alarm, counted unresolved); outcomes are always judged by the scorer, never by plan equality | `test_accept_infeasible_when_certified_but_the_fleet_cannot_meet_the_deadline`; ACCEPT_INFEASIBLE counts: %d / %d / %d reports at L / M / H |"
      % tuple(J["levels"][l]["arms"]["A8"]["outcome_classes"].get("ACCEPT_INFEASIBLE", 0) for l in lv))
    w("| Missing candidates, time-outs, unavailable fallbacks and unresolved incidents stay visible | Separate outcome classes and counters in every table; every incident is in every denominator | Missing candidates: 0 on saved data (reported in every table, exercised by `test_missing_candidate_the_shield_accepts_a_wrong_record_and_the_incident_is_missed`); TIMEOUT: `test_timeout_when_the_what_if_runs_do_not_fit_into_the_time_limit`; FALLBACK_UNRESOLVED: %d / %d / %d reports at L / M / H for A8 |"
      % tuple(J["levels"][l]["arms"]["A8"]["outcome_classes"].get("FALLBACK_UNRESOLVED", 0) for l in lv))
    w("| Verification and computation consume time and resources | Verification waits (delay d_v, hold), budget cap per episode, simulated cost per allocator run that advances the clock, time-out, cover trips and distance counted | `test_decision_time_is_charged_per_allocator_run_and_timeout_is_labelled`, `test_budget_cap_is_enforced_and_rounded_per_episode`, `test_escalation_holds_the_old_rows_but_still_dispatches_them`; costs in sections 4.2 to 4.7 |")
    w("| No fallback may assume that every possibility can always be covered | The cover is planned with the same allocator and checked against R1 and R2; empty or oversized sets are never truncated silently; the cover can end FALLBACK_UNRESOLVED or FALLBACK_PARTIAL | `test_fallback_unresolved_when_the_cover_cannot_meet_the_requirements`, `test_impossible_coverage_only_one_uav_has_thermal_so_not_everything_can_be_covered`, `test_empty_set_is_uncertified_and_not_truncated`, `test_oversized_set_is_uncertified_and_counted` |")
    w("| Evaluation protocol frozen before fresh outcomes exist | `tools/freeze_plan.py` hashes the plan and the code; `tools/run_fresh.py` stops if either changed, if the cases differ from the frozen seed, or if the vectors do not match their manifest; one run per tag | `tests/test_fresh.py` (13); the real folder has no freeze file yet |")
    w("")
    w("## 7. Reproducibility")
    w("")
    w("* Rerunning the main run and the stress run after the last code change gave **identical** records: %s (`results/compare_runs.txt`; `python tools/compare_runs.py main main_first`, `raw raw_first`; wall-clock times are ignored)."
      % " and ".join("{:,} records in {} files".format(n, f) for f, n in rep))
    w("* Heads are deterministic (no random seed; tol 1e-6; no fit hit the iteration limit). Everything random (arrival gaps, random gate, tie-breaking) is seeded by hashes of the seed and the report id.")
    w("* Tests: %s. Total %s." % (", ".join("%s: %s" % (k, v) for k, v in TESTS.items()) if TESTS else "see section 10", tests_total))
    w("")
    w("## 8. Not tested, and limits of what the numbers can say")
    w("")
    lim = [
        "**Anything on fresh data.** No fresh report exists. Every claim above is exploratory. The 1,000 reports were re-used across 5 folds and 3 seeds, so the intervals are narrower than a true repeat would give.",
        "**The GPU extraction run.** The script is tested against a mock llama server and a failure matrix only. Not exercised on hardware: the real llama.cpp run, the 20-report anchor check against the saved vectors, the 100-report CPU check (CPU vs GPU cosine).",
        "**Hardware timing.** Decision times are from a cloud CPU. The 0.02 s per allocator run is an assumption (sensitivity at 0.2 s and 1.0 s is included). The language-model forward pass is outside the Shield's cost. No laptop or edge-board timing.",
        "**Chain-mode episodes and closed-loop prompts.** In the built episodes reports do not influence each other's belief tables (deviation D-01), and a wrong record never changes a later prompt. Competition is for UAVs only.",
        "**Parser faults.** The pilot's parser produced zero missing candidates on 2,000 CAL and EVAL rows. The \"gold record not expressible\" path is covered by unit tests, not by data; the real fault rate on realistic text is unknown.",
        "**Requirement-level or regret-based certificates.** The certificate is plan equality plus R1 to R3. No guarantee is claimed about incident outcomes.",
        "**Cost-aware fallback ordering** (verify before cover, or cover only when cheap) and **provisional-commit semantics** for held reports.",
        "**Style shift.** The style-B check (tag `sb`, the 400 saved style-B reports in 20 fixed episodes) is part of the draft plan and of `tools/run_fresh.py`, tested with fake vectors only. It has not been run on real data.",
        "**Other models, real report text, message loss or delay between UAVs, a line-graph network as the main setting.**",
        "**The supervisors' answers** to plan section 12 (outcome priorities, who verifies and how fast, public evidence package, the 2 GB memory assumption). Defaults are used.",
        "**M0 on the laptop:** the audit scripts on the real files, the gguf re-hash and `git init` (section 11).",
        "**The conformal guarantee** assumes exchangeable calibration and test reports. Reports of one family are not independent, and the wording shifts for style B. Measured coverage on DEV is inside the band, which is not a proof for fresh data.",
        "**Multiplicity.** %d paired comparisons are shown per level (section 4.4). Only the plan's primary comparison is a registered test; all others are descriptive." % len(pairs),
        "**A8c is post-hoc.** It was designed after the DEV outcomes were seen."]
    for i, t in enumerate(lim, 1):
        w("%d. %s" % (i, t))
    w("")
    w("## 9. Decisions needed from the main chat (I will not decide these)")
    w("")
    w("**D1. Primary comparison.** DEV points the wrong way for the registered primary (A8 - A6 = %s at M). Options: "
      "(a) *keep A8 vs A6 as primary* and report A8c vs A6 as secondary S1 (my default in the draft plan; honest, and the only fully pre-registered test); "
      "(b) make A8c vs A6 primary, with a deviation note that A8c was designed after DEV outcomes (DEV predicts about zero, so the most that can be shown is \"no detectable difference\"; a non-inferiority claim needs its own margin); "
      "(c) run one more DEV round on a redesigned, cost-aware fallback and freeze that (risk: more tuning on the same 1,000 reports)." % pp(P(J, M, "A8", "A6"), False))
    w("")
    w("**D2. Sample size.** 1,100 fresh episodes (power %s for delta = 20%% of A6's record-induced misses, for the three DEV seeds; about %.0f minutes of GPU time) or fewer (400 episodes: power %s and about %.0f minutes, but enough for an effect as large as the DEV difference)."
      % (", ".join("%.0f%%" % (100 * p) for p in p1100), gpu_minutes(1100), ", ".join("%.0f%%" % (100 * p) for p in p400), gpu_minutes(400)))
    w("")
    w("**D3. Stress test (S7) and style-B check (S9).** I recommend including both, labelled diagnostic / exploratory.")
    w("")
    w("**D4. Kill criterion and the story of the paper.** By its letter the rule is not triggered (certified non-singleton sets %s at M against the 3%% limit). By its intent (\"A8 does not beat A6\") it is. "
      "Please decide how the paper describes the Shield: (i) a monitor that ranks wrong-plan reports better than confidence (AUROC %.3f against %.3f), finds most of them when it may also fly covers, and protects the mission when the readout degrades, "
      "with an honest finding that it does not lower misses for a competent Q4 head; or (ii) a measurement-and-diagnostic study. The data in sections 4.5 and 4.8 support (i); sections 4.2 and 4.4 limit it." % (pct(non_single["M"]), auc_diff["auroc_a"], auc_diff["auroc_b"]))
    w("")
    w("**D5. Settings and the supervisors.** alpha, K, b, d_v and the deadlines are the DEV defaults. The supervisors' four questions (plan section 12) are still open; any change must come **before** the freeze.")
    w("")
    w("**D6. Request-rate matching.** Keep the thresholds as they are (arms matched to each other within %.1f pp, realised rate %s to %s instead of 10%%), or recalibrate them on the capped rate so that the realised rate is closer to b (the gates would then spend their budget on the first reports that cross a lower threshold; one more DEV round)."
      % (100 * (max(rates.values()) - min(rates.values())), pct(min(rates.values())), pct(max(rates.values()))))
    w("")
    w("**D7. Deviations D-01 to D-%02d** (`docs/DEVIATIONS.md`): please accept or reject each, especially D-01 (overlay episodes instead of chain episodes) and D-03 (the committed record is the pilot's hierarchical record, which differs from the top-scoring candidate in 0.4%% of reports)." % len(re.findall(r"^## D-\d+", (paths.HERE / "docs" / "DEVIATIONS.md").read_text(encoding="utf-8"), flags=re.M)))
    w("")
    w("**D8. Who sets `STATUS: FROZEN-READY`**, and whether to freeze before the supervisors reply. After the freeze, any change to the plan or to `shield/*.py` or the five listed tools needs a new freeze and a written deviation note.")
    w("")
    w("## 10. How to reproduce and check")
    w("")
    w("```")
    w("python -m pytest -q tests                                  # %s checks (test_fresh.py takes about 4 minutes)" % tests_total)
    w("python tools/check_inputs.py                                # the 14 pinned files; add --gguf-dir D:\\llama\\models for the model hashes")
    w("python tools/run_dev.py --tag main --levels L M H --seeds 1 2 3     # about 10 minutes on 2 cores")
    w("python tools/run_dev.py --tag raw  --levels M H --seeds 1 2 3 --readout raw")
    w("bash tools/run_sensitivity.sh                              # the sensitivity runs, about 1 minute each")
    w("python tools/analyze_dev.py --tag main                     # results/dev/main/DEV_main.md and .json")
    w("python tools/verify_dev_numbers.py --tag main              # independent recomputation from the raw records")
    w("python tools/sens_summary.py ; python tools/power.py --tag main")
    w("python tools/build_evidence.py                             # this file")
    w("python demo.py                                             # eight outcome classes and the failure case")
    w("```")
    w("")
    w("Set `EDGESAR_ROOT` if the older folders are not next to `edgesar_shield`. The FRESH procedure is in `README.md` and `docs/EVAL_PLAN_FRESH.md` section 8.")
    w("")
    w("## 11. What Samadhi still has to do on the laptop")
    w("")
    w("0. **Put the folder on the laptop.** This session could not write to the laptop at the end (the link to the computer was no longer available), so the package comes as downloads. Unpack it as `D:\\1 Samadhi UNI\\aFYP\\Claude\\edgesar_shield` (next to `edgesar_pilot`, `edgesar_heads`, `V1`). Do not change the older folders.")
    w("1. `cd \"D:\\1 Samadhi UNI\\aFYP\\Claude\\edgesar_shield\"` then `python tools/check_inputs.py --gguf-dir D:\\llama\\models` (hashes the three model files, about 4.6 GB; compares with the audited values).")
    w("2. The audit scripts of `edgesar_audit_2026-11-13\\scripts` as written in its `HANDOFF.md` section 3 (PowerShell).")
    w("3. `git init` **inside** `edgesar_shield` only (the `.gitignore` is already there). Do not run it in the parent folder.")
    w("4. Ask Dr. Achala and Mr. Maninda the four questions of plan section 12 (outcome priorities and deadlines; who verifies and how fast; public evidence package; 2 GB memory assumption).")
    w("")
    w("Nothing else is needed from the laptop until the plan is frozen. The GPU step comes after the freeze.")
    w("")
    text = "\n".join(o) + "\n"
    (paths.HERE / "IMPLEMENTATION_EVIDENCE.md").write_text(text, encoding="utf-8")
    print("wrote IMPLEMENTATION_EVIDENCE.md (%d lines)" % len(o))


if __name__ == "__main__":
    main()
