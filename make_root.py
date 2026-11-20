"""Build the ROOT folder that the fresh-confirmation and exploratory scripts expect (--root <ROOT>).

    python make_root.py ROOT

ROOT gets edgesar_pilot (with data/cases.jsonl), edgesar_heads, edgesar_shield, V1 (from zenodo_v1/code) and repair_package (from code/).
The development cases are written with Windows line endings, as in the original run, so that their SHA-256 equals the one recorded
in fresh_confirmation/generation_manifest.json (3c51f0b4...). The content is the published zenodo_v1/data/cases.jsonl.

Not included (Llama 3.2 licence and size): the GGUF model files and the saved hidden-state vectors (edgesar_heads/features and the
fresh vectors). Without them you can still run zenodo_v1/verify_dataset.py, the simulator tests, and
fresh_confirmation/rebuild_primary.py; a full rerun needs llama.cpp b11901 and the three GGUF files named in zenodo_v1/DATA_CARD.md."""
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECT_DEV = "3c51f0b4b1481242da6855c80bff8e976971fd461bd67767a68797cb7826c8b7"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("edgesar_pilot", "edgesar_heads", "edgesar_shield", "V1"):
        shutil.copytree(HERE / "zenodo_v1" / "code" / name, root / name, dirs_exist_ok=True)
    shutil.copytree(HERE / "code" / "repair_package", root / "repair_package", dirs_exist_ok=True)
    data = (HERE / "zenodo_v1" / "data" / "cases.jsonl").read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    (root / "edgesar_pilot" / "data").mkdir(parents=True, exist_ok=True)
    (root / "edgesar_pilot" / "data" / "cases.jsonl").write_bytes(data)
    got = hashlib.sha256(data).hexdigest()
    print("ROOT:", root)
    print("development cases sha256:", got, "OK" if got == EXPECT_DEV else "MISMATCH")
    sys.exit(0 if got == EXPECT_DEV else 1)


if __name__ == "__main__":
    main()
