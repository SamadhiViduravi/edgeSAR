"""
Run the FRESH confirmation (milestone M8).  Everything it does is set by the frozen plan; there are no command-line switches for the science.

    python tools/run_fresh.py --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --tag main
    python tools/run_fresh.py --cases ... --vectors ... --tag all
    python tools/run_fresh.py --cases ... --vectors ... --check-only      (all the checks, no simulation)

It STOPS unless:
  1. docs/EVAL_PLAN_FRESH.sha256 exists and the plan and all code are exactly what was frozen (shield/frozen.py);
  2. the cases file is exactly what the frozen seed generates (so nobody picked, dropped or edited a report);
  3. the extraction manifest says OK, names this cases file, and its vector hashes match the .npy files;
  4. the run has not been done before (a repeat needs --rerun-reason, and is written to the run log as a deviation).
Output: results/fresh/<tag>/records_<level>_s<seed>.json.gz, manifest.json  and a line in results/fresh/RUN_LOG.json.
Analyse with:  python tools/analyze_dev.py --base fresh --tag <tag>
"""
import argparse
import gzip
import json
import platform
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shield import devrun, frozen, paths                          # noqa: E402
from shield.sim import SimConfig                                  # noqa: E402

FRESH = paths.RESULTS / "fresh"
MODELS = ("f16", "Q8_0", "Q4_K_M")


def verify_cases(cases_path, P):
    """The cases file must equal the output of the frozen generator seed."""
    import gen_episodes_fresh as gen
    pilot_cases = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
    want, _ = gen.generate(P["fresh_seed"], P["cal_episodes"], P["eval_episodes"], P["R"], pilot_cases)
    got = [json.loads(l) for l in open(cases_path, encoding="utf-8") if l.strip()]
    want = [json.loads(json.dumps(c)) for c in want]
    if got != want:
        n = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
        return ["the cases file is not what the frozen seed %s generates (%d reports in the file, %d expected; first difference at report %d)" %
                (P["fresh_seed"], len(got), len(want), n)]
    return []


def verify_vectors(cases_path, vec_dir):
    vd = Path(vec_dir)
    f = vd / "extraction_manifest.json"
    if not f.exists():
        return ["no extraction_manifest.json in %s" % vd]
    man = json.loads(f.read_text(encoding="utf-8"))
    bad = []
    if man.get("result") != "OK":
        bad.append("the extraction manifest says result = %s (it must be OK)" % man.get("result"))
    cases = [json.loads(l) for l in open(cases_path, encoding="utf-8") if l.strip()]
    if man.get("cases_sha256") != paths.sha256_file(cases_path):
        bad.append("the extraction was made for another cases file (hash differs)")
    ids = [c["id"] for c in cases]
    if man.get("report_ids_sha256") != frozen.sha256_text(",".join(ids)):
        bad.append("the report ids of the extraction differ from the cases file")
    for mk in MODELS:
        meta = man.get("models", {}).get(mk)
        npy = vd / ("%s_end.npy" % mk)
        if not meta:
            bad.append("no extraction record for %s" % mk)
        elif not npy.exists():
            bad.append("%s is missing" % npy.name)
        elif meta.get("vectors_sha256") != paths.sha256_file(npy):
            bad.append("%s differs from the hash in the extraction manifest" % npy.name)
        elif meta.get("n") != len(ids):
            bad.append("%s has %s vectors but the cases file has %d reports" % (npy.name, meta.get("n"), len(ids)))
    fails = [c for c in man.get("checks", []) if c.get("status") == "FAIL"]
    if fails:
        bad.append("the extraction manifest lists FAILED checks: " + "; ".join("%s: %s" % (c["model"], c["text"]) for c in fails))
    return bad


