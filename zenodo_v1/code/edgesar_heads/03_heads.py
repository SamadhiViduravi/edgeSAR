"""
Step 3 of the heads test: train the heads, test them, and write the report. Needs no model and no server.

    python 03_heads.py

Reads features\\*.npy (from step 2), trains the heads (action, sensor, priority) on development style A, and tests them:
  - on style A, out-of-fold (folds grouped by family);
  - on held-out style B, ONCE, with heads trained on all of A.
Then it compares the heads with the pilot's own numbers (Rule, TF-IDF/LR, the generated answers of FP16/Q8/Q4)
and writes results_heads\\heads_report.md, heads_summary.json and a line in attempts.log.
Time: a few minutes (up to about 20, my estimate).
"""
import hashlib
import json
import sys

import numpy as np

import heads_common as hc
from heads_common import CFG, CFG_SHA, check_pilot_frozen, load_cases, load_features
import heads_lib as hl
import heads_report as hr


def main():
    check_pilot_frozen()
    cases = load_cases()
    dev, held = hc.case_split_indexes(cases)
    ids_file = hc.FEAT_DIR / "case_ids.json"
    if not ids_file.exists():
        print("No features yet. Run step 2 first:  python 02_extract.py")
        sys.exit(1)
    if json.loads(ids_file.read_text(encoding="utf-8")) != [c["id"] for c in cases]:
        print("The feature files were made for different cases. Stop.")
        sys.exit(1)

    feats, meta_lines, files_sha = {}, [], hashlib.sha256()
    for mk in CFG["models"]:
        for v in CFG["variants"]:
            X = load_features(mk, v)
            if X is None:
                print("missing: %s" % hc.feat_path(mk, v))
                continue
            if X.shape[0] != len(cases) or not np.all(np.isfinite(X)):
                print("bad feature file: %s" % hc.feat_path(mk, v))
                sys.exit(1)
            feats[(mk, v)] = X
            files_sha.update(hc.sha256_file(hc.feat_path(mk, v)).encode())
            mp = hc.meta_path(mk, v)
            if mp.exists():
                m = json.loads(mp.read_text(encoding="utf-8"))
                if m.get("cases_sha256") != hc.FROZEN["data/cases.jsonl"]:
                    print("The feature file %s was made from different cases. Stop." % hc.feat_path(mk, v))
                    sys.exit(1)
    if not any(k[1] == CFG["primary_variant"] for k in feats):
        print("No features for the main variant '%s'. Run step 2." % CFG["primary_variant"])
        sys.exit(1)

    # attempts log: held-out B is tested once per setting; every run is written down
    hc.OUT_DIR.mkdir(exist_ok=True)
    log_path = hc.OUT_DIR / "attempts.log"
    prev = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()] if log_path.exists() else []
    attempt = len(prev) + 1
    same = [p for p in prev if p.get("config_sha") == CFG_SHA and p.get("features_sha") == files_sha.hexdigest()]
    print("Held-out B attempt number %d.%s" % (attempt, (" The same settings and the same features were already run %d time(s)." % len(same)) if same else ""))
    if prev and not same:
        print("Settings or features are different from earlier attempts. Write the reason in your log (what you changed and why).")

    print("Loading the pilot's own answers (Rule, TF-IDF/LR, generated FP16/Q8/Q4) ...")
    G = {a: hl.generative_decisions(cases, hc.GEN_RUN[mk]) for mk, a in hc.ARM_NAME.items()}
    B = hl.baseline_decisions(cases)

    R = hr.analyze_all(cases, dev, held, feats, G, B, say=print)
    meta_lines = ["Feature files: " + ", ".join("%s_%s" % k for k in sorted(feats)) + "."]
    text = hr.write_report(R, hc.OUT_DIR / "heads_report.md", meta_lines)
    hr.write_summary(R, hc.OUT_DIR / "heads_summary.json")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"attempt": attempt, "time": hc.now_text(), "config_sha": CFG_SHA,
                            "features_sha": files_sha.hexdigest(), "outcomes": R.get("outcomes")}, default=hr.jsonable) + "\n")
    print("\nWrote results_heads\\heads_report.md  (open it, then send it to me)")
    if R.get("outcomes"):
        o = R["outcomes"]
        print("O1 vs TF-IDF/LR: %s   O2 Q4: %s   O2 Q8: %s   O3: %s" % (o["O1"]["vs_tfidf"], o["O2"]["Q4"]["code"], o["O2"]["Q8"]["code"], o["O3"]["code"]))


if __name__ == "__main__":
    main()
