#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛神 · 全栈式审计
================
用户要的不是「对标某个产品」，是把仓库统一到【全栈式】这个范式：
    从数据到界面到线上可访问，全链路自己跑得通，别人点开就能用。

六层判据（少一层就不是全栈式，是半成品）
--------------------------------------
    L1 内核层    有可运行的核心逻辑（不只是文档/配置）
    L2 数据层    有数据进出：输入源 + 产物落盘
    L3 接口层    有非交互入口：CLI 或 HTTP API（别人能调，不用读你源码）
    L4 界面层    有人能看的呈现：HTML / 图 / 仪表盘
    L5 部署层    线上能访问：Pages / 站点 / 包索引
    L6 可验证层  有自证：能跑出数字证明自己在工作
"""
import json, urllib.request, os, re

TOK="ghp_REDACTED"
H={"Authorization":f"token {TOK}","User-Agent":"luoshen-fs"}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=45).read())
    except urllib.error.HTTPError as e: return {"__err__":e.code}
    except Exception as e: return {"__err__":str(e)[:50]}

repos=[];p=1
while True:
    r=get(f"https://api.github.com/users/zhumeiyan/repos?per_page=100&page={p}&sort=updated")
    if not isinstance(r,list) or not r: break
    repos+=r
    if len(r)<100: break
    p+=1

def tree(name,br):
    t=get(f"https://api.github.com/repos/zhumeiyan/{name}/git/trees/{br}?recursive=1")
    if not isinstance(t,dict) or "tree" not in t: return []
    return [x["path"] for x in t["tree"] if x["type"]=="blob"]

print("="*80)
print(" 洛神 · 全栈式审计 —— 六层，少一层就是半成品")
print("="*80)
print(f" 仓库 {len(repos)} 个\n")
print(f"{'仓库':<24}{'内核':<6}{'数据':<6}{'接口':<6}{'界面':<6}{'部署':<6}{'自证':<6} 层数")
print("-"*80)

rows=[]
for d in sorted(repos,key=lambda x:x["name"]):
    n=d["name"]; br=d.get("default_branch") or "main"
    paths=tree(n,br)
    low=[p.lower() for p in paths]
    py=[p for p in paths if p.endswith(".py")]
    js=[p for p in paths if p.endswith((".js",".ts",".jsx",".tsx"))]
    html=[p for p in paths if p.endswith((".html",".htm"))]

    L1 = 1 if (py or js) else 0                                     # 内核
    L2 = 1 if (any("state" in p for p in low) or any("data" in p for p in low)
               or any(p.endswith((".json",".csv",".sqlite",".db")) for p in low)
               or any("log" in p for p in low)) else 0               # 数据
    L3 = (1 if any(re.search(r"(cli|api|serve|server|main|__main__|app)\.py$",p) for p in py)
             or any(re.search(r"(server|api|index|main)\.(js|ts)$",p) for p in js) else 0)  # 接口
    L4 = 1 if (html or any("site" in p or "docs" in p or "fig" in p for p in low)) else 0   # 界面
    L5 = 1 if (bool(d.get("homepage")) or any(x in low for x in
               ["index.html",".github/workflows/pages","deploy.py","site/index.html"])) else 0
    L6 = 1 if (any(re.search(r"(verify|test|check|selftest)",p) for p in low)) else 0
    rows.append(dict(name=n,layers=[L1,L2,L3,L4,L5,L6],n=sum([L1,L2,L3,L4,L5,L6]),
                     archived=d.get("archived"),size=d.get("size")))

for r in sorted(rows,key=lambda x:-x["n"]):
    m="".join(f"{'✓' if v else '✗':<6}" for v in r["layers"])
    tag="🔒" if r["archived"] else "  "
    print(f"{tag}{r['name'][:21]:<22}{m}  {r['n']}/6")
print("-"*80)
from collections import Counter
c=Counter(r["n"] for r in rows)
print(" 层数分布：", dict(sorted(c.items(),reverse=True)))
print(f" 平均 {sum(r['n'] for r in rows)/len(rows):.2f}/6")
full=[r["name"] for r in rows if r["n"]==6]
print(f" 六层齐全：{full if full else '❌ 0 个 —— 没有一个仓库是全栈式'}")
alive=[r for r in rows if not r["archived"]]
print(f"\n 未归档的 {len(alive)} 个：")
for r in alive: print(f"   {r['name']:<22}{r['n']}/6  缺: {[n for n,v in zip(['内核','数据','接口','界面','部署','自证'],r['layers']) if not v]}")
json.dump(rows,open(".sense/fullstack_audit.json","w"),ensure_ascii=False,indent=1)
