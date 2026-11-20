"""
Are the older folders exactly the audited versions?   (milestone M0, the check that belongs to this folder)

    python tools/check_inputs.py                                   # the 14 pinned files (shield/paths.py PINS, from the audit HANDOFF.md section 2)
    python tools/check_inputs.py --root "D:\\1 Samadhi UNI\\aFYP\\Claude"
    python tools/check_inputs.py --gguf-dir D:\\llama\\models       # also hashes the three model files (about 4.6 GB, takes a minute)

Exit code 0 = everything checked is exactly as audited. Exit code 1 = a pinned file is missing or changed, or a model file differs.
The Python, numpy and scikit-learn versions are only printed next to the versions of the project environment: a different platform can move a few
near-tie records (AUDIT_REPORT section 5), so a version difference is a note, not a failure.
"""
import argparse
import platform
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shield import paths                                          # noqa: E402

PROJECT_ENV = {"python": "3.12.6", "numpy": "2.5.3", "scikit-learn": "1.9.1"}


def versions():
    out = {"python": platform.python_version()}
    for name, mod in (("numpy", "numpy"), ("scikit-learn", "sklearn")):
        try:
            out[name] = __import__(mod).__version__
        except Exception:                                          # noqa: BLE001
            out[name] = "not installed"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="the folder that holds edgesar_pilot, edgesar_heads, V1 (default: the parent of edgesar_shield)")
    ap.add_argument("--gguf-dir", default=None, help="folder with the three .gguf files (optional; hashing takes about a minute)")
    a = ap.parse_args()
    root = Path(a.root) if a.root else paths.ROOT
    failed = False

    bad = paths.check_pins(root)
    if bad:
        failed = True
        print("FAIL  %d of %d pinned files are not the audited version (root %s):" % (len(bad), len(paths.PINS), root))
        for b in bad:
            print("      - " + b)
    else:
        print("PASS  all %d pinned files under %s are exactly the audited versions (SHA-256)." % (len(paths.PINS), root))

    here, want = versions(), PROJECT_ENV
    for k in want:
        note = "same as the project environment" if here[k] == want[k] else "project environment: %s (a different platform can move a few near-tie records; report any difference)" % want[k]
        print("INFO  %s %s  (%s)" % (k, here[k], note))

    if a.gguf_dir:
        import extract_fresh_vectors as ex
        for mk, fname in ex.GGUF_FILE.items():
            f = Path(a.gguf_dir) / fname
            if not f.exists():
                failed = True
                print("FAIL  %s is missing" % f)
                continue
            h = paths.sha256_file(f)
            size_ok = f.stat().st_size == ex.GGUF_BYTES[mk]
            if h == ex.GGUF_SHA256[mk] and size_ok:
                print("PASS  %s: SHA-256 %s... and %d bytes equal the audited values." % (fname, h[:16], f.stat().st_size))
            else:
                failed = True
                print("FAIL  %s: SHA-256 %s (audited %s), %d bytes (audited %d)." % (fname, h, ex.GGUF_SHA256[mk], f.stat().st_size, ex.GGUF_BYTES[mk]))
    else:
        print("NOTE  model files not checked (pass --gguf-dir D:\\llama\\models to hash them).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
