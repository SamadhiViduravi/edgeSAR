"""Generative path (grammar-constrained JSON, greedy decoding): 4-way split of Q vs FP16 against the gold record.
Read-only on the pilot folder. Usage: python gen_path_split.py --root <folder with edgesar_pilot> --out out"""
import argparse, json, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args(); P = Path(a.root) / "edgesar_pilot"; sys.path.insert(0, str(P))
import common as pc

cases = [json.loads(l) for l in open(P / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
def load(run):
    d = {}
    for l in open(P / "runs" / (run + ".jsonl"), encoding="utf-8"):
        if l.strip():
            r = json.loads(l); d[r["case_id"]] = r
    return d
runs = {k: load(v) for k, v in (("f16", "f16_P1"), ("q8", "q8_P1"), ("q4", "q4_P1"), ("f16_rerun", "f16_P1_rerun"))}

def decide(r, c):
    obj, _ = pc.parse_decision(r["text"])
    norm, status = pc.validate(obj, c)
    fmt_ok = status not in ("fallback_unparsed", "fallback_schema")     # formatting / schema failure, separate from a wrong meaning
    return fmt_ok, norm, status

res = {}
for split in ("dev", "held", "all"):
    sub = [c for c in cases if split == "all" or c["split"] == split]
    out = {"n": len(sub)}
    D = {m: [decide(runs[m][c["id"]], c) for c in sub] for m in runs}
    gold = [pc.gold_norm(c) for c in sub]
    for m in runs:
        out[m] = {"format_fail": sum(not d[0] for d in D[m]),
                  "record_correct": sum(pc.strict_key(d[1]) == pc.strict_key(g) for d, g in zip(D[m], gold)),
                  "action_correct": sum(d[1]["action"] == g["action"] for d, g in zip(D[m], gold)),
                  "status": dict(Counter(d[2] for d in D[m]).most_common())}
    for q in ("q8", "q4", "f16_rerun"):
        for level, same in (("record", lambda x, y: pc.strict_key(x) == pc.strict_key(y)), ("action", lambda x, y: x["action"] == y["action"])):
            cnt = Counter()
            for dr, dq, g in zip(D["f16"], D[q], gold):
                r_ok, q_ok = same(dr[1], g), same(dq[1], g)
                changed = not same(dr[1], dq[1])
                k = ("both_right" if r_ok and q_ok else "harmful_r_right_q_wrong" if r_ok else "beneficial_r_wrong_q_right" if q_ok
                     else "both_wrong_same" if not changed else "both_wrong_different")
                cnt[k] += 1
                cnt["changed"] += changed
            out["%s_vs_f16_%s" % (q, level)] = dict(cnt)
    res[split] = out
Path(a.out).mkdir(exist_ok=True, parents=True)
(Path(a.out) / "gen_path_split.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for split, o in res.items():
    print("==", split, "n", o["n"])
    for m in runs:
        print("  %-10s format_fail %d  record_ok %d (%.1f%%)  action_ok %d (%.1f%%)" % (m, o[m]["format_fail"], o[m]["record_correct"], 100*o[m]["record_correct"]/o["n"], o[m]["action_correct"], 100*o[m]["action_correct"]/o["n"]))
    for k in o:
        if "_vs_f16_" in k: print("  ", k, o[k])
