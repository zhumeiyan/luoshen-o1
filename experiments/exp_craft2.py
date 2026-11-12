#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★72 能力习得 · 第二批：求证 / 上下文隔离 / 并行试探 / 规划执行分离

★ 规矩（★71 血泪）：
  - 对照实验【每个对象必须重建】（survivors 污染）
  - held-out 只能换样本，不能换分布
  - 先验尺子：先扫出内部峰，再让她学（没有峰 = 尺子没区分度，如实记）

判据（8 条）：
  1 四项能力各自的尺子都有【内部峰】（不是越多越好 / 越隔离越好）
  2 求证：她学出搜索阈值，且 held-out 胜过我填的
  3 隔离：她学出委托阈值，且 held-out 胜过我填的
  4 并行：她学出 k，且 held-out 胜过我填的
  5 规划：她学出隔离阈值，且 held-out 胜过我填的
  6 ★ 她学的参数 ≠ 我填的（否则是我装的）
  7 ★ 交叉：学求证的参数用到隔离上要变差（不同能力不同解，不是同一个旋钮）
  8 ★ 硬依赖：把噪声/时效的 oracle 关掉 → 学习失效（不许回退到默认）
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft2 import (Query, answer_query, session_with_exploration,
                         parallel_trial, PlanTask, plan_session)

