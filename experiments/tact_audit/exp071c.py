#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
071c · 自审（修正版）：用与权威清点脚本一致的解析，量我们自己
   含第 23 条活性检验：注入已知重复，确认近重复指标真的会响
"""
import json, re, os, random
ROOT = "/data/workspace/luoshen-o1"
PATH = os.path.join(ROOT, "evidence", "失败模式库", "判据核.md")
DEF_RE = re.compile(r'^第\s*(\d+)\s*条')

def parse_def(line):
    s = line.strip().lstrip('-•').strip().lstrip('#').strip().lstrip('*').strip()
    m = DEF_RE.match(s)
    return int(m.group(1)) if m else None

lines = open(PATH, encoding="utf-8").read().split("\n")
defs = []
for i, line in enumerate(lines):
    n = parse_def(line)
    if n is not None:
        defs.append((n, i, line.strip().lstrip('-•#*').strip()))
print(f"定义行 {len(defs)}")
# 按出现顺序切正文（同一编号可能多处定义：以首次为准，但都保留用于统计）
bodies = {}
for k, (n, i, title) in enumerate(defs):
    end = defs[k+1][1] if k+1 < len(defs) else len(lines)
    body = "\n".join(lines[i+1:end])
    bodies.setdefault(n, "")
    bodies[n] += "\n" + body
uniq = sorted(set(n for n, _, _ in defs))
print(f"唯一编号 {len(uniq)}   范围 {min(uniq)}–{max(uniq)}")

def grams(s, n=3):
    s = re.sub(r"[\s，。、；：（）()【】\"'“”·,.;:!?！？\-|]+", "", s)
    return set(s[i:i+n] for i in range(len(s)-n+1))
def jac(a, b):
    if not a or not b: return 0.0
    return len(a & b)/len(a | b)

# 可证伪性
fals = 0; withnum = 0; nofat = []
for n in uniq:
    b = bodies.get(n, "")
    has_exp = bool(re.search(r"\b(0\d\d|1\d\d|2\d\d)\b", b)) or \
              bool(re.search(r"exp\d+\.py|result_\d+|tools/\w+\.py", b))
    has_num = bool(re.search(r"[-+]?\d\.\d{2,}", b))
    if has_exp or has_num: fals += 1
    if has_num: withnum += 1
    else: nofat.append(n)
print(f"\n可证伪（绑实验编号/可运行产物 或 含≥2位小数实测值）: {fals}/{len(uniq)} = {fals/len(uniq)*100:.1f}%")
print(f"含实测数值: {withnum}/{len(uniq)} = {withnum/len(uniq)*100:.1f}%")
print(f"纯规范性陈述（无任何实测锚）: {len(nofat)} 条  例: {nofat[:12]}")

# 近重复
G = [(n, grams((bodies.get(n,'') or '')[:800])) for n in uniq]
G = [(n, g) for n, g in G if g]
pairs = 0; total = 0; worst = []
for i in range(len(G)):
    for j in range(i+1, len(G)):
        s = jac(G[i][1], G[j][1]); total += 1
        if s >= 0.5: pairs += 1
        worst.append((s, G[i][0], G[j][0]))
worst.sort(reverse=True)
print(f"\n近重复(Jaccard>=0.5): {pairs}/{total} = {pairs/max(1,total)*100:.3f}%")
print(f"最高相似 5 对: " + ", ".join(f"{a}↔{b}:{s:.3f}" for s,a,b in worst[:5]))

# ---- 第23条活性检验：注入 5 条已知重复，指标必须响应 ----
G2 = list(G)
for k in range(5):
    G2.append((9000+k, G[k][1]))
p2 = 0; t2 = 0
for i in range(len(G2)):
    for j in range(i+1, len(G2)):
        t2 += 1
        if jac(G2[i][1], G2[j][1]) >= 0.5: p2 += 1
print(f"\n[活性检验] 注入 5 条完全重复后: {p2}/{t2} = {p2/t2*100:.3f}%  "
      f"(注入前 {pairs/max(1,total)*100:.3f}%)  → 指标{'活着' if p2>pairs else '未响应[BUG]'}")

json.dump(dict(n_defs=len(defs), n_unique=len(uniq), rng=[min(uniq), max(uniq)],
               falsifiable=fals, frac=fals/len(uniq), with_number=withnum,
               no_anchor=len(nofat), example_no_anchor=nofat[:20],
               neardup_pairs=pairs, neardup_total=total,
               neardup_frac=pairs/max(1,total),
               liveness=dict(before=pairs, after=p2, alive=bool(p2>pairs))),
          open("/data/workspace/luoshen-o1/result_071c.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("已写 result_071c.json")
