"""
Make the pilot cases. Every case is one field report plus the list of open incidents.
The correct answer ("gold") is known by construction, because the report is written from facts
that the generator chose first (who, how many, danger, visibility, which incident).

Two writing styles:
  A = development style   (used to write the Rule baseline and to train the TF-IDF/LR baseline)
  B = held-out style      (different words and sentence shapes; no baseline has seen it)

Run:  python gen_cases.py            (writes data/cases.jsonl, data/subsets.json, data/audit_sample.csv)
The seed is fixed, so everyone who runs it gets the same 1,400 cases.
"""
import argparse
import csv
import json
import random
from pathlib import Path

from common import LANDMARKS, SENSORS, ROOT, render_open

SOURCES = ["UAV1", "UAV2", "UAV3", "Ground team", "Command post"]

# ---------------------------------------------------------------- word banks
WHO = {  # key -> {style: phrases}
    "single":  {"A": ["a person", "one person", "a man", "a woman"], "B": ["an individual", "a lone survivor", "one adult"]},
    "pair":    {"A": ["two people", "a couple of people"], "B": ["a pair of survivors", "two individuals"]},
    "family":  {"A": ["a family of four", "a family with their bags"], "B": ["a household of five", "relatives huddled together"]},
    "group":   {"A": ["several people", "a group of people", "about six people"], "B": ["a cluster of survivors", "a crowd of residents"]},
    "child":   {"A": ["a small child", "a child", "a kid"], "B": ["a minor", "a young boy", "an infant"]},
    "elderly": {"A": ["an elderly person", "an old man", "an old woman"], "B": ["a senior citizen", "an aged resident"]},
    "injured": {"A": ["an injured person", "a person who cannot walk"], "B": ["a casualty", "someone bleeding and unable to move"]},
}
VULN = {"child", "elderly", "injured"}
VERB = {
    "A": ["waving for help", "standing on a rooftop", "stranded on a roof", "calling out for help", "clinging to a fence"],
    "B": ["signalling for rescue", "marooned atop a structure", "shouting for assistance", "sheltering on high ground", "gesturing at the drone"],
}
UNCONF = {
    "A": ["Possible movement near {L}, cannot confirm a person.", "Something that might be a person at {L}.",
          "Unclear shape at {L} that could be a person."],
    "B": ["Tentative motion detected around {L}, identity uncertain.", "An ambiguous figure near {L}, may or may not be human.",
          "Faint activity at {L}, unverified."],
}
HAZ = {
    "water":    {"A": ["Water is rising fast.", "The water level is climbing."], "B": ["Floodwater is surging upward.", "The current is intensifying and the level is increasing."]},
    "fire":     {"A": ["There is a fire close by.", "Flames are spreading toward them."], "B": ["A blaze is advancing on their position.", "Burning debris is adjacent to them."]},
    "collapse": {"A": ["The roof is starting to collapse.", "The wall is giving way."], "B": ["The structure is failing.", "Masonry is crumbling beneath them."]},
}
VIS = {
    "night": {"A": ["It is dark.", "Night conditions."], "B": ["Low light, after sunset.", "Visibility is nil without illumination."]},
    "smoke": {"A": ["Heavy smoke here.", "Smoke is covering the area."], "B": ["Dense haze from burning material.", "A thick plume obscures the ground."]},
    "fog":   {"A": ["Thick fog.", "Fog is covering the water."], "B": ["Heavy mist over the water.", "Dense low cloud at ground level."]},
    "day":   {"A": ["Clear daylight.", "Good visibility."], "B": ["Full sun, unobstructed view.", "Excellent line of sight in daylight."]},
}
VIS_SENSOR = {"night": "THERMAL", "smoke": "THERMAL", "fog": "THERMAL", "day": "RGB", None: "ANY"}
VULN_ADD = {
    "A": ["A small child is also with them.", "An elderly person is also with them.", "One of them is injured."],
    "B": ["A minor has been spotted among the group.", "A senior citizen is part of the group.", "One individual appears to be hurt."],
}
CREATE_T = {
    "A": ["{src} reports {who} {verb} at {L}.", "At {L}: {who} {verb}.", "{src}: {who} seen at {L}, {verb}."],
    "B": ["{src} - {L}: {who}, {verb}.", "Observation at {L}: {who} {verb}.", "Sighting by {src}: {who} {verb} near {L}."],
}
ESC_T = {
    "A": ["{src}: update at {L}. {x} Worse than first reported.", "{src}: {L} has changed. {x}"],
    "B": ["{src} - {L}: conditions have deteriorated. {x}", "Re-check of {L} by {src}: {x}"],
}
SENS_T = {  # to THERMAL / to RGB
    "A": {"THERMAL": "{src}: at {L} now. {v} The visible camera cannot see anything there.",
          "RGB": "{src}: at {L} now. {v} The visible camera works well again."},
    "B": {"THERMAL": "{src} - {L}: {v} The optical feed is unusable.",
          "RGB": "{src} - {L}: {v} The optical feed is fully usable."},
}
MOVE_T = {
    "A": ["{src}: the people from {old} have moved to {new}.", "{src}: they left {old} and are now at {new}."],
    "B": ["{src}: survivors previously at {old} relocated to {new}.", "{src}: the group formerly at {old} is now at {new}."],
}
CLOSE_T = {
    "rescued": {"A": ["{src}: ground team reached {L}. Everyone is safe and has been evacuated.", "{src}: {L} is resolved, all rescued."],
                "B": ["{src}: personnel extracted the individuals at {L}; the site is cleared.", "{src}: operation at {L} concluded, occupants recovered."]},
    "false":   {"A": ["{src}: false alarm at {L}. It was {thing}, nobody there.", "{src}: checked {L}, it was only {thing}."],
                "B": ["{src}: closer inspection of {L} shows {thing}; no humans present.", "{src}: the {L} contact was {thing}, not a person."]},
    "self":    {"A": ["{src}: the people at {L} walked out to the main road on their own."],
                "B": ["{src}: occupants of {L} observed departing under their own power."]},
}
THINGS = {"A": ["a tarp", "a scarecrow", "floating debris", "a bundle of clothes"],
          "B": ["a discarded tarpaulin", "a mannequin", "drifting wreckage"]}
