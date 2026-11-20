"""
The freeze: what makes a FRESH run a confirmation and not another development run.

    docs/EVAL_PLAN_FRESH.md       the plan, written and approved BEFORE any fresh report exists. It carries a machine-readable parameter block.
    docs/EVAL_PLAN_FRESH.sha256   written once by tools/freeze_plan.py: the plan's SHA-256, a fingerprint of all code that produces or analyses results,
                                  and the time of the freeze.

tools/run_fresh.py calls `require_freeze()` first.  It stops if the plan is not frozen, or if the plan or any code file has changed since.
(A change after the freeze is allowed only as a new freeze with a written deviation note; the old freeze file is kept.)
"""
import hashlib
import json
import platform
import re
import time
from pathlib import Path

from . import paths

PLAN = paths.HERE / "docs" / "EVAL_PLAN_FRESH.md"
FREEZE = paths.HERE / "docs" / "EVAL_PLAN_FRESH.sha256"
# analysis and data tools whose content decides what a FRESH result means (the whole shield/ folder is always included)
TOOLS = ("run_fresh.py", "analyze_dev.py", "gen_episodes_fresh.py", "extract_fresh_vectors.py", "freeze_plan.py")
BEGIN, END = "<!-- PARAMS-BEGIN -->", "<!-- PARAMS-END -->"
REQUIRED = ("fresh_seed", "cal_episodes", "eval_episodes", "R", "alpha", "K", "b", "d_v", "alloc_cost_s", "decision_timeout_s", "level_gap_s", "runs",
            "primary", "deadlines_s", "allocator_default")


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def plan_text(path=None):
    return Path(path or PLAN).read_text(encoding="utf-8")


def plan_status(text):
    m = re.search(r"^STATUS:\s*(\S+)", text, re.M)
    return m.group(1).strip().upper() if m else "UNKNOWN"


def plan_params(text):
    """The JSON block between the PARAMS markers."""
    if BEGIN not in text or END not in text:
        raise SystemExit("The plan has no parameter block (%s ... %s)." % (BEGIN, END))
    block = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    block = re.sub(r"^```\w*\s*|\s*```$", "", block.strip())
    try:
        p = json.loads(block)
    except ValueError as e:
        raise SystemExit("The parameter block of the plan is not valid JSON: %s" % e)
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        raise SystemExit("The parameter block of the plan lacks: %s" % ", ".join(missing))
    return p


def code_fingerprint(root=None):
    """SHA-256 over all shield/*.py (names and bytes, sorted) and over the analysis/data tools listed in TOOLS."""
    root = Path(root or paths.HERE)
    h = hashlib.sha256()
    files = sorted((root / "shield").glob("*.py"))
    for p in files:
        h.update(("shield/" + p.name).encode())
        h.update(p.read_bytes())
    per_tool = {}
    for t in TOOLS:
        f = root / "tools" / t
        per_tool[t] = paths.sha256_file(f) if f.exists() else None
        h.update(("tools/" + t).encode())
        h.update((per_tool[t] or "missing").encode())
    return h.hexdigest(), per_tool, [p.name for p in files]


def make_freeze(plan_path=None, root=None):
    text = plan_text(plan_path)
    st = plan_status(text)
    if st != "FROZEN-READY":
        raise SystemExit("STOP. The plan says STATUS: %s. Freezing needs the line 'STATUS: FROZEN-READY', written by the person who approves the plan "
                         "(the main chat / the user), not by the implementation." % st)
    params = plan_params(text)
    code, per_tool, files = code_fingerprint(root)
    now = time.time()
    return {"plan_file": "docs/EVAL_PLAN_FRESH.md", "plan_sha256": sha256_text(text), "params_sha256": sha256_text(json.dumps(params, sort_keys=True)),
            "code_sha256": code, "shield_files": files, "tool_sha256": per_tool,
            "pins_ok": not paths.check_pins(), "frozen_at_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)),
            "frozen_at_colombo": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now + 5.5 * 3600)), "python": platform.python_version(),
            "platform": platform.platform()}


def check_freeze(freeze_path=None, plan_path=None, root=None):
    """Returns (problems, freeze_dict).  No problems = the plan and the code are exactly what was frozen."""
    fp = Path(freeze_path or FREEZE)
    if not fp.exists():
        return ["The plan is not frozen: %s does not exist." % fp.name], None
    fz = json.loads(fp.read_text(encoding="utf-8"))
    problems = []
    text = plan_text(plan_path)
    if sha256_text(text) != fz["plan_sha256"]:
        problems.append("docs/EVAL_PLAN_FRESH.md changed after the freeze.")
    code, per_tool, _ = code_fingerprint(root)
    if code != fz["code_sha256"]:
        changed = [t for t, h in per_tool.items() if fz["tool_sha256"].get(t) != h]
        problems.append("code changed after the freeze (shield/*.py or tools: %s)." % (", ".join(changed) or "see shield/*.py"))
    if paths.check_pins():
        problems.append("the pinned older folders are not the audited versions: " + "; ".join(paths.check_pins()))
    return problems, fz


def require_freeze(freeze_path=None, plan_path=None, root=None):
    problems, fz = check_freeze(freeze_path, plan_path, root)
    if problems:
        raise SystemExit("STOP. No FRESH run is allowed:\n  - " + "\n  - ".join(problems) +
                         "\nA change after the freeze needs a new freeze and a written deviation note (plan section 8.5).")
    return fz
