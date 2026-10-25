#!/usr/bin/env python3
"""Zero-dependency test runner (pytest is not installable in this sandbox:
pypi.org returns 403). Same assertions, no framework."""
import pathlib, sys
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))          # -> overseas/
from evalguard import cli, rules

PLANTED = ("EG001","EG002","EG003","EG004","EG005","EG006","EG007","EG008",
           "EG009","EG011","EG012","EG013","EG014","EG015","EG016")

# exp134 split the rule set in two and only one half is shipped:
#   syntax rules       15/16 strict true  (93.8%)   -> shipped
#   methodology rules   1/29 strict true  ( 3.4%)   -> NOT shipped
# This test used to demand all 15 planted defects be reported. That became
# unsatisfiable the day the ship gate excluded methodology rules, and the
# failure then measured the policy, not the engine -- so it was a test that
# could never pass and taught us nothing.
#
# It now asserts what the product actually promises: every SHIPPED rule
# fires on its planted defect. The full-set recall is still measured and
# printed below as research data, so the gap stays visible instead of being
# asserted away.
from evalguard.classes import SYNTAX

results = []

def check(name, fn):
    try:
        fn(); results.append((name, "PASS", ""))
    except AssertionError as e:
        results.append((name, "FAIL", str(e)))
    except Exception as e:
        results.append((name, "ERROR", f"{type(e).__name__}: {e}"))

def scan(n):
    return {r["eg_id"]: r["severity"] for r in cli.scan(str(HERE / n))}

def t_positive():
    """Every rule we sell must fire on the defect planted for it."""
    h = scan("planted_eval.py")
    sellable = [e for e in PLANTED if e in SYNTAX]
    missing = [e for e in sellable if e not in h]
    assert missing == [], f"shipped rules missed planted defects: {missing}"
    caught_all = [e for e in PLANTED if e in h]
    print(f"    (shipped recall {len(sellable)-len(missing)}/{len(sellable)}; "
          f"full-set recall {len(caught_all)}/{len(PLANTED)} — the gap is the "
          f"exp134 methodology exclusion, not an engine regression)")

def t_negative():
    h = scan("clean_eval.py")
    noisy = {k: v for k, v in h.items() if v in ("blocker", "warn")}
    assert noisy == {}, f"false positives on clean code: {noisy}"

def t_dotted():
    s = rules._code_only("r = requests.get(u)  # baseline\n")
    assert "requests.get" in s, "dotted name destroyed by token join"
    assert "baseline" not in s, "comment leaked into code view"

def t_strings():
    assert "archived" not in rules._code_only('print("saved and archived")\n')

def t_syntax():
    assert any(r["eg_id"] == "EG000" for r in cli.scan(str(HERE / "broken_syntax.py")))

def t_exitcode():
    assert cli.main(["--format","json",str(HERE/"planted_eval.py")]) == 0
    assert cli.main([str(HERE/"planted_eval.py")]) == 1
    assert cli.main([str(HERE/"clean_eval.py")]) == 0

for n, f in [("positive control: planted defects caught", t_positive),
             ("negative control: clean fixture silent", t_negative),
             ("regression: dotted names survive strip", t_dotted),
             ("regression: strings stripped", t_strings),
             ("syntax error reported, not crashed", t_syntax),
             ("exit code: 1 only on blocker", t_exitcode)]:
    check(n, f)

w = max(len(r[0]) for r in results)
for n, st, msg in results:
    print(f"  [{st:5}] {n:<{w}}  {msg}")
npass = sum(1 for r in results if r[1] == "PASS")
print(f"\n{npass}/{len(results)} passed")
sys.exit(0 if npass == len(results) else 1)
