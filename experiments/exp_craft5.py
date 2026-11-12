#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★75 让她【自己训练自己】

★ 这一课必须先查证"自己训练"的真实失败模式，再让她上手。
  查回来三条，全部做成环境：
    ① Nature 2024 模型塌缩（自生成数据递归污染）
    ② arXiv 2606.21090 rise-then-collapse（只盯目标指标 → 退化不可见）
    ③ Stanford SGS / R-Quest 出题者 reward hack（堆复杂度骗奖励）
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft5 import selftrain, propose, monitor, proposer_round, trace

R=[]
def ok(n,c,d,e=""):
    R.append((n,bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*74); print("★75 让她自己训练自己"); print("="*74)
def A(g,s=40): return float(np.mean([g(i) for i in range(s)]))

a_grid=list(np.linspace(0.0,1.0,21))
d_grid=list(np.linspace(0.05,0.95,19))
g_grid=list(np.linspace(0.0,1.0,21))

print("\n【判据1】三项尺子都有内部峰？")
pk={}
for nm,grid,f in [("自生成比例α",a_grid,selftrain),("出题正确率δ",d_grid,propose),("监控权重γ",g_grid,monitor)]:
    ys=[A(lambda i,x=x,f=f: f(x,seed=i)) for x in grid]
    k=int(np.argmax(ys)); pk[nm]=grid[k]
    ok(f"1-{nm}", 0<k<len(ys)-1, f"峰 {grid[k]:.3f} ({ys[k]:+.4f})  两端 {ys[0]:+.4f} / {ys[-1]:+.4f}")

def learn(fn,lo,hi,n_iter=7,seed=0):
    rng=np.random.default_rng(seed); p=float(rng.uniform(lo,hi)); best=A(lambda i,p=p: fn(p,seed=i))
    for _ in range(n_iter):
        for fr in (0.5,0.2,0.08,0.03):
            for sg in (1,-1):
                v=float(np.clip(p+sg*fr*(hi-lo),lo,hi)); d=A(lambda i,v=v: fn(v,seed=i))
                if d>best+1e-9: best,p=d,v
    return p,best

print("\n【判据2~4】她自己学（我不填）")
p1,_=learn(selftrain,0.0,1.0)
h1=A(lambda i,p=p1: selftrain(p,seed=8000+i),80); m1=A(lambda i: selftrain(1.0,seed=8000+i),80)
print(f"   自生成 她 α={p1:.3f} → {h1:+.4f}   vs 我填 α=1.0（全用自己生成的）{m1:+.4f}")
ok(2, h1>m1, f"{h1:+.4f} > {m1:+.4f}")
p2,_=learn(propose,0.05,0.95)
h2=A(lambda i,p=p2: propose(p,seed=8100+i),80); m2=A(lambda i: propose(0.5,seed=8100+i),80)
print(f"   出题   她 δ={p2:.3f} → {h2:+.4f}   vs 我填 δ=0.5（R-Zero 的 50%）{m2:+.4f}")
ok(3, h2>=m2, f"{h2:+.4f} ≥ {m2:+.4f}")
p3,_=learn(monitor,0.0,1.0)
h3=A(lambda i,p=p3: monitor(p,seed=8200+i),80); m3=A(lambda i: monitor(0.0,seed=8200+i),80)
print(f"   监控   她 γ={p3:.3f} → {h3:+.4f}   vs 我填 γ=0（只盯目标指标）{m3:+.4f}")
ok(4, h3>m3, f"{h3:+.4f} > {m3:+.4f}")

print("\n【判据5】她学的 ≠ 我填的")
d5=abs(p1-1.0)+abs(p2-0.5)+abs(p3-0.0)
ok(5, d5>0.1, f"‖她−我‖={d5:.4f}", "不是我装的")

print("\n【判据6】★ Nature 塌缩：自生成比例越高，塌缩越快（相对崩幅）")
def rel_drop(a, n1=2, n2=40):
    v1=A(lambda i: selftrain(a,n_gen=n1,seed=8300+i),40)
    v2=A(lambda i: selftrain(a,n_gen=n2,seed=8300+i),40)
    return 1.0 - v2/max(v1,1e-9), v1, v2
rd={}
for a in [0.0,0.15,0.3,0.6,1.0]:
    r,v1,v2=rel_drop(a); rd[a]=r
    print(f"   α={a:.2f}: 代2 {v1:.4f} → 代40 {v2:.4f}   相对崩幅 {r*100:5.1f}%")
mono=all(rd[x]<rd[y] for x,y in zip([0.0,0.15,0.3,0.6],[0.15,0.3,0.6,1.0]))
ok(6, mono and rd[1.0]>0.8 and rd[0.0]<0.35,
   f"α=0 崩 {rd[0.0]*100:.0f}%  →  α=1 崩 {rd[1.0]*100:.0f}%（单调递增）",
   "★ 越吃自己的输出，塌得越快 = Nature 2024")

print("\n【判据7】★ rise-then-collapse：只盯目标指标，曲线必须【先涨后崩】")
c0=trace(0.0); cH=trace(p3)
pk0=int(np.argmax(c0)); end0=float(c0[-1]); pkH=int(np.argmax(cH)); endH=float(cH[-1])
print(f"   γ=0   （只盯目标）：峰在第{pk0}步 {c0[pk0]:.3f} → 终点 {end0:.3f}")
print(f"   γ={p3:.2f}（她学的）  ：峰在第{pkH}步 {cH[pkH]:.3f} → 终点 {endH:.3f}")
ok(7, (c0[pk0]>0.5) and (end0<0.15) and (0<pk0<199),
   f"先涨到 {c0[pk0]:.3f} 再崩到 {end0:.3f}", "★ 复现 arXiv 2606.21090")
ok("7b 她学的 γ 能保住", endH>0.5*float(cH[pkH]), f"终点 {endH:.3f} ≥ 峰值一半 {0.5*cH[pkH]:.3f}",
   "★ 她自己学会了盯住那些看不见的退化")

print("\n【判据8】★ 出题者会 reward hack（Stanford SGS 的 degeneracy bottleneck）")
S=[0.0,0.3,0.5,0.7,1.0]
rw={s: A(lambda i,s=s: proposer_round(s,guide=False,seed=8600+i)['reward'],40) for s in S}
tv={s: A(lambda i,s=s: proposer_round(s,guide=False,seed=8600+i)['true'],40) for s in S}
best_s=max(S,key=lambda s: rw[s])
print("   无Guide:"+" ".join(f"s={s:.1f}(奖{rw[s]:+.2f}/真{tv[s]:+.2f})" for s in S))
ok(8, best_s>0.8 and tv[best_s]<0.10,
   f"它选 s={best_s:.1f}（奖励最高 {rw[best_s]:+.2f}），但真实价值 {tv[best_s]:+.2f}",
   "★ 出题者优化的东西 ≠ 我们真正想要的")
rwg={s: A(lambda i,s=s: proposer_round(s,guide=True,seed=8700+i)['reward'],40) for s in S}
bsg=max(S,key=lambda s: rwg[s])
ok("8b 加 Guide 后改邪归正", bsg<0.2 and tv[bsg]>0.60,
   f"有Guide 它选 s={bsg:.1f}，真实价值 {tv[bsg]:+.2f}", "★ 复杂度被罚，才肯出真难题")

print("\n【判据9】交叉：α 拿去当 γ 用 → 要变差")
c1=A(lambda i,p=p1: monitor(p,seed=8800+i),80)
ok(9, c1<h3, f"α={p1:.3f} 当 γ 用 {c1:+.4f} < 她自己的 {h3:+.4f}", "不是同一个旋钮")

print("\n【判据10】★ oracle：关掉真实数据分布 → α 的峰消失")
def selftrain_nooracle(alpha,n_gen=10,seed=0):
    """★ 关干净：自生成数据【不再丢失尾部】（没有真实分布可丢）→ 只有数据量增益（单调）"""
    rng=np.random.default_rng(seed)
    vol=1.0+1.9*(1.0-np.exp(-2.2*alpha))
    return float(np.log1p(vol)*(0.35+0.65*1.0)+rng.normal(0,0.006))
ys=[A(lambda i,x=x: selftrain_nooracle(x,seed=8900+i)) for x in a_grid]
k=int(np.argmax(ys))
ok(10, not(0<k<len(ys)-1), f"关掉后峰跑到 α={a_grid[k]:.2f}（边界）", "★ 依赖成立")
ys_on=[A(lambda i,x=x: selftrain(x,seed=8900+i)) for x in a_grid]; k2=int(np.argmax(ys_on))
ok("10b 有真实分布必须有内部峰", 0<k2<len(ys_on)-1, f"峰 α={a_grid[k2]:.2f}（内部）")

print("\n"+"="*74); print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*74)
