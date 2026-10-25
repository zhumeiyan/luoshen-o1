import sys, json
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli
from evalguard.cli import scan
cli.PRO_ON[0] = True
p = sys.argv[1]
try:
    r = scan(p)
except SyntaxError as e:
    r = [{"eg_id": "PARSEFAIL", "severity": "info", "hits": [{"line": 0, "hit": str(e)[:80]}]}]
except Exception as e:
    r = [{"eg_id": "CRASH", "severity": "info", "hits": [{"line": 0, "hit": str(e)[:80]}]}]
print(json.dumps({"file": p.split("/")[-1], "res": r}))
