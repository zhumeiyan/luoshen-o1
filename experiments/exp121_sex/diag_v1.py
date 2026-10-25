# -*- coding: utf-8 -*-
"""给 v1 做探针：找静默失效"""
import random
import sys
sys.path.insert(0, "/data/workspace/luoshen-o1/experiments/exp121_sex")
from v1 import Ind, mate_v1, reproduce_v1

rng = random.Random(7)

print("=== 探针1: 重组会不会丢失多样性（取平均） ===")
a = Ind([0.0]*8, "M")
b = Ind([1.0]*8, "F")
kids = [mate_v1(a, b, rng) for _ in range(20)]
uniq = {tuple(round(x, 3) for x in k.genome) for k in kids}
print(f"  两亲本 [0]*8 与 [1]*8，20 个后代唯一基因型 = {len(uniq)}")
print(f"  后代基因型样例 = {[round(x,3) for x in kids[0].genome]}")

print()
print("=== 探针2: 连续多代后基因型还剩什么 ===")
pop = [Ind([0.0]*8, "M"), Ind([1.0]*8, "F")]
for g in range(12):
    pop = reproduce_v1(pop, rng)
    if not pop:
        print(f"  gen {g}: 种群灭绝")
        break
    if g in (0, 1, 2, 5, 11):
        vals = [round(x, 4) for x in pop[0].genome]
        print(f"  gen {g}: N={len(pop)} 个体0 = {vals[:4]}...")

print()
print("=== 探针3: 性别比例是否稳定 ===")
pop = [Ind([rng.random() for _ in range(8)], rng.choice(["M", "F"])) for _ in range(40)]
for g in range(15):
    pop = reproduce_v1(pop, rng)
    if not pop:
        print(f"  gen {g}: 灭绝"); break
    if g in (0, 4, 9, 14):
        nm = sum(1 for p in pop if p.sex == "M")
        print(f"  gen {g}: N={len(pop)}  M={nm}  F={len(pop)-nm}")

print()
print("=== 探针4: 能量守恒 ===")
pop = [Ind([rng.random() for _ in range(8)], rng.choice(["M", "F"])) for _ in range(10)]
for g in range(10):
    pop = reproduce_v1(pop, rng)
    if not pop:
        break
print(f"  起始 N=10，10 代后 N={len(pop) if pop else 0}（无死亡机制时 N 应单调翻倍）")
