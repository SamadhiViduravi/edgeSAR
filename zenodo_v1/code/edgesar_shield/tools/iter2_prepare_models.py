"""
Iteration 2 (docs/ITERATION2_PROTOCOL.md): make the three new model files and get their vectors, on Samadhi's PC.

    python tools\\iter2_prepare_models.py make    --llama-dir D:\\llama --models-dir D:\\llama\\models --generic-calib D:\\llama\\calib\\calib_generic.txt
    python tools\\iter2_prepare_models.py check   --models-dir D:\\llama\\models
    python tools\\iter2_prepare_models.py extract --models-dir D:\\llama\\models

make    : llama-imatrix + llama-quantize -> <models-dir>\\iter2\\<KEY>\\Llama-3.2-1B-Instruct-Q4_K_M.gguf  (KEY = Q4_IMX_DOMAIN, Q4_IMX_GENERIC, Q5;
          the file name is the same for all so that the unchanged extraction pipeline finds it; results\\iter2\\MANIFEST.json says what each really is)
check   : the unchanged pipeline on the existing plain Q4_K_M file, 50 reports, must reproduce the saved vectors
extract : copies edgesar_heads to edgesar_heads_iter2_<KEY> (next to it) and runs 02_extract.py there; the frozen folders are never written.
Every step refuses to run if docs/ITERATION2_PROTOCOL.md changed after it was hashed. A finished output is skipped, never overwritten.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROTOCOL = HERE / "docs" / "ITERATION2_PROTOCOL.md"
PHASH = HERE / "results" / "ITER2_PROTOCOL.sha256"
RES = HERE / "results" / "iter2"
MANIFEST = RES / "MANIFEST.json"
LOGS = HERE / "logs" / "iter2"
F16_NAME = "Llama-3.2-1B-Instruct-f16.gguf"
F16_SHA = "1f33ad43d2b85b908ff06fe7002b69806a57359b9b2617ca27d7bdea428ae146"      # edgesar_pilot model_hashes.json
PLAIN_Q4_NAME = "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
PLAIN_Q4_SHA = "26bac8efd811cb41a80db4393dbe5c8360abd54b98954ec766aa4ba7dacc0bc5"
KEYS = {"Q4_IMX_DOMAIN": ("Q4_K_M", "domain"), "Q4_IMX_GENERIC": ("Q4_K_M", "generic"), "Q5": ("Q5_K_M", None),
        # Amendment 1 (docs/ITERATION2_AMENDMENT1.md): control, in-domain text cut to the same number of chunks as the generic file
        "Q4_IMX_DOMAIN_M": ("Q4_K_M", "domain_matched")}
AMEND = HERE / "docs" / "ITERATION2_AMENDMENT1.md"
AHASH = HERE / "results" / "ITER2_AMENDMENT1.sha256"


def sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def check_protocol(skip):
    if skip:
        return "skipped (test)"
    h = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    want = PHASH.read_text(encoding="utf-8").split()[0]
    if h != want:
        sys.exit("docs/ITERATION2_PROTOCOL.md changed after it was hashed. Stop. (A change needs a new protocol and written approval.)")
    return h


def check_amendment(skip):
    if skip:
        return "skipped (test)"
    h = hashlib.sha256(AMEND.read_bytes()).hexdigest()
    want = AHASH.read_text(encoding="utf-8").split()[0]
    if h != want:
        sys.exit("docs/ITERATION2_AMENDMENT1.md changed after it was hashed. Stop.")
    return h


def generic_chunks():
    """number of 1024-token chunks that llama-imatrix really used for the generic file (read from its log)"""
    import re
    for ext in ("gguf", "dat"):
        p = LOGS / ("imatrix_generic_%s.log" % ext)
        if p.exists():
            m_ = re.search(r"computing over (\d+) chunks", p.read_text(encoding="utf-8", errors="replace"))
            if m_:
                return int(m_.group(1))
    return None


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"files": {}, "steps": []}


def save_manifest(m):
    RES.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8")


def find_exe(bin_dir, name):
    for n in (name + ".exe", name):
        if (Path(bin_dir) / n).exists():
            return Path(bin_dir) / n
    sys.exit("%s not found in %s" % (name, bin_dir))


def run(cmd, log_name, cwd, dry):
    LOGS.mkdir(parents=True, exist_ok=True)
    line = " ".join('"%s"' % c if " " in str(c) else str(c) for c in cmd)
    print("   $ " + line, flush=True)
    if dry:
        return 0, 0.0, line
    t0 = time.time()
    with open(LOGS / log_name, "w", encoding="utf-8", errors="replace") as log:
        log.write("COMMAND: " + line + "\n\n")
        log.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=log, stderr=subprocess.STDOUT, cwd=str(cwd))
    return r.returncode, time.time() - t0, line


def tail(log_name, n=15):
    p = LOGS / log_name
    if p.exists():
        print("   --- last lines of logs\\iter2\\%s ---" % log_name)
        for l in p.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]:
            print("   " + l)


def cmd_make(a):
    ph = check_protocol(a.no_checks)
    ah = check_amendment(a.no_checks)
    models = Path(a.models_dir)
    imat, quant = find_exe(a.llama_dir, "llama-imatrix"), find_exe(a.llama_dir, "llama-quantize")
    f16 = models / F16_NAME
    if not f16.exists():
        sys.exit("FP16 file not found: %s" % f16)
    m = load_manifest()
    if not a.no_checks:
        print("checking the FP16 file hash (takes a few seconds) ...")
        if sha256(f16) != F16_SHA:
            sys.exit("FP16 file hash differs from the pinned one. Stop.")
    m["protocol_sha256"], m["amendment1_sha256"], m["f16_sha256"] = ph, ah, F16_SHA
    gen = Path(a.generic_calib) if a.generic_calib else None
    if gen is None or not gen.exists() or gen.stat().st_size < 100_000:
        print("NOTE: no usable generic calibration file (need >= 100 KB): Q4_IMX_GENERIC will be skipped.")
        gen = None
    else:
        m["generic_calib"] = {"path": str(gen), "bytes": gen.stat().st_size, "sha256": sha256(gen)}
    # does this build parse special tokens in the calibration text?
    hp = subprocess.run([str(imat), "--help"], capture_output=True, text=True, cwd=str(imat.parent)) if not a.dry_run else None
    help_text = ((hp.stdout or "") + (hp.stderr or "")) if hp else ""
    special = "--parse-special" in help_text
    calib_domain = HERE / "calib" / ("calib_domain_special.txt" if special else "calib_domain_plain.txt")
    m["domain_calib"] = {"file": calib_domain.name, "sha256": sha256(calib_domain), "parse_special_flag_used": special}
    for key, (qtype, calib) in KEYS.items():
        if a.only and key not in a.only:
            continue
        outdir = models / "iter2" / key
        out = outdir / PLAIN_Q4_NAME
        if out.exists() and key in m["files"]:
            print("%-15s exists, skipped" % key)
            continue
        if calib == "generic" and gen is None:
            continue
        nchunks = None
        if calib == "domain_matched":
            nchunks = generic_chunks()
            if nchunks is None:
                print("%-15s waits: the generic imatrix must be made first (its chunk count is needed). Run 'make' again after it." % key)
                continue
            if "--chunks" not in help_text and not a.dry_run:
                sys.exit("this llama-imatrix has no --chunks option. Send me the output of:  D:\\llama\\llama-imatrix.exe --help")
            m["matched_chunks"] = nchunks
        outdir.mkdir(parents=True, exist_ok=True)
        imfile = None
        if calib:
            src = gen if calib == "generic" else calib_domain
            for ext in (".gguf", ".dat"):
                imfile = models / "iter2" / ("imatrix_%s%s" % (calib, ext))
                cmd = [imat, "-m", f16, "-f", src, "-o", imfile, "-ngl", str(a.ngl), "-c", "1024"] + (["--parse-special"] if (special and calib != "generic") else []) + (["--chunks", str(nchunks)] if nchunks else [])
                print("%-15s imatrix (%s) ..." % (key, ext))
                rc, secs, line = run(cmd, "imatrix_%s%s.log" % (calib, ext.replace(".", "_")), imat.parent, a.dry_run)
                if rc == 0 and (a.dry_run or imfile.exists()):
                    m["steps"].append({"key": key, "step": "imatrix", "seconds": round(secs, 1), "command": line})
                    break
                tail("imatrix_%s%s.log" % (calib, ext.replace(".", "_")))
                print("   imatrix with %s output failed; trying the other format" % ext)
            else:
                sys.exit("llama-imatrix failed for %s. Send me the last lines printed above." % key)
        cmd = [quant] + (["--imatrix", imfile] if imfile else []) + [f16, out, qtype]
        print("%-15s quantize to %s ..." % (key, qtype))
        rc, secs, line = run(cmd, "quantize_%s.log" % key, quant.parent, a.dry_run)
        if rc != 0 or (not a.dry_run and not out.exists()):
            tail("quantize_%s.log" % key)
            sys.exit("llama-quantize failed for %s." % key)
        if a.dry_run:
            continue
        m["files"][key] = {"real_type": qtype, "imatrix": (str(imfile) if imfile else None), "path": str(out), "bytes": out.stat().st_size,
                           "sha256": sha256(out), "quantize_seconds": round(secs, 1), "command": line}
        save_manifest(m)
        print("   done: %.2f GB, sha256 %s..." % (out.stat().st_size / 1e9, m["files"][key]["sha256"][:12]))
    if not a.dry_run:
        save_manifest(m)
    print("\nNext: python tools\\iter2_prepare_models.py check --models-dir %s" % models)


def feat_check(src_heads, dst, models_dir, limit=50):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src_heads, dst, ignore=shutil.ignore_patterns("features", "features_limit*", "results_heads", "logs", "__pycache__", "*.pyc", "attempts.log"))
    env = dict(os.environ, EDGESAR_MODELS_DIR=str(models_dir), PYTHONDONTWRITEBYTECODE="1")
    return env


def cmd_check(a):
    check_protocol(a.no_checks)
    import numpy as np
    heads = HERE.parent / "edgesar_heads"
    dst = HERE.parent / "edgesar_heads_iter2_check"
    env = feat_check(heads, dst, a.models_dir)
    print("running the unchanged pipeline on the existing plain Q4_K_M file, 50 reports ...")
    r = subprocess.run([sys.executable, "02_extract.py", "--models", "Q4_K_M", "--limit", "50"], cwd=str(dst), env=env)
    if r.returncode != 0:
        sys.exit("extraction failed (see above). Close other llama-server.exe programs and run again.")
    out = {}
    for v in ("end", "prefix"):
        new = np.load(dst / "features_limit50" / ("Q4_K_M_%s.npy" % v)).astype(np.float64)
        old = np.load(heads / "features" / ("Q4_K_M_%s.npy" % v)).astype(np.float64)[:50]
        cos = (new * old).sum(1) / (np.linalg.norm(new, axis=1) * np.linalg.norm(old, axis=1))
        out[v] = {"max_abs_diff": float(np.abs(new - old).max()), "min_cosine": float(cos.min())}
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "identity_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    ok = all(v["min_cosine"] > 0.9999 for v in out.values())
    print("IDENTITY CHECK:", "PASS" if ok else "CHECK - send me results\\iter2\\identity_check.json before you go on")


def cmd_extract(a):
    check_protocol(a.no_checks)
    m = load_manifest()
    if not (RES / "identity_check.json").exists():
        sys.exit("run the 'check' step first")
    heads = HERE.parent / "edgesar_heads"
    fdir = RES / "features"
    fdir.mkdir(parents=True, exist_ok=True)
    for key, info in m["files"].items():
        if a.only and key not in a.only:
            continue
        done = all((fdir / ("%s_%s.npy" % (key, v))).exists() for v in ("end", "prefix"))
        if done:
            print("%-15s features already collected, skipped" % key)
            continue
        dst = HERE.parent / ("edgesar_heads_iter2_" + key)
        if not dst.exists():
            shutil.copytree(heads, dst, ignore=shutil.ignore_patterns("features", "features_limit*", "results_heads", "logs", "__pycache__", "*.pyc", "attempts.log"))
        env = dict(os.environ, EDGESAR_MODELS_DIR=str(Path(info["path"]).parent), PYTHONDONTWRITEBYTECODE="1")
        print("\n=== %s (%s) ===" % (key, info["real_type"]), flush=True)
        r = subprocess.run([sys.executable, "02_extract.py", "--models", "Q4_K_M"], cwd=str(dst), env=env)
        if r.returncode != 0:
            sys.exit("extraction failed for %s. Run the same command again: it continues where it stopped." % key)
        for v in ("end", "prefix"):
            shutil.copy2(dst / "features" / ("Q4_K_M_%s.npy" % v), fdir / ("%s_%s.npy" % (key, v)))
            shutil.copy2(dst / "features" / ("Q4_K_M_%s.meta.json" % v), fdir / ("%s_%s.meta.json" % (key, v)))
        shutil.copy2(dst / "features" / "case_ids.json", fdir / "case_ids.json")
    print("\nAll collected in %s. Tell Claude 'iter2 vectors ready'." % fdir)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("make", "check", "extract"):
        p = sub.add_parser(name)
        p.add_argument("--models-dir", required=True)
        p.add_argument("--no-checks", action="store_true", help="tests only")
        p.add_argument("--only", nargs="*", default=None)
        if name == "make":
            p.add_argument("--llama-dir", required=True)
            p.add_argument("--generic-calib", default=None)
            p.add_argument("--ngl", type=int, default=99)
            p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    {"make": cmd_make, "check": cmd_check, "extract": cmd_extract}[a.cmd](a)


if __name__ == "__main__":
    main()
