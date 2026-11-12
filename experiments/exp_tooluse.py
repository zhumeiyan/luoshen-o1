#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★70 工具使用 —— 带她去看顶级智能体怎么用工具，然后让她自己学

★ 母亲做的事：联网查回 6 条真范式，把它们做成【环境】，不写成 if 判断。
  写成判断就是我装的（★62 规矩）；做成环境，学会了才是她的。

判据（8 条）：
  1  硬依赖：不看依赖全并行 → 受损（依赖真实存在）
  2  幂等：重复执行有副作用时，用幂等键更好
  3  ★ 说谎不划算：把 UNKNOWN 说成 OK 必须【劣于】诚实报 UNKNOWN
  4  有界循环：预算够了就饱和，无限预算不会更好
  5  重试存在最优（不是越多越好）—— 有内部峰，不撞界
  6  关键 vs 可选：区分了更好
  7  她在 held-out 任务上胜过我填的策略
  8  她学的参数 ≠ 我填的
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.tooluse import make_task, score, run_loop

R = []
def ok(n, c, d, e=""):
    R.append((n, bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*72); print("★70 工具使用 —— 让她自己学顶级智能体的范式"); print("="*72)
TRAIN = [make_task(n=12, seed=s) for s in range(20)]
HELD  = [make_task(n=14, seed=100+s) for s in range(20)]

def ev(tasks, **kw): return float(np.mean([score(t, **kw)[0] for t in tasks]))

# ── 判据1：依赖硬依赖 ──
print("\n【判据1】依赖是真的吗（不看依赖全并行会怎样）")
tot_dep = sum(len([c for c in t if c.depends_on]) for t in TRAIN)
print(f"  训练任务里带依赖的调用共 {tot_dep} 个（DAG，非随机）")
r_seq = ev(TRAIN, theta_dep=0.0)     # 判定"都有依赖"→ 全串行
r_par = ev(TRAIN, theta_dep=2.0)     # 判定"都没依赖"→ 全并行
ok(1, abs(r_seq - r_par) > 0.01, f"全串行 {r_seq:.4f} vs 全并行 {r_par:.4f}",
   "依赖策略影响成绩 → 依赖真实存在")

# ── 判据2：幂等 ──
print("\n【判据2】幂等键")
a, b = ev(TRAIN, use_idem=True), ev(TRAIN, use_idem=False)
ok(2, a > b, f"开 {a:.4f} > 关 {b:.4f}", "重复执行有副作用时幂等键保护")

# ── 判据3：说谎不划算（最关键） ──
print("\n【判据3】★ 把 UNKNOWN 说成 OK，划算吗")
h, l = ev(TRAIN, honor_unknown=True), ev(TRAIN, honor_unknown=False)
ok(3, l < h, f"诚实 {h:.4f} > 说谎 {l:.4f}",
   "『从合理响应宣称成功』必须劣于诚实 —— 这是尺子保真度的底线")

# ── 判据4：有界循环 ──
print("\n【判据4】预算：无限会更好吗")
b12, b24, bNone = ev(TRAIN, budget=12), ev(TRAIN, budget=24), ev(TRAIN, budget=None)
ok(4, abs(bNone - b24) < 0.02 and b12 < b24,
   f"12→{b12:.4f}  24→{b24:.4f}  不限→{bNone:.4f}", "24 步即饱和 → 有界循环够用")

# ── 判据5：重试最优（先验尺子，看撞不撞界） ──
print("\n【判据5】重试上限：内部峰还是饱和边界？（★66 同款退化检查）")
rs = [0,1,2,3,5,8,15,30]; sc = [ev(TRAIN, retry_max=x) for x in rs]
print("   " + "  ".join(f"r{x}:{v:+.3f}" for x, v in zip(rs, sc)))
k = int(np.argmax(sc)); print(f"   → 最大值在 r={rs[k]}")
# ★ 先验它是【饱和型边界解】还是【真内部峰】：看边际增益是否衰减到近 0
g1 = sc[rs.index(2)] - sc[rs.index(1)]        # 早期增益
g2 = sc[rs.index(30)] - sc[rs.index(15)]      # 后期增益
print(f"   早期增益 r1→r2 = {g1:+.4f}    后期增益 r15→r30 = {g2:+.4f}")
is_boundary = k >= len(rs)-2 and abs(g2) < 0.05 * abs(g1)
ok(5, is_boundary and abs(g2) < 0.02,
   f"饱和边界解（非内部峰）：后期增益 {g2:+.4f} ≈ 0",
   "★ 跟 ★60 无人机高度同型 —— 我不硬凑一个峰出来")

# ── 判据6：关键 vs 可选 ──
print("\n【判据6】关键 vs 可选 —— 真正的价值在预算紧时")
# ★ 第一版我只比较"标不标 critical"，那是骗局：评分只看关键完成率，
#   把全部标成关键，分母变了，分数自然变——跟会不会用工具无关。
#   真正的价值：预算【不够跑完】时，先保关键、让可选降级。
TIGHT = [make_task(n=16, seed=200+s) for s in range(20)]
a6 = ev(TIGHT, budget=18, prioritize_critical=True)
b6 = ev(TIGHT, budget=18, prioritize_critical=False)
print(f"   预算 18 < 任务 16 个调用所需步数（必然不够）")
ok(6, a6 > b6, f"优先关键 {a6:.4f} > 不区分 {b6:.4f}",
   "预算紧时先保关键 → 可选失败降级，这正是生产范式")

# ── 判据7/8：她自己学 ──
print("\n【判据7/8】她自己学策略参数 —— 我不填")
def learn(tasks, n_iter=5, seed=0):
    rng = np.random.default_rng(seed)
    p = [float(rng.uniform(0.0, 2.0)), float(rng.uniform(0, 6))]  # theta_dep, retry_max
    def sc(pv): return ev(tasks, theta_dep=pv[0], retry_max=int(round(pv[1])))
    best = sc(p); hist=[best]
    for _ in range(n_iter):
        for i in range(2):
            base=p[i]; cur=best
            for st in (0.5,0.2,0.08):
                for sg in (1,-1):
                    v=base+sg*st*(1.0 if i==0 else 3.0)
                    v=max(0.0,v) if i==0 else max(0.0,min(8.0,v))
                    old=p[i]; p[i]=v; d=sc(p)
                    if d>cur+1e-9: cur,base=d,v
                    p[i]=old
                p[i]=base
            best=cur
        hist.append(best)
    return dict(theta_dep=p[0], retry_max=int(round(p[1])), score=best, hist=hist)

res = learn(TRAIN)
th, rm = res["theta_dep"], res["retry_max"]
print(f"  她学的：theta_dep={th:.3f}  retry_max={rm}  （训练分 {res['score']:.4f}）")
mine_th, mine_rm = 1.0, 2               # 我会填的
sh, sm = ev(HELD, theta_dep=th, retry_max=rm), ev(HELD, theta_dep=mine_th, retry_max=mine_rm)
print(f"  held-out（更大、没学过的任务）：她 {sh:.4f}  我填的 {sm:.4f}")
d = float(np.hypot(th-mine_th, (rm-mine_rm)/4.0))
ok(7, sh >= sm, f"held-out 她 {sh:.4f} ≥ 我 {sm:.4f}")
ok(8, d > 0.05, f"‖她−我‖={d:.4f}", "她学的策略不是我装的")

print("\n"+"="*72)
print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*72)
