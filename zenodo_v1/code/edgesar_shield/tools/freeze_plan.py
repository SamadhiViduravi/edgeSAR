"""
Freeze the FRESH evaluation plan.   Run it ONLY after the plan was approved, and BEFORE any fresh report is generated.

    python tools/freeze_plan.py            writes docs/EVAL_PLAN_FRESH.sha256 (refuses if the plan says STATUS: DRAFT, or if a freeze file already exists)
    python tools/freeze_plan.py --check    checks that the plan and the code are still exactly what was frozen (exit code 0 = intact)

What it records: SHA-256 of docs/EVAL_PLAN_FRESH.md, a fingerprint of every code file that makes or analyses results (all of shield/*.py and the
tools listed in shield/frozen.py), the time, and the versions.  Then it prints the text to send to the supervisors (the hash and the time),
which is the "email" step of plan section 8.5.  Registering on OSF is optional and needs the user's explicit approval: this script does not do it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import frozen, paths                                  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        problems, fz = frozen.check_freeze()
        if problems:
            print("NOT INTACT:\n  - " + "\n  - ".join(problems))
            sys.exit(1)
        print("INTACT. Plan SHA-256 %s, frozen %s (Colombo)." % (fz["plan_sha256"], fz["frozen_at_colombo"]))
        return
    if frozen.FREEZE.exists():
        sys.exit("STOP. %s already exists. A second freeze needs a written deviation note and a new file name; the first freeze is never overwritten." % frozen.FREEZE.name)
    fz = frozen.make_freeze()
    if not fz["pins_ok"]:
        sys.exit("STOP. The older folders are not the audited versions (see tools/check_inputs.py).")
    frozen.FREEZE.write_text(json.dumps(fz, indent=1), encoding="utf-8")
    print(json.dumps(fz, indent=1))
    print("\n--- text for the supervisors ---")
    print("EdgeSAR evaluation plan for the fresh confirmation run is frozen.\n"
          "File: docs/EVAL_PLAN_FRESH.md\nSHA-256: %s\nFrozen at: %s Colombo time (%s UTC)\nCode fingerprint: %s\n"
          "No fresh report has been generated and no fresh outcome has been seen." % (fz["plan_sha256"], fz["frozen_at_colombo"], fz["frozen_at_utc"], fz["code_sha256"]))


if __name__ == "__main__":
    main()