CHATTER = {
    "A": ["{src}: battery at {n} percent, returning to charge.", "{src}: wind is picking up from the west.",
          "{src}: reached waypoint {k}, nothing to report.", "{src}: camera calibration finished."],
    "B": ["{src} reports remaining endurance {n} percent; heading to base.", "{src}: gusts increasing out of the west.",
          "{src}: transit leg {k} complete, no observations.", "{src}: sensor self-test complete."],
}
DISTRACT = {
    "A": ["Battery at {n} percent.", "Wind is picking up.", "Next waypoint reached.", "Radio check ok."],
    "B": ["Endurance {n} percent remaining.", "Gusts are increasing.", "Waypoint transit complete.", "Link quality nominal."],
}
DUP_T = {"A": ["{src}: still seeing the same people at {L}, no change.", "{src}: {L} looks the same as before."],
         "B": ["{src}: situation at {L} unchanged; same individuals present.", "{src}: no difference at {L} since the last pass."]}
NONHUMAN_T = {"A": ["{src}: only cattle at {L}, nobody visible.", "{src}: an abandoned car at {L}, no one inside."],
              "B": ["{src}: livestock near {L}, no humans detected.", "{src}: an unoccupied vehicle at {L}; nobody aboard."]}
NEG_T = {"A": ["{src}: searched {L}, no people found.", "{src}: {L} is empty, nobody there."],
         "B": ["{src}: sweep of {L} complete; no humans located.", "{src}: nothing living at {L}."]}


# ---------------------------------------------------------------- helpers
def cap(s):
    return s[0].upper() + s[1:] if s else s


def tidy(s):
    s = " ".join(s.split())
    return cap(s)


def make_open(rng, n, avoid=()):
    lms = rng.sample([l for l in LANDMARKS if l not in avoid], n)
    ids = sorted(rng.sample(range(1, 15), n))
    return [{"id": "I%d" % i, "landmark": lm, "sensor": rng.choice(SENSORS), "priority": rng.choice([1, 2, 3])}
            for i, lm in zip(ids, lms)]


def rand_time(rng):
    return "%02d:%02d" % (rng.randint(6, 23), rng.randint(0, 59))


def maybe_distract(rng, style, text, p=0.25):
    if rng.random() < p:
        d = rng.choice(DISTRACT[style]).format(n=rng.choice([22, 35, 41, 58]))
        return text + " " + d
    return text


def id_hint(rng, style, text, inc_id, p):
    if rng.random() < p:
        return ("Re %s: %s" % (inc_id, text)) if style == "A" else ("%s (ref %s)" % (text, inc_id))
    return text


