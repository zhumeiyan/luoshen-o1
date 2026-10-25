import sys, json, pathlib, os
ROOT="/data/workspace/luoshen-o1"
sys.path.insert(0, ROOT+"/overseas"); os.chdir(ROOT)
from evalguard import cli
from evalguard.classes import SYNTAX
BASE = pathlib.Path(ROOT+"/experiments/exp129_corpus/exp136")

D = BASE/"corpus5"
rows=[]; per={}; tot_b=0
for f in sorted(D.glob("*.py")):
    b=f.stat().st_size; tot_b+=b
    try: res=cli.scan(str(f))
    except Exception as e:
        print("SCAN FAIL",f.name,e); continue
    for r in res:
        eg=r.get("eg_id","")
        # BUG FIX (exp136): EG000 records are AUDIT lines, not findings.
        # v1 counted them and reported "methodology fired 5x" on this corpus.
        # It fired zero times; I had counted the audit ledger as output.
        if eg == "EG000" or r.get("severity")=="info":
            continue
        for h in r.get("hits",[]):
            rows.append({"file":f.name,"eg":eg,"line":h.get("line"),
                         "hit":h.get("hit",""),"title":r.get("title",""),
                         "why":r.get("why",""),"sev":r.get("severity",""),
                         "cls":"syntax" if eg in SYNTAX else "methodology"})
            if eg in SYNTAX: per[f.name]=per.get(f.name,0)+1
    per.setdefault(f.name,0)
syn=[r for r in rows if r["cls"]=="syntax"]
print("files",len(per),"bytes",tot_b)
print("findings",len(rows),"syntax",len(syn),"methodology",len(rows)-len(syn))
print("per_kb SYNTAX %.4f"%(len(syn)/tot_b*1000))
print("silent",sum(1 for v in per.values() if v==0),"/",len(per))
(BASE/"scan5.json").write_text(json.dumps(rows,indent=1))
(BASE/"per5.json").write_text(json.dumps({"per":per,"bytes":tot_b,
  "files":len(per),"syn":len(syn),"meth":len(rows)-len(syn)},indent=1))
