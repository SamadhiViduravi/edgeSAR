"""
Step Q1: download the Qwen2.5-1.5B-Instruct FP16 GGUF file (3.56 GB, from the Qwen team on Hugging Face), check its SHA-256,
and make the Q4_K_M file from it with llama-quantize of the same llama.cpp build (b11901), without an importance matrix,
as was done for Llama 3.2 1B.

    python qwen_download.py

If the download stops, run it again: it continues where it stopped. Files go to the models folder of edgesar_pilot/config.json.
"""
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "edgesar_pilot"
URL = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-fp16.gguf"
F16 = "qwen2.5-1.5b-instruct-fp16.gguf"
Q4 = "qwen2.5-1.5b-instruct-Q4_K_M.gguf"
F16_SHA256 = "fc89e330deb3fd8fa560f1c0f35a1e2b8da96d59e13445559ed190307a6f5649"
Q4_MIN_BYTES = 800_000_000          # a complete Qwen2.5-1.5B Q4_K_M file is about 1.1 GB; a smaller one is broken


def memory_gb():
    """(free RAM, total RAM, memory that can still be committed) in GB, on Windows; None elsewhere."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return None
        return m.ullAvailPhys / 1e9, m.ullTotalPhys / 1e9, m.ullAvailPageFile / 1e9
    except Exception:
        return None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def download(dst):
    part = dst.with_name(dst.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(URL, headers={"User-Agent": "edgesar-qwen/1.0"})
    if have:
        req.add_header("Range", "bytes=%d-" % have)
        print("Continuing the download from %.2f GB" % (have / 1e9))
    with urllib.request.urlopen(req, timeout=60) as r:
        if have and r.status != 206:                 # the server did not continue: start again
            print("The server did not continue the old download; starting again.")
            have = 0
        total = r.headers.get("Content-Length")
        total = (int(total) + have) if total else None
        mode = "ab" if have else "wb"
        t0, got, last = time.time(), have, 0
        with open(part, mode) as f:
            while True:
                buf = r.read(1 << 20)
                if not buf:
                    break
                f.write(buf)
                got += len(buf)
                if got - last >= 200 * (1 << 20):
                    last = got
                    rate = (got - have) / max(time.time() - t0, 1e-9)
                    left = ((total - got) / rate / 60) if total else float("nan")
                    print("   %.2f of %s GB (%.1f MB/s, about %.0f min left)" % (got / 1e9, ("%.2f" % (total / 1e9)) if total else "?", rate / 1e6, left))
    print("Checking the file ...")
    h = sha(part)
    if h != F16_SHA256:
        part.unlink()
        sys.exit("STOP: the downloaded file is damaged (SHA-256 %s). Run this again to download it once more." % h)
    part.rename(dst)


def main():
    cfg = json.loads((PILOT / "config.json").read_text(encoding="utf-8"))
    models = Path(cfg["paths"]["models_dir"])
    bin_dir = Path(cfg["paths"]["llama_bin_dir"])
    models.mkdir(parents=True, exist_ok=True)
    f16 = models / F16
    if f16.exists() and sha(f16) == F16_SHA256:
        print("FP16 file already here and correct: %s" % f16)
    else:
        if f16.exists():
            f16.rename(f16.with_name(f16.name + ".bad"))
        print("Downloading %s (3.56 GB) to %s" % (F16, models))
        download(f16)
        print("FP16 file downloaded and checked.")
    q4 = models / Q4
    if q4.exists() and q4.stat().st_size < Q4_MIN_BYTES:
        bad = q4.with_name(q4.name + ".broken")
        if bad.exists():
            bad.unlink()
        q4.rename(bad)
        print("The old Q4_K_M file was incomplete (%.2f GB); renamed to %s. It will be made again." % (bad.stat().st_size / 1e9, bad.name))
    if q4.exists():
        print("Q4_K_M file already made: %s (%.2f GB)" % (q4, q4.stat().st_size / 1e9))
    else:
        exe = next((bin_dir / n for n in ("llama-quantize.exe", "llama-quantize") if (bin_dir / n).exists()), None)
        if exe is None:
            sys.exit("llama-quantize not found in %s" % bin_dir)
        mem = memory_gb()
        if mem:
            print("Free memory now: %.1f GB of %.1f GB RAM; %.1f GB can still be committed." % mem)
            if mem[0] < 3.0 or mem[2] < 4.0:
                print("WARNING: little free memory. Close other programs (Blender, browsers, games), or restart the laptop, then run this again.")
        (HERE / "logs").mkdir(exist_ok=True)
        log = HERE / "logs" / "quantize_Q4_K_M.log"
        tmp = q4.with_name(q4.stem + ".tmp.gguf")
        if tmp.exists():
            tmp.unlink()
        print("Making the Q4_K_M file (about 1-3 minutes) ...")
        with open(log, "w", encoding="utf-8", errors="replace") as lf:
            r = subprocess.run([str(exe), str(f16), str(tmp), "Q4_K_M"], stdout=lf, stderr=subprocess.STDOUT, cwd=str(exe.parent))
        if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < Q4_MIN_BYTES:
            if tmp.exists():
                tmp.unlink()
            sys.exit("STOP: llama-quantize failed (log: %s). This usually means too little free memory: close other programs or "
                     "restart the laptop, then run STEP_Q1 again." % log)
        tmp.rename(q4)
        print("Q4_K_M file made: %.2f GB" % (q4.stat().st_size / 1e9))
    info = {"f16": {"file": F16, "sha256": F16_SHA256, "source": URL}, "Q4_K_M": {"file": Q4, "sha256": sha(q4), "made_with": "llama-quantize (llama.cpp b11901), no importance matrix"}}
    (HERE / "model_files.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print("\nDONE. Model files are ready. Now run STEP_Q2_check.bat")


if __name__ == "__main__":
    main()
