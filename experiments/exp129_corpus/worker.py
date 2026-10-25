import sys, os, json, pathlib, collections
root = sys.argv[1]; outj = sys.argv[2]
sys.path.insert(0, root)
from evalguard import cli
from evalguard.cli import scan
cli.PRO_ON[0] = True
paths = [pathlib.Path(l) for l in sys.stdin.read().split("\n") if l.strip()]
res = {}
for p in paths:
    try: res[str(p)] = scan(str(p))
    except Exception as e:
        res[str(p)] = [{"severity":"err","eg_id":"ERR","canon":[],"hits":[{"line":0,"hit":str(e)}]}]
sev = collections.Counter()
for f,r in res.items():
    for x in r: sev[x["severity"]] += 1
print(f"{outj}: files_with={sum(1 for r in res.values() if r)}/{len(res)} "
      f"blocker={sev['blocker']} warn={sev['warn']} info={sev['info']}")
json.dump(res, open(outj,"w"), indent=1)
