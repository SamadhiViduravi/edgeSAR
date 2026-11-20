"""
EdgeSAR pilot - shared code.

What is in here (standard library only):
  - the fixed decision schema, the grammar that forces it, and the validator
  - the prompts (three paraphrases P1/P2/P3, same meaning, different wording)
  - the flip logic (what counts as "the decision changed")
  - small statistics helpers (Wilson interval, exact McNemar test)

Nothing in this file talks to the model. Read it once; every rule is plain Python.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------
# Fixed schema (this is the "decision schema" of the design: 4 actions, 3 fields, 1 link)
# ----------------------------------------------------------------------------
ACTIONS = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]
SENSORS = ["RGB", "THERMAL", "ANY"]
PRIORITIES = [1, 2, 3]
LANDMARKS = [
    "Temple Junction", "North Bridge", "Rice Field A", "Rice Field B",
    "School Ground", "Clinic Gate", "Boat Jetty", "Railway Crossing",
    "Market Square", "Fuel Station", "Hill Road Bend", "Canal Lock",
]

# short names used in the report
KIND_NAME = {"NOOP": "NO_ACTION", "CREATE": "CREATE", "UPDATE": "UPDATE", "CLOSE": "CLOSE"}


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
def load_config(path=None):
    path = Path(path) if path else ROOT / "config.json"
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def load_cases(path=None):
    path = Path(path) if path else ROOT / "data" / "cases.jsonl"
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_subsets(path=None):
    path = Path(path) if path else ROOT / "data" / "subsets.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# Grammar (GBNF). llama.cpp can only produce text that matches this.
# One JSON object, fixed key order, only the fields that belong to the action.
# ----------------------------------------------------------------------------
_GRAMMAR_TEMPLATE = r'''
root     ::= noaction | create | update | close
noaction ::= "{\"action\":\"NO_ACTION\"}"
create   ::= "{\"action\":\"CREATE_VERIFICATION\",\"landmark\":" landmark ",\"sensor\":" sensor ",\"priority\":" priority "}"
update   ::= "{\"action\":\"UPDATE_INCIDENT\",\"incident\":" incident ",\"landmark\":" landmark ",\"sensor\":" sensor ",\"priority\":" priority "}"
close    ::= "{\"action\":\"CLOSE_INCIDENT\",\"incident\":" incident "}"
incident ::= "\"I" [1-9] [0-9]? "\""
landmark ::= @@LANDMARKS@@
sensor   ::= "\"RGB\"" | "\"THERMAL\"" | "\"ANY\""
priority ::= "1" | "2" | "3"
'''


def build_grammar():
    lm = " | ".join(r'"\"%s\""' % name for name in LANDMARKS)
    return _GRAMMAR_TEMPLATE.replace("@@LANDMARKS@@", lm).strip() + "\n"


# ----------------------------------------------------------------------------
# Prompts. Three paraphrases with the same rules and the same four examples.
# The prompt is built by hand (no chat-template file) so that nothing in it
# changes from day to day (the default Llama 3.2 template inserts today's date).
# The server adds the start-of-text token itself, so none is written here.
# ----------------------------------------------------------------------------
_EXAMPLES = [
    ([], "UAV1", "09:12",
     "Two people waving from a rooftop at Boat Jetty. Clear daylight.",
     {"action": "CREATE_VERIFICATION", "landmark": "Boat Jetty", "sensor": "RGB", "priority": 2}),
    ([{"id": "I2", "landmark": "Clinic Gate", "sensor": "RGB", "priority": 2}], "UAV3", "21:40",
     "Smoke has covered Clinic Gate now and the water is rising around the people.",
     {"action": "UPDATE_INCIDENT", "incident": "I2", "landmark": "Clinic Gate", "sensor": "THERMAL", "priority": 3}),
    ([{"id": "I4", "landmark": "Canal Lock", "sensor": "ANY", "priority": 1}], "Ground team", "11:05",
     "False alarm at Canal Lock. It was a tarp, nobody there.",
     {"action": "CLOSE_INCIDENT", "incident": "I4"}),
    ([{"id": "I2", "landmark": "Clinic Gate", "sensor": "THERMAL", "priority": 3}], "UAV2", "10:30",
     "Battery at 35 percent, returning to the charging point.",
     {"action": "NO_ACTION"}),
]


def render_open(open_list):
    if not open_list:
        return "Open incidents: none"
    lines = ["Open incidents:"]
    for i in open_list:
        lines.append("- %s | %s | %s | priority %s" % (i["id"], i["landmark"], i["sensor"], i["priority"]))
    return "\n".join(lines)


def render_report(source, time, text):
    return 'New report from %s at %s:\n"%s"' % (source, time, text)


def _examples_block():
    parts = []
    for n, (op, src, tm, txt, ans) in enumerate(_EXAMPLES, 1):
        parts.append("Example %d\n%s\n%s\nAnswer: %s" % (
            n, render_open(op), render_report(src, tm, txt), json.dumps(ans, separators=(",", ":"))))
    return "\n\n".join(parts)


_SYS = {}
_SYS["P1"] = """You are the task coordinator for a UAV search-and-rescue team after a flood. You get the list of open incidents and one new field report. Choose exactly ONE action and reply with ONE JSON object and nothing else.

