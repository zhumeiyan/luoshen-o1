import sys, json, pathlib, collections
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli
from evalguard.cli import scan
cli.PRO_ON[0] = True
files = sorted(pathlib.Path("corpus2").glob("*.py"))
res = {}
for f in files:
    try:
        res[f.name] = scan(str(f))
    except Exception as e:
        res[f.name] = [{"eg_id":"CRASH","err":str(e)}]
pathlib.Path("scan2.json").write_text(json.dumps(res, indent=1))
sev=collections.Counter(); rule=collections.Counter(); nf=0
for f,fs in res.items():
    if fs: nf+=1
    for r in fs:
        sev[r.get("severity","?")]+=1; rule[r.get("eg_id","?")]+=1
print("files:",len(res),"with findings:",nf)
print("sev:",dict(sev))
print("rules:",rule.most_common(20))
