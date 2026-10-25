# -*- coding: utf-8 -*-
"""剂量-反应梯度：对每条按命中关键词数累积替换 k=1..K，测翻转率。
把"单词替换 25%"与"全部替换 100%"统一为一条曲线。"""
import json, os, subprocess, sys, shutil, re, importlib.util, time
from minimal import SYN, hits, base, IDS, run_with, orig, ok_ids

res = {}
print(f"{'ID':<9}{'命中词数':<10}翻转所需最少替换数")
need = []
for cid in ok_ids:
    text = next(c for c in base["cases"] if c["id"] == cid)["phenomenon"]
    cand = [k for k in hits(text) if k in SYN]
    K = len(cand)
    curve = []
    first = None
    for k in range(1, K + 1):
        t = text
        for kw in cand[:k]:
            t = t.replace(kw, SYN[kw])
        after = run_with({cid: t})[cid]
        flipped = (after != "OK")
        if flipped and first is None:
            first = k
        curve.append({"k": k, "flipped": flipped})
    need.append({"id": cid, "K": K, "first": first, "curve": curve})
    print(f"{cid:<9}{K:<10}{first if first else '>K'}")

res["per_case"] = need
maxK = max(n["K"] for n in need)
print(f"\n累积替换 k 个关键词时的整体翻转率（分母={len(ok_ids)} 条原本 OK 的样例）")
agg = []
for k in range(1, maxK + 1):
    tot = sum(1 for n in need if n["K"] >= k)
    fl = sum(1 for n in need if n["K"] >= k and n["curve"][k-1]["flipped"])
    agg.append({"k": k, "n": tot, "flipped": fl, "rate": fl/tot if tot else None})
    print(f"  k={k:<2}  可测 {tot:>2} 条   翻转 {fl:>2} 条   = {fl/tot:.4f}" if tot else f"  k={k}  n=0")
res["aggregate"] = agg
json.dump(res, open("result_070d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
