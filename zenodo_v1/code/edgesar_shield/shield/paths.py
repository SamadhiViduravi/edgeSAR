"""
Where things are, and which exact versions of the older work this folder is allowed to read.

Rule: the older folders (edgesar_pilot, edgesar_heads, V1, the audit) are READ-ONLY. Nothing here writes into them.
Every file that matters is checked against a SHA-256 fingerprint taken from HANDOFF.md of the audit (13 Nov 2026).
"""
import hashlib
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True            # never write __pycache__ into the frozen folders

HERE = Path(__file__).resolve().parent.parent                      # .../edgesar_shield
ROOT = Path(os.environ.get("EDGESAR_ROOT") or HERE.parent).resolve()   # .../Claude
V1 = Path(os.environ.get("EDGESAR_V1_DIR") or (ROOT / "V1")).resolve()
PILOT = Path(os.environ.get("EDGESAR_PILOT_DIR") or (ROOT / "edgesar_pilot")).resolve()
HEADS = Path(os.environ.get("EDGESAR_HEADS_DIR") or (ROOT / "edgesar_heads")).resolve()
AUDIT = Path(os.environ.get("EDGESAR_AUDIT_DIR") or (ROOT / "edgesar_audit_2026-11-13")).resolve()
RESULTS = HERE / "results"

# relative to ROOT -> SHA-256 (from audit HANDOFF.md section 2; checked again by tools/check_inputs.py)
PINS = {
    "edgesar_pilot/data/cases.jsonl": "3c51f0b4b1481242da6855c80bff8e976971fd461bd67767a68797cb7826c8b7",
    "edgesar_pilot/common.py": "332ec94d84fa385b2fae2b2949cd8cbf7463a1de2527236f0b2a78ba47f3c91a",
    "edgesar_pilot/baselines.py": "e410b94c788e848aeca21b3c0cb37a9c216f957c712f67238cb4b3896bf105a7",
    "edgesar_pilot/gen_cases.py": "b65695c5b2b5e9a959645f0d8a317d9ed80935212db5b19cff940e0aac978e39",
    "edgesar_heads/features/f16_end.npy": "02565a16e33ccc87350fe455f4dd4494935bdf0fafdc90af7f8e8ca9d0bfbdd5",
    "edgesar_heads/features/Q8_0_end.npy": "5280a4b5bbe5531a0d196895d33349c81a5ddbbb7c5dd2beae97f801ff59eb19",
    "edgesar_heads/features/Q4_K_M_end.npy": "9f8b235458b2e97c806aaa293d49e78f8668fc279ed9290e6efd7ddd17ac6754",
    "edgesar_heads/features/case_ids.json": "c068b9b48c5071773f78706d71e524f8e4298bbc38e886738cce85c9eb692719",
    "V1/packages/allocation/cbba.py": "b390bf313dc8144e66f37539cc32387846b959ca688e8a13f9f4b6b4df26fdc7",
    "V1/packages/allocation/bids.py": "ef8e819caf4269fda682c79109136f232a3d232c13239e6eb3eb1e522004c364",
    "V1/packages/allocation/mission.py": "df521fad3126fa5fe198c2c1bc66b4e57c65866e9fc8cb872addca3979ddc0c6",
    "V1/packages/allocation/world.py": "41ca798b6881e14c6025cd0b7ee8aa74df826148c2e70e6b74704a988608b693",
    "V1/packages/allocation/funnel.py": "a25bee9ee4d29da095774068ee8c30438d1e042ce860105ae3407bc68ef0f609",
    "V1/packages/allocation/decisions.py": "4c0b6582cb00bd8832d285cd17f7fcdd05452a17b22329385b80b123559b056d",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pins(root=None):
    """Return a list of problems (empty list = every pinned file is exactly the audited version)."""
    root = Path(root) if root else ROOT
    bad = []
    for rel, want in PINS.items():
        p = root / rel
        if not p.exists():
            bad.append("missing: %s" % rel)
        elif sha256_file(p) != want:
            bad.append("CHANGED since the audit: %s" % rel)
    return bad


def require_pins(root=None):
    bad = check_pins(root)
    if bad:
        raise SystemExit("Input check failed (older folders are not the audited versions):\n  " + "\n  ".join(bad))


def add_pilot_to_path():
    """Make the pilot's common.py / baselines.py importable (read-only)."""
    if str(PILOT) not in sys.path:
        sys.path.insert(0, str(PILOT))


def add_v1_to_path():
    if str(V1) not in sys.path:
        sys.path.insert(0, str(V1))
