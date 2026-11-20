"""
Step 6 (EXPLORATORY): a small demo that you can run in one command.

    python 06_demo.py

For one report it shows the whole chain that IS implemented:
    report text -> the record a system wrote -> the task table -> who flies where (simplified CBBA) -> what is verified
and compares it with the same report when the allocator gets the GOLD (correct) record.
With no options it picks, from held-out style B, the FIRST case (in id order) of each kind for the system "Heads Q4":
    * an ABSORBED change   (the record is wrong, the task table differs, but every real incident is verified as before)
    * a CONSEQUENTIAL change (the task table differs and a verification changes)
These two cases are only ILLUSTRATIONS. They are not chosen to be typical. The counts that say how common each kind is are printed
under them, for the same system and split.

Options
    --arm "Heads FP16"      which system's saved records to use (any system name in predictions_end.csv)
    --ref "Heads FP16"      compare with another system instead of the gold-record reference
    --case c0123            show this case id (then --arm decides the system)
    --split held|dev        where to look for the examples (default held)

NOT implemented (planned): candidate-set construction, the Shield gate, Cover, closed-loop missions, full multi-task CBBA.
Nothing in this demo is mocked: every number comes from the saved answers and the real allocation code.
"""
import argparse
import csv
import sys

import heads_common as hc
from heads_common import HERE, check_pilot_frozen, load_cases, sha256_file
import harm_lib as hl


def fmt_norm(n):
    if n["action"] == "NO_ACTION":
        return "NO_ACTION"
    bits = [n["action"]]
    if "incident" in n:
        bits.append("incident " + str(n["incident"]))
    if "landmark" in n:
        bits.append("%s, sensor %s, priority %s" % (n["landmark"], n["sensor"], n["priority"]))
    return "  ".join(bits)


def fmt_table(table):
    if not table:
        return "  (empty)"
    return "\n".join("  %-4s %-17s sensor %-7s priority %s" % (t["id"], t["landmark"], t["sensor"], t["priority"]) for t in table)


def show_run(title, run, truth, H):
    L = [title, "  Tasks given to the allocator:", fmt_table(run.table), "  Flights (simulated):"]
    for v in sorted(run.res["visits"], key=lambda v: (v["start"], v["uav"])):
        L.append("    %s  leaves at %6.1f s  arrives %6.1f s  finishes %6.1f s  -> %-17s [%s]"
                 % (v["uav"], v["start"], v["arrive"], v["finish"], v["landmark"], v["result"]))
    if not run.res["visits"]:
        L.append("    (no UAV flies)")
    L.append("  Real incidents:")
    for l, need in sorted(truth.items()):
        t = run.res["verify_time"].get(l)
        ok = t is not None and t <= H
        L.append("    %-17s camera needed %-7s -> %s" % (l, need, ("verified at %.1f s" % t) if ok else "NOT verified by %d s" % H))
    return "\n".join(L)


