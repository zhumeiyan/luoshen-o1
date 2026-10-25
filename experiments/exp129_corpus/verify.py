import json, pathlib
res = json.loads(pathlib.Path("scan.json").read_text())
def ctx(f, line, w=3):
    p = pathlib.Path("corpus")/f
    L = p.read_text(errors="replace").split("\n")
    i = max(0, line-1-w); j = min(len(L), line+w)
    return "\n".join(f"{k+1:5d}| {L[k]}" for k in range(i,j))
n=0
for f,d in res.items():
    for r in d["findings"]:
        if r["severity"]!="blocker": continue
        n+=1
        print(f"\n### B{n} {r['eg_id']} canon={r['canon']} {d['repo']} :: {d['path']}")
        print(f"    {r['title']}")
        for h in r["hits"][:2]:
            print(ctx(f, h["line"]))
            print(f"    --> L{h['line']}: {h['hit'][:120]}")
print("\nBLOCKER TOTAL", n)
