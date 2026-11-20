"""
Make the FRESH reports for PROTOCOL_FRESH_CONFIRM.md (inputs only: texts, open tables, gold records). CPU only, no model.

    python gen_fresh.py --root <ROOT> --out fresh

Uses the pilot's own generator functions (edgesar_pilot/gen_cases.py, SHA-256 pinned) exactly like edgesar_shield/tools/gen_episodes_fresh.py
(13 Nov 2026), with two sets:
    A  6,000 reports in the development wording (style A), seed 20261118, 300 episodes of 20 (FA001..FA300)   -> split fresh_eval_A (primary)
    B  1,000 reports in the new wording (style B),        seed 20261119,  50 episodes of 20 (FB001..FB050)   -> split fresh_eval_B (secondary)
Class mix as the pilot (CREATE 25%, UPDATE 20%, CLOSE 15%, NO_ACTION 40% in four kinds). A report whose (text, open table, gold record) is already
in the 1,400 development reports or earlier in this file is thrown away and drawn again; the number of throw-aways is logged.
Writes fresh/cases_fresh.jsonl and fresh/generation_manifest.json.
"""
import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
KINDS = (["create"] * 25 + ["update"] * 20 + ["close"] * 15 + ["chatter"] * 10 + ["duplicate"] * 10 + ["nonhuman"] * 10 + ["negation"] * 10)
SETS = [("A", "A", 20261118, 300), ("B", "B", 20261119, 50)]          # (set, style, seed, episodes)
R = 20
GEN_SHA = "b65695c5b2b5e9a959645f0d8a317d9ed80935212db5b19cff940e0aac978e39"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canon_open(open_list):
    return tuple(sorted((i["id"], i["landmark"], i["sensor"], i["priority"]) for i in open_list))


def case_key(c):
    return (c["text"], canon_open(c["open"]), json.dumps(c["gold"], sort_keys=True))


def make_one(gc, rng, kind, style):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="fresh")
    a = ap.parse_args()
    pilot = Path(a.root) / "edgesar_pilot"
    if sha(pilot / "gen_cases.py") != GEN_SHA:
        raise SystemExit("edgesar_pilot/gen_cases.py is not the pinned version. Stop.")
    sys.path.insert(0, str(pilot))
    import gen_cases as gc
    dev = [json.loads(l) for l in open(pilot / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
    seen = {case_key(c) for c in dev}
    out_cases, stats = [], {}
    for st, style, seed, n_ep in SETS:
        rng = random.Random(seed)
        total = n_ep * R
        plan = [KINDS[i % 100] for i in range(total)]
        rng.shuffle(plan)
        rejected = 0
        cs = []
        for kind in plan:
            for _ in range(200):
                c = make_one(gc, rng, kind, style)
                k = case_key(c)
                if k not in seen:
                    seen.add(k)
                    break
                rejected += 1
            else:
                raise SystemExit("could not draw a unique %s report" % kind)
            cs.append(c)
        for j, c in enumerate(cs):
            ep = j // R
            c2 = {"id": "f%s%05d" % (st.lower(), j + 1)}
            c2.update(c)
            c2.update({"split": "fresh_eval_" + st, "episode": "F%s%03d" % (st, ep + 1), "pos": j % R, "family": "F%s%03d" % (st, ep + 1)})
            out_cases.append(c2)
        dev_texts = {c["text"] for c in dev}
        stats[st] = {"style": style, "seed": seed, "episodes": n_ep, "reports": total, "rejected_duplicates": rejected,
                     "text_identical_to_a_development_text": sum(c["text"] in dev_texts for c in cs),
                     "class_mix": {t: sum(c["type"] == t for c in cs) for t in sorted({c["type"] for c in cs})}}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / "cases_fresh.jsonl"
    with open(f, "w", encoding="utf-8", newline="\n") as fh:
        for c in out_cases:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    man = {"made": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "R": R, "sets": stats, "reports": len(out_cases),
           "cases_sha256": sha(f), "gen_cases_sha256": GEN_SHA, "development_cases_sha256": sha(pilot / "data" / "cases.jsonl"),
           "script_sha256": sha(__file__), "note": "Inputs only. No model output was looked at."}
    (out / "generation_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
