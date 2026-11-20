"""PROTOCOL_WORDING_SHIFT.md: the saved style-B predictions (new wording) through the SAME mission simulator, at three load levels.
Exploratory. Nothing is refitted, extracted or tuned; the saved records are used exactly as saved.

   python wording_shift_mission.py --release <unzipped EdgeSAR_dataset_release_v1.0 folder> --out out_new
   (needs only the public release and this supplement; numpy, scipy, scikit-learn; about 1 minute)

Step 1 checks the preconditions (P1 to P7) and writes WORDING_SHIFT_AUDIT.md. If a hard precondition fails the run stops (exit code 3) and the audit
names the missing prerequisite. Step 2 runs the missions and writes WORDING_SHIFT_RESULTS.md, results.json and the per-episode records."""
import argparse, csv, gzip, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SUPP = HERE.parent                                   # the supplement root (holds practical_advantage/ and repair_package/)
sys.path.insert(0, str(HERE))
from text_baselines_mission import by_arm, paired_w, share_w          # noqa: E402  (same weighted-outcome helpers as the style-A baseline run)

LEVELS, SEEDS = "LMH", (1, 2, 3)
PRIMARY = {"tfidf": ("out", "TFIDF"), "rule": ("out", "RULES"), "f16p": ("out2", "REFp"), "q4p": ("out2", "MATCHEDp"),
           "recp": ("out2", "C1p"), "alnp": ("out2", "C2p"), "rawp": ("out2", "FROZENp")}
SECOND = {"f16": ("out", "REF"), "q4": ("out", "MATCHED"), "rec": ("out", "C1"), "aln": ("out", "C2"), "raw": ("out", "FROZEN")}
ARMS = {**PRIMARY, **SECOND}
NAMES = {"gold": "Gold records", "tfidf": "TF-IDF + LR (text)", "rule": "Keyword rule engine (text)",
         "f16p": "F16 reader", "q4p": "Q4 retrained, 1,000 labels", "recp": "Q4 recentred", "alnp": "Q4 label-free map", "rawp": "Q4 unchanged transfer",
         "f16": "F16 reader (end)", "q4": "Q4 retrained (end)", "rec": "Q4 recentred (end)", "aln": "Q4 label-free map (end)", "raw": "Q4 unchanged (end)"}
PAIRS_P = [("tfidf", "f16p"), ("tfidf", "q4p"), ("tfidf", "recp"), ("tfidf", "alnp"), ("tfidf", "gold"), ("rule", "f16p"), ("rule", "q4p"), ("rule", "recp"),
           ("rule", "alnp"), ("rule", "gold"), ("tfidf", "rule"), ("f16p", "q4p"), ("alnp", "q4p"), ("alnp", "recp"), ("recp", "q4p"), ("f16p", "gold")]
PAIRS_E = [("tfidf", "f16"), ("tfidf", "q4"), ("tfidf", "rec"), ("tfidf", "aln"), ("rule", "f16"), ("rule", "q4"), ("rule", "rec"), ("rule", "aln"),
           ("aln", "q4"), ("aln", "rec"), ("rec", "q4"), ("f16", "q4")]
KEYCOLS = ("action", "incident", "landmark", "sensor", "priority")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def load_pred(path):
    """{saved arm name: {case_id: key tuple}} for protocol B, labels all."""
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["protocol"] != "B" or r["labels"] != "all":
                continue
            key = tuple(None if r[c] == "" else (int(r[c]) if c == "priority" else r[c]) for c in KEYCOLS)
            d = out.setdefault(r["arm"], {})
            if r["case_id"] in d:
                d[r["case_id"]] = "DUPLICATE ROW"
            else:
                d[r["case_id"]] = key
    return out


