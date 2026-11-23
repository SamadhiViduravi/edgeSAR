"""
Exploratory (not pre-registered), added 23 Nov 2026: overlap of the fresh reports with the development reports,
counted separately against the 1,000 style-A fitting reports, the 400 style-B development (evaluation-only) reports
and all 1,400 (Table 6 of the paper). Masked template = template_key(): text with landmarks, incident ids, sources
and numbers masked.

    python review_overlap.py --root ROOT --cases fresh/cases_fresh.jsonl --out out_review
"""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = Path(a.root)
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "repair_package"))
    sys.path.insert(0, str(root / "edgesar_shield"))
    sys.path.insert(0, str(root / "edgesar_heads"))
    from ppr_lib import Data, template_key
    D = Data(root)
    pc = D.pc
    ev = [json.loads(l) for l in open(a.cases, encoding="utf-8")]
    sets = {"A": [c for c in ev if c["split"] == "fresh_eval_A"], "B": [c for c in ev if c["split"] == "fresh_eval_B"]}
    pops = {"fit1000_styleA": [c for c in D.cases if c["split"] == "dev"],
            "eval400_styleB": [c for c in D.cases if c["split"] == "held"],
            "all1400": list(D.cases)}
    res = {"note": __doc__.strip().splitlines()[0]}
    for pn, pcs in pops.items():
        texts = {c["text"] for c in pcs}
        keys = {template_key(c["text"], pc.LANDMARKS) for c in pcs}
        for st, cs in sets.items():
            tk = [template_key(c["text"], pc.LANDMARKS) for c in cs]
            res["%s_vs_%s" % (st, pn)] = {"reports": len(cs), "text_identical": sum(c["text"] in texts for c in cs),
                                          "masked_template_seen": sum(t in keys for t in tk), "distinct_masked_templates": len(set(tk)),
                                          "distinct_not_seen": len(set(tk) - keys)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "review_overlap_by_population.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