def story(A, cfg, case, truth, ref, test, ref_name, arm_name, conf_row):
    M, cmps = hl.pair_vector(A, cfg, ref, test, truth)
    v = dict(zip(hl.COLS, M))
    cls = "table unchanged" if not v["l1"] else ("CONSEQUENTIAL" if v["l4"] else "ABSORBED")
    L = ["=" * 78, "Case %s  (split %s, family %s)" % (case["id"], case["split"], case["family"]), "=" * 78,
         "REPORT (time %s, source %s):" % (case["time"], case["source"]), "  " + case["text"],
         "Open incidents before this report:", fmt_table(case["open"]), "",
         "GOLD record (correct):   " + fmt_norm(hc.pc.gold_norm(case)),
         "%s wrote: %s" % (arm_name, fmt_norm(test.norm)) + ("   (confidence %s)" % conf_row["confidence"] if conf_row and conf_row.get("confidence") else ""),
         "Record equals gold: %s" % ("yes" if test.norm == ref.norm and ref_name == hl.GOLD_NAME else ("no" if ref_name == hl.GOLD_NAME else "n/a")), "",
         show_run("--- Allocator with the %s record ---" % ref_name, ref, truth, A.H), "",
         show_run("--- Allocator with the %s record ---" % arm_name, test, truth, A.H), "",
         "RESULT: record differs: %s | task table differs: %s | assignment differs: %s | route differs: %s | verification differs: %s"
         % tuple("yes" if v[k] else "no" for k in ("l0", "l1", "l2", "l3", "l4")),
         "        class: %s | real incidents verified with %s but not with %s: %d | the other way: %d"
         % (cls, ref_name, arm_name, v["v2u"], v["u2v"]), ""]
    return "\n".join(L), cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="Heads Q4")
    ap.add_argument("--ref", default=hl.GOLD_NAME)
    ap.add_argument("--case", default=None)
    ap.add_argument("--split", default="held")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out-dir", default=None, help="tests only")
    args = ap.parse_args()

    cfg = hl.load_harm_config(args.config)
    check_pilot_frozen()
    bad = hl.check_allocator_frozen(cfg)
    if bad:
        print("STOP. The allocation code is not the frozen one:\n  " + "\n  ".join(bad))
        sys.exit(2)
    pred_path = HERE / cfg["predictions_file"]
    if sha256_file(pred_path) != cfg["predictions_sha256"]:
        print("NOTE: %s is not the file named in the plan. The demo still runs, but its numbers are not those of the frozen harm test."
              % cfg["predictions_file"])
    cases = load_cases()
    A = hl.load_allocator(cfg)
    preds, _, mism = hl.load_predictions(pred_path, cases)
    if mism:
        print("STOP. %d saved records do not match their own record_ok flag." % mism)
        sys.exit(2)
    for name in (args.arm,) + (() if args.ref == hl.GOLD_NAME else (args.ref,)):
        if name not in preds:
            print("Unknown system '%s'. Systems in the file: %s" % (name, "; ".join(sorted(preds))))
            sys.exit(1)
    conf = {}
    with open(pred_path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["system"] == args.arm:
                conf[r["case_id"]] = r
    truths = {c["id"]: hl.truth_of(c) for c in cases}
    gold_norms = {c["id"]: hc.pc.gold_norm(c) for c in cases}
    ref_norms = gold_norms if args.ref == hl.GOLD_NAME else preds[args.ref]
    pool = [c for c in cases if c["split"] == args.split]
    ref_runs = hl.run_arm(A, pool, truths, ref_norms)
    arm_runs = hl.run_arm(A, pool, truths, preds[args.arm])

    chosen = []
    if args.case:
        c = next((c for c in cases if c["id"] == args.case), None)
        if c is None:
            print("Unknown case id %s" % args.case)
            sys.exit(1)
        if c["split"] != args.split:
            pool = [c]
            ref_runs = hl.run_arm(A, pool, truths, ref_norms)
            arm_runs = hl.run_arm(A, pool, truths, preds[args.arm])
        chosen = [c]
    count = {"table unchanged": 0, "ABSORBED": 0, "CONSEQUENTIAL": 0}
    first = {}
    for c in pool:
        v, cmp = hl.pair_vector(A, cfg, ref_runs[c["id"]], arm_runs[c["id"]], truths[c["id"]])
        d = dict(zip(hl.COLS, v))
        k = "table unchanged" if not d["l1"] else ("CONSEQUENTIAL" if d["l4"] else "ABSORBED")
        count[k] += 1
        first.setdefault(k, c)
    if not args.case:
        chosen = [first[k] for k in ("ABSORBED", "CONSEQUENTIAL") if k in first]
        if not chosen:
            print("No absorbed or consequential change for %s on split %s." % (args.arm, args.split))

    out = ["EdgeSAR demo (EXPLORATORY). System: %s. Reference: %s." % (args.arm, args.ref),
           "Implemented: report -> record -> task table -> simplified CBBA (3 UAVs) -> simulated verification (12 s visit, 600 s horizon).",
           "Planned, NOT implemented here: candidate-set construction, Shield gate, Cover, closed-loop missions, full CBBA.",
           "The cases below are ILLUSTRATIONS (the first of their kind in id order), not typical cases.", ""]
    for c in chosen:
        text, _ = story(A, cfg, c, truths[c["id"]], ref_runs[c["id"]], arm_runs[c["id"]], args.ref, args.arm, conf.get(c["id"]))
        out.append(text)
    n = len(pool)
    out.append("-" * 78)
    out.append("How common is each kind? %s on split %s (%d reports): task table unchanged %d, ABSORBED %d, CONSEQUENTIAL %d."
               % (args.arm, args.split, n, count["table unchanged"], count["ABSORBED"], count["CONSEQUENTIAL"]))
    out.append("Absorbed = the table differs from the reference but every real incident is verified as before (within %.1f s)." % cfg["eps_s"])
    out.append("Consequential = the table differs and a verification changes (later/earlier by more than %.1f s, or a miss appears or goes)." % cfg["eps_s"])
    out.append("The full numbers with intervals are in results_harm\\run_NN\\harm_report.md (python 05_harm_test.py).")
    text = "\n".join(out) + "\n"
    print(text)
    dest = __import__("pathlib").Path(args.out_dir) if args.out_dir else HERE / "results_harm"
    dest.mkdir(exist_ok=True)
    (dest / "demo_cases.md").write_text("```text\n" + text + "```\n", encoding="utf-8")
    print("Also written to results_harm\\demo_cases.md")


if __name__ == "__main__":
    main()
