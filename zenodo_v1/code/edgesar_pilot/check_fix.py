import json
def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
old = load("data_v1_before_fix/cases.jsonl")
new = load("data/cases.jsonl")
print("same number of cases:", len(old) == len(new), len(new))
changed = [(a, b) for a, b in zip(old, new) if a != b]
print("changed cases:", len(changed))
only_text = all({k for k in a if a[k] != b[k]} == {"text"} for a, b in changed)
print("only the text field changed (gold, ids, open incidents untouched):", only_text)
print("old phrase left anywhere:", any("Good visibility." in c["text"] for c in new))