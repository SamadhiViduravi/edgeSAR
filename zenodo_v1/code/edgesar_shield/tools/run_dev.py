"""
Run the development experiment (saved vectors, overlay episodes) and save compact records.

    python tools/run_dev.py --tag main --levels L M H --seeds 1 2 3
    python tools/run_dev.py --tag b30  --levels M --seeds 1 2 3 --b 0.30
    python tools/run_dev.py --tag raw  --levels M --seeds 1 2 3 --readout raw

Output: results/dev/<tag>/records_<level>_s<seed>.json.gz  and  results/dev/<tag>/manifest.json
Everything here is DEVELOPMENT only.  Nothing is tuned on style B.  Seeds change the partition of reports into episodes, the arrival gaps and the
random gate; they do not change the heads.
"""
import argparse
import gzip
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import devrun, paths                                  # noqa: E402
from shield.devset import DevSet                                  # noqa: E402
from shield.sim import SimConfig                                  # noqa: E402


def code_fingerprint():
    h = hashlib.sha256()
    names = sorted(p for p in (paths.HERE / "shield").glob("*.py"))
    for p in names:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--levels", nargs="+", default=["L", "M", "H"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--b", type=float, default=0.10)
    ap.add_argument("--alpha", type=float, default=0.10)
    ap.add_argument("--K", type=int, default=8)
    ap.add_argument("--allocator", default="cbba_bounded")
    ap.add_argument("--d-v", type=float, default=60.0)
    ap.add_argument("--alloc-cost", type=float, default=0.02)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--readout", default="q4", choices=["q4", "raw"])
    ap.add_argument("--arms", nargs="+", default=None)
    ap.add_argument("--folds", nargs="+", type=int, default=None)
    ap.add_argument("--processes", type=int, default=2)
    a = ap.parse_args()

    out = paths.RESULTS / "dev" / a.tag
    out.mkdir(parents=True, exist_ok=True)
    ds = DevSet()
    arms = a.arms or (devrun.ARM_ORDER + ["OBS"])
    cfg = SimConfig(d_v=a.d_v, alloc_cost_s=a.alloc_cost, decision_timeout_s=a.timeout)
    manifest = {"tag": a.tag, "args": vars(a), "cfg": cfg.__dict__ | {"budget_fraction": a.b}, "code_sha256": code_fingerprint(),
                "python": platform.python_version(), "numpy": __import__("numpy").__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cache_sha256": paths.sha256_file(paths.RESULTS / "cache" / "readout_probs.npz"), "runs": []}
    for level in a.levels:
        for seed in a.seeds:
            t0 = time.time()
            recs, infos = devrun.run_level(ds, level, processes=a.processes, alpha=a.alpha, K=a.K, b=a.b, seed=seed, allocator=a.allocator,
                                           cfg=cfg, arms=arms, readout=a.readout, folds=a.folds)
            f = out / ("records_%s_s%d.json.gz" % (level, seed))
            with gzip.open(f, "wt", encoding="utf-8") as fh:
                json.dump(recs, fh, separators=(",", ":"))
            manifest["runs"].append({"level": level, "seed": seed, "records": len(recs), "seconds": round(time.time() - t0, 1), "file": f.name,
                                     "sha256": paths.sha256_file(f), "folds": infos})
            print("%s level %s seed %d: %d records, %.0f s" % (a.tag, level, seed, len(recs), time.time() - t0), flush=True)
            (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    manifest["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
