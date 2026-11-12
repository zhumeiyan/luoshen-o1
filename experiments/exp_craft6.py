#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★76 多智能体辩论 + 唱反调的批评者 —— 追 Grok 4 Heavy 那种程度

★ Grok 4 Heavy 的护城河不是基础模型更强，是架构：
   同一模型并行最多 16 个实例 → 独立推理 → 辩论式收敛
   AIME 2025 91~93% → 100%   HLE 44.4% → 50.7%   幻觉率 ~12% → ~4.2%
★ 且有一个【职责就是反对】的角色（报道称 Lucas）
★ 已知死法：AI 回音室 —— 不独立就锚定，错误被放大而非纠正
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft6 import debate

R=[]
def ok(n,c,d,e=""):
    R.append((n,bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  ★ '+e if e else ''}")

print("="*76); print("★76 追 Grok 4 Heavy：多智能体辩论 + 唱反调的批评者"); print("="*76)
def A(g,s=40): return float(np.mean([g(i) for i in range(s)]))

n_grid=[1,2,3,4,5,6,8,10,12,16,20,24]
r_grid=[round(x,3) for x in np.linspace(0,1,21)]
l_grid=[round(x,3) for x in np.linspace(0,1,21)]

print("\n【判据1】三项尺子都有内部峰？")
pk={}
for nm,grid,kw in [("并行数n",n_grid,"n"),("独立性ρ",r_grid,"rho"),("批评者λ",l_grid,"lam")]:
    ys=[A(lambda i,x=x,kw=kw: debate(**{kw:x},seed=i)[0]) for x in grid]
    k=int(np.argmax(ys)); pk[nm]=grid[k]
    ok(f"1-{nm}", 0<k<len(ys)-1, f"峰 {grid[k]} ({ys[k]:+.4f})   两端 {ys[0]:+.4f}/{ys[-1]:+.4f}")

def learn(kw,grid,n_iter=7,seed=0):
    rng=np.random.default_rng(seed); p=float(rng.choice(grid)); best=A(lambda i,p=p: debate(**{kw:p},seed=i)[0])
    for _ in range(n_iter):
        for fr in (0.5,0.25,0.12,0.06):
            for sg in (1,-1):
                v=float(np.clip(p+sg*fr*(max(grid)-min(grid)),min(grid),max(grid)))
                d=A(lambda i,v=v: debate(**{kw:v},seed=i)[0])
                if d>best+1e-9: best,p=d,v
    return p,best

print("\n【判据2~4】她自己学（我不填）")
p1,_=learn("n",n_grid);   p1=int(round(p1))
h1=A(lambda i,p=p1: debate(n=p,seed=9000+i)[0],80); m1=A(lambda i: debate(n=16,seed=9000+i)[0],80)
print(f"   并行数  她 n={p1}  → {h1:+.4f}   vs 我填 n=16（Grok Heavy 的满配）{m1:+.4f}")
ok(2, h1>m1, f"{h1:+.4f} > {m1:+.4f}")
p2,_=learn("rho",r_grid)
h2=A(lambda i,p=p2: debate(rho=p,seed=9100+i)[0],80); m2=A(lambda i: debate(rho=1.0,seed=9100+i)[0],80)
print(f"   独立性  她 ρ={p2:.3f} → {h2:+.4f}   vs 我填 ρ=1.0（完全独立）{m2:+.4f}")
ok(3, h2>m2, f"{h2:+.4f} > {m2:+.4f}")
p3,_=learn("lam",l_grid)
h3=A(lambda i,p=p3: debate(lam=p,seed=9200+i)[0],80); m3=A(lambda i: debate(lam=0.0,seed=9200+i)[0],80)
print(f"   批评者  她 λ={p3:.3f} → {h3:+.4f}   vs 我填 λ=0（不要批评者）{m3:+.4f}")
ok(4, h3>m3, f"{h3:+.4f} > {m3:+.4f}")

print("\n【判据5】她学的 ≠ 我填的")
d5=abs(p1-16)/16+abs(p2-1.0)+abs(p3-0.0)
ok(5, d5>0.1, f"‖她−我‖={d5:.4f}", "不是我装的")

print("\n【判据6】★ 回音室：不独立，辩论必须是【负收益】（不是没用，是更糟）")
print("   （用 lam=0.30 测；★ 高准确率下辩论的绝对增益本就很小，看的是【符号】）")
gs={}
for r in [0.0,0.2,0.4,0.6,0.85,1.0]:
    v=A(lambda i,r=r: debate(n=4,rho=r,lam=0.30,seed=9300+i)[3],60)
    h=A(lambda i,r=r: debate(n=4,rho=r,lam=0.30,seed=9300+i)[2],60)
    gs[r]=h-v; print(f"   ρ={r:.2f}: 投票 {v:.4f} → 辩论后 {h:.4f}    辩论增益 {h-v:+.4f}")
g0=gs[0.0]; gmid=max(gs[r] for r in (0.4,0.6,0.85))
ok(6, g0<0 and g0<gmid-0.01,
   f"完全锚定 {g0:+.4f}（负） vs 中高独立 {gmid:+.4f}，差 {gmid-g0:.4f}",
   "★ 锚定 = AI 回音室：辩论不但没用，反而把错误放大了")
# ★ 难题上（错误率高，才是 Grok 的场景）辩论增益应大得多
hv=A(lambda i: debate(n=4,rho=0.85,lam=0.30,seed=9310+i)[6],60)
hf=A(lambda i: debate(n=4,rho=0.85,lam=0.30,seed=9310+i)[5],60)
print(f"   ★ 难题三成上：投票 {hv:.4f} → 辩论 {hf:.4f}   增益 {hf-hv:+.4f}（远大于全体）")
ok("6b 难题上辩论增益显著更大", (hf-hv) > 3*abs(gmid),
   f"难题 {hf-hv:+.4f} vs 全体 {gmid:+.4f}", "★ 错误率高的地方才是辩论的战场")

print("\n【判据7】★ Lucas：难题上，去掉批评者幻觉要显著上升（REAL 12%→4.2%，降65%）")
h_no=A(lambda i: debate(n=4,rho=0.85,lam=0.0,seed=9400+i)[4],60)   # 难题幻觉
h_lu=A(lambda i: debate(n=4,rho=0.85,lam=p3,seed=9400+i)[4],60)
h_ag=A(lambda i: debate(n=4,rho=0.85,lam=0.5,seed=9400+i)[4],60)
a_no=A(lambda i: debate(n=4,rho=0.85,lam=0.0,seed=9400+i)[5],60)   # 难题正确率
a_lu=A(lambda i: debate(n=4,rho=0.85,lam=p3,seed=9400+i)[5],60)
print(f"   难题三成 —— 无批评者: 正确率 {a_no:.4f}  幻觉 {h_no*100:.2f}%")
print(f"              她学的λ={p3:.2f}: 正确率 {a_lu:.4f}  幻觉 {h_lu*100:.2f}%  (降 {(1-h_lu/h_no)*100:.1f}%)")
print(f"              λ=0.50 更激进: 幻觉 {h_ag*100:.2f}%  (降 {(1-h_ag/h_no)*100:.1f}%)")
ok(7, h_lu<h_no*0.85 and a_lu>a_no, f"难题幻觉降 {(1-h_lu/h_no)*100:.1f}%，正确率 {a_no:.4f}→{a_lu:.4f}",
   "★ 唱反调那一席真的在抓错（REAL 降 65%，此处为难题子集实测）")

print("\n【判据8】★ oracle：关掉（批评者的怀疑与真错无关）→ λ 的峰消失")
ys=[A(lambda i,x=x: debate(lam=x,oracle=False,seed=9500+i)[0]) for x in l_grid]
k=int(np.argmax(ys))
ok(8, not(0<k<len(ys)-1), f"关掉后峰跑到 λ={l_grid[k]}（边界）")
ys_on=[A(lambda i,x=x: debate(lam=x,oracle=True,seed=9500+i)[0]) for x in l_grid]; k2=int(np.argmax(ys_on))
ok("8b 有真信号必须有内部峰", 0<k2<len(ys_on)-1, f"峰 λ={l_grid[k2]}（内部）")

print("\n【判据9】交叉：ρ 拿去当 λ 用 → 变差")
c1=A(lambda i,p=p2: debate(lam=p,seed=9600+i)[0],80)
ok(9, c1<h3, f"ρ={p2:.3f} 当 λ 用 {c1:+.4f} < 她自己的 {h3:+.4f}", "不是同一个旋钮")

print("\n【判据10】组合起来，比单实例强多少（Grok: AIME 91~93% → 100%）")
solo=A(lambda i: debate(n=1,rho=0.85,lam=0.0,seed=9700+i)[2],80)
grp =A(lambda i: debate(n=p1,rho=p2,lam=p3,seed=9700+i)[2],80)
print(f"   单实例 {solo*100:.2f}%  →  她配的 {p1}路+ρ{p2:.2f}+λ{p3:.2f}  {grp*100:.2f}%")
ok(10, grp>solo+0.05, f"+{(grp-solo)*100:.2f} 个百分点", "★ 并行+辩论确实抬了上限")

print("\n"+"="*76); print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}"); print("="*76)
