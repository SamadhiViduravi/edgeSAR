"""
Baselines for the pilot (no language model):
  - always NO_ACTION, always VERIFY (CREATE_VERIFICATION)      -> the two floors
  - Rule      : a keyword rule engine that a careful engineer could write in an afternoon.
                It uses words from the DEVELOPMENT style (A) only.
  - TF-IDF/LR : TF-IDF + logistic regression, trained on the DEVELOPMENT cases (style A) only.
                On development cases its answers come from 5-fold cross-validation (grouped by family),
                so it never predicts a case it was trained on.
Both baselines output the same normalised decision as the model, so they go through the same validator.

Warning (also in the report): the cases are templated, and the Rule was written by someone who knows the
templates. Rule and TF-IDF/LR can look better here than they would on real messages.
"""
import re

from common import LANDMARKS, validate

# ------------------------------------------------------------------ word lists (development style only)
PERSON = ["person", "people", "family", "child", "kid", "man", "woman", "survivor", "elderly", "injured", "couple"]
VULNERABLE = ["child", "kid", "elderly", "old man", "old woman", "injured", "cannot walk"]
HAZARD = ["rising", "climbing", "fire", "flames", "collapse", "giving way"]
UNCONFIRMED = ["possible", "might be", "could be", "cannot confirm", "unclear"]
CLOSE_WORDS = ["safe", "evacuated", "false alarm", "resolved", "rescued", "walked out", "cleared"]
UNCHANGED = ["no change", "still seeing", "same as before", "unchanged"]
NEGATION = ["no people", "nobody", "no one", "empty", "no person", "no humans"]
NONHUMAN = ["cattle", "abandoned car", "livestock", "vehicle"]
DARK = ["dark", "night", "smoke", "fog"]
CLEAR = ["daylight", "good visibility"]
MOVE_RE = re.compile(r"(moved to|are now at|now at|relocated to)")
ID_RE = re.compile(r"\bI(\d+)\b")


def _mentioned_landmarks(text):
    """Landmarks in the order they appear in the text."""
    found = []
    for lm in LANDMARKS:
        i = text.find(lm)
        if i >= 0:
            found.append((i, lm))
    return [lm for _, lm in sorted(found)]


def find_target(case):
    """The open incident the report is about: an id written in the text, else the first open landmark mentioned."""
    text = case["text"]
    open_by_id = {i["id"]: i for i in case["open"]}
    for m in ID_RE.finditer(text):
        k = "I" + m.group(1)
        if k in open_by_id:
            return open_by_id[k]
    open_by_lm = {i["landmark"]: i for i in case["open"]}
    for lm in _mentioned_landmarks(text):
        if lm in open_by_lm:
            return open_by_lm[lm]
    return None


def _any(words, t):
    return any(w in t for w in words)


def _sensor_from_text(t):
    if _any(DARK, t):
        return "THERMAL"
    if _any(CLEAR, t):
        return "RGB"
    return None


# ------------------------------------------------------------------ floors
def always_no_action(case):
    return {"action": "NO_ACTION"}


def always_verify(case):
    # a CREATE with the most common field values; only the ACTION of this floor is scored
    return {"action": "CREATE_VERIFICATION", "landmark": LANDMARKS[0], "sensor": "ANY", "priority": 2}


# ------------------------------------------------------------------ rule engine
def rule_decision(case):
    t = case["text"].lower()
    lms = _mentioned_landmarks(case["text"])
    tgt = find_target(case)
    if tgt is not None:
        if _any(CLOSE_WORDS, t):
            return {"action": "CLOSE_INCIDENT", "incident": tgt["id"]}
        rec = {"landmark": tgt["landmark"], "sensor": tgt["sensor"], "priority": tgt["priority"]}
        changed = False
        mv = MOVE_RE.search(t)
        if mv:
            others = [l for l in lms if l != tgt["landmark"]]
            if others:
                rec["landmark"] = others[-1]
                changed = True
        if not changed and _any(UNCHANGED, t):
            return {"action": "NO_ACTION"}
        if (_any(VULNERABLE, t) or _any(HAZARD, t)) and rec["priority"] < 3:
            rec["priority"] = 3
            changed = True
        s = _sensor_from_text(t)
        if s and s != rec["sensor"]:
            rec["sensor"] = s
            changed = True
        if changed:
            return {"action": "UPDATE_INCIDENT", "incident": tgt["id"], **rec}
        return {"action": "NO_ACTION"}
    # no open incident is the subject of the report
    free = [l for l in lms]
    if free and _any(PERSON, t) and not _any(NEGATION, t) and not _any(NONHUMAN, t):
        if _any(VULNERABLE, t) or _any(HAZARD, t):
            prio = 3
        elif _any(UNCONFIRMED, t):
            prio = 1
        else:
            prio = 2
        return {"action": "CREATE_VERIFICATION", "landmark": free[0],
                "sensor": _sensor_from_text(t) or "ANY", "priority": prio}
    return {"action": "NO_ACTION"}


