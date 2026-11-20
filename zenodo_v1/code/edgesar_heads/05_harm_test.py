"""
Step 5 of the heads work (EXPLORATORY): the harm test. Needs no model and no server.

    python 05_harm_test.py

It reads the per-report answers that 04_controls.py saved (results_controls\\predictions_end.csv), gives each system's record to the
SAME allocator (the V1 allocation code, simplified CBBA, pinned by hash), flies a simulated mission, and counts what happens to the
real incidents. The rules are in HARM_TEST_PLAN.md. That file and the allocator files are checked against the hashes in
harm_config.json first. If one of them has changed, the run stops.

Writes results_harm\\run_NN\\ (a new folder each time; nothing is overwritten):
  harm_report.md, harm_summary.json, harm_table.csv, per_report_outcomes.csv, per_incident_outcomes.csv, harm_outcome.png
and adds one line to results_harm\\harm_runs.log.

Options
  --bootstrap-file PATH   bootstrap_predictions_end.csv from a later controls run (default: the newest results_controls\\run_*\\ one)
  --allow-changed-plan    run although HARM_TEST_PLAN.md changed after the freeze (writes the DEVIATION into the report and the log)
  --config PATH           another harm_config.json (tests only)
"""
import argparse
import hashlib
import json
import platform
import re
import sys
import time

import numpy as np

import heads_common as hc
from heads_common import HERE, check_pilot_frozen, load_cases, now_text, sha256_file
import harm_lib as hl
import harm_report as hrep


def newest_bootstrap_file():
    cands = sorted((HERE / "results_controls").glob("run_*/bootstrap_predictions_end.csv"))
    return cands[-1] if cands else None


def next_run_dir(root):
    root.mkdir(exist_ok=True)
    nums = [int(m.group(1)) for p in root.iterdir() if (m := re.fullmatch(r"run_(\d+)", p.name))]
    n = (max(nums) + 1) if nums else 1
    d = root / ("run_%02d" % n)
    d.mkdir()
    return d


def stop(msg):
    print("\nSTOP. " + msg)
    sys.exit(2)


def same_runs(a, b):
    """Two sets of runs have identical results (times of compute are not compared)."""
    for cid, ra in a.items():
        rb = b[cid]
        if ra.res["verify_time"] != rb.res["verify_time"] or ra.res["visits"] != rb.res["visits"] or ra.table != rb.table:
            return False
    return True


def jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, float) and (o != o):
        return None
    raise TypeError(type(o))


