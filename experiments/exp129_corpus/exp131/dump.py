"""exp131: dump every finding on the real corpus with full evidence, for hand triage.

Previous hand-triage (2/35) was done on the file-level build. The statement-level
rewrite changed which findings exist, so old labels do not transfer. Re-dump and
re-triage from scratch: for each finding, read the actual source line and decide
TP (a real defect a reviewer would accept) or FP (standard/idiomatic code).
Anything I cannot decide is recorded FP — conservative, biases AGAINST shipping.
"""
import sys, json, pathlib

sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli
from evalguard.cli import scan

CORP = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/corpus2")

cli.PRO_ON[0] = True
rows = []
n = 0
for f in sorted(CORP.glob("*.py")):
    for r in scan(str(f)):
        n += 1
        src = f.read_text(errors="replace").splitlines()
        ln = (r.get("hits") or [{}])[0].get("line", 0)
        ctx = src[ln - 1].strip() if 1 <= ln <= len(src) else "<no line>"
        rows.append({
            "n": n,
            "eg": r["eg_id"],
            "sev": r["severity"],
            "title": r["title"],
            "file": f.name,
            "line": ln,
            "hit": r["hits"][0]["hit"] if r.get("hits") else "",
            "src_line": ctx[:160],
        })

print(f"total findings: {len(rows)}")
print(json.dumps(rows, ensure_ascii=False, indent=1))
pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp131/dump131.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1))
