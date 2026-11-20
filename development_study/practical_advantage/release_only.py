"""Run the study code from the PUBLIC dataset release alone (no hidden vectors, no private workspace).

Why this file exists
    The release code (`code/edgesar_shield/shield/`) was written for the author's workspace. Three things it expects are not in the public release:
      1. `edgesar_pilot/data/cases.jsonl` with Windows (CRLF) line endings, SHA-256 3c51f0b4... (pinned in shield/paths.py).
         The release publishes the SAME records with LF line endings at `data/cases.jsonl` (SHA-256 833fafe2...; DATA_CARD.md says so).
      2. `edgesar_audit_2026-11-13/out/audit04_duplicate_clusters.csv` (family and exact-text duplicate cluster of every report).
         Both can be rebuilt from `cases.jsonl`: family is a field of each case; the cluster is "same text" (1232 clusters for 1400 reports).
      3. The saved hidden vectors `edgesar_heads/features/*.npy` (Llama 3.2 licence; not published). The TF-IDF and rule-engine arms do not use them,
         so their four pins are skipped here, and ONLY these four.
    The release folder is never modified. A small work folder is built inside the output folder with the layout the study code expects
    (edgesar_pilot with its data file, V1, edgesar_audit_2026-11-13/out); the study code is pointed to it with the environment variable it already
    supports (EDGESAR_ROOT). The study code itself (edgesar_shield/shield) is imported unchanged from the release.

Every check is printed; any mismatch stops the run.
"""
import csv
import hashlib
import json
import os
import shutil
from collections import OrderedDict
from pathlib import Path

PINNED_CASES_CRLF_SHA256 = "3c51f0b4b1481242da6855c80bff8e976971fd461bd67767a68797cb7826c8b7"     # as pinned in shield/paths.py (the file used in the experiments)
PUBLISHED_CASES_LF_SHA256 = "833fafe2fb47af9927603e4aab0cb45031b81999cf38dd796253662f30f0a769"     # as published in the release (DATA_CARD.md, SHA256SUMS.txt)
VECTOR_PINS = ("edgesar_heads/features/f16_end.npy", "edgesar_heads/features/Q8_0_end.npy",
               "edgesar_heads/features/Q4_K_M_end.npy", "edgesar_heads/features/case_ids.json")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def prepare(release_dir, work_dir):
    """Build the work folder and set the environment. Returns a dict of what was checked. Call BEFORE importing `shield`."""
    release = Path(release_dir).resolve()
    work = Path(work_dir).resolve()
    code = release / "code"
    data_file = release / "data" / "cases.jsonl"
    for need in (code / "edgesar_shield" / "shield", code / "edgesar_pilot" / "baselines.py", code / "V1" / "packages" / "allocation", data_file):
        if not need.exists():
            raise SystemExit("not a dataset release folder (missing %s). Unzip EdgeSAR_dataset_release_v1.0.zip and pass that folder." % need)
    info = OrderedDict()

    # 1. the published data file, then the CRLF form the experiments used
    raw = data_file.read_bytes()
    if _sha(raw) != PUBLISHED_CASES_LF_SHA256:
        raise SystemExit("data/cases.jsonl is not the published release file (SHA-256 %s)." % _sha(raw))
    if b"\r" in raw:
        raise SystemExit("data/cases.jsonl already has CR characters; expected LF line endings.")
    crlf = raw.replace(b"\n", b"\r\n")
    if _sha(crlf) != PINNED_CASES_CRLF_SHA256:
        raise SystemExit("the CRLF form of the release data does not equal the pinned experiment file (SHA-256 %s)." % _sha(crlf))
    info["cases_lf_sha256"] = PUBLISHED_CASES_LF_SHA256
    info["cases_crlf_sha256"] = PINNED_CASES_CRLF_SHA256
    print("release data: LF file matches the published hash; its CRLF form matches the pinned experiment file (records identical).", flush=True)

    # 2. work folder: copies of the pilot code and the allocator source (both small; their SHA-256 pins are checked later by the study code)
    #    with the data file in the place the study code expects
    if work.exists():
        shutil.rmtree(work)
    pilot = work / "edgesar_pilot"
    shutil.copytree(code / "edgesar_pilot", pilot, ignore=shutil.ignore_patterns("data", "results", "__pycache__"))
    (pilot / "data").mkdir()
    (pilot / "data" / "cases.jsonl").write_bytes(crlf)
    shutil.copytree(code / "V1", work / "V1", ignore=shutil.ignore_patterns("__pycache__"))

    # 3. duplicate clusters from the texts (cluster = identical text; numbered in order of first appearance)
    cases = [json.loads(l) for l in raw.decode("utf-8").split("\n") if l.strip()]
    first = OrderedDict()
    for c in cases:
        first.setdefault(c["text"], len(first))
    size = {}
    for c in cases:
        size[c["text"]] = size.get(c["text"], 0) + 1
    audit = work / "edgesar_audit_2026-11-13" / "out"
    audit.mkdir(parents=True)
    with open(audit / "audit04_duplicate_clusters.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case_id", "split", "family", "duplicate_cluster", "cluster_size", "in_duplicate_group"])
        for c in cases:
            w.writerow([c["id"], c["split"], c["family"], "D%04d" % first[c["text"]], size[c["text"]], int(size[c["text"]] > 1)])
    info["n_reports"] = len(cases)
    info["n_duplicate_clusters"] = len(first)
    print("rebuilt family / duplicate clusters from the texts: %d reports, %d clusters (expected 1400 and 1232)." % (len(cases), len(first)), flush=True)
    if (len(cases), len(first)) != (1400, 1232):
        raise SystemExit("unexpected cluster count.")

    # 4. point the study code to the work folder (it reads this variable; the others default to subfolders of it)
    for v in ("EDGESAR_PILOT_DIR", "EDGESAR_HEADS_DIR", "EDGESAR_V1_DIR", "EDGESAR_AUDIT_DIR"):
        os.environ.pop(v, None)
    os.environ["EDGESAR_ROOT"] = str(work)
    info["work_root"] = str(work)
    return info


def skip_vector_pins():
    """After `from shield import paths`: drop the four pins of the hidden-vector files, keep every other pin (and check them).
    Also replace the vector loader by an EMPTY stand-in (1400 x 0 arrays), so that `DevData()` builds its cases, families, duplicate clusters and
    the 5-fold split exactly as before without the files. Any attempt to use a hidden vector then fails loudly (zero columns)."""
    import numpy as np
    from shield import data, paths                                            # noqa: E402
    for k in VECTOR_PINS:
        paths.PINS.pop(k, None)
    bad = paths.check_pins()
    if bad:
        raise SystemExit("Input check failed after skipping the vector files:\n  " + "\n  ".join(bad))
    ids = [c["id"] for c in data.load_cases()]

    def load_vectors_stub(kind="end"):
        return {m: np.zeros((len(ids), 0)) for m in data.PREC}, ids

    data.load_vectors = load_vectors_stub
    print("input check: %d pinned study files are exactly the audited versions; the 4 hidden-vector pins are skipped and the vector loader is an "
          "empty stand-in (these arms use no vectors)." % len(paths.PINS), flush=True)
    return len(paths.PINS)
