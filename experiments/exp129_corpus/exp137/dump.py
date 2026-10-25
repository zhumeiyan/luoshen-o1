import json, pathlib, sys, collections
BASE = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137")
CORP = BASE / "corpus5"
findings = json.loads((BASE / "findings.json").read_text())
res = {}
for l in open(BASE / "out.jsonl"):
    d = json.loads(l)
    res[d["file"]] = d["res"]

# EG000 (parse failure) reasons
eg0 = []
for f, fs in res.items():
    for r in fs:
        if r.get("eg_id") == "EG000":
            eg0.append((f, r["hits"][0].get("hit", "")[:60]))
print("EG000 count:", len(eg0))
c = collections.Counter(x[1].split(",")[0][:40] for x in eg0)
for k, v in c.most_common(8):
    print("   ", v, k)
print()

dom = sys.argv[1] if len(sys.argv) > 1 else "B_quant"
lim = int(sys.argv[2]) if len(sys.argv) > 2 else 40
sel = [x for x in findings if x["domain"] == dom][:lim]
print(f"### {dom}: {len(sel)} findings (of {sum(1 for x in findings if x['domain']==dom)})")
for i, x in enumerate(sel, 1):
    src = (CORP / x["file"]).read_text(errors="replace").splitlines()
    ln = x["line"]
    print(f"\n[{i}] {x['eg']}  {x['file'][:60]}  L{ln}")
    for j in range(max(0, ln - 3), min(len(src), ln + 2)):
        mark = ">>" if j + 1 == ln else "  "
        print(f"   {mark}{j+1}: {src[j][:110]}")
    if x["hit"]:
        print("   hit:", x["hit"][:110])
