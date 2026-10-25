"""exp137: per-domain density scan of the SHIPPED rule set.

Pre-registered in PREREG.md before any data was fetched.
Gates: density >= 5.0 /100KB, strict precision >= 60%, n >= 5 with
Wilson lower bound >= 0.45.
"""
import sys, json, pathlib, collections
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli
from evalguard.cli import scan
from evalguard.classes import shipped

cli.PRO_ON[0] = True

CORP = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/corpus5")
man = []
for mf in ("manifest5.json", "manifest5b.json"):
    p = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137")/mf
    if p.exists():
        man += json.loads(p.read_text())

dom_of = {}
for m in man:
    dom_of[m["file"]] = m["domain"]

res = {}
for f in sorted(CORP.glob("*.py")):
    try:
        res[f.name] = scan(str(f))
    except Exception as e:
        res[f.name] = [{"eg_id": "CRASH", "severity": "info", "hits": [{"line": 0, "hit": str(e)}]}]

pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/scan5.json").write_text(
    json.dumps(res, indent=1))

# ---- per-domain aggregation, shipped rules only ----
byt = collections.Counter()
nf  = collections.Counter()
hits= collections.Counter()
files=collections.Counter()
rule= collections.Counter()
findings = []

for f, fs in res.items():
    d = dom_of.get(f) or f.split("__")[0]
    files[d] += 1
    byt[d] += CORP.joinpath(f).stat().st_size
    nh = 0
    for r in fs:
        eg = r.get("eg_id", "?")
        if eg == "CRASH":
            rule["CRASH"] += 1
            continue
        if not shipped(eg):
            continue
        for h in r.get("hits", []):
            hits[d] += 1
            rule[eg] += 1
            nh += 1
            findings.append(dict(domain=d, file=f, eg=eg, line=h.get("line", 0),
                                 hit=h.get("hit", "")))
    if nh: nf[d] += 1

print(f"{'domain':<12}{'files':>6}{'KB':>8}{'hits':>6}{'per100KB':>10}{'silent':>10}")
print("-"*54)
rows=[]
for d in sorted(files):
    kb = byt[d]/1000.0
    rate = hits[d]/(kb/100.0) if kb else 0.0
    silent = f"{files[d]-nf[d]}/{files[d]}"
    print(f"{d:<12}{files[d]:>6}{kb:>8.1f}{hits[d]:>6}{rate:>10.2f}{silent:>10}")
    rows.append(dict(domain=d, files=files[d], kb=round(kb,1), hits=hits[d],
                     per100kb=round(rate,3), silent=silent))
print("-"*54)
print("shipped rule hit counts:", rule.most_common())
print("total shipped findings:", len(findings))
pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/density.json").write_text(
    json.dumps(rows, indent=1))
pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/findings.json").write_text(
    json.dumps(findings, indent=1))
