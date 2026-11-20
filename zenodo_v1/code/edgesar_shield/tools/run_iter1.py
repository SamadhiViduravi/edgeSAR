"""
Run iteration 1 (docs/ITERATION1_PROTOCOL.md) on DEVELOPMENT data and save compact records to results/iter1/<tag>/.

    python tools/run_iter1.py --tag q4  --readout q4
    python tools/run_iter1.py --tag f16 --readout f16 ...

The protocol file is hashed first (results/iter1/PROTOCOL.sha256, created once); a run refuses to start if the protocol changed afterwards.
No fresh data are read here.
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

from shield import devrun2, paths                                  # noqa: E402
from shield.devset import DevSet                                   # noqa: E402
from shield.sim import SimConfig                                   # noqa: E402

PROTOCOL = paths.HERE / "docs" / "ITERATION1_PROTOCOL.md"
HASH_FILE = paths.RESULTS / "iter1" / "PROTOCOL.sha256"


def protocol_hash():
    return hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()


def check_protocol():
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    h = protocol_hash()
    if not HASH_FILE.exists():
        HASH_FILE.write_text("%s  docs/ITERATION1_PROTOCOL.md  hashed %s before the first iteration-1 run\n" % (h, time.strftime("%Y-%m-%d %H:%M:%S")), encoding="utf-8")
    elif HASH_FILE.read_text(encoding="utf-8").split()[0] != h:
        raise SystemExit("the iteration-1 protocol changed after it was hashed. Stop. (A change needs a new protocol file and a new round.)")
    return h


def code_fingerprint():
    h = hashlib.sha256()
    for p in sorted((paths.HERE / "shield").glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--readout", default="q4", choices=["q4", "f16", "q8", "rec", "raw"])
    ap.add_argument("--levels", nargs="+", default=["L", "M", "H"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--b", type=float, default=0.10)
    ap.add_argument("--alpha", type=float, default=0.10)
    ap.add_argument("--K", type=int, default=8)
    ap.add_argument("--d-v", type=float, default=60.0)
    ap.add_argument("--alloc-cost", type=float, default=0.02)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--arms", nargs="+", default=None)
    ap.add_argument("--folds", nargs="+", type=int, default=None)
    ap.add_argument("--processes", type=int, default=4)
    a = ap.parse_args()
    ph = check_protocol()
    out = paths.RESULTS / "iter1" / a.tag
    out.mkdir(parents=True, exist_ok=True)
    ds = DevSet()
    cfg = SimConfig(d_v=a.d_v, alloc_cost_s=a.alloc_cost, decision_timeout_s=a.timeout)
    arms = a.arms or (devrun2.ARM_ORDER2 + ["OBS"])
    man = {"tag": a.tag, "args": vars(a), "cfg": cfg.__dict__ | {"budget_fraction": a.b}, "protocol_sha256": ph, "code_sha256": code_fingerprint(),
           "python": platform.python_version(), "numpy": __import__("numpy").__version__, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
           "cache_sha256": paths.sha256_file(paths.RESULTS / "cache" / "readout_probs.npz"), "runs": []}
    for level in a.levels:
        for seed in a.seeds:
            t0 = time.time()
            recs, infos = devrun2.run_level_v2(ds, level, folds=a.folds, processes=a.processes, alpha=a.alpha, K=a.K, b=a.b, seed=seed, cfg=cfg,
                                               arms=arms, readout=a.readout)
            f = out / ("records_%s_s%d.json.gz" % (level, seed))
            with gzip.open(f, "wt", encoding="utf-8") as fh:
                json.dump(recs, fh, separators=(",", ":"))
            man["runs"].append({"level": level, "seed": seed, "records": len(recs), "seconds": round(time.time() - t0, 1), "file": f.name,
                                "sha256": paths.sha256_file(f), "folds": infos})
            print("%s level %s seed %d: %d records, %.0f s" % (a.tag, level, seed, len(recs), time.time() - t0), flush=True)
            (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    man["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
