import json, pathlib, collections, sys
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard.classes import shipped

BASE = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137")
CORP = BASE / "corpus5"

res = {}
for l in open(BASE / "out.jsonl"):
    d = json.loads(l)
    res[d["file"]] = d["res"]

man = []
for mf in ("manifest5.json", "manifest5b.json"):
    p = BASE / mf
    if p.exists():
        man += json.loads(p.read_text())
dom_of = {m["file"]: m["domain"] for m in man}

byt, nf, hits, fc, rule = (collections.Counter() for _ in range(5))
findings = []
for f, fs in sorted(res.items()):
    d = dom_of.get(f) or f.split("__")[0]
    fc[d] += 1
    byt[d] += (CORP / f).stat().st_size
    nh = 0
    for r in fs:
        eg = r.get("eg_id", "?")
        if eg in ("CRASH", "TIMEOUT", "EG000", "PARSEFAIL"):
            rule[eg] += 1
            continue
        if not shipped(eg):
            continue
        for h in r.get("hits", []):
            hits[d] += 1
            rule[eg] += 1
            nh += 1
            findings.append(dict(domain=d, file=f, eg=eg, line=h.get("line", 0),
                                 hit=str(h.get("hit", ""))[:160]))
    if nh:
        nf[d] += 1

print(f"{'domain':<12}{'files':>6}{'KB':>9}{'hits':>6}{'per100KB':>10}{'silent':>10}")
print("-" * 55)
rows = []
for d in sorted(fc):
    kb = byt[d] / 1000.0
    rate = hits[d] / (kb / 100.0) if kb else 0.0
    print(f"{d:<12}{fc[d]:>6}{kb:>9.1f}{hits[d]:>6}{rate:>10.2f}{fc[d]-nf[d]:>4}/{fc[d]:<5}")
    rows.append(dict(domain=d, files=fc[d], kb=round(kb, 1), hits=hits[d],
                     per100kb=round(rate, 3), silent=f"{fc[d]-nf[d]}/{fc[d]}"))
print("-" * 55)
tot_kb = sum(byt.values()) / 1000.0
tot_h = sum(hits.values())
print(f"{'TOTAL':<12}{sum(fc.values()):>6}{tot_kb:>9.1f}{tot_h:>6}{tot_h/(tot_kb/100.0):>10.2f}")
print("rule counts:", rule.most_common())
print("total shipped findings:", len(findings))
(BASE / "density.json").write_text(json.dumps(rows, indent=1))
(BASE / "findings.json").write_text(json.dumps(findings, indent=1))
