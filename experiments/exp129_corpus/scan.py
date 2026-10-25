import sys, json, pathlib, collections
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli
from evalguard.cli import scan
cli.PRO_ON[0] = True

man = json.loads(pathlib.Path("manifest.json").read_text())
res = {}
for m in man:
    f = pathlib.Path("corpus")/m["file"]
    try:
        res[m["file"]] = dict(repo=m["repo"], path=m["path"],
                              findings=scan(str(f)))
    except Exception as e:
        res[m["file"]] = dict(repo=m["repo"], path=m["path"], findings=[], err=str(e))
pathlib.Path("scan.json").write_text(json.dumps(res, indent=1))

sev = collections.Counter(); rule = collections.Counter()
nfiles_with = 0
for f,d in res.items():
    fs = d["findings"]
    if fs: nfiles_with += 1
    for r in fs:
        sev[r["severity"]] += 1
        rule[r["eg_id"]] += 1
print("files scanned:", len(res))
print("files with >=1 finding:", nfiles_with)
print("by severity:", dict(sev))
print("by rule (top):", rule.most_common(15))
