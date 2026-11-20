"""
EdgeSAR heads - EXPLORATORY controls (step 4). No model and no server are needed: it reads the same feature files as step 3.

Why this exists: in attempt 1, "Q4 heads vs FP16 heads" disagreed on 27.5% of held-out reports. Two things changed at once
there: the vectors (the model was shrunk) AND the head (a new head was trained on the new vectors). These controls pull the
two apart. They also save every per-report answer, so any number can be checked by hand.

Controls (all use the SAME settings as step 3: C grid, folds, seed from heads_config.json):
  1. Separate heads          one head per precision (this is attempt 1; it must come back identical = the MATCH check)
  2. Fixed head              the FP16 head applied to FP16, Q8 and Q4 vectors (this is attempt 1 "transfer")
  3. Bootstrap-sample heads  heads trained on bootstrap samples of the SAME FP16 vectors (families resampled). The vectors do not
                             move, so any disagreement comes from the training sample (this is NOT a pure random-seed floor)
  4. Fixed head + offset fix the fixed head after removing the average shift of the Q4 (or Q8) vectors. The shift is measured on
                             dev A vectors only and uses NO labels
  5. Shared head             ONE head trained on FP16 + Q8 + Q4 vectors together (all three copies of a report stay in one fold)

Nothing here is tuned on held-out B. The C of every head is chosen inside its own training rows, as in step 3.
"""
import csv
import json
from collections import Counter, defaultdict

import numpy as np

import heads_lib as hl
from heads_common import CFG_SHA, HERE, now_text, pc

CONTROLS_CONFIG_PATH = HERE / "controls_config.json"
OUT_DIR_CONTROLS = HERE / "results_controls"
SPLITS = ("held", "dev", "all")
ARMS = ("FP16", "Q8", "Q4")
REC = hl.REC_ACTIONS

# ---- system names (the first five are the same words as in the attempt-1 report)
S_SEP = {"FP16": "Heads FP16", "Q8": "Heads Q8", "Q4": "Heads Q4"}
S_FIX = {"Q8": "FP16-trained heads on Q8 vectors", "Q4": "FP16-trained heads on Q4 vectors"}
S_OFF = {"Q8": "FP16-trained heads on Q8 vectors, offset removed", "Q4": "FP16-trained heads on Q4 vectors, offset removed"}
S_SHR = {"FP16": "Shared head on FP16 vectors", "Q8": "Shared head on Q8 vectors", "Q4": "Shared head on Q4 vectors"}

# ---- reading rules (written in CONTROLS_PLAN.md before the run; they are reading aids, not a registered test)
V1_BIG_SHARE = 0.5          # bootstrap-head disagreement >= half of the separate-heads disagreement -> "training-sample variability is big"
V2_ACC_TOLERANCE = 0.02     # shared head may lose at most 2 points of whole-record accuracy
V3_MIN_REDUCTION = 0.05     # offset fix must lower the fixed-head disagreement by >= 5 points ...
V3_MIN_SHARE_OF_HEADS = 0.90  # ... for at least 90% of the bootstrap heads


