#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp146 统计：配对 CI + 剂量单调 + 交互效应"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "result146.json")))


def paired(a, b):
    """同 seed 配对差 a-b，返回 mean/CI"""
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    m = sum(d) / n
    if n < 2:
        return m, (m, m), 0.0
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    se = sd / math.sqrt(n)
    t = 1.833  # df=9, 90% 双尾（本批仅 n=10，用宽松界并声明）
    return m, (m - t * se, m + t * se), se


def fmt(x):
    return f"{x:+.4f}"


print("=== 地形A（真实·无结构，pretest ratio 1.0936 NO）===")
A = R["res"]["A"]
for arm in ["anti", "random", "curiosity"]:
    print(f"  {arm:10s} gain={fmt(A[arm]['gain'])}  auc={A[arm]['err_auc']:.4f}")

print("\n=== 地形B（真实·有结构，pretest ratio 0.6582 YES）===")
B = R["res"]["B"]
for arm in ["anti", "random", "curiosity"]:
    print(f"  {arm:10s} gain={fmt(B[arm]['gain'])}  auc={B[arm]['err_auc']:.4f}")

print("\n=== 配对检验（auc，同 seed）===")
for tag, D in [("A", A), ("B", B)]:
    for x, y in [("curiosity", "random"), ("random", "anti"),
                 ("curiosity", "anti")]:
        m, ci, se = paired(D[x]["per_seed_auc"], D[y]["per_seed_auc"])
        cross = ci[0] < 0 < ci[1]
        print(f"  {tag} {x:10s} - {y:8s} = {fmt(m)}  "
              f"CI[{ci[0]:+.4f},{ci[1]:+.4f}]  "
              f"{'跨0(不显著)' if cross else '不跨0'}")

print("\n=== 剂量单调（auc 越低越好：anti > random > curiosity）===")
for tag, D in [("A", A), ("B", B)]:
    v = [D["anti"]["err_auc"], D["random"]["err_auc"],
         D["curiosity"]["err_auc"]]
    mono = v[0] > v[1] > v[2]
    print(f"  {tag}: anti={v[0]:.4f} > random={v[1]:.4f} > "
          f"curiosity={v[2]:.4f}  -> {'单调' if mono else '不单调'}")

print("\n=== 关键交互：好奇优势是否只在有结构地形出现 ===")
advB = [b - a for a, b in zip(B["curiosity"]["per_seed_auc"],
                               B["random"]["per_seed_auc"])]
advA = [b - a for a, b in zip(A["curiosity"]["per_seed_auc"],
                              A["random"]["per_seed_auc"])]
inter = [x - y for x, y in zip(advB, advA)]
n = len(inter)
m = sum(inter) / n
sd = math.sqrt(sum((x - m) ** 2 for x in inter) / (n - 1))
se = sd / math.sqrt(n)
ci = (m - 1.833 * se, m + 1.833 * se)
print(f"  curiosity-random 优势: B={fmt(sum(advB)/n)}  A={fmt(sum(advA)/n)}")
print(f"  交互 B-A = {fmt(m)}  CI[{ci[0]:+.4f},{ci[1]:+.4f}]  "
      f"{'跨0(不显著)' if ci[0] < 0 < ci[1] else '不跨0'}")

print("\n=== 闸门 ===")
g1 = all(R["res"][t]["no_drive"]["spont_rate"] == 0.0 for t in ["A", "B"])
print(f"  G1 no_drive 自发率==0 : {'PASS' if g1 else 'FAIL'}")
