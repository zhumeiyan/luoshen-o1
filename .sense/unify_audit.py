#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛神 · 仓库统一对标审计
标尺来源：orchids.app 的外部呈现（先核实它是否还活着，再谈对标）
判据：只认 API 原始字段，不认我的复述
"""
import json, urllib.request, base64, sys

TOK="ghp_REDACTED"
H={"Authorization":f"token {TOK}","User-Agent":"luoshen-unify"}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=45).read())
    except urllib.error.HTTPError as e: return {"__err__":e.code}
    except Exception as e: return {"__err__":str(e)[:50]}

# ---- 统一规范：一个仓库对外要能被陌生人 30 秒内看懂 ----
RULES = [
    ("有 README",        lambda d,f: any(x.lower().startswith("readme") for x in f)),
    ("有 LICENSE",       lambda d,f: d.get("license") is not None),
    ("有一句话定位",      lambda d,f: bool((d.get("description") or "").strip())),
    ("有主语言",         lambda d,f: bool(d.get("language"))),
    ("未归档(可改)",     lambda d,f: not d.get("archived")),
    ("有 Homepage",      lambda d,f: bool(d.get("homepage"))),
    ("有 topics",        lambda d,f: len(d.get("topics") or [])>0),
]

repos=[];p=1
while True:
    r=get(f"https://api.github.com/users/zhumeiyan/repos?per_page=100&page={p}&sort=updated")
    if not isinstance(r,list) or not r: break
    repos+=r
    if len(r)<100: break
    p+=1

print("="*78)
print(" 洛神 · 仓库统一对标审计（@zhumeiyan 全量）")
print("="*78)
print(f" 标尺：一个陌生人在 30 秒内能看懂这个仓库是干什么的、能不能用")
print(f" 仓库总数：{len(repos)}\n")

rows=[]
for d in sorted(repos,key=lambda x:x["name"]):
    files=get(f"https://api.github.com/repos/zhumeiyan/{d['name']}/contents/")
    fn=[x["name"] for x in files] if isinstance(files,list) else []
    passed=[]
    for name,fn_test in RULES:
        try: passed.append(1 if fn_test(d,fn) else 0)
        except Exception: passed.append(0)
    rows.append(dict(name=d["name"],score=sum(passed),detail=passed,
                     archived=d.get("archived"),size=d.get("size")))

hdr=[n for n,_ in RULES]
print(f"{'仓库':<26}" + "".join(f"{h[:4]:<6}" for h in hdr) + " 得分")
print("-"*78)
for r in rows:
    marks="".join(f"{'✓' if v else '✗':<6}" for v in r["detail"])
    print(f"{r['name'][:25]:<26}{marks}  {r['score']}/7")
print("-"*78)
avg=sum(r["score"] for r in rows)/len(rows)
print(f" 平均 {avg:.2f}/7")
print()
print(" 图例：" + "  ".join(f"{h}={'✓'}" for h in hdr))
print()
# 逐条短板
print("="*78)
print(" 逐条短板（按缺失数量排序）")
print("="*78)
for i,(n,_) in enumerate(RULES):
    miss=[r["name"] for r in rows if not r["detail"][i]]
    print(f"  {n:<12} 缺 {len(miss):>2}/{len(rows)}   {', '.join(miss[:6])}{'…' if len(miss)>6 else ''}")
print()
json.dump(rows,open(".sense/unify_audit.json","w"),ensure_ascii=False,indent=1)
