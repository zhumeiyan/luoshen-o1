"""exp131 analysis — why is precision low? Separate the three candidate causes.

Cause 1  FILE ROLE: findings on examples/docs scripts are noise (not eval scripts).
Cause 2  ANCHOR: the line we pin to is not the construct we accuse.
Cause 3  RULE TYPE: absence-rules ("you did not report X") cannot distinguish
          "forgot X" from "X belongs to another layer" in a mature codebase.

For each we ask the same question: is it separable? i.e. is there a subset where
precision is materially better? A cause that does not separate is an excuse, not
a mechanism.
"""
import json, pathlib

D = pathlib.Path(__file__).parent
lab = json.load(open(D / "labels131.json"))
lab = [x for x in lab if x["eg"] != "EG000"]

# ---- role classification by path token -------------------------------------
def role(f):
    if "examples" in f or "docs_" in f or "demo" in f or "template" in f:
        return "example"
    if "scripts_" in f:
        return "script"
    if "evaluator" in f or "run_eval" in f or "evaluate_task" in f:
        return "harness"
    return "metric-lib"

ABSENCE = {"EG002", "EGP06", "EGP09", "EG012", "EG016", "EG011"}
for x in lab:
    x["role"] = role(x["file"])
    x["kind"] = "absence" if x["eg"] in ABSENCE else "presence"

def rate(rows, key):
    n = len(rows)
    if n == 0:
        return (0, 0, 0.0)
    tp = sum(1 for r in rows if r[key] == "TP")
    return (tp, n, tp / n)

print("=== overall (17 findings, EG000 audit rows excluded) ===")
for k in ("strict", "loose"):
    tp, n, r = rate(lab, k)
    print(f"  {k:<7} {tp}/{n} = {r:.1%}   (ship gate 60%)")

print("\n=== sensitivity: does the verdict depend on how generous I am? ===")
print("  strict = reviewer would accept the finding at THAT line")
print("  loose  = the rule's claim holds at file level, line ignored")
print("  gate met under:", [k for k in ("strict", "loose") if rate(lab, k)[2] >= 0.60] or "NEITHER")

print("\n=== cause 1: file role ===")
for r in ("example", "script", "harness", "metric-lib"):
    rows = [x for x in lab if x["role"] == r]
    ts, n, rs = rate(rows, "strict")
    tl, _, rl = rate(rows, "loose")
    print(f"  {r:<11} n={n:<3} strict {ts}/{n} {rs:>6.1%}   loose {tl}/{n} {rl:>6.1%}")

print("\n=== cause 2: is the pinned line the accused construct? ===")
ok = [x for x in lab if x["anchor_ok"]]
bad = [x for x in lab if not x["anchor_ok"]]
print(f"  anchor correct  {len(ok)}/{len(lab)} = {len(ok)/len(lab):.1%}")
for k in ("strict", "loose"):
    tp, n, r = rate(ok, k)
    print(f"    among anchor-correct: {k} {tp}/{n} = {r:.1%}")
    tp, n, r = rate(bad, k)
    print(f"    among anchor-wrong  : {k} {tp}/{n} = {r:.1%}")

print("\n=== cause 3: absence vs presence rules ===")
for c in ("absence", "presence"):
    rows = [x for x in lab if x["kind"] == c]
    ts, n, rs = rate(rows, "strict")
    tl, _, rl = rate(rows, "loose")
    print(f"  {c:<9} n={n:<3} strict {ts}/{n} {rs:>6.1%}   loose {tl}/{n} {rl:>6.1%}")

# ---- the fix I proposed: drop example/docs files only -----------------------
kept = [x for x in lab if x["role"] != "example"]
print("\n=== proposed fix: suppress findings on examples/docs files ONLY ===")
print(f"  findings {len(lab)} -> {len(kept)}")
for k in ("strict", "loose"):
    tp, n, r = rate(kept, k)
    print(f"    {k:<7} {tp}/{n} = {r:.1%}   (was {rate(lab,k)[2]:.1%})")

# ---- and the fix I rejected: also suppress scripts/ -------------------------
kept2 = [x for x in lab if x["role"] not in ("example", "script")]
print("\n=== rejected fix: also suppress scripts/ ===")
print(f"  findings {len(lab)} -> {len(kept2)}")
for k in ("strict", "loose"):
    tp, n, r = rate(kept2, k)
    print(f"    {k:<7} {tp}/{n} = {r:.1%}")
print("  rejected because under loose it removes 2 TP and 2 FP — net zero, and it")
print("  would delete #16, the ONLY finding pinned to the actual external call.")

json.dump({"labels": lab}, open(D / "analysis131.json", "w"), ensure_ascii=False, indent=1)
