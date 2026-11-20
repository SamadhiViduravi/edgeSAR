"""Cross-fit the heads on the saved vectors and cache the probabilities (deterministic: no random seed in head training)."""
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import paths, readout as R                      # noqa: E402
from shield.data import DevData                              # noqa: E402


def main():
    out = paths.RESULTS / "cache" / "readout_probs.npz"
    D = DevData()
    log = R.FitLog()
    t0 = time.time()
    folds = R.cross_fit(D, log, verbose=True)
    R.save_cache(out, folds, log)
    info = {"seconds": round(time.time() - t0, 1), "fold_fingerprint": D.fingerprint(), "purged_per_fold": D.purged, "fit_log": log.as_dict(),
            "sklearn": __import__("sklearn").__version__, "numpy": __import__("numpy").__version__, "python": sys.version.split()[0]}
    (paths.RESULTS / "cache" / "readout_probs.info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
