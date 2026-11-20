"""Check the published dataset against the generator.
Run:  python verify_dataset.py
It (1) checks SHA256SUMS.txt, (2) regenerates the 1,400 reports with the fixed seed in a temporary
folder and compares them with data/cases.jsonl (line endings ignored).
Standard library only."""
import hashlib, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECT = "833fafe2fb47af9927603e4aab0cb45031b81999cf38dd796253662f30f0a769"

def sha(p):
    h = hashlib.sha256()
    h.update(Path(p).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()

ok = True
got = sha(HERE / "data" / "cases.jsonl")
print("published cases.jsonl (LF) :", got, "OK" if got == EXPECT else "MISMATCH")
ok &= got == EXPECT

tmp = Path(tempfile.mkdtemp())
try:
    for f in ("gen_cases.py", "common.py"):
        shutil.copy(HERE / "generator" / f, tmp / f)
    (tmp / "data").mkdir()
    subprocess.run([sys.executable, "gen_cases.py"], cwd=tmp, check=True, stdout=subprocess.DEVNULL)
    regen = sha(tmp / "data" / "cases.jsonl")
    print("regenerated cases.jsonl     :", regen, "OK" if regen == EXPECT else "MISMATCH")
    ok &= regen == EXPECT
finally:
    shutil.rmtree(tmp, ignore_errors=True)

bad = 0
for line in (HERE / "SHA256SUMS.txt").read_text().splitlines():
    if not line.strip():
        continue
    digest, name = line.split("  ", 1)
    if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
        print("CHANGED:", name); bad += 1
print("SHA256SUMS.txt: %d file(s) changed" % bad)
ok &= bad == 0
print("ALL OK" if ok else "PROBLEM")
sys.exit(0 if ok else 1)
