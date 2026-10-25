#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
071b · 公平性检验：4.83% 是引擎的锅，还是坐标库示例本身不具诊断性？
   + 同一把尺子量我们自己（判据核 209 条的可证伪比例 / 近重复率）
"""
import json, os, sys, re, random
from collections import defaultdict

TACT = "/data/workspace/tact_real"
RNG = random.Random(20261016)

def grams(s, n=3):
    s = re.sub(r"[\s，。、；：（）()【】\"'“”·,.;:!?！？]+", "", s)
    return set(s[i:i+n] for i in range(len(s)-n+1))

# ---- 装载 ----
d = json.load(open(os.path.join(TACT, "coordinate_data.json"), encoding="utf-8"))
ex = {}   # code -> [text...]
name = {}
for c in d["L"]:
    name[c["code"]] = c["name"]
for g in d["M_groups"]:
    name[g["code"]] = g["name"]
    for o in g["opts"]:
        name[o["code"]] = o["name"]; ex[o["code"]] = [p[0] for p in o.get("pairs", [])]
for g in d["P_groups"]:
    name[g["code"]] = g["name"]
    for o in g["opts"]:
        name[o["code"]] = o["name"]; ex[o["code"]] = [p[0] for p in o.get("pairs", [])]
codes = sorted(ex)
print(f"坐标 {len(codes)}  示例 {sum(len(v) for v in ex.values())}")

# ---- 1. LOO 最近邻 oracle（示例本身是否互相可区分）----
allitems = [(c, t) for c in codes for t in ex[c]]
G = {i: grams(t) for i, (c, t) in enumerate(allitems)}
def jac(a, b):
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)
nn_exact = nn_group = 0
for i, (c, t) in enumerate(allitems):
    best, bs = None, -1
    for j, (c2, t2) in enumerate(allitems):
        if i == j: continue
        s = jac(G[i], G[j])
        if s > bs: bs, best = s, c2
    if best == c: nn_exact += 1
    if best.split("-")[0] == c.split("-")[0]: nn_group += 1
n = len(allitems)
print(f"\n[Oracle-1] LOO 最近邻（用库自己的示例互相检索）")
print(f"  精确 {nn_exact}/{n} = {nn_exact/n*100:.2f}%   组级 {nn_group/n*100:.2f}%")

# 随机基线
rb_e = rb_g = 0
for _ in range(200):
    hits = sum(1 for c, t in allitems
               if RNG.choice(codes) == c)
    rb_e += hits / n
print(f"  随机基线(精确) ≈ {rb_e/200*100:.2f}%")

# ---- 2. LOO 词汇 oracle：用同坐标其他示例建词表，判留出的那条 ----
def toks(s):
    return set(re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z]{2,}", s))
vocab_exact = vocab_group = 0
for c in codes:
    T = ex[c]
    for k in range(len(T)):
        held = T[k]
        hv = toks(held)
        best, bs = None, -1
        for c2 in codes:
            v = set()
            for j, t2 in enumerate(ex[c2]):
                if c2 == c and j == k: continue
                v |= toks(t2)
            s = len(hv & v) / max(1, len(hv))
            if s > bs: bs, best = s, c2
        if best == c: vocab_exact += 1
        if best and best.split("-")[0] == c.split("-")[0]: vocab_group += 1
print(f"\n[Oracle-2] LOO 词汇表（用同坐标其余示例做词表）")
print(f"  精确 {vocab_exact}/{n} = {vocab_exact/n*100:.2f}%   组级 {vocab_group/n*100:.2f}%")

# ---- 3. 若把关键词改成"从库示例学"，能到多少（引擎上限）----
def learn_keywords(train_frac=1.0):
    """每个坐标取前 ceil(train_frac*len) 条做词表，测其余"""
    hit = tot = 0
    per = {}
    for c in codes:
        T = ex[c]
        k = max(1, int(len(T) * train_frac)) if train_frac < 1 else len(T)
        tr_v = set()
        for t in T[:k]: tr_v |= toks(t)
        if not tr_v: continue
        for t in T[k:]:
            tot += 1
            tv = toks(t)
            best, bs = None, -1
            for c2 in codes:
                v2 = set()
                for t2 in ex[c2][:k]: v2 |= toks(t2)
                if not v2: continue
                s = len(tv & v2) / max(1, len(tv | v2))
                if s > bs: bs, best = s, c2
            if best == c: hit += 1
    return hit, tot
h, t = learn_keywords(0.6)
print(f"\n[Oracle-3] 从库示例学词表（60% 训 / 40% 测，仅同坐标内切分）")
print(f"  精确 {h}/{t} = {h/t*100:.2f}%" if t else "  n/a")

# ---- 4. 同一把尺子量我们自己 ----
K = "/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md"
txt = open(K, encoding="utf-8").read()
ents = re.findall(r"^#{2,4}\s*\*{0,2}第\s*(\d+)\s*条[^\n]*\n(.*?)(?=^#{2,4}\s*\*{0,2}第\s*\d+\s*条|\Z)",
                  txt, re.M | re.S)
print(f"\n[自审] 判据核条目解析到 {len(ents)} 条")
falsifiable = 0
detail = []
for eid, body in ents:
    has_exp = bool(re.search(r"\b(0\d\d|1\d\d|2\d\d)\b", body)) or \
              bool(re.search(r"exp\d+\.py|result_\d+|\.json", body))
    has_num = bool(re.search(r"[-+]?\d+\.\d{2,}", body))
    if has_exp or has_num: falsifiable += 1
    detail.append(dict(id=int(eid), has_exp=has_exp, has_num=has_num))
if ents:
    print(f"  可证伪（绑定实验编号或可运行产物/含实测数值）: "
          f"{falsifiable}/{len(ents)} = {falsifiable/len(ents)*100:.1f}%")
    print(f"  含实测数值(≥2位小数): "
          f"{sum(1 for x in detail if x['has_num'])}/{len(ents)} = "
          f"{sum(1 for x in detail if x['has_num'])/len(ents)*100:.1f}%")

# 近重复（与 TACT 同法：char-3gram Jaccard >= 0.5）
Gk = [(int(eid), grams(re.sub(r"^#{2,4}\s*", "", body)[:600])) for eid, body in ents]
pairs = 0; total = 0
for i in range(len(Gk)):
    for j in range(i+1, len(Gk)):
        total += 1
        if jac(Gk[i][1], Gk[j][1]) >= 0.5: pairs += 1
print(f"  近重复对(Jaccard>=0.5): {pairs}/{total} = {pairs/max(1,total)*100:.2f}%")

out = dict(
  oracle_nn=dict(exact=nn_exact/n, group=nn_group/n, n=n, random_exact=rb_e/200),
  oracle_vocab=dict(exact=vocab_exact/n, group=vocab_group/n, n=n),
  oracle_learn=dict(hit=h, tot=t),
  self_audit=dict(n=len(ents), falsifiable=falsifiable,
                  frac=falsifiable/len(ents) if ents else None,
                  with_number=sum(1 for x in detail if x['has_num']),
                  neardup_pairs=pairs, neardup_total=total,
                  neardup_frac=pairs/max(1,total)),
)
json.dump(out, open("/data/workspace/luoshen-o1/result_071b.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n已写 result_071b.json")
