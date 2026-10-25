#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛神核 Expensify 四单 —— 不采信我的转述，直接读 API 原始字段
判据：只认 API 返回的原始字段，不认我的复述
"""
import json, urllib.request, sys, hashlib, datetime

TOK="ghp_REDACTED"
H={"Authorization":f"token {TOK}","User-Agent":"luoshen-verify"}

def get(u):
    req=urllib.request.Request(u,headers=H)
    raw=urllib.request.urlopen(req,timeout=45).read()
    return raw, json.loads(raw)

print("="*74)
print(" 洛神核 Expensify 四单 · 原始字段直读")
print("="*74)
print(f" 核验时刻(UTC): {datetime.datetime.utcnow().isoformat()[:19]}")
print()

ISSUES=[104742,104725,104611,104738]
rows=[]
for n in ISSUES:
    raw,d=get(f"https://api.github.com/repos/Expensify/App/issues/{n}")
    r2,cs=get(f"https://api.github.com/repos/Expensify/App/issues/{n}/comments?per_page=100")
    mine=[c for c in cs if c["user"]["login"]=="zhumeiyan"]
    # 我是否真的贴了 details
    details=[c for c in mine if "Your Expensify account email" in c["body"]]
    # 我是否真的投了 proposal
    prop=[c for c in mine if "Proposal" in c["body"] or "proposal" in c["body"]]
    labels=[l["name"] for l in d.get("labels",[])]
    rows.append(dict(
        n=n, state=d["state"], labels=labels,
        n_comments=len(cs), n_mine=len(mine),
        has_details=len(details)>0,
        details_at=(details[0]["created_at"][:19] if details else None),
        has_proposal=len(prop)>0,
        title=d["title"][:52],
        sha=hashlib.sha256(raw).hexdigest()[:12],
    ))

print(f"{'#':<8}{'state':<7}{'评论':<5}{'我':<4}{'Proposal':<9}{'Details':<8}{'标签'}")
print("-"*74)
for r in rows:
    print(f"#{r['n']:<7}{r['state']:<7}{r['n_comments']:<5}{r['n_mine']:<4}"
          f"{'✓' if r['has_proposal'] else '✗':<9}{'✓' if r['has_details'] else '✗':<8}{r['labels']}")
print()
print(" 原始响应 sha256 前12位（可独立复取比对）：")
for r in rows: print(f"   #{r['n']:<7} {r['sha']}")
print()

# 洛神判据
print("="*74)
print(" 判定")
print("="*74)
ok_p=all(r["has_proposal"] for r in rows)
ok_d=all(r["has_details"] for r in rows)
rev=[r for r in rows if "Reviewing" in r["labels"]]
print(f"   四单都投了 Proposal ?  {ok_p}   ({sum(r['has_proposal'] for r in rows)}/4)")
print(f"   四单都补了 Details  ?  {ok_d}   ({sum(r['has_details'] for r in rows)}/4)")
print(f"   带 Reviewing 标签    ?  {len(rev)}/4")
if ok_p and ok_d:
    print("   ✅ channels 对齐：我说的『四单全通』与 API 原始字段一致")
else:
    miss=[r['n'] for r in rows if not(r['has_proposal'] and r['has_details'])]
    print(f"   ❌ 残差：{miss} 与我的说法不符")
if len(rev)<4:
    print(f"   ⚠️ 只有 {len(rev)}/4 带 Reviewing —— 我说『四单全部 Reviewing』需要核对")
print("="*74)
json.dump(rows,open(".sense/expensify_verify.json","w"),ensure_ascii=False,indent=1)