# ---------------------------------------------------------------- case makers
def make_create(rng, style):
    n_open = rng.choices([0, 1, 2, 3, 4], [0.2, 0.3, 0.25, 0.15, 0.1])[0]
    open_ = make_open(rng, n_open)
    free = [l for l in LANDMARKS if l not in {i["landmark"] for i in open_}]
    L = rng.choice(free)
    src = rng.choice(SOURCES)
    vis = rng.choices(["night", "smoke", "fog", "day", None], [0.2, 0.12, 0.08, 0.3, 0.3])[0]
    vis_s = rng.choice(VIS[vis][style]) if vis else ""
    if rng.random() < 0.2:  # unconfirmed sighting
        text = rng.choice(UNCONF[style]).format(L=L)
        if vis_s:
            text += " " + vis_s
        prio, sub = 1, "unconfirmed"
    else:
        who_key = rng.choice(list(WHO))
        who = rng.choice(WHO[who_key][style])
        verb = rng.choice(VERB[style])
        haz = rng.choices([None, "water", "fire", "collapse"], [0.7, 0.12, 0.09, 0.09])[0]
        first = rng.choice(CREATE_T[style]).format(src=src, who=who, verb=verb, L=L)
        extra = []
        if haz:
            extra.append(rng.choice(HAZ[haz][style]))
        if vis_s:
            extra.append(vis_s)
        rng.shuffle(extra)
        text = " ".join([first] + extra)
        prio = 3 if (who_key in VULN or haz) else 2
        sub = "confirmed"
    text = tidy(maybe_distract(rng, style, text))
    gold = {"action": "CREATE_VERIFICATION", "landmark": L, "sensor": VIS_SENSOR[vis], "priority": prio}
    return open_, src, text, gold, "CREATE", sub


def make_update(rng, style):
    sub = rng.choices(["escalate", "sensor", "relocate"], [0.4, 0.3, 0.3])[0]
    n_open = rng.choices([1, 2, 3, 4], [0.35, 0.35, 0.2, 0.1])[0]
    src = rng.choice(SOURCES)
    open_ = make_open(rng, n_open)
    tgt = rng.choice(open_)
    if sub == "escalate" and tgt["priority"] == 3:
        tgt["priority"] = rng.choice([1, 2])  # an escalation needs room to go up
    L = tgt["landmark"]
    gold = {"action": "UPDATE_INCIDENT", "incident": tgt["id"], "landmark": tgt["landmark"],
            "sensor": tgt["sensor"], "priority": tgt["priority"]}
    if sub == "escalate":
        if rng.random() < 0.7:
            x = rng.choice(HAZ[rng.choice(list(HAZ))][style])
        else:
            x = rng.choice(VULN_ADD[style])
        text = rng.choice(ESC_T[style]).format(src=src, L=L, x=x)
        gold["priority"] = 3
        text = id_hint(rng, style, text, tgt["id"], 0.4)
    elif sub == "sensor":
        options = []
        if tgt["sensor"] != "THERMAL":
            options.append("THERMAL")
        if tgt["sensor"] != "RGB":
            options.append("RGB")
        to = rng.choice(options)
        vis = rng.choice(["night", "smoke", "fog"]) if to == "THERMAL" else "day"
        v = rng.choice(VIS[vis][style])
        text = SENS_T[style][to].format(src=src, L=L, v=v)
        gold["sensor"] = to
        text = id_hint(rng, style, text, tgt["id"], 0.4)
    else:
        free = [l for l in LANDMARKS if l not in {i["landmark"] for i in open_}]
        new = rng.choice(free)
        text = rng.choice(MOVE_T[style]).format(src=src, old=L, new=new)
        gold["landmark"] = new
        text = id_hint(rng, style, text, tgt["id"], 0.4)
    text = tidy(maybe_distract(rng, style, text))
    return open_, src, text, gold, "UPDATE", sub


def make_close(rng, style):
    sub = rng.choices(["rescued", "false", "self"], [0.4, 0.35, 0.25])[0]
    n_open = rng.choices([1, 2, 3, 4], [0.35, 0.35, 0.2, 0.1])[0]
    open_ = make_open(rng, n_open)
    tgt = rng.choice(open_)
    src = rng.choice(SOURCES)
    text = rng.choice(CLOSE_T[sub][style]).format(src=src, L=tgt["landmark"], thing=rng.choice(THINGS[style]))
    text = id_hint(rng, style, text, tgt["id"], 0.3)
    text = tidy(maybe_distract(rng, style, text, 0.2))
    gold = {"action": "CLOSE_INCIDENT", "incident": tgt["id"]}
    return open_, src, text, gold, "CLOSE", sub


def make_noop(rng, style, sub):
    src = rng.choice(SOURCES)
    if sub == "chatter":
        n_open = rng.choices([0, 1, 2, 3], [0.3, 0.3, 0.25, 0.15])[0]
        open_ = make_open(rng, n_open)
        text = rng.choice(CHATTER[style]).format(src=src, n=rng.choice([22, 35, 41, 58]), k=rng.randint(2, 9))
    elif sub == "duplicate":
        open_ = make_open(rng, rng.choices([1, 2, 3, 4], [0.35, 0.35, 0.2, 0.1])[0])
        L = rng.choice(open_)["landmark"]
        text = rng.choice(DUP_T[style]).format(src=src, L=L)
    else:  # nonhuman / negation: place has no open incident
        n_open = rng.choices([0, 1, 2, 3], [0.25, 0.3, 0.3, 0.15])[0]
        open_ = make_open(rng, n_open)
        free = [l for l in LANDMARKS if l not in {i["landmark"] for i in open_}]
        L = rng.choice(free)
        bank = NONHUMAN_T if sub == "nonhuman" else NEG_T
        text = rng.choice(bank[style]).format(src=src, L=L)
    text = tidy(text if sub == "chatter" else maybe_distract(rng, style, text, 0.2))
    return open_, src, text, {"action": "NO_ACTION"}, "NO_ACTION", sub


