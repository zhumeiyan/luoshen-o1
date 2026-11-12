#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★74 能力习得 · 第四批：多模态整合 / 从反馈学 / 自我改进 / 长上下文管理
判据结构沿用 ★73（12 条 + 交叉 + oracle 两端对照 + 挂件检验）
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft4 import fuse, learn_from_feedback, self_improve, context_keep

R=[]
def ok(n,c,d,e=""):
    R.append((n,bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*74); print("★74 第四批：多模态整合 · 从反馈学 · 自我改进 · 上下文管理"); print("="*74)

# 混合一致性分布：真实世界有的时刻两模态一致，有的时刻冲突
CS = list(np.linspace(0.55, 0.98, 16))   # ★ 真实世界【大多数时候两模态一致】，冲突是少数
def A(g, s=40): return float(np.mean([g(i) for i in range(s)]))
def fuse_mix(w, seed=0):
    """在混合一致性分布上评估融合权重"""
    rng = np.random.default_rng(seed)
    c = float(rng.choice(CS))
    return fuse(w, consistency=c, seed=seed)

w_grid = [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.85,0.9,0.95,1.0]
b_grid = list(np.linspace(0.0, 5.0, 21))
r_grid = list(np.linspace(0.0, 1.0, 21))
k_grid = list(np.linspace(0.05, 1.0, 20))

print("\n【判据1】四项尺子都有内部峰？")
peaks={}
for nm, grid, f in [("多模态融合", w_grid, fuse_mix), ("负例权重", b_grid, learn_from_feedback),
                    ("新动作占比", r_grid, self_improve), ("上下文保留", k_grid, context_keep)]:
    ys=[A(lambda i,x=x,f=f: f(x,seed=i)) for x in grid]
    kk=int(np.argmax(ys)); peaks[nm]=grid[kk]
    inside = 0 < kk < len(ys)-1
    print(f"   {nm}: 峰={grid[kk]:.3f} ({ys[kk]:+.4f})  两端 {ys[0]:+.4f} / {ys[-1]:+.4f}")
    ok(f"1-{nm}", inside, f"内部峰 @ {grid[kk]:.3f}")

def learn(fn, lo, hi, n_iter=7, seed=0):
    rng=np.random.default_rng(seed); p=float(rng.uniform(lo,hi)); best=A(lambda i,p=p: fn(p,seed=i))
    for _ in range(n_iter):
        for frac in (0.5,0.2,0.08,0.03):
            for sg in (1,-1):
                v=float(np.clip(p+sg*frac*(hi-lo),lo,hi)); d=A(lambda i,v=v: fn(v,seed=i))
                if d>best+1e-9: best,p=d,v
    return p,best

print("\n【判据2~5】她自己学（我不填）")
p1,_ = learn(fuse_mix, 0.0, 1.0)
h1 = float(np.mean([fuse_mix(p1, seed=7000+s) for s in range(80)]))
m1 = float(np.mean([fuse_mix(1.0, seed=7000+s) for s in range(80)]))       # 我填的：只用视觉
print(f"   融合 她 w={p1:.3f} → {h1:+.4f}   vs 我填 w=1.0（纯视觉）{m1:+.4f}")
ok(2, h1>m1, f"{h1:+.4f} > {m1:+.4f}")

p2,_ = learn(learn_from_feedback, 0.0, 5.0)
h2 = float(np.mean([learn_from_feedback(p2, seed=7100+s) for s in range(80)]))
m2 = float(np.mean([learn_from_feedback(0.0, seed=7100+s) for s in range(80)]))  # 我填的：只看正例
print(f"   负例权重 她 β={p2:.2f} → {h2:+.4f}   vs 我填 β=0 {m2:+.4f}")
ok(3, h2>m2, f"{h2:+.4f} > {m2:+.4f}")

p3,_ = learn(self_improve, 0.0, 1.0)
h3 = float(np.mean([self_improve(p3, seed=7200+s) for s in range(80)]))
m3 = float(np.mean([self_improve(0.0, seed=7200+s) for s in range(80)]))     # 我填的：不造新动作
print(f"   新动作 她 ρ={p3:.3f} → {h3:+.4f}   vs 我填 ρ=0 {m3:+.4f}")
ok(4, h3>m3, f"{h3:+.4f} > {m3:+.4f}")

p4,_ = learn(context_keep, 0.05, 1.0)
h4 = float(np.mean([context_keep(p4, seed=7300+s) for s in range(80)]))
m4 = float(np.mean([context_keep(1.0, seed=7300+s) for s in range(80)]))     # 我填的：全保留
print(f"   上下文 她 k={p4:.3f} → {h4:+.4f}   vs 我填 k=1.0（全留）{m4:+.4f}")
ok(5, h4>m4, f"{h4:+.4f} > {m4:+.4f}")

print("\n【判据6】她学的 ≠ 我填的")
d6 = abs(p1-1.0)+abs(p2-0.0)/5+abs(p3-0.0)+abs(p4-1.0)
ok(6, d6>0.1, f"‖她−我‖={d6:.4f}", "不是我装的")

print("\n【判据7】交叉：融合权重拿去当上下文保留比例 → 要变差")
c1 = float(np.mean([context_keep(p1, seed=7400+s) for s in range(80)]))
ok(7, c1<h4, f"w={p1:.3f} 当 k 用 {c1:+.4f} < 她自己的 {h4:+.4f}", "四个解不通用")

print("\n【判据8】★ 硬依赖：关掉一致性 oracle → 融合峰消失")
def fuse_nooracle(w, seed=0):
    """★ 关干净：c 与真实一致性无关（纯随机），融合拿不到"该不该信"的信号"""
    rng=np.random.default_rng(seed)
    c=float(rng.random())                       # 与真实无关
    sv,sa=0.2,0.4; w=float(np.clip(w,0,1))
    sig=float(np.sqrt((w*sv)**2+((1-w)*sa)**2)); rel=1.0-sig
    return float(rel*(1.0+0.20*c) - 1.0*(1.0-c)*w*(1-w)
                 - 0.12*(1.0-c)*(w*w+(1-w)**2) + rng.normal(0,0.006))
ys=[A(lambda i,x=x: fuse_nooracle(x,seed=i)) for x in w_grid]
kk=int(np.argmax(ys))
ok(8, not(0<kk<len(ys)-1), f"关掉后峰跑到边界 w={w_grid[kk]:.2f}", "★ 依赖成立")
ys_on=[A(lambda i,x=x: fuse_mix(x,seed=i)) for x in w_grid]; kk2=int(np.argmax(ys_on))
ok("8b 有 oracle 必须有内部峰", 0<kk2<len(ys_on)-1, f"峰 w={w_grid[kk2]:.2f}（内部）")

print("\n【判据9】★ 整合不是挂件：只用单模态要显著变差")
blind = float(np.mean([fuse_mix(0.0, seed=7500+s) for s in range(80)]))   # 纯听觉
ok(9, h1-blind>0.02, f"融合 {h1:+.4f} vs 纯听觉 {blind:+.4f}  差 +{h1-blind:.4f}",
   "★ 33/44 同族：去掉组件必须变差")

print("\n【判据10】负例权重和新动作占比不能互相替代")
c2 = float(np.mean([self_improve(min(p2/5.0,1.0), seed=7600+s) for s in range(80)]))
ok(10, abs(c2-h3)>0.02, f"β→ρ 映射 {c2:+.4f} vs 她自己 {h3:+.4f}", "不是同一个旋钮")

print("\n"+"="*74); print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*74)
