"""
Make the Q8_0 and Q4_K_M files from the F16 file with llama-quantize (same tool, same weights, no importance matrix).
Do NOT download ready-made Q8/Q4 files from the internet: they may be made with different settings,
and then a difference between models could come from the recipe and not from the precision.

  python make_quants.py
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, load_config


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    bin_dir = Path(cfg["paths"]["llama_bin_dir"])
    models_dir = Path(cfg["paths"]["models_dir"])
    exe = None
    for name in ("llama-quantize.exe", "llama-quantize"):
        if (bin_dir / name).exists():
            exe = bin_dir / name
    if exe is None:
        sys.exit("llama-quantize not found in %s. Check paths.llama_bin_dir in config.json." % bin_dir)
    src = models_dir / cfg["models"]["f16"]
    if not src.exists():
        sys.exit("F16 model file not found: %s\nDownload it first (see README step 3)." % src)
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    for key, fname in cfg["models"].items():
        if key == "f16":
            continue
        out = models_dir / fname
        if out.exists():
            print("%-8s exists, skipping: %s" % (key, out))
            continue
        print("%-8s making %s ..." % (key, out.name))
        t0 = time.time()
        log = open(ROOT / "logs" / ("quantize_%s.log" % key), "w", encoding="utf-8", errors="replace")
        r = subprocess.run([str(exe), str(src), str(out), key], stdout=log, stderr=subprocess.STDOUT, cwd=str(exe.parent))
        log.close()
        if r.returncode != 0 or not out.exists():
            sys.exit("llama-quantize failed for %s. Read logs/quantize_%s.log" % (key, key))
        print("         done in %.0f s, %.2f GB" % (time.time() - t0, out.stat().st_size / 1e9))
    hashes = {}
    for key, fname in cfg["models"].items():
        p = models_dir / fname
        if p.exists():
            hashes[key] = {"file": fname, "bytes": p.stat().st_size, "sha256": sha256(p)}
    json.dump(hashes, open(ROOT / "results" / "model_hashes.json", "w", encoding="utf-8"), indent=2)
    print("File sizes and checksums saved to results/model_hashes.json")


if __name__ == "__main__":
    main()