# ---------------------------------------------------------------- build
def build_split(rng, style, n):
    """n cases in this style. Class mix: CREATE 25%, UPDATE 20%, CLOSE 15%, NO_ACTION 40% (4 kinds x 10%)."""
    plan = (["create"] * (n * 25 // 100) + ["update"] * (n * 20 // 100) + ["close"] * (n * 15 // 100)
            + ["chatter"] * (n * 10 // 100) + ["duplicate"] * (n * 10 // 100)
            + ["nonhuman"] * (n * 10 // 100) + ["negation"] * (n - (n * 25 // 100) - (n * 20 // 100)
                                                            - (n * 15 // 100) - 3 * (n * 10 // 100)))
    rng.shuffle(plan)
    out = []
    for kind in plan:
        if kind == "create":
            r = make_create(rng, style)
        elif kind == "update":
            r = make_update(rng, style)
        elif kind == "close":
            r = make_close(rng, style)
        else:
            r = make_noop(rng, style, kind)
        open_, src, text, gold, typ, sub = r
        out.append({"style": style, "open": open_, "source": src, "time": rand_time(rng), "text": text,
                    "gold": gold, "type": typ, "subtype": sub})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261026)
    ap.add_argument("--n-dev", type=int, default=1000)
    ap.add_argument("--n-held", type=int, default=400)
    ap.add_argument("--out", default=str(ROOT / "data"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    dev = build_split(rng, "A", args.n_dev)
    held = build_split(rng, "B", args.n_held)
    for k, c in enumerate(dev):
        c["split"] = "dev"
        c["family"] = "A%03d" % (k // 10)
    for k, c in enumerate(held):
        c["split"] = "held"
        c["family"] = "B%03d" % (k // 10)
    cases = dev + held
    rng.shuffle(cases)  # mixed order, so the first N cases are a fair sample
    for k, c in enumerate(cases):
        c["id"] = "c%04d" % (k + 1)
        # put id first for readability
    cases = [{"id": c["id"], **{k: v for k, v in c.items() if k != "id"}} for c in cases]

    with open(out / "cases.jsonl", "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # subsets: prompt-paraphrase check (300 dev cases) and no-grammar check (first 100 of those), stratified by subtype
    rng2 = random.Random(args.seed + 1)
    dev_cases = [c for c in cases if c["split"] == "dev"]
    by_type = {}
    for c in dev_cases:
        by_type.setdefault(c["type"] + "/" + c["subtype"], []).append(c["id"])
    prompt_ids = []
    want = min(300, len(dev_cases))
    for key, ids in sorted(by_type.items()):
        k = round(want * len(ids) / len(dev_cases))
        prompt_ids += rng2.sample(ids, min(k, len(ids)))
    rng2.shuffle(prompt_ids)
    rest = [c["id"] for c in dev_cases if c["id"] not in set(prompt_ids)]
    rng2.shuffle(rest)
    prompt_ids = (prompt_ids + rest)[:want]
    rng2.shuffle(prompt_ids)
    subsets = {"all": [c["id"] for c in cases], "prompt": prompt_ids, "nogrammar": prompt_ids[:100]}
    with open(out / "subsets.json", "w", encoding="utf-8") as f:
        json.dump(subsets, f)

    # audit sample for a human check of the gold labels
    rng3 = random.Random(args.seed + 2)
    aud = rng3.sample(cases, 60)
    with open(out / "audit_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "open incidents", "source", "report", "gold answer", "gold looks right? (y/n)", "your note"])
        for c in aud:
            w.writerow([c["id"], c["split"], render_open(c["open"]).replace("\n", " "), c["source"], c["text"],
                        json.dumps(c["gold"], separators=(",", ":")), "", ""])

    # summary
    from collections import Counter
    cnt = Counter((c["split"], c["gold"]["action"]) for c in cases)
    print("cases written:", len(cases), "->", out / "cases.jsonl")
    for sp in ("dev", "held"):
        row = {a: cnt[(sp, a)] for a in ("CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION")}
        print(" ", sp, row)
    print("prompt subset:", len(subsets["prompt"]), " no-grammar subset:", len(subsets["nogrammar"]))
    print("audit sample (60 rows) -> data/audit_sample.csv")


if __name__ == "__main__":
    main()