R = []
def ok(n, c, d, e=""):
    R.append((n, bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*72); print("★72 第二批：求证 / 隔离 / 并行 / 规划分离"); print("="*72)

# ── 尺子先验：四项都要扫出内部峰 ──
Q  = [Query(i, stale=s>0.5, signal=1-s, seed=i) for i,s in enumerate(np.linspace(0.05,0.95,14))]
QH = [Query(200+i, stale=s>0.5, signal=1-s, seed=200+i) for i,s in enumerate(np.linspace(0.03,0.93,16))]
DS  = [np.random.default_rng(i).uniform(0.02,0.40,10) for i in range(20)]
DSH = [np.random.default_rng(500+i).uniform(0.02,0.40,10) for i in range(20)]
T   = [PlanTask(i, coupling=c, seed=i) for i,c in enumerate(np.linspace(0.05,0.95,12))]
TH  = [PlanTask(300+i, coupling=c, seed=300+i) for i,c in enumerate(np.linspace(0.03,0.97,14))]

ths = np.linspace(0.0, 1.0, 11)
s1 = [np.mean([answer_query(q, search_threshold=t)[1] for q in Q]) for t in ths]
ths2 = np.linspace(0.0, 0.45, 10)
s2 = [np.mean([session_with_exploration(d, delegate_threshold=t, seed=i)['acc']
               for i,d in enumerate(DS)]) for t in ths2]
ks = [1,2,3,4,5,7,10,14,20]
s3 = [parallel_trial(k) for k in ks]
ths4 = np.linspace(0.0, 1.0, 11)
s4 = [np.mean([plan_session(t, isolate_threshold=x) for t in T]) for x in ths4]

print("\n【判据1】★ 先验：四项尺子都扫出内部峰了吗")
for nm, xs, ys in [("求证", ths, s1), ("隔离", ths2, s2), ("并行", ks, s3), ("规划", ths4, s4)]:
    k = int(np.argmax(ys))
    inside = 0 < k < len(ys)-1
    print(f"   {nm}: 峰在 {xs[k]:.3f}（{ys[k]:+.4f}）  端点 {ys[0]:+.4f} / {ys[-1]:+.4f}")
    R.append((f"1-{nm}", inside))
    print(f"   {'✅' if inside else '❌'} {nm} 有内部峰")

# ── 她自己学 ──
def learn(fn, lo, hi, n_iter=7, seed=0):
    rng = np.random.default_rng(seed)
    p = float(rng.uniform(lo, hi)); best = fn(p)
    for _ in range(n_iter):
        for frac in (0.5, 0.2, 0.08, 0.03):
            for sg in (1, -1):
                v = float(np.clip(p + sg*frac*(hi-lo), lo, hi))
                d = fn(v)
                if d > best + 1e-9: best, p = d, v
    return p, best

print("\n【判据2~5】她自己学（我不填）")
# 求证
p1, _ = learn(lambda x: np.mean([answer_query(q, search_threshold=x)[1] for q in Q]), 0.0, 1.0)
h1 = np.mean([answer_query(q, search_threshold=p1)[1] for q in QH])
m1 = np.mean([answer_query(q, search_threshold=0.5)[1] for q in QH])
print(f"   求证 她 {p1:.3f} → held-out {h1:.4f}   vs 我填0.5 {m1:.4f}")
ok(2, h1 >= m1, f"{h1:.4f} ≥ {m1:.4f}")
# 隔离
p2, _ = learn(lambda x: np.mean([session_with_exploration(d, delegate_threshold=x, seed=i)['acc']
                                 for i,d in enumerate(DS)]), 0.0, 0.45)
h2 = np.mean([session_with_exploration(d, delegate_threshold=p2, seed=i)['acc'] for i,d in enumerate(DSH)])
m2 = np.mean([session_with_exploration(d, delegate_threshold=0.5, seed=i)['acc'] for i,d in enumerate(DSH)])
print(f"   隔离 她 {p2:.3f} → held-out {h2:.4f}   vs 我填0.5 {m2:.4f}")
ok(3, h2 >= m2, f"{h2:.4f} ≥ {m2:.4f}")
# 并行
p3, _ = learn(lambda x: parallel_trial(max(1,int(round(x)))), 1, 20)
h3 = parallel_trial(max(1,int(round(p3))), seed=99)
m3 = parallel_trial(1, seed=99)
print(f"   并行 她 k={int(round(p3))} → held-out {h3:+.4f}   vs 我填k=1 {m3:+.4f}")
ok(4, h3 >= m3, f"{h3:+.4f} ≥ {m3:+.4f}")
# 规划
p4, _ = learn(lambda x: np.mean([plan_session(t, isolate_threshold=x) for t in T]), 0.0, 1.0)
h4 = np.mean([plan_session(t, isolate_threshold=p4) for t in TH])
m4 = np.mean([plan_session(t, isolate_threshold=0.5) for t in TH])
print(f"   规划 她 {p4:.3f} → held-out {h4:+.4f}   vs 我填0.5 {m4:+.4f}")
ok(5, h4 >= m4, f"{h4:+.4f} ≥ {m4:+.4f}")

print("\n【判据6】她学的 ≠ 我填的")
d6 = abs(p1-0.5) + abs(p2-0.5) + abs(int(round(p3))-1)/10 + abs(p4-0.5)
ok(6, d6 > 0.1, f"‖她−我‖={d6:.4f}", "不是我装的")

print("\n【判据7】★ 交叉检验：学求证的参数拿去隔离用，要变差")
cross = np.mean([session_with_exploration(d, delegate_threshold=p1, seed=i)['acc'] for i,d in enumerate(DSH)])
ok(7, cross < h2, f"把求证阈值{p1:.3f}用在隔离上 {cross:.4f} < 她自己的 {h2:.4f}",
   "四项是四个不同的解，不是一个通用旋钮")

print("\n【判据8】★ 硬依赖：oracle 关掉 → 不该再有内部峰")
# oracle = "信号能反映真时效"。关掉：信号与 stale 无关（纯噪声）
Qoff = [Query(900+i, stale=bool(np.random.default_rng(900+i).random()>0.5),
              signal=float(np.random.default_rng(4000+i).random()), seed=900+i)
        for i in range(200)]
off = [np.mean([answer_query(q, search_threshold=t)[1] for q in Qoff]) for t in ths]
k_off = int(np.argmax(off)); inside_off = 0 < k_off < len(off)-1
spread = max(off) - min(off)
print("   关 oracle 后扫描：" + " ".join(f"{x:.2f}:{y:.3f}" for x, y in zip(ths, off)))
print(f"   峰在 {ths[k_off]:.2f}（{'内部' if inside_off else '边界'}）  跨度 {spread:.4f}")
ok(8, not inside_off, "关掉 oracle → 只剩边界解（要么全搜要么全不搜），学不出阈值",
   "★ 有 oracle 才有内部峰；关了就退化 = 依赖成立")
# 对照：有 oracle 时必须【有】内部峰（同一把尺子）
s1b = [np.mean([answer_query(q, search_threshold=t)[1] for q in Q]) for t in ths]
k_on = int(np.argmax(s1b))
ok("8b 有 oracle 必须有内部峰", 0 < k_on < len(s1b)-1, f"峰在 {ths[k_on]:.2f}（内部）",
   "两端对照：依赖真的成立，不是我把尺子做坏了")

print("\n"+"="*72); print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*72)
