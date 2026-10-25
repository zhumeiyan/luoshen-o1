"""Loose baseline (exp136).

The shipped rules are narrow because exp129-135 traded coverage for
precision, six rounds in a row. That raises a question precision cannot
answer: is the tool mute because real code is clean, or because we made
the rules narrow?

This measures the *un-pruned* density of the same three defect classes,
with no guard detection at all, on the same corpus. Two points on the
precision/coverage curve, measured, not argued.
"""
import ast, json, pathlib

BASE = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp136")
D = BASE/"corpus5"

def guarded(node, src_lines, tree):
    """cheap: is any enclosing If testing the denominator or a truthiness?"""
    return False  # loose baseline: never claim a guard

def scan(path):
    src = pathlib.Path(path).read_text()
    try: tree = ast.parse(src)
    except Exception: return []
    out = []
    for n in ast.walk(tree):
        # LOOSE EG005: every division, guard or not
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv)):
            out.append({"eg":"EG005","line":n.lineno,
                        "hit":ast.unparse(n)[:60]})
        # LOOSE EG006: bare except OR except Exception / except BaseException
        if isinstance(n, ast.ExceptHandler):
            if n.type is None:
                out.append({"eg":"EG006","line":n.lineno,"hit":"bare except"})
            else:
                t = ast.unparse(n.type)
                if t in ("Exception","BaseException"):
                    out.append({"eg":"EG006","line":n.lineno,"hit":f"except {t}"})
        # LOOSE EGP01: any try/except inside a loop where handler body is
        # pass/continue/break or only logging
        if isinstance(n,(ast.For,ast.While)):
            for sub in ast.walk(n):
                if isinstance(sub, ast.ExceptHandler):
                    body=[b for b in sub.body if not isinstance(b,ast.Expr)]
                    if not body or all(isinstance(b,(ast.Pass,ast.Continue,ast.Break)) for b in body):
                        out.append({"eg":"EGP01","line":sub.lineno,"hit":"silent handler in loop"})
    return out

tot_b=0; allhits=[]; per={}
for f in sorted(D.glob("*.py")):
    tot_b += f.stat().st_size
    h = scan(f)
    per[f.name]=len(h)
    for x in h: x["file"]=f.name; allhits.append(x)
print("files",len(per),"bytes",tot_b)
print("LOOSE findings",len(allhits),"per_kb %.4f"%(len(allhits)/tot_b*1000))
from collections import Counter
print(Counter(x["eg"] for x in allhits))
print("silent",sum(1 for v in per.values() if v==0),"/",len(per))
print("per-file",json.dumps(per))
(BASE/"loose5.json").write_text(json.dumps(allhits,indent=1))