def run_entry(ds, tag, P, run, plan_sha, code_sha, processes, rerun_reason):
    out = FRESH / tag
    if out.exists() and any(out.iterdir()):
        if not rerun_reason:
            sys.exit("STOP. results/fresh/%s already exists. The FRESH run is done once. A repeat needs --rerun-reason '<why>', and is logged as a deviation." % tag)
        old = FRESH / ("%s.superseded-%s" % (tag, time.strftime("%Y%m%d-%H%M%S")))
        shutil.move(str(out), str(old))
    out.mkdir(parents=True, exist_ok=True)
    alpha, K, b = run.get("alpha", P["alpha"]), run.get("K", P["K"]), run.get("b", P["b"])
    d_v, alloc_cost = run.get("d_v", P["d_v"]), run.get("alloc_cost_s", P["alloc_cost_s"])
    allocator, readout = run.get("allocator", P["allocator_default"]), run.get("readout", "q4")
    cfg = SimConfig(d_v=d_v, alloc_cost_s=alloc_cost, decision_timeout_s=P["decision_timeout_s"], dwell=P.get("dwell_s", SimConfig().dwell),
                    deadlines={int(k): float(v) for k, v in P["deadlines_s"].items()})
    arms = run.get("arms") or (devrun.ARM_ORDER + ["OBS"])
    args = {"tag": tag, "levels": run["levels"], "seeds": run["arrival_seeds"], "b": b, "alpha": alpha, "K": K, "allocator": allocator, "d_v": d_v,
            "alloc_cost": alloc_cost, "timeout": P["decision_timeout_s"], "readout": readout, "arms": run.get("arms"), "processes": processes}
    manifest = {"kind": "fresh", "eval_set": run.get("eval_set", "fresh"), "tag": tag, "args": args, "cfg": cfg.__dict__ | {"budget_fraction": b}, "plan_sha256": plan_sha, "code_sha256": code_sha,
                "plan": {k: P[k] for k in ("fresh_seed", "cal_episodes", "eval_episodes", "R")}, "level_gap_s": P["level_gap_s"],
                "python": platform.python_version(), "numpy": __import__("numpy").__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": []}
    for level in run["levels"]:
        for seed in run["arrival_seeds"]:
            t0 = time.time()
            recs, infos = devrun.run_level(ds, level, folds=[0], processes=processes, shards=max(1, processes), alpha=alpha, K=K, b=b, seed=seed,
                                           allocator=allocator, cfg=cfg, arms=arms, readout=readout, gap=P["level_gap_s"][level])
            f = out / ("records_%s_s%d.json.gz" % (level, seed))
            with gzip.open(f, "wt", encoding="utf-8") as fh:
                json.dump(recs, fh, separators=(",", ":"))
            manifest["runs"].append({"level": level, "seed": seed, "records": len(recs), "seconds": round(time.time() - t0, 1), "file": f.name,
                                     "sha256": paths.sha256_file(f), "folds": infos})
            (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
            print("%s: level %s arrival seed %d written (%d records, %.0f s)" % (tag, level, seed, len(recs), time.time() - t0), flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--tag", default="main", help="a run name from the plan's parameter block, or 'all'")
    ap.add_argument("--processes", type=int, default=2)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args()

    fz = frozen.require_freeze()
    P = frozen.plan_params(frozen.plan_text())
    bad = verify_cases(a.cases, P) + verify_vectors(a.cases, a.vectors)
    if bad:
        sys.exit("STOP. Input checks failed:\n  - " + "\n  - ".join(bad))
    print("Freeze intact (plan SHA-256 %s, frozen %s Colombo). Cases and vectors verified." % (fz["plan_sha256"][:16], fz["frozen_at_colombo"]))
    # 'all' = every run of the plan except those marked "hold" (the exploratory style-B check is run by name, after the main report is written)
    tags = [t for t in P["runs"] if not P["runs"][t].get("hold")] if a.tag == "all" else [a.tag]
    for t in tags:
        if t not in P["runs"]:
            sys.exit("STOP. '%s' is not a run in the plan (%s)." % (t, ", ".join(P["runs"])))
    if a.check_only:
        print("All checks passed. Runs in the plan: %s" % ", ".join(P["runs"]))
        return
    from shield.freshset import FreshSet
    sets = {}
    FRESH.mkdir(parents=True, exist_ok=True)
    log_f = FRESH / "RUN_LOG.json"
    log = json.loads(log_f.read_text()) if log_f.exists() else []
    for t in tags:
        entry = {"tag": t, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "plan_sha256": fz["plan_sha256"], "code_sha256": fz["code_sha256"],
                 "rerun_reason": a.rerun_reason, "cases_sha256": paths.sha256_file(a.cases)}
        kind = P["runs"][t].get("eval_set", "fresh")
        if kind not in sets:                                         # the heads are fitted once per kind of evaluation set
            sets[kind] = FreshSet.from_files(a.cases, a.vectors, eval_set=kind)
        run_entry(sets[kind], t, P, P["runs"][t], fz["plan_sha256"], fz["code_sha256"], a.processes, a.rerun_reason)
        entry["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        log.append(entry)
        log_f.write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
