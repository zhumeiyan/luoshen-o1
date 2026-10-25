import re, json

lines = open("evidence/失败模式库/判据核.md", encoding="utf-8").read().split("\n")
pat = re.compile(
    r'^\s*(?:[-*+]\s+)?(?:\*\*|#{2,4}\s*)?\s*'
    r'第\s*(\d+)\s*条\s*[（(]?\s*(\d{4}-\d{2}-\d{2})?\s*[)）]?\s*[·:：.\-–]?\s*(.*?)\s*\**\s*$'
)

entries, cur = [], None
for ln in lines:
    s = ln.strip()
    m = pat.match(s)
    if m and len(s) < 400:
        if cur: entries.append(cur)
        cur = {"id": int(m.group(1)), "date": m.group(2) or "", "title": m.group(3) or "", "body": []}
    elif cur is not None:
        cur["body"].append(ln)
if cur: entries.append(cur)

seen, out = {}, []
for e in entries:
    b = re.sub(r'\n{3,}', '\n\n', "\n".join(e["body"]).strip()).strip("- ").strip()
    t = re.sub(r'[）)]+$', '', e["title"]).strip().strip("·").strip()
    if e["id"] in seen:
        seen[e["id"]]["body"] += "\n" + b
        seen[e["id"]]["nchar"] = len(seen[e["id"]]["body"])
        continue
    rec = {"id": e["id"], "date": e["date"], "title": t, "body": b, "nchar": len(b)}
    seen[e["id"]] = rec
    out.append(rec)

out.sort(key=lambda x: x["id"])
json.dump(out, open("overseas/raw_entries.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
ids = [e["id"] for e in out]
print("条目数:", len(out), "| 范围:", ids[0], "-", ids[-1])
miss = [i for i in range(ids[0], ids[-1]+1) if i not in set(ids)]
print("真实缺口:", len(miss), "->", miss)
print("平均长度:", sum(e["nchar"] for e in out)//len(out))
