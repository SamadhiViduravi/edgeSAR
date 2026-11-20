"""
Step 4 of the heads work (EXPLORATORY controls). Needs no model and no server. Run it after step 3.

    python 04_controls.py

It reads features\\*.npy (the same files as step 3) and runs five controls that separate "the model was shrunk" from
"the head was retrained" (see CONTROLS_PLAN.md for the reason of each one):
  1. separate heads   2. fixed head   3. bootstrap-sample heads (training-sample variability)   4. fixed head after an offset fix   5. one shared head
It writes (the attempt-1 folder results_heads\\ is not touched; the first run keeps its files in results_controls\\ and every later run
gets its own folder results_controls\\run_02, run_03, ... so nothing from run 1 is overwritten):
  controls_report.md, controls_summary.json, predictions_<variant>.csv (one row per system and report, with provenance columns),
  bootstrap_predictions_<variant>.csv (every bootstrap head, five vector sets, held-out B), bootstrap_samples.json, provenance.json,
  and a line in results_controls\\controls_attempts.log. A later run also checks that it reproduces the run-1 records.
Time: about 1.5 to 2 times as long as step 3 (my estimate).
Optional:  python 04_controls.py --bootstraps 5     (a quick trial run; the real run uses the number in controls_config.json)
"""
import argparse
import hashlib
import json
import sys

import numpy as np

