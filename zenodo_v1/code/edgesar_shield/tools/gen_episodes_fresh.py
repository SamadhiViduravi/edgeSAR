"""
Make the FRESH reports (inputs only: texts, open tables, gold records).  CPU only, deterministic from the seed, no model needed.

    python tools/gen_episodes_fresh.py --seed 20261201 --cal-episodes 40 --eval-episodes 1100 --out fresh/   (the numbers of the frozen plan; run_fresh.py checks them)

It writes:
    cases_fresh.jsonl         one case per line, the SAME schema as the pilot cases (id, style, open, source, time, text, gold, type, subtype)
                              plus  split = fresh_cal | fresh_eval,  episode = "FC001"... / "FE001"...,  pos = position in the episode
    generation_manifest.json  seed, counts, SHA-256 of the cases file and of the pilot generator files that were read, duplicate statistics

How the reports are made: with the pilot's own generator functions (gen_cases.py, read-only, SHA-256 pinned), style A, with the pilot's class mix
(CREATE 25%, UPDATE 20%, CLOSE 15%, NO_ACTION 40%).  Every report is unique: a report whose (text, open table, gold record) is already in the
development set or earlier in this file is thrown away and drawn again.  The number of throw-aways is logged.
The reports are independent of each other (each carries its own open table).  An episode is a fixed group of R reports; arrival times are drawn
later, by the evaluation, from the seed in EVAL_PLAN_FRESH.md.

This script does NOT look at any model output.  Run it only after EVAL_PLAN_FRESH.md is frozen (tools/freeze_plan.py), then copy
cases_fresh.jsonl to the GPU computer for tools/extract_fresh_vectors.py.
"""
import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import paths                                          # noqa: E402

KINDS = (["create"] * 25 + ["update"] * 20 + ["close"] * 15 + ["chatter"] * 10 + ["duplicate"] * 10 + ["nonhuman"] * 10 + ["negation"] * 10)


def canon_open(open_list):
    return tuple(sorted((i["id"], i["landmark"], i["sensor"], i["priority"]) for i in open_list))


def case_key(c):
    return (c["text"], canon_open(c["open"]), json.dumps(c["gold"], sort_keys=True))


def load_pilot_generator():
    """gen_cases.py of the pilot, imported read-only after its fingerprint is checked."""
    paths.require_pins()
    sys.path.insert(0, str(paths.PILOT))
    import gen_cases                                              # noqa: E402
    return gen_cases


def make_one(gc, rng, kind, style="A"):
    if kind == "create":
        r = gc.make_create(rng, style)
    elif kind == "update":
        r = gc.make_update(rng, style)
    elif kind == "close":
        r = gc.make_close(rng, style)
    else:
        r = gc.make_noop(rng, style, kind)
    open_, src, text, gold, typ, sub = r
    return {"style": style, "open": open_, "source": src, "time": gc.rand_time(rng), "text": text, "gold": gold, "type": typ, "subtype": sub}


def generate(seed, n_cal_ep, n_eval_ep, R, dev_cases, style="A", max_tries=200):
    gc = load_pilot_generator()
    rng = random.Random(seed)
    seen = {case_key(c) for c in dev_cases}
    n_dev_keys = len(seen)
    total = (n_cal_ep + n_eval_ep) * R
    # exact class mix, in random order
    plan = [KINDS[i % 100] for i in range(total)]
    rng.shuffle(plan)
    cases, rejected = [], 0
    for kind in plan:
        for _ in range(max_tries):
            c = make_one(gc, rng, kind, style)
            k = case_key(c)
            if k not in seen:
                seen.add(k)
                break
            rejected += 1
        else:
            raise RuntimeError("could not draw a unique %s report in %d tries" % (kind, max_tries))
        cases.append(c)
    for j, c in enumerate(cases):
        ep = j // R
        role = "fresh_cal" if ep < n_cal_ep else "fresh_eval"
        c["id"] = "f%06d" % (j + 1)
        c["split"] = role
        c["episode"] = ("FC%03d" % (ep + 1)) if role == "fresh_cal" else ("FE%04d" % (ep - n_cal_ep + 1))
        c["pos"] = j % R
        c["family"] = c["episode"]
    cases = [{"id": c["id"], **{k: v for k, v in c.items() if k != "id"}} for c in cases]
    return cases, {"rejected_duplicates": rejected, "dev_keys": n_dev_keys}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--cal-episodes", type=int, default=30)
    ap.add_argument("--eval-episodes", type=int, required=True)
    ap.add_argument("--R", type=int, default=20)
    ap.add_argument("--out", default=str(paths.HERE / "fresh"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pilot_cases = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
    cases, st = generate(a.seed, a.cal_episodes, a.eval_episodes, a.R, pilot_cases)
    f = out / "cases_fresh.jsonl"
    with open(f, "w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    mix = {}
    for c in cases:
        mix[c["type"]] = mix.get(c["type"], 0) + 1
    man = {"made": time.strftime("%Y-%m-%d %H:%M:%S"), "seed": a.seed, "style": "A", "R": a.R, "cal_episodes": a.cal_episodes,
           "eval_episodes": a.eval_episodes, "reports": len(cases), "class_mix": mix, "cases_sha256": paths.sha256_file(f),
           "pilot_files_read": {k: v for k, v in paths.PINS.items() if k.startswith("edgesar_pilot/")}, **st,
           "generator_sha256": paths.sha256_file(Path(__file__)),
           "note": "Inputs only. No model output was looked at. Roles: fresh_cal (conformal threshold and gate thresholds), fresh_eval (all reported numbers)."}
    (out / "generation_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