# ------------------------------------------------------------------ TF-IDF + logistic regression
def lr_text(case):
    tgt = find_target(case)
    flags = ["zzopen%d" % len(case["open"])]
    flags.append("zztarget" if tgt else "zznotarget")
    if tgt:
        flags += ["zzcursensor" + tgt["sensor"].lower(), "zzcurprio%d" % tgt["priority"]]
    if ID_RE.search(case["text"]):
        flags.append("zzidmention")
    return case["text"].lower() + " " + " ".join(flags)


def _make_pipe():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2),
                         LogisticRegression(C=10.0, max_iter=5000))


class LRBaseline:
    def __init__(self):
        self.action = _make_pipe()
        self.sensor = _make_pipe()
        self.prio = _make_pipe()

    def fit(self, cases):
        X = [lr_text(c) for c in cases]
        self.action.fit(X, [c["gold"]["action"] for c in cases])
        rec = [c for c in cases if c["gold"]["action"] in ("CREATE_VERIFICATION", "UPDATE_INCIDENT")]
        Xr = [lr_text(c) for c in rec]
        self.sensor.fit(Xr, [c["gold"]["sensor"] for c in rec])
        self.prio.fit(Xr, [str(c["gold"]["priority"]) for c in rec])
        return self

    def predict(self, cases):
        X = [lr_text(c) for c in cases]
        acts = self.action.predict(X)
        sens = self.sensor.predict(X)
        prios = self.prio.predict(X)
        out = []
        for c, a, s, p in zip(cases, acts, sens, prios):
            out.append(_assemble(c, a, s, int(p)))
        return out


def _assemble(case, action, sensor, prio):
    """Turn the three classifier answers into one decision (landmark and incident come from string matching)."""
    lms = _mentioned_landmarks(case["text"])
    tgt = find_target(case)
    if action == "CLOSE_INCIDENT" and tgt:
        return {"action": action, "incident": tgt["id"]}
    if action == "UPDATE_INCIDENT" and tgt:
        lm = tgt["landmark"]
        if MOVE_RE.search(case["text"].lower()):
            others = [l for l in lms if l != tgt["landmark"]]
            if others:
                lm = others[-1]
        return {"action": action, "incident": tgt["id"], "landmark": lm, "sensor": sensor, "priority": prio}
    if action == "CREATE_VERIFICATION" and lms:
        return {"action": action, "landmark": lms[0], "sensor": sensor, "priority": prio}
    return {"action": "NO_ACTION"}


def lr_predictions(dev_cases, held_cases, folds=5):
    """Return {case_id: normalised decision}. Development = out-of-fold; held-out = model trained on all development."""
    from sklearn.model_selection import GroupKFold
    preds = {}
    groups = [c["family"] for c in dev_cases]
    gkf = GroupKFold(n_splits=folds)
    for tr, te in gkf.split(dev_cases, groups=groups):
        m = LRBaseline().fit([dev_cases[i] for i in tr])
        sub = [dev_cases[i] for i in te]
        for c, d in zip(sub, m.predict(sub)):
            preds[c["id"]] = d
    m = LRBaseline().fit(dev_cases)
    for c, d in zip(held_cases, m.predict(held_cases)):
        preds[c["id"]] = d
    return preds


def baseline_table(cases, with_lr=True):
    """{name: {case_id: norm}} for floors, rule and (optionally) the classifier. All go through validate()."""
    out = {"always_NO_ACTION": {}, "always_VERIFY": {}, "rule": {}}
    for c in cases:
        out["always_NO_ACTION"][c["id"]] = validate(always_no_action(c), c)[0]
        out["always_VERIFY"][c["id"]] = validate(always_verify(c), c)[0]
        out["rule"][c["id"]] = validate(rule_decision(c), c)[0]
    if with_lr:
        dev = [c for c in cases if c["split"] == "dev"]
        held = [c for c in cases if c["split"] == "held"]
        raw = lr_predictions(dev, held)
        out["tfidf_lr"] = {c["id"]: validate(raw[c["id"]], c)[0] for c in cases}
    return out