def load_controls_config(path=None):
    with open(path or CONTROLS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =================================================================== fitting
def fit_heads_and_apply(X_train_list, train_rows, y, rec, groups, X_apply, apply_rows, cfg, log=None):
    """Train the three heads on the rows `train_rows` of every matrix in X_train_list (stacked), then predict `apply_rows`
    of every matrix in X_apply. Several matrices = ONE shared head. The copies of a report keep the same group, so the
    inner cross-validation never puts two copies of one report (or family) on different sides.
    Returns {name: {head: (len(apply_rows), n_classes)}}."""
    train_rows = np.asarray(train_rows)
    apply_rows = np.asarray(apply_rows)
    k = len(X_train_list)
    out = {name: {} for name in X_apply}
    for h in hl.HEAD_CLASSES:
        rows = train_rows if h == "action" else train_rows[rec[train_rows]]
        Xtr = np.vstack([X[rows] for X in X_train_list])
        ytr = np.tile(y[h][rows], k)
        gtr = np.tile(groups[rows], k)
        model = hl.fit_head(Xtr, ytr, gtr, cfg["c_grid"], cfg["inner_folds"], log)
        for name, XA in X_apply.items():
            out[name][h] = hl.proba_fixed(model, XA[apply_rows], hl.HEAD_CLASSES[h])
    return out


def run_scheme_shared(X_list, X_apply, cases, dev_idx, held_idx, cfg, log=None, progress=None):
    """Same plan as hl.run_scheme (dev out-of-fold by family, held-out once), but ONE head trained on the stacked matrices."""
    y, rec = hl.make_labels(cases)
    plan, groups = hl.make_plan(cases, dev_idx, held_idx, cfg["outer_folds"])
    N = len(cases)
    out = {name: {h: np.zeros((N, len(hl.HEAD_CLASSES[h]))) for h in hl.HEAD_CLASSES} for name in X_apply}
    for fi, (tr, te) in enumerate(plan):
        P = fit_heads_and_apply(X_list, tr, y, rec, groups, X_apply, te, cfg, log)
        for name in X_apply:
            for h in hl.HEAD_CLASSES:
                out[name][h][te] = P[name][h]
        if progress:
            progress(fi + 1, len(plan))
    return out


def bootstrap_rows(dev_rows, groups, rs):
    """Resample whole FAMILIES (with replacement) from the dev rows. A family is the independent unit, so rows of one family
    always travel together. Returns the training row numbers (a family drawn twice appears twice)."""
    fam_rows = defaultdict(list)
    for r in dev_rows:
        fam_rows[groups[r]].append(int(r))
    fams = sorted(fam_rows)
    pick = rs.choice(len(fams), size=len(fams), replace=True)
    return np.array([r for j in pick for r in fam_rows[fams[j]]], dtype=int)


# =================================================================== the vector offset (no labels)
def offset_stats(X_ref, X_other, dev_idx):
    """delta = average of (other - ref) over the dev reports. No labels are used.
    'explained' = share of the average squared change of the vector that this one constant offset accounts for."""
    d = (X_other[dev_idx].astype(np.float64) - X_ref[dev_idx].astype(np.float64))
    delta = d.mean(axis=0)
    total = float((d ** 2).sum(axis=1).mean())
    resid = float(((d - delta) ** 2).sum(axis=1).mean())
    return delta.astype(np.float32), {"offset_norm": float(np.linalg.norm(delta)), "mean_change_norm": float(np.sqrt(total)),
                                      "explained": (1.0 - resid / total) if total > 0 else 0.0}


# =================================================================== measures
def gold_effects(cases):
    return [pc.effect(pc.gold_norm(c), c) for c in cases]


def field_accuracy(cases, D, idx):
    """Per-field accuracy. A field is counted only on reports whose GOLD answer has that field."""
    idx = list(idx)
    out = {"action": _share(sum(D[i]["norm"]["action"] == cases[i]["gold"]["action"] for i in idx), len(idx))}
    spec = (("location", "landmark", REC), ("sensor", "sensor", REC), ("priority", "priority", REC),
            ("link", "incident", ("UPDATE_INCIDENT", "CLOSE_INCIDENT")))
    for name, key, acts in spec:
        rows = [i for i in idx if cases[i]["gold"]["action"] in acts]
        ok = sum(D[i]["norm"].get(key) == cases[i]["gold"].get(key) for i in rows)
        out[name] = _share(ok, len(rows))
    return out


def _share(k, n):
    return [k, n, (k / n) if n else None]


def critical_counts(cases, D, idx, geff=None):
    """My proxies for 'a real person is hurt by this error' (the allocator harm test replaces them):
       missed_alarm     gold says CREATE/UPDATE, the system does nothing
       wrong_close      the system closes an incident that gold does not close (a live incident is dropped)
       priority_too_low same record action as gold, but a lower priority number (3 = most urgent)
       false_alarm      gold says NO_ACTION/CLOSE, the system starts or changes a record (a wasted trip; less serious)
       danger_total     missed_alarm + wrong_close + priority_too_low (a report is counted once; the three never overlap)"""
    geff = geff or gold_effects(cases)
    c = Counter()
    for i in idx:
        g, n = cases[i]["gold"], D[i]["norm"]
        ga, da = g["action"], n["action"]
        if ga in REC and da == "NO_ACTION":
            c["missed_alarm"] += 1
        elif da == "CLOSE_INCIDENT" and D[i]["eff"] != geff[i]:
            c["wrong_close"] += 1
        elif ga in REC and da == ga and int(n["priority"]) < int(g["priority"]):
            c["priority_too_low"] += 1
        if ga in ("NO_ACTION", "CLOSE_INCIDENT") and da in REC and D[i]["eff"] != ("NOOP",):
            c["false_alarm"] += 1
    c["danger_total"] = c["missed_alarm"] + c["wrong_close"] + c["priority_too_low"]
    return {k: int(c.get(k, 0)) for k in ("missed_alarm", "wrong_close", "priority_too_low", "danger_total", "false_alarm")}


def system_block(cases, D, idx, geff=None):
    a = hl.accuracy(cases, D, idx)
    return {"n": a["n"], "action": list(a["action"]), "record": list(a["record"]),
            "fields": field_accuracy(cases, D, idx), "critical": critical_counts(cases, D, idx, geff)}


def compare(cases, Ref, X, idx):
    """Pilot flip statistics, plus: how many reports changed their ACTION, and how many kept the action but changed a field."""
    idx = list(idx)
    f = hl.flip_stats(cases, Ref, X, idx)
    act = sum(Ref[i]["norm"]["action"] != X[i]["norm"]["action"] for i in idx)
    key = sum(Ref[i]["key"] != X[i]["key"] for i in idx)
    n = len(idx)
    return {"n": n, "table_changing": f["table_changing"], "table_ci": list(f["table_ci"]), "any_field": f["any_field"],
            "any_ci": list(f["any_ci"]), "action_changed": int(act), "action_ci": list(pc.wilson(int(act), n)),
            "same_action_field_change": int(key - act), "right_to_wrong": f["right_to_wrong"],
            "wrong_to_right": f["wrong_to_right"], "wrong_other": f["wrong_other"],
            "ref_already_wrong": hl.head_correct_split(cases, Ref, f["tab_mask"], idx),
            "top_transitions": [[k, v] for k, v in f["transitions"].most_common(5)]}


def spread(values):
    v = np.asarray(values, dtype=float)
    return {"mean": float(v.mean()), "median": float(np.median(v)), "min": float(v.min()), "max": float(v.max()), "n": int(len(v))}


# =================================================================== the bootstrap-sample heads
def run_bootstraps(cases, dev, held, X16, X_apply, ref_held, cfg, K, seed, log=None, progress=None, keep=None):
    """K heads trained on bootstrap samples of the FP16 vectors (families resampled), tested on held-out B only.
    ref_held = the full-data FP16 heads' decisions for the held rows (a list in held order).
    For each head we record:
       floor      bootstrap head vs the reference head, both on FP16 vectors (nothing but the training sample changed)
       fixed_*    the same bootstrap head on Q8/Q4 vectors vs on FP16 vectors (shrinking alone, readout fixed)
       off_*      the same, after the offset fix
    X_apply must hold the keys FP16, Q8, Q4, Q8s, Q4s.
    keep: if a list is given, every head's per-report decisions on all five vector sets are appended to it (for the export)."""
    y, rec = hl.make_labels(cases)
    groups = np.array([c["family"] for c in cases])
    dev = np.array(dev)
    held = np.array(held)
    sub = [cases[i] for i in held]
    rng_idx = list(range(len(sub)))
    geff = gold_effects(sub)
    runs, fp16_dec = [], []
    for b in range(K):
        rs = np.random.RandomState(seed + 1000 + b)
        rows = bootstrap_rows(dev, groups, rs)
        P = fit_heads_and_apply([X16], rows, y, rec, groups, X_apply, held, cfg, log)
        D = {name: hl.decisions_from_probs(sub, P[name]) for name in X_apply}
        fp16_dec.append(D["FP16"])
        if keep is not None:
            fam_rows = Counter(groups[rows])
            keep.append({"head_id": "boot_%02d" % (b + 1), "seed": int(seed + 1000 + b), "unique_families": int(len(fam_rows)),
                         "training_rows": int(len(rows)), "training_rows_per_family": {str(k): int(v) for k, v in sorted(fam_rows.items())},
                         "decisions": D})
        r = {"unique_families": int(len(set(groups[rows]))),
             "floor": compare(sub, ref_held, D["FP16"], rng_idx),
             "own_fp16": system_block(sub, D["FP16"], rng_idx, geff),
             "own_q4": system_block(sub, D["Q4"], rng_idx, geff)}
        for a, s in (("q8", "Q8"), ("q4", "Q4")):
            r["fixed_" + a] = compare(sub, D["FP16"], D[s], rng_idx)
            r["off_" + a] = compare(sub, D["FP16"], D[s + "s"], rng_idx)
            r["off_" + a + "_block"] = system_block(sub, D[s + "s"], rng_idx, geff)
        runs.append(r)
        if progress:
            progress(b + 1, K)
    pairs = [compare(sub, fp16_dec[j], fp16_dec[j + 1], rng_idx) for j in range(0, K - 1, 2)]
    n = len(sub)
    rate = lambda key, field="table_changing": [r[key][field] / n for r in runs]
    agg = {"K": K, "n": n, "unique_families_mean": float(np.mean([r["unique_families"] for r in runs])),
           "dev_families": int(len(set(groups[dev]))),
           "floor": spread(rate("floor")), "floor_action": spread(rate("floor", "action_changed")),
           "floor_pairs": spread([p["table_changing"] / n for p in pairs]) if pairs else None,
           "fixed_q8": spread(rate("fixed_q8")), "fixed_q4": spread(rate("fixed_q4")),
           "off_q8": spread(rate("off_q8")), "off_q4": spread(rate("off_q4")),
           "fixed_q4_action": spread(rate("fixed_q4", "action_changed")),
           "own_fp16_record": spread([r["own_fp16"]["record"][0] for r in runs]),
           "own_fp16_action": spread([r["own_fp16"]["action"][0] for r in runs]),
           "own_q4_record": spread([r["own_q4"]["record"][0] for r in runs]),
           "off_q4_record": spread([r["off_q4_block"]["record"][0] for r in runs]),
           "own_fp16_danger": spread([r["own_fp16"]["critical"]["danger_total"] for r in runs]),
           "off_q4_reduction": [(r["fixed_q4"]["table_changing"] - r["off_q4"]["table_changing"]) / n for r in runs],
           "off_q8_reduction": [(r["fixed_q8"]["table_changing"] - r["off_q8"]["table_changing"]) / n for r in runs]}
    return agg


# =================================================================== reading rules (pure functions: easy to test)
def verdict_noise(floor_rate, separate_rate):
    """V1. How big is the disagreement of bootstrap-sample heads (trained on resampled dev families) with the reference FP16 head,
    compared with the separate-heads disagreement? floor_rate = its mean on B. A reading aid only. It is not additive: the
    difference of the two numbers is NOT the quantization effect."""
    if separate_rate is None or separate_rate <= 0:
        return {"code": "NOT JUDGED", "share": None}
    share = floor_rate / separate_rate
    return {"code": "TRAINING-SAMPLE VARIABILITY IS BIG" if share >= V1_BIG_SHARE else "TRAINING-SAMPLE VARIABILITY IS SMALL", "share": share}


def verdict_shared(sep_rate, shr_rate, sep_record, shr_record, sep_danger, shr_danger):
    """V2. Does ONE shared head help for Q4? It must disagree less, keep whole-record accuracy, and not add danger errors."""
    lower = shr_rate < sep_rate
    acc_ok = shr_record >= sep_record - V2_ACC_TOLERANCE
    danger_ok = shr_danger <= sep_danger
    if not lower:
        code = "DOES NOT HELP"
    elif acc_ok and danger_ok:
        code = "HELPS"
    else:
        code = "MIXED"
    return {"code": code, "lower_disagreement": lower, "accuracy_kept": acc_ok, "danger_not_higher": danger_ok}


def verdict_offset(reductions, record_off_mean, record_fixed):
    """V3. Does removing the average shift of the Q4 vectors help the fixed head? Needs a clear drop for (nearly) every head."""
    r = np.asarray(reductions, dtype=float)
    share = float(np.mean(r >= V3_MIN_REDUCTION)) if len(r) else 0.0
    ok = share >= V3_MIN_SHARE_OF_HEADS and float(r.mean() if len(r) else 0) >= V3_MIN_REDUCTION and record_off_mean >= record_fixed
    return {"code": "HELPS" if ok else "NO CLEAR HELP", "share_of_heads_with_clear_drop": share,
            "mean_reduction": float(r.mean()) if len(r) else None}


# =================================================================== regression check against attempt 1
def check_attempt1(summary_path, variant, D, pairs):
    """Compare what this run recomputed with the numbers attempt 1 wrote. Same data + same settings must give the same numbers."""
    if not summary_path.exists():
        return {"status": "NO ATTEMPT-1 FILE", "lines": ["%s not found, so nothing to compare with." % summary_path.name]}
    S = json.loads(summary_path.read_text(encoding="utf-8"))["variants"].get(variant)
    if not S or "accuracy" not in S:
        return {"status": "NO ATTEMPT-1 FILE", "lines": ["the summary has no numbers for variant '%s'." % variant]}
    diffs, checked = [], 0
    for name, byspl in S["accuracy"].items():
        mine = D.get(name)
        if mine is None:
            continue
        for sp in SPLITS:
            checked += 1
            a, b = byspl[sp]["record"][0], mine[sp]["record"][0]
            if abs(a - b) > 1e-9:
                diffs.append("%s, %s, whole record: attempt 1 %.4f, now %.4f" % (name, sp, a, b))
    for kind, label in (("own", "Separate heads: %s vs FP16"), ("transfer", "Fixed FP16 head: %s vs FP16 vectors")):
        for a in ("Q8", "Q4"):
            for sp in SPLITS:
                checked += 1
                want = S["flips"][kind][a][sp]["table_changing"]
                got = pairs[label % a][sp]["table_changing"]
                if want != got:
                    diffs.append("%s, %s, table-changing: attempt 1 %d, now %d" % (label % a, sp, want, got))
    if diffs:
        return {"status": "DIFFERENT", "lines": diffs}
    return {"status": "MATCH", "lines": ["%d numbers checked: the same as attempt 1." % checked]}


# =================================================================== all the numbers
def analyze_controls(cases, dev, held, X16, X8, X4, G, B, cfg, ccfg, attempt1_path=None, say=print, kept_out=None):
    N = len(cases)
    idx = {"held": list(held), "dev": list(dev), "all": list(range(N))}
    geff = gold_effects(cases)
    log = hl.FitLog()
    prog = lambda tag: (lambda a, b: say("   fold %d of %d %s" % (a, b, tag)))

    dev_arr = np.array(dev)
    d8, off8 = offset_stats(X16, X8, dev_arr)
    d4, off4 = offset_stats(X16, X4, dev_arr)
    X8s, X4s = X8 - d8, X4 - d4

    say("1 of 4: separate heads and fixed head (the attempt-1 numbers, recomputed) ...")
    P16 = hl.run_scheme(X16, {"FP16": X16, "Q8": X8, "Q4": X4, "Q8s": X8s, "Q4s": X4s}, cases, dev, held, cfg, log=log, progress=prog("(FP16 heads)"))
    P8 = hl.run_scheme(X8, {"Q8": X8}, cases, dev, held, cfg, log=log, progress=prog("(Q8 heads)"))["Q8"]
    P4 = hl.run_scheme(X4, {"Q4": X4}, cases, dev, held, cfg, log=log, progress=prog("(Q4 heads)"))["Q4"]
    say("2 of 4: one shared head on FP16 + Q8 + Q4 vectors together ...")
    PS = run_scheme_shared([X16, X8, X4], {"FP16": X16, "Q8": X8, "Q4": X4}, cases, dev, held, cfg, log=log, progress=prog("(shared head)"))

    dec = lambda P: hl.decisions_from_probs(cases, P)
    D = {S_SEP["FP16"]: dec(P16["FP16"]), S_SEP["Q8"]: dec(P8), S_SEP["Q4"]: dec(P4),
         S_FIX["Q8"]: dec(P16["Q8"]), S_FIX["Q4"]: dec(P16["Q4"]),
         S_OFF["Q8"]: dec(P16["Q8s"]), S_OFF["Q4"]: dec(P16["Q4s"]),
         S_SHR["FP16"]: dec(PS["FP16"]), S_SHR["Q8"]: dec(PS["Q8"]), S_SHR["Q4"]: dec(PS["Q4"])}
    refs = {"Rule engine": B["rule"], "TF-IDF + LR": B["tfidf_lr"], "Generative FP16": G["FP16"],
            "Generative Q8": G["Q8"], "Generative Q4": G["Q4"]}
    ALL = dict(refs)
    ALL.update(D)

    systems = {name: {sp: system_block(cases, dec_, idx[sp], geff) for sp in SPLITS} for name, dec_ in ALL.items()}

    pair_defs = {}
    for a in ("Q8", "Q4"):
        pair_defs["Separate heads: %s vs FP16" % a] = (D[S_SEP["FP16"]], D[S_SEP[a]])
        pair_defs["Fixed FP16 head: %s vs FP16 vectors" % a] = (D[S_SEP["FP16"]], D[S_FIX[a]])
        pair_defs["Fixed FP16 head, offset removed: %s vs FP16 vectors" % a] = (D[S_SEP["FP16"]], D[S_OFF[a]])
        pair_defs["Shared head: %s vs FP16 vectors" % a] = (D[S_SHR["FP16"]], D[S_SHR[a]])
        pair_defs["Generative: %s vs FP16" % a] = (G["FP16"], G[a])
    pairs = {name: {sp: compare(cases, Ref, X, idx[sp]) for sp in SPLITS} for name, (Ref, X) in pair_defs.items()}
    held_fams = [cases[i]["family"] for i in held]
    for name, (Ref, X) in pair_defs.items():       # 40 families, not 400 independent reports: an interval that resamples whole families
        pairs[name]["held"]["table_family_ci"] = family_ci([Ref[i]["eff"] != X[i]["eff"] for i in held], held_fams)

    K = int(ccfg["bootstraps"])
    say("3 of 4: %d heads trained on bootstrap samples of the FP16 vectors (tested on held-out B only) ..." % K)
    ref_held = [D[S_SEP["FP16"]][i] for i in held]
    kept = [] if kept_out is not None else None
    boot = run_bootstraps(cases, dev, held, X16, {"FP16": X16, "Q8": X8, "Q4": X4, "Q8s": X8s, "Q4s": X4s}, ref_held, cfg, K,
                          int(ccfg["bootstrap_seed"]), log=log, progress=lambda a, b: say("   bootstrap head %d of %d" % (a, b)),
                          keep=kept)

    say("4 of 4: checking against attempt 1 and writing the reading ...")
    R = {"created": now_text(), "heads_config_sha": CFG_SHA, "n_cases": N, "n_dev": len(dev), "n_held": len(held),
         "variant": ccfg["variant"], "systems": systems, "pairs": pairs, "bootstrap": boot,
         "offset": {"Q8": off8, "Q4": off4},
         "fit_log": {"fits": log.fits, "hit_iteration_limit": log.hit_limit,
                     "chosen_c": {str(k): v for k, v in sorted(log.chosen_c.items())}}}
    R["attempt1_check"] = (check_attempt1(attempt1_path, ccfg["variant"], systems, pairs) if attempt1_path
                           else {"status": "NO ATTEMPT-1 FILE", "lines": ["not looked for."]})
    R["audit"] = audit_block(R)
    R["verdicts"] = verdicts(R)
    if kept_out is not None:
        kept_out.extend(kept)
    return R, ALL


def audit_block(R):
    """The audit of the number '27.5%': what it compares and how much of it is the ACTION field."""
    p = R["pairs"]["Separate heads: Q4 vs FP16"]["held"]
    a16 = R["systems"][S_SEP["FP16"]]["held"]
    a4 = R["systems"][S_SEP["Q4"]]["held"]
    n = p["n"]
    e16, e4 = n - a16["action"][0] * n, n - a4["action"][0] * n
    return {"n": n, "table_changing": p["table_changing"], "any_field": p["any_field"], "action_changed": p["action_changed"],
            "same_action_field_change": p["same_action_field_change"], "fp16_action_errors": int(round(e16)),
            "q4_action_errors": int(round(e4)), "action_upper_bound": int(round(e16 + e4)),
            "top_transitions": p["top_transitions"]}


def verdicts(R):
    n = R["n_held"]
    B_ = R["bootstrap"]
    V = {}
    floor = B_["floor"]["mean"]
    V["V1_noise"] = {a: verdict_noise(floor, R["pairs"]["Separate heads: %s vs FP16" % a]["held"]["table_changing"] / n)
                     for a in ("Q8", "Q4")}
    sep = R["pairs"]["Separate heads: Q4 vs FP16"]["held"]["table_changing"] / n
    shr = R["pairs"]["Shared head: Q4 vs FP16 vectors"]["held"]["table_changing"] / n
    sysr = R["systems"]
    V["V2_shared"] = verdict_shared(sep, shr, sysr[S_SEP["Q4"]]["held"]["record"][0], sysr[S_SHR["Q4"]]["held"]["record"][0],
                                    sysr[S_SEP["Q4"]]["held"]["critical"]["danger_total"],
                                    sysr[S_SHR["Q4"]]["held"]["critical"]["danger_total"])
    V["V3_offset"] = verdict_offset(B_["off_q4_reduction"], B_["off_q4_record"]["mean"], B_["own_q4_record"]["mean"])
    return V


# =================================================================== per-report answers (so every number can be checked by hand)
PRED_COLUMNS = ["system", "case_id", "split", "family", "gold_action", "gold_location", "gold_link", "gold_sensor", "gold_priority",
                "pred_action", "pred_location", "pred_link", "pred_sensor", "pred_priority", "status", "confidence", "record_ok",
                "action_ok"]


def write_predictions(path, cases, systems):
    """Long format: one row per (system, report). Open it in Excel and filter by system."""
    gold = [pc.gold_norm(c) for c in cases]
    n_rows = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(PRED_COLUMNS)
        for name, D in systems.items():
            for i, c in enumerate(cases):
                g, n = c["gold"], D[i]["norm"]
                conf = D[i].get("conf")
                w.writerow([name, c["id"], c["split"], c["family"], g["action"], g.get("landmark", ""), g.get("incident", ""),
                            g.get("sensor", ""), g.get("priority", ""), n["action"], n.get("landmark", ""), n.get("incident", ""),
                            n.get("sensor", ""), n.get("priority", ""), D[i].get("status", ""),
                            "" if conf is None else "%.4f" % conf, int(n == gold[i]), int(n["action"] == g["action"])])
                n_rows += 1
    return n_rows


# =================================================================== a family-level interval (40 families are the independent units, not 400 reports)
def family_ci(flags, families, B=2000, seed=20261112, level=0.95):
    """Share of True flags with a percentile interval from resampling whole FAMILIES with replacement.
    Returns [point, low, high]. This is a descriptive interval; the 20 bootstrap heads are not used here."""
    flags = np.asarray(flags, dtype=float)
    uniq, inv = np.unique(np.asarray(families), return_inverse=True)
    F = len(uniq)
    s, n = np.zeros(F), np.zeros(F)
    np.add.at(s, inv, flags)
    np.add.at(n, inv, 1.0)
    counts = np.random.default_rng(seed).multinomial(F, np.full(F, 1.0 / F), size=B)
    vals = (counts @ s) / (counts @ n)
    lo, hi = np.percentile(vals, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return [float(flags.mean()), float(lo), float(hi)]


# =================================================================== provenance: what exactly produced each saved answer
_TRAIN_A = ("dev A (1000 reports, 100 families). Dev rows are answered out-of-fold by family (5 folds); held-out B rows by the head "
            "trained on ALL of dev A.")
SYSTEM_INFO = {
    "Heads FP16": ("FP16", "separate head, trained on FP16 vectors", "FP16 vectors", _TRAIN_A),
    "Heads Q8": ("Q8", "separate head, trained on Q8 vectors", "Q8 vectors", _TRAIN_A),
    "Heads Q4": ("Q4", "separate head, trained on Q4 vectors", "Q4 vectors", _TRAIN_A),
    "FP16-trained heads on Q8 vectors": ("Q8", "fixed head (trained on FP16 vectors)", "Q8 vectors", _TRAIN_A + " Head trained on FP16 vectors."),
    "FP16-trained heads on Q4 vectors": ("Q4", "fixed head (trained on FP16 vectors)", "Q4 vectors", _TRAIN_A + " Head trained on FP16 vectors."),
    "FP16-trained heads on Q8 vectors, offset removed": ("Q8", "fixed head (trained on FP16 vectors), offset removed",
                                                         "Q8 vectors minus the mean (Q8-FP16) shift of the 1000 dev A reports", _TRAIN_A),
    "FP16-trained heads on Q4 vectors, offset removed": ("Q4", "fixed head (trained on FP16 vectors), offset removed",
                                                         "Q4 vectors minus the mean (Q4-FP16) shift of the 1000 dev A reports", _TRAIN_A),
    "Shared head on FP16 vectors": ("FP16", "one shared head trained on FP16+Q8+Q4 vectors", "FP16 vectors", _TRAIN_A + " Three copies of a report stay in one fold."),
    "Shared head on Q8 vectors": ("Q8", "one shared head trained on FP16+Q8+Q4 vectors", "Q8 vectors", _TRAIN_A + " Three copies of a report stay in one fold."),
    "Shared head on Q4 vectors": ("Q4", "one shared head trained on FP16+Q8+Q4 vectors", "Q4 vectors", _TRAIN_A + " Three copies of a report stay in one fold."),
    "Generative FP16": ("FP16", "pilot text writer (saved pilot run f16_P1)", "-", "no training here"),
    "Generative Q8": ("Q8", "pilot text writer (saved pilot run q8_P1)", "-", "no training here"),
    "Generative Q4": ("Q4", "pilot text writer (saved pilot run q4_P1)", "-", "no training here"),
    "TF-IDF + LR": ("n/a", "pilot TF-IDF + logistic regression", "report text", "dev A, cross-validated by the pilot code"),
    "Rule engine": ("n/a", "pilot hand-written rules", "report text", "written while style A was visible"),
}
PRED_COLUMNS_V2 = PRED_COLUMNS + ["precision", "head_type", "vectors_used", "training_data", "random_seed"]
BOOT_VECTORS = {"FP16": "FP16", "Q8": "Q8", "Q4": "Q4", "Q8s": "Q8-offset", "Q4s": "Q4-offset"}


def write_predictions_v2(path, cases, systems):
    """Same rows as write_predictions, plus provenance columns (precision, head type, vectors, training data, seed)."""
    base = path.with_name(path.name + ".tmp")
    n = write_predictions(base, cases, systems)
    with open(base, "r", encoding="utf-8", newline="") as f, open(path, "w", encoding="utf-8", newline="") as g:
        r, w = csv.reader(f), csv.writer(g)
        next(r)
        w.writerow(PRED_COLUMNS_V2)
        for row in r:
            prec, head, vec, train = SYSTEM_INFO.get(row[0], ("?", "?", "?", "?"))
            is_head = row[0].startswith(("Heads", "FP16-trained", "Shared"))
            w.writerow(row + [prec, head, vec, train, "none: lbfgs, no random_state, deterministic" if is_head else "-"])
    base.unlink()
    return n


def write_bootstrap_predictions(path, cases, held, kept):
    """One row per (bootstrap head, vector set, held-out B report). Vector sets: FP16, Q8, Q4, Q8-offset, Q4-offset."""
    gold = [pc.gold_norm(c) for c in cases]
    n_rows = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["head_id", "vector", "seed"] + PRED_COLUMNS + ["unique_training_families", "training_rows"])
        for h in kept:
            for key, vec in BOOT_VECTORS.items():
                D = h["decisions"][key]
                for k, i in enumerate(held):
                    c = cases[i]
                    g, nm = c["gold"], D[k]["norm"]
                    conf = D[k].get("conf")
                    w.writerow([h["head_id"], vec, h["seed"], "Bootstrap-sample head", c["id"], c["split"], c["family"], g["action"],
                                g.get("landmark", ""), g.get("incident", ""), g.get("sensor", ""), g.get("priority", ""), nm["action"],
                                nm.get("landmark", ""), nm.get("incident", ""), nm.get("sensor", ""), nm.get("priority", ""),
                                D[k].get("status", ""), "" if conf is None else "%.4f" % conf, int(nm == gold[i]),
                                int(nm["action"] == g["action"]), h["unique_families"], h["training_rows"]])
                    n_rows += 1
    return n_rows


def reproduction_check(ALL, legacy_path, cases):
    """Does this run give exactly the same per-report records as the saved run-1 file? (a consistency check, not a validation)"""
    if not legacy_path.exists():
        return {"status": "NO RUN-1 FILE", "rows_compared": 0, "rows_different": 0, "rows_missing_in_run1": 0, "per_system_different": {}}
    old = {}
    with open(legacy_path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            old[(r["system"], r["case_id"])] = (r["pred_action"], r["pred_location"], r["pred_link"], r["pred_sensor"], str(r["pred_priority"]))
    n = diff = missing = 0
    per = {}
    for name, D in ALL.items():
        d = 0
        for i, c in enumerate(cases):
            nm = D[i]["norm"]
            key = (nm["action"], nm.get("landmark", ""), nm.get("incident", ""), nm.get("sensor", ""), str(nm.get("priority", "")))
            o = old.get((name, c["id"]))
            n += 1
            if o is None:
                missing += 1
            elif o != key:
                d += 1
        per[name] = d
        diff += d
    ok = diff == 0 and missing == 0
    return {"status": "REPRODUCES RUN 1" if ok else "DIFFERENT FROM RUN 1", "rows_compared": n, "rows_different": diff,
            "rows_missing_in_run1": missing, "per_system_different": per}


def build_provenance(cases, dev, held, cfg, ccfg, R, kept, extra):
    """Everything needed to say exactly what produced the saved answers. `extra` carries hashes and versions from the driver."""
    groups = np.array([c["family"] for c in cases])
    o8, o4 = R["offset"]["Q8"], R["offset"]["Q4"]
    return {
        "written": now_text(), "status": "EXPLORATORY",
        "danger_error_definitions": {
            "note": "Rough proxies counted per report (a report is counted once in danger_total). They are NOT used in the harm test.",
            "missed_alarm": "gold action is CREATE_VERIFICATION or UPDATE_INCIDENT and the system's action is NO_ACTION",
            "wrong_close": "the system's action is CLOSE_INCIDENT and its effect on the task table differs from the gold effect (not counted if already a missed alarm)",
            "priority_too_low": "same action as gold (CREATE or UPDATE) but a numerically LOWER priority than gold (3 = most urgent)",
            "danger_total": "missed_alarm + wrong_close + priority_too_low (the three never overlap)",
            "false_alarm": "gold action is NO_ACTION or CLOSE_INCIDENT, the system CREATEs or UPDATEs, and the effect is not a no-op (a wasted trip; reported separately, not in danger_total)",
        },
        "heads": {
            "model": "StandardScaler + LogisticRegression(C chosen per head, lbfgs, max_iter=%d, tol=1e-3); three heads: action (4 classes), sensor (3), priority (3)" % hl.MAX_ITER,
            "c_grid": cfg["c_grid"], "c_selection": "grouped %d-fold log-loss inside the training rows of that head only" % cfg["inner_folds"],
            "random_state": "none is set, and no random seed is used anywhere in head training: the same data gives the same head (deterministic)",
            "seed_in_heads_config": "heads_config.json contains seed %s; it is NOT used by head training (only the bootstrap sampling uses controls_config.json bootstrap_seed)" % cfg["seed"],
            "outer_folds": "%d folds by family (GroupKFold, no shuffling) for dev A; held-out B is answered by heads trained on all of dev A" % cfg["outer_folds"],
            "matched_across_precisions": [
                "the same 1400 reports in the same order (checked with case_ids.json), the same dev/held split",
                "the same training reports for every head: dev A only (held-out B is never used for training)",
                "the same outer folds (GroupKFold on the same family labels gives the same folds for every precision)",
                "the same labels, the same C grid, the same pipeline (StandardScaler fitted on the training rows of each fit, then LogisticRegression)",
                "the same prompt (P1) and the same vector type: last-token hidden state, L2-normalised, 2048 numbers",
                "NOT matched on purpose: the vectors (they come from the shrunk model), and the C that each head picks inside its own training rows",
            ]},
        "offset": {
            "definition": "delta = mean over the 1000 dev A reports of (Q vector - FP16 vector); the Q vectors of all reports are replaced by Q - delta",
            "labels_used": False, "style_B_vectors_used": False,
            "dev_a_note": "The dev A out-of-fold answers use the same delta (computed from ALL 1000 dev vectors, including the vectors of the test fold). It is label-free, but the test-fold vectors take part in it.",
            "held_b_note": "Held-out B answers use a delta computed from dev A only.",
            "explained_definition": "explained = 1 - mean||d - delta||^2 / mean||d||^2 with d = Q - FP16 per report: the share of the average squared vector change that one constant shift accounts for. It is NOT a share of errors repaired.",
            "Q8": o8, "Q4": o4},
        "bootstrap_heads": {
            "count": int(ccfg["bootstraps"]), "bootstrap_seed": int(ccfg["bootstrap_seed"]),
            "seed_of_head_b": "bootstrap_seed + 1000 + b, b = 0..K-1 (head_id boot_01 is b = 0)",
            "sampling": "whole families of dev A are resampled with replacement (a family drawn twice appears twice); about 63-64% of the families are unique in each sample",
            "meaning": "bootstrap training-sample variability of the head on the SAME FP16 vectors. It is not a pure random-seed noise floor and it must not be subtracted from the separate-heads disagreement to get a quantization effect.",
            "tested_on": "held-out B only (400 reports, 40 families)",
            "dev_families": int(len(set(groups[dev]))), "held_families": int(len(set(groups[held]))),
            "heads": [{"head_id": h["head_id"], "seed": h["seed"], "unique_families": h["unique_families"], "training_rows": h["training_rows"]} for h in (kept or [])]},
        "how_the_two_percentages_are_formed": {
            "bootstrap_vs_reference": "mean over the bootstrap heads of the share of held-out B reports whose task table differs between the bootstrap head and the full-data FP16 head (both on FP16 vectors)",
            "bootstrap_vs_bootstrap": "the same share between two bootstrap heads, in consecutive pairs (head 1 vs 2, 3 vs 4, ...). Head vs head, so about twice the variability of head vs the full-data head.",
            "not_additive": "Neither number can be subtracted from the separate-heads disagreement to get a quantization effect."},
        **extra}