import heads_common as hc
from heads_common import CFG, CFG_SHA, check_pilot_frozen, load_cases, load_features
import heads_controls as hk
import heads_lib as hl
import controls_report as cr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstraps", type=int, default=None, help="override the number of bootstrap heads (trial runs only)")
    args = ap.parse_args()

    check_pilot_frozen()
    ccfg = hk.load_controls_config()
    ccfg_sha = hashlib.sha256(hk.CONTROLS_CONFIG_PATH.read_bytes()).hexdigest()
    if args.bootstraps is not None:
        ccfg = dict(ccfg, bootstraps=int(args.bootstraps))
        print("TRIAL RUN: %d bootstrap heads instead of the number in controls_config.json." % ccfg["bootstraps"])
    if ccfg.get("heads_config_sha256_expected") and ccfg["heads_config_sha256_expected"] != CFG_SHA:
        print("NOTE: heads_config.json is not the file attempt 1 used (fingerprint %s, expected %s). "
              "Write the reason in your log." % (CFG_SHA[:8], ccfg["heads_config_sha256_expected"][:8]))

    cases = load_cases()
    dev, held = hc.case_split_indexes(cases)
    ids_file = hc.FEAT_DIR / "case_ids.json"
    if not ids_file.exists():
        print("No features yet. Run step 2 first:  python 02_extract.py")
        sys.exit(1)
    if json.loads(ids_file.read_text(encoding="utf-8")) != [c["id"] for c in cases]:
        print("The feature files were made for different cases. Stop.")
        sys.exit(1)

    v = ccfg["variant"]
    X, files_sha = {}, hashlib.sha256()
    for mk in CFG["models"]:
        A = load_features(mk, v)
        if A is None:
            print("missing: %s  (run step 2 first)" % hc.feat_path(mk, v))
            sys.exit(1)
        if A.shape[0] != len(cases) or not np.all(np.isfinite(A)):
            print("bad feature file: %s" % hc.feat_path(mk, v))
            sys.exit(1)
        mp = hc.meta_path(mk, v)
        if mp.exists() and json.loads(mp.read_text(encoding="utf-8")).get("cases_sha256") != hc.FROZEN["data/cases.jsonl"]:
            print("The feature file %s was made from different cases. Stop." % hc.feat_path(mk, v))
            sys.exit(1)
        X[mk] = A
        files_sha.update(hc.sha256_file(hc.feat_path(mk, v)).encode())

    root = hk.OUT_DIR_CONTROLS
    root.mkdir(exist_ok=True)
    log_path = root / "controls_attempts.log"
    prev = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()] if log_path.exists() else []
    run_no = len(prev) + 1
    out_dir = root if run_no == 1 else root / ("run_%02d" % run_no)
    if run_no > 1:
        out_dir.mkdir(exist_ok=False)
    print("Controls run number %d (exploratory; results are logged). Files go to %s" % (run_no, out_dir))

    print("Loading the pilot's own answers (Rule, TF-IDF/LR, generated FP16/Q8/Q4) ...")
    G = {a: hl.generative_decisions(cases, hc.GEN_RUN[mk]) for mk, a in hc.ARM_NAME.items()}
    B = hl.baseline_decisions(cases)

    kept = []
    R, ALL = hk.analyze_controls(cases, dev, held, X["f16"], X["Q8_0"], X["Q4_K_M"], G, B, CFG, ccfg,
                                 attempt1_path=hc.OUT_DIR / "heads_summary.json", say=print, kept_out=kept)
    legacy = root / ("predictions_%s.csv" % v)
    if run_no > 1:
        R["reproduction"] = hk.reproduction_check(ALL, legacy, cases)
        print("Reproduction of the run-1 records: %s (%d different of %d)" % (
            R["reproduction"]["status"], R["reproduction"]["rows_different"], R["reproduction"]["rows_compared"]))
    rows = hk.write_predictions_v2(out_dir / ("predictions_%s.csv" % v), cases, ALL)
    brows = hk.write_bootstrap_predictions(out_dir / ("bootstrap_predictions_%s.csv" % v), cases, held, kept)
    (out_dir / "bootstrap_samples.json").write_text(json.dumps(
        [{k: h[k] for k in ("head_id", "seed", "unique_families", "training_rows", "training_rows_per_family")} for h in kept], indent=1),
        encoding="utf-8")
    import platform
    import sklearn
    prov = hk.build_provenance(cases, dev, held, CFG, ccfg, R, kept, {
        "run": run_no, "folder": str(out_dir.name if run_no > 1 else "results_controls (root, run 1 layout)"),
        "heads_config_sha256": CFG_SHA, "controls_config_sha256": ccfg_sha, "feature_files_sha256_combined": files_sha.hexdigest(),
        "pilot_frozen_files": hc.FROZEN, "python": platform.python_version(), "numpy": np.__version__, "scikit_learn": sklearn.__version__,
        "predictions_file": "predictions_%s.csv" % v, "predictions_sha256": hc.sha256_file(out_dir / ("predictions_%s.csv" % v)),
        "bootstrap_predictions_file": "bootstrap_predictions_%s.csv" % v,
        "bootstrap_predictions_sha256": hc.sha256_file(out_dir / ("bootstrap_predictions_%s.csv" % v)),
        "reproduction_of_run_1": R.get("reproduction")})
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                                             encoding="utf-8")
    text = cr.write_controls_report(R, out_dir / "controls_report.md", ccfg, meta_lines=[
        "Files of this run: `predictions_%s.csv` (with provenance columns), `bootstrap_predictions_%s.csv`, `bootstrap_samples.json`, "
        "`provenance.json` (definitions of the danger errors, what the offset was fitted on, what was matched across precisions)." % (v, v)])
    cr.write_controls_summary(R, out_dir / "controls_summary.json")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_no, "folder": out_dir.name, "reproduces_run_1": (R.get("reproduction") or {}).get("status"), "time": hc.now_text(), "controls_config_sha": ccfg_sha, "heads_config_sha": CFG_SHA,
                            "features_sha": files_sha.hexdigest(), "bootstraps": ccfg["bootstraps"], "check_attempt1": R["attempt1_check"]["status"],
                            "verdicts": R["verdicts"]}, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")

    print("\nWrote %s: controls_report.md, controls_summary.json, predictions_%s.csv (%d rows), bootstrap_predictions_%s.csv (%d rows), "
          "bootstrap_samples.json, provenance.json." % (out_dir, v, rows, v, brows))
    c = R["attempt1_check"]["status"]
    VD = R["verdicts"]
    print("Same numbers as attempt 1: %s" % c)
    print("V1 bootstrap-sample variability  Q4: %s   Q8: %s" % (VD["V1_noise"]["Q4"]["code"], VD["V1_noise"]["Q8"]["code"]))
    print("V2 shared head (Q4): %s   V3 offset removed (Q4): %s" % (VD["V2_shared"]["code"], VD["V3_offset"]["code"]))
    print("Open controls_report.md and send it to me.")
    if c == "DIFFERENT":
        print("WARNING: the numbers are NOT the same as attempt 1. Do not use this report before we find out why.")


if __name__ == "__main__":
    main()
