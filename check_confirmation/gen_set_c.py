"""
Make the NEW reports (set C) for PROTOCOL_CHECK_CONFIRM.md (inputs only: texts, open tables, gold records). CPU only, no model.
Same generator and rules as gen_fresh.py (18 Nov 2026); new seeds; a report that is already among the 1,400 development reports or the
7,000 fresh reports of the first confirmation is thrown away and drawn again.

    python gen_set_c.py --root <ROOT> --fresh <cases_fresh.jsonl> --out .

Two sets:
    C1  3,000 reports in the development wording (style A), seed 20261126, 150 episodes of 20 (K1001..K1150) -> split check_eval_C1
    C2  2,000 reports in the new wording (style B),         seed 20261127, 100 episodes of 20 (K2001..K2100) -> split check_eval_C2
Class mix as the pilot (CREATE 25%, UPDATE 20%, CLOSE 15%, NO_ACTION 40% in four kinds). A report whose (text, open table, gold record) is already
in the 1,400 development reports or earlier in this file is thrown away and drawn again; the number of throw-aways is logged.
Writes cases_C.jsonl and generation_manifest_C.json.
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
SETS = [("C1", "A", 20261126, 150), ("C2", "B", 20261127, 100)]       # (set, style, seed, episodes)
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
    ap.add_argument("--fresh", required=True, help="cases_fresh.jsonl of the first confirmation")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    pilot = Path(a.root) / "edgesar_pilot"
    if sha(pilot / "gen_cases.py") != GEN_SHA:
        raise SystemExit("edgesar_pilot/gen_cases.py is not the pinned version. Stop.")
    sys.path.insert(0, str(pilot))
    import gen_cases as gc
    dev = [json.loads(l) for l in open(pilot / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
    fresh = [json.loads(l) for l in open(a.fresh, encoding="utf-8") if l.strip()]
    assert sha(a.fresh) == "115e09d8780771beb0e3721feb74ba8b83333e9a230b74dc863023e508e7414b", "not the fresh reports of the first confirmation"
    seen = {case_key(c) for c in dev} | {case_key(c) for c in fresh}
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
            c2 = {"id": "k%s%05d" % (st[1], j + 1)}
            c2.update(c)
            c2.update({"split": "check_eval_" + st, "episode": "K%s%03d" % (st[1], ep + 1), "pos": j % R, "family": "K%s%03d" % (st[1], ep + 1)})
            out_cases.append(c2)
        dev_texts = {c["text"] for c in dev}
        fresh_texts = {c["text"] for c in fresh}
        stats[st] = {"style": style, "seed": seed, "episodes": n_ep, "reports": total, "rejected_duplicates": rejected,
                     "text_identical_to_a_development_text": sum(c["text"] in dev_texts for c in cs),
                     "text_identical_to_a_fresh_text": sum(c["text"] in fresh_texts for c in cs),
                     "class_mix": {t: sum(c["type"] == t for c in cs) for t in sorted({c["type"] for c in cs})}}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / "cases_C.jsonl"
    with open(f, "w", encoding="utf-8", newline="\n") as fh:
        for c in out_cases:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    man = {"made": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "R": R, "sets": stats, "reports": len(out_cases),
           "cases_sha256": sha(f), "gen_cases_sha256": GEN_SHA, "development_cases_sha256": sha(pilot / "data" / "cases.jsonl"),
           "fresh_cases_sha256": sha(a.fresh),
           "script_sha256": sha(__file__), "note": "Inputs only. No model output was looked at."}
    (out / "generation_manifest_C.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
