"""
Writes ITERATION1_EVIDENCE.md from the iteration-1 result files (numbers come from results/iter1/ITER1_RESULTS.json, the benchmark json, the repro
diagnostic and the test summary; the sentences around them are fixed text).   python tools/build_iter1_evidence.py
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import paths                                          # noqa: E402

R = json.loads((paths.RESULTS / "iter1" / "ITER1_RESULTS.json").read_text(encoding="utf-8"))
BENCH = json.loads(next((paths.RESULTS).glob("bench_cloud_shield_only_*/bench.json")).read_text(encoding="utf-8"))
PROTO = (paths.RESULTS / "iter1" / "PROTOCOL.sha256").read_text().split()[0]
TS = json.loads((paths.RESULTS / "tests_summary_iter1.json").read_text()) if (paths.RESULTS / "tests_summary_iter1.json").exists() else None


def U(tag, lv, a):
    return 100 * R[tag]["levels"][lv]["table"][a]["U_deadline"]


def CI(tag, lv, a):
    c = R[tag]["levels"][lv]["ci"][a]
    return 100 * c[0], 100 * c[1]


def P(tag, lv, k):
    p = R[tag]["levels"][lv]["pairs"][k]
    return 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["p_signflip"]


def pr(tag, lv, k):
    d, lo, hi, p = P(tag, lv, k)
    return "%+.2f pp (95%% CI %+.2f to %+.2f)" % (d, lo, hi)


def Q(tag, lv, a, f):
    return 100 * R[tag]["levels"][lv]["quality"][a][f]


def T(tag, lv, a, f):
    return R[tag]["levels"][lv]["table"][a][f]


def row(tag, lv, a, name):
    lo, hi = CI(tag, lv, a)
    t = R[tag]["levels"][lv]["table"][a]
    return "| %s | %s | %.2f%% | %.2f to %.2f | %.3f | %.3f | %d | %d | %.0f |" % (a, name, U(tag, lv, a), lo, hi, t["request_rate"], t["wasted_per_report"], t["cover_visits"],
                                                                                    t["cover_wasted_visits"], t["distance_per_report_m"])


def main():
    L = []
    A = L.append
    lab = R["label"]
    A("# EdgeSAR iteration 1: evidence (development data only)")
    A("")
    A("Written 2026-11-13 by the implementation chat. Protocol: `docs/ITERATION1_PROTOCOL.md`, SHA-256 `%s` (hashed before the first run). Old results, old arms and the old cache are unchanged "
      "(`tests/test_iter1.py` checks that A1, A6, A8, A8c, A10 give exactly the old incident counts). **No fresh case was generated or read. This is not a confirmation.** "
      "Pooled intervals are optimistic: the three arrival seeds re-use the same 1,000 reports." % PROTO)
    A("")
    A("## 0. Short answer")
    A("")
    A("1. **Label by the rule fixed in advance: %s** (competent Q4 head, level M). Shield-2 (B3) minus equal-footing confidence gate (G1) = %s; B3 minus always commit (A1) = %s. "
      "No second round of mechanisms follows from this (stopping rule, protocol section 4)." % (lab["label"], pr("q4", "M", "B3-G1"), pr("q4", "M", "B3-A1")))
    A("2. **What improved.** (a) The certificate is much safer: certified-and-wrong plan %.2f%% -> %.2f%%, certified-and-wrong table %.2f%% -> %.2f%% (A8 -> B3, level M), at the price of flagging "
      "%.0f%% instead of %.0f%% of the reports. (b) The cost-aware fallback removes harm done by the plan's full cover: B3 minus B2 = %s. (c) When the head is NOT adapted to Q4 "
      "(frozen FP16 head on Q4 vectors) Shield-2 cuts the missed share from %.1f%% to %.1f%%, and beats the equal-footing gate (%.1f%%): B3 minus G1 = %s." % (
          Q("q4", "M", "A8", "certified_wrong_plan"), Q("q4", "M", "B3", "certified_wrong_plan"), Q("q4", "M", "A8", "certified_wrong_table"), Q("q4", "M", "B3", "certified_wrong_table"),
          Q("q4", "M", "B3", "flagged"), Q("q4", "M", "A8", "flagged"), pr("q4", "M", "B3-B2"), U("raw", "M", "A1"), U("raw", "M", "B3"), U("raw", "M", "G1"), pr("raw", "M", "B3-G1")))
    A("3. **What did not improve.** With a competent Q4 head nothing beats always committing: the best any gate could do (oracle, A12) is %s, and every real arm is inside the noise or worse than A1. "
      "The pre-specified B3 (%.2f%%) is worse than the post-hoc A8c (%.2f%%) of iteration 0 at level M, and also on the unadapted head (%.2f%% vs %.2f%%); the mass guard alone and the strict check alone change nothing in the missed share." % (
          pr("q4", "M", "A12-A1"), U("q4", "M", "B3"), U("q4", "M", "A8c"), U("raw", "M", "B3"), U("raw", "M", "A8c")))
    A("4. **Quantisation does cost something, even when the head is retrained for it.** Q4 minus FP16 = %s at M (L: %s; H: %s). Q8 minus FP16 = %s at M." % (
        pr("q4", "M", "A1-A2"), pr("q4", "L", "A1-A2"), pr("q4", "H", "A1-A2"), pr("q4", "M", "A3-A2")))
    A("5. **Most of the harm of a quantised model comes from using a head that was not adapted to it, and cheap adaptation removes most of it:** unadapted Q4 %.1f%%, recentred (no labels) %.1f%%, "
      "retrained on Q4 vectors %.1f%%, FP16 %.1f%%, gold records %.1f%% (level M). Shield-2 on the unadapted head gives %.1f%%." % (
          U("raw", "M", "A1"), U("q4", "M", "A4"), U("q4", "M", "A1"), U("q4", "M", "A2"), U("q4", "M", "A0"), U("raw", "M", "B3")))
    A("6. **Not measured:** speed and memory of llama.cpp on Samadhi's computer (script ready, needs his machine); fresh data; chain-mode episodes; the Shield on the recentred head.")
    A("")
    A("## 1. The five priorities: what was built, what came out")
    A("")
    A("| # | priority | built (new files only) | result |")
    A("|---|---|---|---|")
    A("| 1 | fallback congestion and delay | `policy2.ShieldV2(cost_aware=True)`: the fallback is chosen by the predicted number of unmet requirements over ALL pending tasks of ALL reports "
      "(believed deadlines; runtime information only): full cover, else location cover, else commit r-hat (COVER_DECLINED) | B3 - B2 = %s at M, %s at H. Lowers the harm of the full cover; does not reach 'no worse than always commit' with a competent head |" % (pr("q4", "M", "B3-B2"), pr("q4", "H", "B3-B2")))
    A("| 2 | requirements under every candidate | `assess2`: each candidate's plan is checked against its own task (own priority -> own deadline, own camera); certified needs one signature AND one feasibility status | "
      "certified-and-wrong plan %.2f%% -> %.2f%% with the mass guard; the strict check alone moves it only %.2f%% -> %.2f%% (B1); missed share unchanged (B1 - A8 = %s) |" % (
          Q("q4", "M", "A8", "certified_wrong_plan"), Q("q4", "M", "B2", "certified_wrong_plan"), Q("q4", "M", "A8", "certified_wrong_plan"), Q("q4", "M", "B1", "certified_wrong_plan"), pr("q4", "M", "B1-A8")))
    A("| 3 | unsupported interpretations, missing candidates | mass guard (set mass >= 1 - alpha); class UNSUPPORTED_COMMIT (visible, unresolved, no cover because a cover cannot serve mass outside the set); EMPTY / OVERSIZE / R-hat-outside already uncertified | "
      "certified share %.1f%% -> %.1f%%; %d reports at M ended as UNSUPPORTED_COMMIT; B2 - B1 = %s (no change in misses) |" % (
          Q("q4", "M", "B1", "certified"), Q("q4", "M", "B2", "certified"), T("q4", "M", "B2", "outcome_classes").get("UNSUPPORTED_COMMIT", 0), pr("q4", "M", "B2-B1")))
    A("| 4 | equal-footing comparators | G1 (confidence gate, same cap, same cost-aware fallback, same flag rate as B3 on CAL); A1; A4 recentred; A2 FP16; A3 Q8; also all arms on FP16, Q8 and the unadapted head | sections 4 and 5 |")
    A("| 5 | latency and memory on his computer | `tools/bench_local.py` (llama.cpp per precision, heads, Shield, memory) | script tested here against a fake server; the Shield part measured in the cloud (section 6); his numbers are still to be made |")
    A("")
    A("## 2. Competent Q4 head (retrained on Q4 vectors), level M")
    A("")
    A("| arm | what | missed share | 95% CI | verification requests / report | wasted trips / report | cover visits | cover visits wasted | distance m / report |")
    A("|---|---|---|---|---|---|---|---|---|")
    names = {"A0": "gold records", "A1": "Q4, always commit", "A2": "FP16, always commit", "A3": "Q8, always commit", "A4": "recentred Q4", "A6": "confidence gate (verification only)",
             "A8": "plan's Shield (full cover)", "A8c": "Shield + location cover (post-hoc, iteration 0)", "A12": "oracle gate (diagnostic)", "B1": "strict check", "B2": "B1 + mass guard",
             "B3": "Shield-2 = B2 + cost-aware fallback", "B4": "B1 + cost-aware fallback", "G1": "equal-footing gate"}
    for a in ("A0", "A2", "A3", "A1", "A4", "A6", "A8", "A8c", "A12", "B1", "B2", "B3", "B4", "G1"):
        A(row("q4", "M", a, names[a]))
    A("")
    A("Paired differences (negative = first arm better):")
    A("")
    A("| comparison | L | M | H |")
    A("|---|---|---|---|")
    for k, w in (("B3-G1", "P1 PRIMARY: Shield-2 vs equal-footing gate"), ("B3-A1", "P2: Shield-2 vs always commit"), ("B3-A8", "P3: Shield-2 vs plan's Shield"), ("B3-A6", "Shield-2 vs verification-only gate"),
                 ("G1-A1", "equal-footing gate vs always commit"), ("B3-B2", "cost-aware fallback"), ("B2-B1", "mass guard"), ("B1-A8", "strict check"), ("A12-A1", "oracle gate vs always commit (headroom)")):
        A("| %s %s | %s | %s | %s |" % (k, w, pr("q4", "L", k), pr("q4", "M", k), pr("q4", "H", k)))
    A("")
    ps = R["q4"]["levels"]["M"]["per_seed"]
    A("Per arrival seed at M, B3 - G1: %s; B3 - A1: %s (pp)." % (", ".join("%+.2f" % ps["B3-G1"][s]["diff_pp"] for s in sorted(ps["B3-G1"])), ", ".join("%+.2f" % ps["B3-A1"][s]["diff_pp"] for s in sorted(ps["B3-A1"]))))
    A("")
    A("Reading. With a head trained on Q4 vectors, %.0f%% of the reports are certified by Shield-2 and the certified ones are almost always right, but intervening on the other %.0f%% (%.0f%% of them "
      "needed it) costs about as much as it saves: fallback trips delay other incidents. The oracle gate (told which reports are wrong, same delay, same cap) changes the missed share by only %s, so this setting has "
      "little headroom for any gate." % (Q("q4", "M", "B3", "certified"), Q("q4", "M", "B3", "flagged"), Q("q4", "M", "B3", "flagged_precision"), pr("q4", "M", "A12-A1")))
    A("")
    A("## 3. The certificate (priorities 2 and 3)")
    A("")
    A("| arm (level M) | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports left unflagged | precision of flags |")
    A("|---|---|---|---|---|---|---|")
    for a in ("A8", "B1", "B2", "B3", "G1", "A6"):
        q = R["q4"]["levels"]["M"]["quality"][a]
        A("| %s | %.1f%% | %.2f%% | %.2f%% | %.1f%% | %.2f%% | %.1f%% |" % (a, 100 * q["certified"], 100 * q["certified_wrong_plan"], 100 * q["certified_wrong_table"], 100 * q["flagged"], 100 * q["wrong_plan_unflagged"], 100 * q["flagged_precision"]))
    A("")
    A("The mass guard is what makes agreement inside the set mean something: A8 certified %.1f%% of the reports and was wrong on %.2f%% of all reports; with the guard %.1f%% are certified and %.2f%% are wrong. "
      "The conformal set misses the gold record on about 9%% of the reports (coverage 90.8%% in iteration 0); the heads and the parser can express the gold record in every report (gold_missing = 0), so "
      "the misses are set truncation, not an unsupported record type." % (Q("q4", "M", "A8", "certified"), Q("q4", "M", "A8", "certified_wrong_plan"), Q("q4", "M", "B3", "certified"), Q("q4", "M", "B3", "certified_wrong_plan")))
    A("")
    A("## 4. Equal footing (priority 4)")
    A("")
    A("G1 gets everything B3 gets except the trigger: the same two-level use of the cap (verify first, fallback after), the same cost-aware fallback on the same conformal set, the same share of flagged reports on CAL. "
      "Competent head: B3 - G1 = %s: a tie. Unadapted head: B3 - G1 = %s. So the candidate set + signature + checks trigger is worth something only when the head is poor "
      "(wrong-plan reports left unflagged: B3 %.2f%% vs G1 %.2f%% on the unadapted head)." % (pr("q4", "M", "B3-G1"), pr("raw", "M", "B3-G1"), Q("raw", "M", "B3", "wrong_plan_unflagged"), Q("raw", "M", "G1", "wrong_plan_unflagged")))
    A("")
    A("## 5. Precision, adaptation and the safety net (level M; all readouts, same episodes)")
    A("")
    A("| head | always commit | confidence gate (verification only) | equal-footing gate G1 | plan's Shield A8 | Shield-2 B3 | B3 minus always commit |")
    A("|---|---|---|---|---|---|---|")
    for tag, nm in (("f16", "FP16 (reference)"), ("q8", "Q8_0, retrained"), ("q4", "Q4_K_M, retrained on Q4 vectors"), ("raw", "Q4_K_M, head NOT adapted (frozen FP16 head)")):
        A("| %s | %.2f%% | %.2f%% | %.2f%% | %.2f%% | %.2f%% | %s |" % (nm, U(tag, "M", "A1"), U(tag, "M", "A6"), U(tag, "M", "G1"), U(tag, "M", "A8"), U(tag, "M", "B3"), pr(tag, "M", "B3-A1")))
    A("")
    A("Other references at M: gold records %.2f%%; Q4 head recentred (label-free shift removed from the Q4 vectors, FP16 head) %.2f%%. Quantisation effect with a retrained head: Q8 - FP16 %s; Q4 - FP16 %s. "
      "Unadapted Q4 - FP16 %s. At levels L / H the same ordering holds (see `results/iter1/ITER1_RESULTS.md`)." % (U("q4", "M", "A0"), U("q4", "M", "A4"), pr("q4", "M", "A3-A2"), pr("q4", "M", "A1-A2"), pr("raw", "M", "A1-A2")))
    A("")
    A("What this says about quantisation: (i) the large damage appears when the readout head was fitted on full-precision vectors and is applied to quantised ones; (ii) removing the average shift "
      "or retraining on quantised vectors removes most of it; (iii) a small cost remains for Q4 (about %.1f pp of missed share here); (iv) a runtime safety net helps in case (i) and not in case (iii). "
      "The conclusions are for this model, this head, this simulated mission and these reports." % (P("q4", "M", "A1-A2")[0]))
    A("")
    A("## 6. Speed and memory (priority 5)")
    A("")
    s = BENCH["shield"]
    A("Measured now, **in the cloud container (%s; %s CPUs; not Samadhi's computer)**, on saved vectors: heads p50 %.2f ms; one Shield-2 decision p50 %.2f ms, p95 %.2f ms, p99 %.2f ms (%.2f allocator runs per decision); "
      "the allocator takes %.2f ms per run. The simulation charges **20 ms per run**, about %.0f times more than measured here, so the simulated delay is a conservative stand-in for a slow edge CPU, and decision time is not "
      "what limits Shield-2. Python process peak memory %.0f MB (includes the whole development set)." % (
          BENCH["processor"] or BENCH["machine"], BENCH["cpu_count"], BENCH["heads_ms_p50"], s["B3"]["decision_ms_p50"], s["B3"]["decision_ms_p95"], s["B3"]["decision_ms_p99"],
          s["B3"]["allocator_runs_per_decision_mean"], s["B3"]["allocator_ms_per_run_median"], 20.0 / s["B3"]["allocator_ms_per_run_median"], BENCH["python_peak_mb"]))
    A("")
    A("**Not measured:** the llama.cpp part (time to embed one report, server memory, GPU memory) for f16, Q8_0 and Q4_K_M. Model files: 2.31, 1.23 and 0.75 GiB. "
      "Run on his computer: `python tools\\bench_local.py --llama-dir D:\\llama --models-dir D:\\llama\\models --n 100` (add `--cpu` for CPU only; `pip install psutil` for memory). "
      "The script writes `results/bench_<time>/BENCH.md`; paste it back and the evidence is complete.")
    A("")
    A("## 7. Sample size for the fresh test (estimate from development; the final number is a main-chat decision)")
    A("")
    A("From the DEV paired standard deviation of the per-episode difference (episodes of 20 reports, ~36.7 incidents). Details: `results/iter1/POWER_ITER1.md` and `POWER_ITER1_raw.md`.")
    A("")
    A("| comparison | sd (missed incidents / episode) | effect | episodes for 80% / 90% power |")
    A("|---|---|---|---|")
    import math
    for tag, pairs in (("q4", ("B3-G1", "B3-A1")), ("raw", ("B3-G1", "B3-A1"))):
        for k in pairs:
            recs = {}
            import gzip
            sds = []
            for f in sorted((paths.RESULTS / "iter1" / tag).glob("records_M_s*.json.gz")):
                rr = json.load(gzip.open(f, "rt"))
                m = {}
                for r in rr:
                    m.setdefault(r["arm"], {})[r["episode"]] = r["counts"]["late"] + r["counts"]["unverified"]
                x, y = k.split("-")
                d = [m[x][e] - m[y][e] for e in m[x]]
                mu = sum(d) / len(d)
                sds.append(math.sqrt(sum((v - mu) ** 2 for v in d) / (len(d) - 1)))
            sd = sum(sds) / len(sds)
            for eff in ((0.5, 0.75, 1.0) if tag == "q4" else (1.0, 2.0)):
                dm = eff / 100 * 36.7
                A("| %s, %s | %.2f | %.2f pp | %.0f / %.0f |" % (tag, k, sd, eff, (2.8016 * sd / dm) ** 2, (3.2416 * sd / dm) ** 2))
    A("")
    A("With a competent head the expected effect is about zero, so the fresh test there would be a 'no harm' (non-inferiority) test against a margin that Samadhi and the supervisors must choose; "
      "with the unadapted head the expected effect of B3 over G1 is about 2 pp. 600 episodes (12,000 reports, roughly 65 min of GPU time) gives >= 98% power for a 0.75 pp margin against A1 and "
      "~100% for the unadapted comparison; 1,100 episodes is needed only for a 0.5 pp margin against A1 (95%). The 0.75 pp margin (about 10% of the Q4 missed share) is a choice, not a result.")
    A("")
    A("## 8. Reproducibility repair (Windows)")
    A("")
    A("Samadhi's run (Python 3.12.6, Windows) failed 3 tests: `fork` does not exist on Windows (repaired by the patch the main chat prepared and Samadhi applied (`shield/devrun.py`, `tests/test_windows_spawn.py`; I have not seen those files and my update does not overwrite them); the iteration-1 runner "
      "`shield/devrun2.py` has its own portable pool and a test that serial = spawn), and two comparisons of cached against refitted probabilities. The diagnostic (`diagnosis.json`) shows: the fresh path and the development path give "
      "**identical** probabilities on the same machine (difference 0.0); cached (built elsewhere, Python 3.13.17) against local differ by at most 0.0094 in one probability (q4 action 0.0022), "
      "with **0 changed pilot-style records, 0 changed top records, 0 changed conformal sets** for q4, f16, q8 and recentred, and 1 changed set for the diagnostic raw head; outcomes of A1, A6, A8 on 10 episodes identical. "
      "The cause (lbfgs stops at a slightly different point under another BLAS, tol 1e-6) is consistent with this but not proven. Nothing was loosened silently: the same-machine equality test runs everywhere (1e-12); "
      "the decision-level test (probabilities < 2e-2, records and sets identical) runs everywhere; the bit-for-bit comparison with the cache runs only in the environment that built the cache and is reported as skipped elsewhere. "
      "The cache was not changed (SHA-256 `e5b07161...`).")
    A("")
    A("## 9. Improved / failed / untested")
    A("")
    A("**Improved (DEV, exploratory):** safer certificate; cost-aware fallback; large protection when the head is not adapted; Windows portability; a cleaner statement of what quantisation costs.")
    A("")
    A("**Failed or not shown:** a gain over always-commit or over the equal-footing gate with a competent head (label %s); the pre-specified B3 is worse than the post-hoc A8c on both the competent and the unadapted head; the mass guard and the strict check "
      "do not lower missed share by themselves." % lab["label"])
    A("")
    A("**Untested:** fresh data; llama.cpp speed and memory on Samadhi's computer; CPU backend; the Shield on the recentred head; location cover combined with the new certificate (the most promising untried variant, "
      "needs a second, approved round); chain-mode episodes; a verification queue; another model or real text. **Not built:** `tools/run_fresh.py` still runs the old arms only (devrun, not devrun2); B1-B4 and G1 are not wired into the fresh runner, and there is no fresh demo.")
    A("")
    A("## 10. Decisions needed from the main chat (and supervisors)")
    A("")
    A("1. **Which condition is primary in the fresh test?** (a) competent Q4 only, (b) unadapted Q4 only, (c) both. Recommended (c): competent Q4 as a 'no harm and no gain claimed' test, unadapted Q4 as the superiority test of B3 against G1 and A1. "
      "Disclose that (b) became primary after seeing DEV.")
    A("2. **Which method is frozen?** B3 as registered, with A8c carried as a named secondary arm (it already exists; no new tuning). Or a second round for 'location cover + new certificate' under its own protocol.")
    A("3. **Fresh size and margin** (section 7). Suggested 600 episodes with a 0.75 pp no-harm margin; the main chat decides.")
    A("4. The plan's section 12 questions to the supervisors are still open.")
    A("")
    A("## 11. Files (new in iteration 1)")
    A("")
    A("`docs/ITERATION1_PROTOCOL.md`, `shield/policy2.py`, `shield/devrun2.py`, `tools/run_iter1.py`, `tools/analyze_iter1.py`, `tools/power_iter1.py`, `tools/bench_local.py`, `tools/build_iter1_evidence.py`, `tests/test_iter1.py`, "
      "changed `tests/test_fresh.py` (two-tier numerical tests), `results/iter1/*` (records for q4, f16, q8, raw; ITER1_RESULTS.md/json; POWER files; PROTOCOL.sha256), `results/bench_cloud_shield_only_20261113/`.")
    if TS:
        A("")
        A("Tests: %s" % TS.get("text", ""))
    (paths.HERE / "ITERATION1_EVIDENCE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("written", len(L), "lines")


if __name__ == "__main__":
    main()