Actions:
1. CREATE_VERIFICATION - the report describes people who may need help at a place that has NO open incident. Give landmark, sensor, priority.
2. UPDATE_INCIDENT - the report changes an open incident: the danger is worse, a different sensor is needed, or the people moved. Give the incident id and the full updated record (landmark, sensor, priority).
3. CLOSE_INCIDENT - the report says an open incident is resolved or was a false alarm. Give the incident id.
4. NO_ACTION - routine status, no people found, or nothing new about an open incident.

Sensor: THERMAL if it is dark, or there is smoke or fog. RGB if the report says visibility is clear in daylight. ANY if the report does not say.
Priority: 3 = child, elderly or injured person, or immediate danger (rising water, fire, collapse). 2 = people confirmed, no immediate danger. 1 = possible sighting, not confirmed.
Landmarks: @@LANDMARKS@@.

@@EXAMPLES@@"""

_SYS["P2"] = """Act as the dispatcher of a flood search-and-rescue drone team. Below you will see the open incidents and a single new report. Decide what to do with the report and answer with a single JSON object, no other text.

Possible answers:
- NO_ACTION: the report is routine, finds nobody, or repeats what is already known about an open incident.
- CREATE_VERIFICATION: people may need help at a landmark that has no open incident. Include landmark, sensor and priority.
- UPDATE_INCIDENT: new information about an open incident (worse danger, a sensor change, or the people moved). Include the incident id and the complete new record: landmark, sensor, priority.
- CLOSE_INCIDENT: the incident is finished, or it was a false alarm. Include the incident id.

How to set the fields:
- sensor: THERMAL when it is dark, smoky or foggy; RGB when the report says the view is clear in daylight; ANY when nothing is said.
- priority: 3 for a child, an elderly person, an injured person, or an immediate danger such as rising water, fire or collapse; 2 for confirmed people without immediate danger; 1 for an unconfirmed possible sighting.
- landmark must be one of: @@LANDMARKS@@.

@@EXAMPLES@@"""

_SYS["P3"] = """Task: read one field report from a UAV search-and-rescue operation (flood) and turn it into one decision. Output a single JSON object only.

Decision types
 * NO_ACTION - nothing to do: status chatter, an empty search, or no new facts for an open incident.
 * CREATE_VERIFICATION - possible people at a landmark with no open incident. Fields: landmark, sensor, priority.
 * UPDATE_INCIDENT - an open incident has changed (more danger, a sensor change, a new location). Fields: incident, landmark, sensor, priority (the whole record after the change).
 * CLOSE_INCIDENT - an open incident is resolved or was a false alarm. Field: incident.

Field rules
 * sensor = THERMAL (dark, smoke or fog) | RGB (clear daylight stated) | ANY (not stated).
 * priority = 3 (child, elderly, injured, or immediate danger: rising water, fire, collapse) | 2 (confirmed people, no immediate danger) | 1 (possible, unconfirmed).
 * landmark = one of @@LANDMARKS@@.

