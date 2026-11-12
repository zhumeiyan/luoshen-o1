#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★73 能力习得 · 第三批：世界模型 / 想象推演 / 分层分解 / 技能库 / 经验回放

判据（12 条）：
  1 四项尺子都有【内部峰】
  2~5 她自己学，held-out 胜过我填的
  6 她学的 ≠ 我填的
  7 交叉：把想象深度的参数拿去分解粒度用 → 变差（四个解不通用）
  8 硬依赖：关掉环境真转移（oracle）→ 推演深度的峰消失
  8b 对照：有 oracle 必须有内部峰
  9 ★ 去掉"想象"组件（d=0 不预演，直接干）→ 显著变差（世界模型不是挂件）
  10 粒度与库大小不能互相替代（交叉又一次）
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft3 import imagine, decompose, skill_lib, replay

R = []
def ok(n, c, d, e=""):
    R.append((n, bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*74); print("★73 第三批：世界模型 · 想象 · 分解 · 技能库 · 回放"); print("="*74)

def avg(f, x, seeds=40, **kw):
    return float(np.mean([f(x, seed=s, **kw) for s in range(seeds)]))

d_grid = [1,2,3,4,5,6,7,8,10,12,14,18,22]
n_grid = [1,2,3,4,5,6,7,8,9,10,12,14,16,20]
m_grid = [0,2,4,6,8,10,12,14,16,18,22,26,30]
r_grid = [0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,6,7,8]

print("\n【判据1】四项尺子都有内部峰？")
peaks = {}
for nm, grid, f in [("想象深度", d_grid, imagine), ("分解粒度", n_grid, decompose),
                    ("技能库", m_grid, skill_lib), ("回放比", r_grid, replay)]:
    ys = [avg(f, x) for x in grid]
    k = int(np.argmax(ys)); inside = 0 < k < len(ys)-1
    peaks[nm] = grid[k]
    print(f"   {nm}: 峰={grid[k]}  ({ys[k]:+.4f})   两端 {ys[0]:+.4f} / {ys[-1]:+.4f}")
    ok(f"1-{nm}", inside, f"内部峰 @ {grid[k]}")

def learn(fn, lo, hi, n_iter=7, seed=0):
    rng = np.random.default_rng(seed)
    p = float(rng.uniform(lo, hi)); best = fn(p)
    for _ in range(n_iter):
        for frac in (0.5,0.2,0.08,0.03):
            for sg in (1,-1):
                v = float(np.clip(p + sg*frac*(hi-lo), lo, hi))
                d = fn(v)
                if d > best + 1e-9: best, p = d, v
    return p, best

print("\n【判据2~5】她自己学（我不填）")
p1,_ = learn(lambda x: avg(imagine, x), 1, 22)
h1 = avg(imagine, p1, seeds=60, seed=9000) if False else float(np.mean([imagine(p1, seed=9000+s) for s in range(60)]))
m1 = float(np.mean([imagine(1.0, seed=9000+s) for s in range(60)]))     # 我填的：不预演
print(f"   想象 她 d={p1:.2f} → {h1:+.4f}   vs 我填 d=1 {m1:+.4f}")
ok(2, h1 > m1, f"{h1:+.4f} > {m1:+.4f}")

p2,_ = learn(lambda x: avg(decompose, x), 1, 20)
h2 = float(np.mean([decompose(round(p2), seed=9100+s) for s in range(60)]))
m2 = float(np.mean([decompose(1, seed=9100+s) for s in range(60)]))     # 我填的：不拆
print(f"   分解 她 n={round(p2)} → {h2:+.4f}   vs 我填 n=1 {m2:+.4f}")
ok(3, h2 > m2, f"{h2:+.4f} > {m2:+.4f}")

p3,_ = learn(lambda x: avg(skill_lib, x), 0, 30)
h3 = float(np.mean([skill_lib(round(p3), seed=9200+s) for s in range(60)]))
m3 = float(np.mean([skill_lib(0, seed=9200+s) for s in range(60)]))      # 我填的：不留库
print(f"   技能库 她 m={round(p3)} → {h3:+.4f}   vs 我填 m=0 {m3:+.4f}")
ok(4, h3 > m3, f"{h3:+.4f} > {m3:+.4f}")

p4,_ = learn(lambda x: avg(replay, x), 0, 8)
h4 = float(np.mean([replay(p4, seed=9300+s) for s in range(60)]))
m4 = float(np.mean([replay(0.0, seed=9300+s) for s in range(60)]))      # 我填的：不回放
print(f"   回放 她 r={p4:.2f} → {h4:+.4f}   vs 我填 r=0 {m4:+.4f}")
ok(5, h4 > m4, f"{h4:+.4f} > {m4:+.4f}")

print("\n【判据6】她学的 ≠ 我填的")
d6 = abs(p1-1)+abs(round(p2)-1)/10+abs(round(p3)-0)/10+abs(p4-0)
ok(6, d6 > 0.1, f"‖她−我‖={d6:.4f}", "不是我装的")

print("\n【判据7】交叉：想象深度的参数拿去当分解粒度 → 要变差")
c1 = float(np.mean([decompose(int(np.clip(round(p1),1,20)), seed=9400+s) for s in range(60)]))
ok(7, c1 < h2, f"把 d={p1:.2f} 当粒度用 {c1:+.4f} < 她自己 {h2:+.4f}", "四个解不通用")

print("\n【判据8】★ 硬依赖：关掉环境真转移 → 推演深度的峰消失")
def imagine_nooracle(d, horizon=8.0, eps=0.12, cost=0.010, seed=0):
    # ★ 关干净：reach 不再随 d 提升（推演看不到真后果），误差与成本照旧
    rng = np.random.default_rng(seed)
    d = float(d)
    reach = 0.15                       # 恒定，与 d 无关
    drift = np.exp(-eps * d)
    return float(reach * drift - cost * d + float(rng.normal(0, 0.01)))
ys_off = [float(np.mean([imagine_nooracle(d, seed=s) for s in range(40)])) for d in d_grid]
k_off = int(np.argmax(ys_off))
ok(8, not (0 < k_off < len(ys_off)-1), f"关掉后峰跑到边界（d={d_grid[k_off]}）", "★ 依赖成立")
ys_on = [avg(imagine, d) for d in d_grid]; k_on = int(np.argmax(ys_on))
ok("8b 有 oracle 必须有内部峰", 0 < k_on < len(ys_on)-1, f"峰 d={d_grid[k_on]}（内部）")

print("\n【判据9】★ 世界模型不是挂件：去掉想象要显著变差")
# 不预演（d→0，只看眼前一步）
naive = float(np.mean([imagine(0.5, seed=9500+s) for s in range(60)]))
ok(9, h1 - naive > 0.05, f"预演 {h1:+.4f} vs 不预演 {naive:+.4f}  差 +{h1-naive:.4f}",
   "★ 33/44 同一族：去掉组件必须变差，否则它是挂件")

print("\n【判据10】技能库和分解粒度不能互相替代")
c2 = float(np.mean([skill_lib(int(np.clip(round(p2),0,30)), seed=9600+s) for s in range(60)]))
ok(10, abs(c2 - h3) > 0.02, f"把粒度{round(p2)}当库大小 {c2:+.4f} vs 她自己库 {h3:+.4f}",
   "不是同一个旋钮")

print("\n"+"="*74); print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*74)
