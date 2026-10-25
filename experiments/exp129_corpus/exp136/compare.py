import sys, json, pathlib, os, ast
ROOT="/data/workspace/luoshen-o1"
sys.path.insert(0, ROOT+"/overseas"); os.chdir(ROOT)
from evalguard import cli
from evalguard.classes import SYNTAX
BASE = pathlib.Path(ROOT+"/experiments/exp129_corpus/exp136")

def shipped_hits(d):
    tot_b=0; rows=[]; per={}
    for f in sorted(pathlib.Path(d).glob("*.py")):
        tot_b+=f.stat().st_size
        for r in cli.scan(str(f)):
            eg=r.get("eg_id","")
            if eg=="EG000" or r.get("severity")=="info": continue
            for h in r.get("hits",[]):
                rows.append({"file":f.name,"eg":eg,"line":h.get("line"),"hit":h.get("hit","")})
                if eg in SYNTAX: per[f.name]=per.get(f.name,0)+1
        per.setdefault(f.name,0)
    syn=len(rows)
    return {"files":len(per),"bytes":tot_b,"findings":syn,
            "per_kb":syn/tot_b*1000 if tot_b else 0,
            "silent":sum(1 for v in per.values() if v==0),"rows":rows}

def loose_hits(d):
    tot_b=0; rows=[]
    for f in sorted(pathlib.Path(d).glob("*.py")):
        tot_b+=f.stat().st_size
        src=f.read_text()
        try: tree=ast.parse(src)
        except Exception: continue
        for n in ast.walk(tree):
            if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Div,ast.FloorDiv)):
                # BUG FIX (exp136, canon #23 6th recurrence): at AST level a
                # pathlib join `Path.home() / ".hermes"` is ALSO BinOp(Div).
                # v1 counted 53 "divisions" on corpus6; most were path joins
                # with a string operand. Drop those from the loose baseline.
                if isinstance(n.right, ast.Constant) and isinstance(n.right.value, str):
                    continue
                rows.append({"eg":"EG005","line":n.lineno,"hit":ast.unparse(n)[:60],"file":f.name})
            if isinstance(n,ast.ExceptHandler):
                if n.type is None: rows.append({"eg":"EG006","line":n.lineno,"hit":"bare except","file":f.name})
                else:
                    t=ast.unparse(n.type)
                    if t in ("Exception","BaseException"): rows.append({"eg":"EG006","line":n.lineno,"hit":f"except {t}","file":f.name})
            if isinstance(n,(ast.For,ast.While)):
                for sub in ast.walk(n):
                    if isinstance(sub,ast.ExceptHandler):
                        # BUG FIX (exp136): v1 stripped bare Expr nodes first,
                        # so `except: log(...)` counted as SILENT. A handler
                        # that logs is not silent. Silent means no action.
                        body=list(sub.body)
                        if body and all(isinstance(b,(ast.Pass,ast.Continue,ast.Break)) for b in body):
                            rows.append({"eg":"EGP01","line":sub.lineno,"hit":"silent handler in loop","file":f.name})
    return {"bytes":tot_b,"findings":len(rows),"per_kb":len(rows)/tot_b*1000 if tot_b else 0,"rows":rows}

out={}
for name,d in [("corpus5_mature",BASE/"corpus5"),("corpus6_lowstar",BASE/"corpus6")]:
    s=shipped_hits(d); l=loose_hits(d)
    out[name]={"shipped":{k:v for k,v in s.items() if k!="rows"},
               "loose":{k:v for k,v in l.items() if k!="rows"}}
    (BASE/f"{name}_shipped.json").write_text(json.dumps(s["rows"],indent=1))
    (BASE/f"{name}_loose.json").write_text(json.dumps(l["rows"],indent=1))
    print(f"== {name}")
    print("   shipped: files %d bytes %d findings %d per_kb %.4f silent %d/%d"%(
        s["files"],s["bytes"],s["findings"],s["per_kb"],s["silent"],s["files"]))
    print("   loose  : findings %d per_kb %.4f"%(l["findings"],l["per_kb"]))
(BASE/"compare.json").write_text(json.dumps(out,indent=1))