def clean(o):
    """Replace NaN by None so the json file is valid json."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if o != o else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap-file", default=None)
    ap.add_argument("--allow-changed-plan", action="store_true")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out-root", default=None, help="tests only")
    args = ap.parse_args()
    t_start = time.time()

    cfg_path = args.config or hl.HARM_CONFIG_PATH
    cfg = hl.load_harm_config(cfg_path)
    cfg_sha = hashlib.sha256(open(cfg_path, "rb").read()).hexdigest()
    check_pilot_frozen()

    # ---------------------------------------------------------------- 1. frozen things
    deviations = []
    plan_path = HERE / cfg["plan_file"]
    plan_sha = sha256_file(plan_path)
    if plan_sha != cfg["plan_sha256"]:
        if not args.allow_changed_plan:
            stop("%s is not the frozen plan (its fingerprint differs from harm_config.json).\n"
                 "Do not change a plan after the freeze. If you must, write the reason in your log and run again with "
                 "--allow-changed-plan; the report will say DEVIATION." % cfg["plan_file"])
        deviations.append("PLAN CHANGED after the freeze (now %s, frozen %s)" % (plan_sha[:12], cfg["plan_sha256"][:12]))
    bad = hl.check_allocator_frozen(cfg)
    if bad:
        stop("The allocation code is not the frozen one:\n  " + "\n  ".join(bad))
    pred_path = HERE / cfg["predictions_file"]
    if not pred_path.exists():
        stop("Cannot find %s. Run step 4 first (python 04_controls.py)." % cfg["predictions_file"])
    pred_sha = sha256_file(pred_path)
    if pred_sha != cfg["predictions_sha256"]:
        stop("%s is not the file named in the plan (fingerprint differs). The harm test must use exactly the frozen answers." % cfg["predictions_file"])

    # ---------------------------------------------------------------- 2. data and allocator
    cases = load_cases()
    truths = {c["id"]: hl.truth_of(c) for c in cases}
    A = hl.load_allocator(cfg)
    print("Allocator loaded from %s (frozen hashes match)." % hl.v1_dir(cfg))
    preds, n_rows, mism = hl.load_predictions(pred_path, cases)
    checks = ["plan fingerprint %s" % ("matches" if not deviations else "DIFFERS (deviation)"), "allocator fingerprints match",
              "predictions fingerprint matches", "pilot files are the frozen ones"]
    if mism:
        stop("%d saved records do not match their own record_ok flag. The file cannot be trusted." % mism)
    checks.append("round-trip: all %d saved records agree with their record_ok flag" % n_rows)

    wanted = [a for g in hl.GROUPS for a in cfg["arms"][g]]
    for a in wanted:
        if a not in preds:
            stop("System '%s' is not in %s." % (a, cfg["predictions_file"]))
        if set(preds[a]) != {c["id"] for c in cases}:
            stop("System '%s' does not have exactly one record for every report." % a)
    checks.append("every one of the %d systems has one record for each of the %d reports" % (len(wanted), len(cases)))

    # ---------------------------------------------------------------- 3. flights
    print("Flying the gold-record reference ...")
    gold_norms = {c["id"]: hc.pc.gold_norm(c) for c in cases}
    gold_runs = hl.run_arm(A, cases, truths, gold_norms)
    arm_runs = {}
    for g in hl.GROUPS:
        arm_runs[g] = {}
        for a in cfg["arms"][g]:
            print("Flying %-52s (%s)" % (a, g))
            arm_runs[g][a] = hl.run_arm(A, cases, truths, preds[a])

    # ---------------------------------------------------------------- 4. required checks
    allidx = list(range(len(cases)))
    M0, _ = hl.pair_matrix(A, cfg, cases, truths, gold_runs, gold_runs, allidx)
    s0 = M0.sum(0)
    zero_cols = ["v2u", "u2v", "delay_sum", "l0", "l1", "l2", "l3", "l4", "harmful", "absorbed", "consequential"]
    if any(abs(s0[hl.CI[c]]) > 1e-9 for c in zero_cols):
        stop("The reference compared with itself shows a change. The comparison code is wrong. Do not use any result.")
    checks.append("reference compared with itself: no change at all")
    probe = cfg["arms"]["primary"][-1]
    again = hl.run_arm(A, cases, truths, preds[probe])
    gold_again = hl.run_arm(A, cases, truths, gold_norms)
    if not (same_runs(arm_runs["primary"][probe], again) and same_runs(gold_runs, gold_again)):
        stop("Two identical runs gave different results (not deterministic). Do not use any result.")
    checks.append("two identical runs (reference and %s) give identical results" % probe)

    # ---------------------------------------------------------------- 5. optional bootstrap-sample heads
    bsrc = args.bootstrap_file or (str(newest_bootstrap_file()) if newest_bootstrap_file() else None)
    boot_runs, boot_info = None, None
    if bsrc:
        from pathlib import Path
        bp = Path(bsrc)
        if not bp.is_absolute():
            bp = (HERE / bp) if (HERE / bp).exists() else bp.resolve()
        bsets, seeds, bn, bbad = hl.load_bootstrap(bp, cases)
        if bbad:
            stop("%d records in %s do not match their record_ok flag." % (bbad, bp.name))
        held = [c for c in cases if c["split"] == cfg["primary_split"]]
        boot_runs = {}
        print("Flying %d bootstrap head/vector sets on the %d %s reports ..." % (len(bsets), len(held), cfg["primary_split"]))
        for key, norms in sorted(bsets.items()):
            if set(norms) != {c["id"] for c in held}:
                stop("Bootstrap head %s does not cover exactly the %s reports." % (key, cfg["primary_split"]))
            boot_runs[key] = hl.run_arm(A, held, truths, norms)
        boot_info = {"file": str(bp), "sha256": sha256_file(bp), "rows": bn, "head_vector_sets": len(bsets),
                     "pinned_in_plan": False}
        checks.append("bootstrap-head records round-trip OK (%d rows); file not pinned in the plan" % bn)
    else:
        print("No bootstrap_predictions_end.csv found: the bootstrap-head section is skipped (as the plan says).")

    # ---------------------------------------------------------------- 6. statistics and files
    print("Computing paired family-bootstrap intervals ...")
    S, rep_rows, inc_rows = hl.compute_summary(A, cfg, cases, truths, gold_runs, arm_runs, boot_runs)
    out_root = (hl.OUT_DIR_HARM if not args.out_root else __import__("pathlib").Path(args.out_root))
    run_dir = next_run_dir(out_root)
    hl.write_csv(run_dir / "per_report_outcomes.csv", rep_rows)
    hl.write_csv(run_dir / "per_incident_outcomes.csv", inc_rows)
    hrep.write_table(run_dir / "harm_table.csv", S, cfg)
    ctx = {"created": now_text(), "run_name": run_dir.name, "checks": checks + (["DEVIATION: " + d for d in deviations]),
           "plan_status": "frozen, fingerprint %s" % plan_sha[:12] if not deviations else "CHANGED after freeze: " + "; ".join(deviations)}
    hrep.write_report(run_dir / "harm_report.md", S, cfg, ctx)
    plotted = hrep.write_plot(run_dir / "harm_outcome.png", S, cfg)
    summary = {"created": ctx["created"], "run": run_dir.name, "status": "EXPLORATORY", "plan_file": cfg["plan_file"],
               "plan_sha256": plan_sha, "harm_config_sha256": cfg_sha, "allocator_sha256": cfg["allocator_sha256"],
               "predictions_file": cfg["predictions_file"], "predictions_sha256": pred_sha, "bootstrap_file": boot_info,
               "deviations": deviations, "checks": checks, "settings": {k: cfg[k] for k in (
                   "horizon_s", "dwell_s", "eps_s", "harm_seconds_exploratory", "bootstrap_resamples", "bootstrap_seed", "ci_level",
                   "primary_split", "secondary_splits")},
               "reports": len(cases), "incidents_total": sum(len(t) for t in truths.values()),
               "python": platform.python_version(), "numpy": np.__version__, "result": S}
    (run_dir / "harm_summary.json").write_text(json.dumps(clean(summary), indent=1), encoding="utf-8")
    with open(out_root / "harm_runs.log", "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_dir.name, "time": ctx["created"], "plan_sha256": plan_sha, "harm_config_sha256": cfg_sha,
                            "predictions_sha256": pred_sha, "allocator_sha256": cfg["allocator_sha256"],
                            "bootstrap_file": boot_info, "deviations": deviations, "checks_passed": len(checks),
                            "seconds": round(time.time() - t_start, 1)}) + "\n")

    sp = cfg["primary_split"]
    print("\nWrote %s : harm_report.md, harm_summary.json, harm_table.csv, per_report_outcomes.csv, per_incident_outcomes.csv%s"
          % (run_dir, ", harm_outcome.png" if plotted else " (no plot: matplotlib is not installed)"))
    ref = S["vs_gold"][cfg["arms"]["primary"][0]][sp]
    print("Held-out B: %d real incidents, %d families. Unverified with the gold record: %d."
          % (ref["totals"]["n_truth"], ref["n_families"], ref["totals"]["ref_unver"]))
    for a in cfg["arms"]["primary"]:
        s = S["vs_gold"][a][sp]
        print("  %-12s unverified %3d (%.1f%%)   dU %+.1f points (95%% %+.1f to %+.1f)   V->U %d  U->V %d"
              % (a, s["totals"]["test_unver"], 100 * s["U_test"]["point"], 100 * s["dU"]["point"], 100 * s["dU"]["low"],
                 100 * s["dU"]["high"], s["totals"]["v2u"], s["totals"]["u2v"]))
    print("Open harm_report.md and send it to me.")


if __name__ == "__main__":
    main()