def key_to_norm(key):
    return {c: v for c, v in zip(KEYCOLS, key) if v is not None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True); ap.add_argument("--out", required=True); ap.add_argument("--max-episodes", type=int, default=None)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t_all = time.time()
    psha = sha(HERE / "PROTOCOL_WORDING_SHIFT.md")
    (out / "PROTOCOL.sha256").write_text(psha + "  PROTOCOL_WORDING_SHIFT.md\n")
    import release_only
    release_only.prepare(a.release, out / "_release_work")
    os.environ["EDGESAR_ROOT"] = str((out / "_release_work").resolve())
    sys.path.insert(0, str(Path(a.release).resolve() / "code" / "edgesar_shield"))
    from shield import devrun, paths                                   # noqa: E402
    release_only.skip_vector_pins()
    from shield import data                                            # noqa: E402
    from shield.alloc import make_allocator                            # noqa: E402
    from shield.candidates import pilot                                # noqa: E402
    from shield.episodes import EPISODE_REPORTS, make_episodes         # noqa: E402
    from shield.policy import CommitPolicy                             # noqa: E402
    from shield.service import Service                                 # noqa: E402
    from shield.sim import Sim, SimConfig                              # noqa: E402
    from types import SimpleNamespace
    pc, pb = pilot()
    cases = data.load_cases(); cid = [c["id"] for c in cases]; byid = {c["id"]: c for c in cases}
    A = [c["id"] for c in cases if c["style"] == "A"]; B = [c["id"] for c in cases if c["style"] == "B"]
    gold_key = {i: pc.strict_key(pc.gold_norm(byid[i])) for i in cid}

    # ================================================================== step 1: preconditions and audit
    audit, problems = [], []
    md = ["# Wording-shift check: audit of the saved style-B predictions", "", "Protocol hash `%s` (PROTOCOL_WORDING_SHIFT.md). Exploratory; style B has been inspected many times." % psha, ""]

    # P1 integrity
    sums = {}
    for line in (SUPP / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, p = line.split(None, 1); sums[p.strip().lstrip("*").lstrip("./")] = h
    files = ["repair_package/out/predictions.csv", "repair_package/out2/predictions.csv", "repair_package/out/fold_log.json", "repair_package/out2/fold_log.json"]
    md += ["## P1 File integrity", "", "| File | SHA-256 (first 16) | Equals CHECKSUMS.sha256 |", "|---|---|---|"]
    ok1 = True
    for f in files:
        h = sha(SUPP / f); good = sums.get(f) == h; ok1 &= good
        md.append("| %s | %s | %s |" % (f, h[:16], "yes" if good else "NO"))
    md.append("| data/cases.jsonl (release; CRLF form is the pinned experiment file) | 833fafe2fb47af9a | yes (checked by release_only.py) |")
    md.append("")
    if not ok1: problems.append("P1: a saved prediction or fold-log file differs from CHECKSUMS.sha256")

    P = {}
    for d in ("out", "out2"):
        P[d] = load_pred(SUPP / "repair_package" / d / "predictions.csv")
    logs = {d: json.loads((SUPP / "repair_package" / d / "fold_log.json").read_text(encoding="utf-8")) for d in ("out", "out2")}

    # P2 coverage
    md += ["## P2 Coverage (one row per style-B report, no style-A report)", "", "| Arm in this check | Saved name | Rows | Covers exactly the 400 style-B reports |", "|---|---|---|---|"]
    ok2 = True
    pred = {}
    for arm, (d, name) in ARMS.items():
        rows = P[d].get(name, {})
        good = set(rows) == set(B) and len(rows) == 400 and "DUPLICATE ROW" not in rows.values()
        ok2 &= good; pred[arm] = rows
        md.append("| %s | %s (%s) | %d | %s |" % (arm, name, "text only" if arm in ("tfidf", "rule") else "prefix" if d == "out2" else "end", len(rows), "yes" if good else "NO"))
    md.append("")
    if not ok2: problems.append("P2: an arm does not cover exactly the 400 style-B reports")

    # P3 training data and label budget
    md += ["## P3 Training data and label budget", ""]
    ok3 = True
    tf_rows = []
    for d, tag in (("out", "end"), ("out2", "prefix")):
        b = [l for l in logs[d]["folds"] if l["proto"] == "B"]
        good = len(b) == 1 and b[0]["n_lab"] == 1000 and b[0]["n_bank"] == 1000 and b[0]["n_test"] == 400
        ok3 &= good
        tf_rows.append("* fold log `%s` (%s): style-B task has n_lab %s, n_bank %s, n_test %s (%s)." % (d, tag, *(b[0][k] for k in ("n_lab", "n_bank", "n_test")), "as required" if good else "NOT as required"))
    md += tf_rows
    md.append("* The 1,000 training reports are the 1,000 style-A reports (script `run_ppr.py`: `A = split == dev`, `tr = A`, `lab = tr` for protocol B; all supervised arms use `lab`). "
              "The test reports are the 400 style-B reports (`B = split == held`). %d style-A and %d style-B reports in the release." % (len(A), len(B)))
    # TF-IDF refit as a consistency check (same code, same 1,000 reports; the SAVED predictions are the ones used)
    tf = pb.LRBaseline().fit([byid[i] for i in A])
    refit = [pc.validate(d_, byid[i])[0] for i, d_ in zip(B, tf.predict([byid[i] for i in B]))]
    same = sum(pc.strict_key(n) == pred["tfidf"][i] for i, n in zip(B, refit))
    md.append("* Consistency check: refitting the pilot TF-IDF classifier on the 1,000 style-A reports and predicting the 400 style-B reports reproduces the saved TF-IDF records in %d of 400 reports. "
              "The rule engine has no fitted part; recomputing it reproduces the saved rule records in %d of 400." %
              (same, sum(pc.strict_key(pc.validate(pb.rule_decision(byid[i]), byid[i])[0]) == pred["rule"][i] for i in B)))
    md.append("* Label budget: TF-IDF, F16 reader and Q4 retrained each use all 1,000 style-A labels. Recentring and the map reuse the F16 reader (1,000 labels) and add unlabelled F16-Q4 pairs of the same 1,000 reports. The rule engine uses no labels. "
              "**No 100- or 300-label arms exist for style B** (only `labels = all`), so a label-budget curve on style B is not available.")
    md.append("")
    if not ok3: problems.append("P3: the style-B training protocol is not 1,000 labels / 1,000 pairs / 400 test reports")

    # P4 duplicates
    textsA = {byid[i]["text"] for i in A}
    overlap = [i for i in B if byid[i]["text"] in textsA]
    from collections import Counter
    cB = Counter(byid[i]["text"] for i in B); dupB = {t: n for t, n in cB.items() if n > 1}
    md += ["## P4 Duplicate handling", "",
           "* Style-B reports whose text equals any style-A report text: **%d** (so training on style A cannot have seen a style-B text; no purge is needed)." % len(overlap),
           "* Style-B internal duplicate texts: %d groups covering %d reports (they count twice in style-B totals; they are all in the test side, never used for fitting)." % (len(dupB), sum(dupB.values())), ""]
    if overlap: problems.append("P4: %d style-B texts also occur in style A (a purge would be needed)" % len(overlap))

    # P5 record parity and P6 assembler parity
    md += ["## P5 / P6 Record parity and assembler parity", "", "| Arm | Records rebuilt as valid and equal to the saved key | Equal to the common assembler's record from the saved action / sensor / priority |", "|---|---|---|"]
    ok5 = True; norm = {}
    for arm in ARMS:
        n5 = n6 = 0; norm[arm] = {}
        for i in B:
            k = pred[arm][i]; nm = key_to_norm(k)
            v, st = pc.validate(nm, byid[i]); good5 = st == "ok" and v == nm and pc.strict_key(nm) == k
            n5 += good5; norm[arm][i] = nm
            act = k[0]; s = k[3] if k[3] is not None else "ANY"; p = k[4] if k[4] is not None else 2
            rebuilt, _ = pc.validate(pb._assemble(byid[i], act, s, int(p)), byid[i])
            n6 += pc.strict_key(rebuilt) == k
        ok5 &= n5 == 400
        md.append("| %s | %d / 400 | %d / 400 |" % (arm, n5, n6))
    md += ["", "(P5 must be 400 / 400 for every arm. P6 is information for the two text arms; for the hidden-vector arms the saved records were built with the same assembler.)", ""]
    if not ok5: problems.append("P5: a saved record cannot be rebuilt as a valid record")

    # P7 input information
    md += ["## P7 What each arm sees (information)", "",
           "| Arm | Report text | Open-incident table | Labels used | Fitting / adaptation data |", "|---|---|---|---|---|",
           "| hidden-vector arms | in the prompt | the full list, in the prompt | F16 reader, Q4 retrained: 1,000 | F16 / Q4 vectors of the 1,000 style-A reports |",
           "| TF-IDF | yes | a summary: number open, target found, its sensor and priority, id mentioned | 1,000 | the 1,000 style-A texts |",
           "| rules | yes | target found by string matching | 0 | none (code frozen 28 Oct 2026, hash e410b94c...) |",
           "| recentring, map | in the prompt | in the prompt | 1,000 (through the F16 reader) | unlabelled F16-Q4 pairs of the 1,000 style-A reports |", "",
           "Landmark and incident link come from the same string-matching assembler for every arm. Heads for style B were fitted by `ppr_lib.fit_head` (grouped by template); the style-A mission arms used `shield/readout.py` (grouped by family): same recipe, different code path.", ""]

    # record-level accuracy
    md += ["## Decision accuracy on the 400 style-B reports (saved predictions)", "", "| Arm | Whole record right | Action right |", "|---|---|---|"]
    acc = {}
    for arm in ARMS:
        w = sum(pred[arm][i] == gold_key[i] for i in B); ac = sum(pred[arm][i][0] == gold_key[i][0] for i in B); acc[arm] = {"record": w, "action": ac, "n": 400}
        md.append("| %s | %d / 400 (%.1f%%) | %d / 400 (%.1f%%) |" % (NAMES[arm], w, 100 * w / 400, ac, 100 * ac / 400))
    md += ["", "Cross-check with the earlier record-level report (heads package attempt 1 and the pilot, same 400 reports; `audit04_report.md` in the release): TF-IDF 53.5%, F16 heads 70.8%, Q4 heads 66.5% whole record right; rule engine 50.7% (pilot). "
           "TF-IDF and rules reproduce. The F16 and Q4 heads of this check (`ppr_lib.fit_head`, refitted in the repair experiment) give 72.0% and 67.0% at `end`, i.e. +1.2 and +0.5 points: a different fitting code path (template-grouped selection of C, different folds); the cause of the difference was not investigated. "
           "The mission check uses the repair-experiment records, because they are the ones that contain the recentring and map arms.", ""]
    res = {"protocol_sha256": psha, "problems": problems, "accuracy_B": acc, "style_B_text_overlap_with_A": len(overlap), "style_B_duplicate_groups": len(dupB),
           "tfidf_refit_reproduces": same}
    if problems:
        md += ["## STOP", "", "A hard precondition failed. The mission run was not done. Missing prerequisite(s):", ""] + ["* " + p for p in problems]
        (out / "WORDING_SHIFT_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8"); (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print("\n".join(md)); sys.exit(3)
    md += ["## Result of the preconditions", "", "P1 to P5 hold. P6 and P7 are information. The mission run follows (20 episodes of 20 reports per level and arrival seed; the three arrival seeds reuse the same 400 reports, so the 60 episodes per level are not independent).", ""]
    (out / "WORDING_SHIFT_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)

    # ================================================================== step 2: missions
    svc = {}
    for arm in ARMS:
        cands, hier, conf = {}, {}, {}
        for i in B:
            nm = norm[arm][i]; c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i] = [c]; hier[i] = c; conf[i] = 1.0
        svc[arm] = Service(cands, hier, conf)
    ds = SimpleNamespace(cases=cases)
    idxB = [k for k, c in enumerate(cases) if c["style"] == "B"]
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    recs = {lev: [] for lev in LEVELS}
    for lev in LEVELS:
        for seed in SEEDS:
            t0 = time.time(); srecs = []
            eps = make_episodes(ds, idxB, lev, seed * 1000, EPISODE_REPORTS)
            if a.max_episodes: eps = eps[:a.max_episodes]
            for e in eps:
                srecs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), 0, lev, seed))
                for arm in ARMS: srecs.append(devrun.compact(sim.run(e, CommitPolicy(svc[arm]), arm), 0, lev, seed))
            with gzip.open(out / ("records_%s_s%d.json.gz" % (lev, seed)), "wt", encoding="utf-8") as fh: json.dump(srecs, fh, separators=(",", ":"))
            recs[lev] += srecs; print("level %s seed %d: %d episodes, %d records in %.0f s" % (lev, seed, len(eps), len(srecs), time.time() - t0), flush=True)

    # replay consistency: where the saved record equals gold the simulator must see table and plan equal to gold
    viol = 0; chk = 0
    for lev in LEVELS:
        for r in recs[lev]:
            if r["arm"] == "gold": continue
            for rep in r["reports"]:
                if pred[r["arm"]][rep["id"]] == gold_key[rep["id"]]:
                    chk += 1; viol += not (rep["tg"] and rep["pg"])
    res["replay_consistency"] = {"reports_checked": chk, "violations": viol}

    md = ["# Wording-shift check at mission level: results", "",
          "Exploratory. Style B (new wording, 400 reports) has been inspected many times; nothing is chosen with it. Frozen predictions from heads and a TF-IDF classifier fitted on all 1,000 style-A reports; "
          "bounded CBBA, always commit; 20 episodes of 20 reports per level and arrival seed (60 per level); gaps set on style A. Protocol hash `%s`." % psha,
          "Pooled intervals are optimistic (the three arrival seeds reuse the same 400 reports). Replay consistency: %d reports whose saved record equals gold were checked, %d violations (%s)." % (chk, viol, "PASS" if viol == 0 else "FAIL"), ""]
    res["levels"] = {}
    for panel, arms, pairs in (("PRIMARY panel: reading position `prefix`", ["tfidf", "rule", "f16p", "q4p", "recp", "alnp", "rawp"], PAIRS_P),
                               ("SECOND panel: reading position `end`", ["tfidf", "rule", "f16", "q4", "rec", "aln", "raw"], PAIRS_E)):
        md += ["# " + panel, ""]
        for lev in LEVELS:
            rs = [r for r in recs[lev] if r["arm"] == "gold" or r["arm"] in arms]; by = by_arm(rs)
            res["levels"].setdefault(lev, {"arms": {}, "paired": {}})
            md += ["## Level %s" % lev, "", "| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |", "|---|---|---|---|---|"]
            for arm in ["gold"] + arms:
                eps_ = list(by[arm].values()); m = sum(r["counts"]["late"] + r["counts"]["unverified"] for r in eps_); n = sum(r["counts"]["n"] for r in eps_)
                lo, hi = devrun.episode_bootstrap_ci(rs, arm); w, wlo, whi = share_w(by, arm)
                res["levels"][lev]["arms"][arm] = {"missed": m, "incidents": n, "share": m / n, "ci": [lo, hi], "w_share": w, "w_ci": [wlo, whi], "episodes": len(eps_)}
                md.append("| %s | %.2f%% | %.2f to %.2f | %.2f%% | %.2f to %.2f |" % (NAMES[arm], 100 * m / n, 100 * lo, 100 * hi, 100 * w, 100 * wlo, 100 * whi))
            md += ["", "| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |", "|---|---|---|---|"]
            for x, y in pairs:
                p = devrun.paired(rs, x, y); pw = paired_w(by, x, y); res["levels"][lev]["paired"]["%s-%s" % (x, y)] = {"ordinary": p, "weighted": pw}
                md.append("| %s minus %s | %+.2f (%+.2f to %+.2f) | %d / %d / %d | %+.2f (%+.2f to %+.2f) |" % (x, y, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["wins_x"], p["wins_y"], p["ties"],
                         100 * pw["diff"], 100 * pw["ci"][0], 100 * pw["ci"][1]))
            md.append("")
    md += ["Total run time %.0f s." % (time.time() - t_all)]
    (out / "WORDING_SHIFT_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))
    if viol: sys.exit(2)


if __name__ == "__main__":
    main()