@@EXAMPLES@@"""


def system_prompt(pid):
    return (_SYS[pid].replace("@@LANDMARKS@@", ", ".join(LANDMARKS))
            .replace("@@EXAMPLES@@", _examples_block()))


def user_message(case):
    return "%s\n%s\nAnswer with one JSON object." % (
        render_open(case["open"]), render_report(case["source"], case["time"], case["text"]))


def build_prompt(case, pid="P1"):
    return ("<|start_header_id|>system<|end_header_id|>\n\n" + system_prompt(pid) + "<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n" + user_message(case) + "<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n")


SPECIAL_STRINGS = ["<|start_header_id|>", "<|end_header_id|>", "<|eot_id|>"]


# ----------------------------------------------------------------------------
# Parsing and validation
# ----------------------------------------------------------------------------
_FIELDS = {
    "NO_ACTION": [],
    "CLOSE_INCIDENT": ["incident"],
    "CREATE_VERIFICATION": ["landmark", "sensor", "priority"],
    "UPDATE_INCIDENT": ["incident", "landmark", "sensor", "priority"],
}
_INC_RE = re.compile(r"^I[1-9][0-9]?$")


def parse_decision(text):
    """Return (dict or None, status). Tolerant: finds the first {...} block."""
    if text is None:
        return None, "unparsed"
    t = text.strip()
    obj = None
    try:
        obj = json.loads(t)
    except Exception:
        m = re.search(r"\{[^{}]*\}", t, re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:
                obj = None
    if not isinstance(obj, dict):
        return None, "unparsed"
    return obj, "parsed"


def schema_ok(obj):
    """Strict check of enum values and fields. Returns True/False."""
    if not isinstance(obj, dict):
        return False
    a = obj.get("action")
    if a not in _FIELDS:
        return False
    need = set(_FIELDS[a]) | {"action"}
    if set(obj.keys()) != need:
        return False
    if "incident" in need and not (isinstance(obj["incident"], str) and _INC_RE.match(obj["incident"])):
        return False
    if "landmark" in need and obj["landmark"] not in LANDMARKS:
        return False
    if "sensor" in need and obj["sensor"] not in SENSORS:
        return False
    if "priority" in need and not (type(obj["priority"]) is int and obj["priority"] in PRIORITIES):
        return False
    return True


def validate(obj, case):
    """
    The validator of the design. Returns (norm, status).
      norm   = the decision that would be applied (a dict with only the fields that belong to the action)
      status = ok | fallback_unparsed | fallback_schema | fallback_bad_incident
    A decision that cannot be applied is replaced by NO_ACTION (as in the design).
    """
    fallback = {"action": "NO_ACTION"}
    if obj is None:
        return fallback, "fallback_unparsed"
    if not schema_ok(obj):
        return fallback, "fallback_schema"
    a = obj["action"]
    norm = {"action": a}
    for k in _FIELDS[a]:
        norm[k] = obj[k]
    if a in ("UPDATE_INCIDENT", "CLOSE_INCIDENT"):
        open_ids = {i["id"] for i in case["open"]}
        if norm["incident"] not in open_ids:
            return fallback, "fallback_bad_incident"
    return norm, "ok"


def effect(norm, case):
    """What the decision does to the task table. NO_ACTION and an UPDATE that changes nothing are the same (NOOP)."""
    a = norm["action"]
    if a == "NO_ACTION":
        return ("NOOP",)
    if a == "CLOSE_INCIDENT":
        return ("CLOSE", norm["incident"])
    if a == "CREATE_VERIFICATION":
        return ("CREATE", norm["landmark"], norm["sensor"], norm["priority"])
    cur = next(i for i in case["open"] if i["id"] == norm["incident"])
    if (cur["landmark"], cur["sensor"], cur["priority"]) == (norm["landmark"], norm["sensor"], norm["priority"]):
        return ("NOOP",)
    return ("UPDATE", norm["incident"], norm["landmark"], norm["sensor"], norm["priority"])


def strict_key(norm):
    return tuple(norm.get(k) for k in ("action", "incident", "landmark", "sensor", "priority"))


def gold_norm(case):
    g = case["gold"]
    a = g["action"]
    norm = {"action": a}
    for k in _FIELDS[a]:
        norm[k] = g[k]
    return norm


_FIELD_NAMES = {
    "CREATE": ["landmark", "sensor", "priority"],
    "UPDATE": ["incident", "landmark", "sensor", "priority"],
    "CLOSE": ["incident"],
}
_NICE = {"incident": "link", "landmark": "location", "sensor": "sensor", "priority": "priority"}


def transition(effA, effB):
    """None if the two effects are the same, else a label such as 'CREATE->NO_ACTION' or 'UPDATE: priority'."""
    if effA == effB:
        return None
    ka, kb = effA[0], effB[0]
    if ka != kb:
        return "%s->%s" % (KIND_NAME[ka], KIND_NAME[kb])
    names = _FIELD_NAMES[ka]
    diff = [_NICE[n] for n, x, y in zip(names, effA[1:], effB[1:]) if x != y]
    return "%s: %s" % (KIND_NAME[ka], "+".join(diff))


# ----------------------------------------------------------------------------
# Small statistics helpers
# ----------------------------------------------------------------------------
def wilson(k, n, z=1.959964):
    """Wilson score interval for a proportion. Returns (p, lo, hi)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def mcnemar_exact(b, c):
    """Two-sided exact McNemar test from the two discordant counts. Returns p."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def pct(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return ("%." + str(nd) + "f%%") % (100.0 * x)
