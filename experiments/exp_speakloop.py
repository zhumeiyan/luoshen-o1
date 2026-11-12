#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★76 让她真的开口 —— 说 → 听 → 比 → 改 → 再说（闭环）

★57 建的是【开链】：学参数 → 合成 → 耳朵提特征，完。
   她从没因为【听到自己说错了】而改过一次口。
真实的说话是闭环：babbling → 听自己 → 跟目标比 → 下一句改一点。

REAL 机制（查证后做成环境，不是 if 判断）：
  ① pitch-shift reflex：偏移反馈 → 说话者【反向】补偿，且补偿不完全
  ② DAF：破坏在 ~200ms 最大，更长延迟反而减弱（非单调）
  ③ corollary discharge：说话时自己的听觉被抑制 → 听自己更钝
  ④ 语后聋：反馈长期缺失 → 产出漂移、言语退化
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.speakloop import (closed_loop, score_loop, drift_mean,
                            EAR_OK, EAR_DAMAGED, EAR_DEAF)

RES=[]
def ok(n,c,d,e=""):
    RES.append((n,bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*74); print("★76 让她真的开口（说→听→比→改→再说）"); print("="*74)
TGT=160.0
LAMG=[0.05,0.2,0.4,0.6,0.8,1.0,1.2,1.5,1.8,2.2]
THG =[0.002,0.005,0.01,0.02,0.035,0.05,0.07,0.10,0.14,0.18]
RG  =[1,2,3,4,5,6,8,10]

print("\n【判据1】三项尺子都有内部峰？")
for nm,grid,base in [("λ",LAMG,(0.02,6)),("θ",THG,(1.0,6)),("R",RG,(1.0,0.02))]:
    ys=[score_loop(TGT, (x,base[0],base[1])[0] if nm=="λ" else (base[0] if nm=="θ" else base[0]),
                        (base[0] if nm=="λ" else (x if nm=="θ" else base[1])),
                        (base[1] if nm!="R" else x), seeds=8) for x in grid]
    k=int(np.argmax(ys))
    ok(f"1-{nm}", 0<k<len(ys)-1, f"峰 {grid[k]} ({ys[k]:+.4f})  两端 {ys[0]:+.4f} / {ys[-1]:+.4f}")

def ev(lam,theta,R,seeds=14): return score_loop(TGT,lam,theta,R,seeds=seeds)
def cd(key,cur,lo,hi,iters=3):
    p=cur[key]; best=ev(lam=cur['lam'],theta=cur['theta'],R=cur['R'])
    for _ in range(iters):
        for fr in (0.4,0.15,0.05):
            for sg in (1,-1):
                v=float(np.clip(p+sg*fr*(hi-lo),lo,hi)); d={**cur}; d[key]=v
                s=ev(lam=d['lam'],theta=d['theta'],R=d['R'])
                if s>best+1e-9: best,p=s,v
    return {**cur,key:p}, best
def enumR(cur):
    best=None;bR=cur['R']
    for R in range(1,11):
        s=ev(lam=cur['lam'],theta=cur['theta'],R=R)
        if best is None or s>best: best,bR=s,R
    return {**cur,'R':bR}, best

print("\n【判据2~4】她自己学（我不填）")
rng=np.random.default_rng(7)
cur=dict(lam=float(rng.uniform(0.2,1.8)),theta=float(rng.uniform(0.005,0.12)),R=int(rng.integers(1,10)))
print(f"   起点 λ={cur['lam']:.3f} θ={cur['theta']:.4f} R={cur['R']}（随机，不是我给的好起点）")
for rd in range(2):
    cur,_=cd('lam',cur,0.05,2.2); cur,_=cd('theta',cur,0.002,0.18); cur,b=enumR(cur)
    print(f"   轮{rd+1}: λ={cur['lam']:.3f} θ={cur['theta']:.4f} R={cur['R']}  score={b:+.4f}")
PL,PT,PR=cur['lam'],cur['theta'],int(cur['R'])
MINE=(1.0,0.02,6)
h=score_loop(TGT,PL,PT,PR,seeds=40); m=score_loop(TGT,*MINE,seeds=40)
print(f"   她学的 λ={PL:.3f} θ={PT:.4f} R={PR} → {h:+.4f}")
print(f"   我填的 λ={MINE[0]:.3f} θ={MINE[1]:.4f} R={MINE[2]} → {m:+.4f}")
ok(2, h>m, f"同分布：她 {h:+.4f} > 我 {m:+.4f}")
h2=score_loop(230.0,PL,PT,PR,seeds=40); m2=score_loop(230.0,*MINE,seeds=40)
h3=score_loop(110.0,PL,PT,PR,seeds=40); m3=score_loop(110.0,*MINE,seeds=40)
ok(3, h2>m2 and h3>m3, f"held-out 230Hz {h2:+.4f}>{m2:+.4f}；110Hz {h3:+.4f}>{m3:+.4f}")
ok(4, abs(PL-1.0)+abs(PT-0.02)+abs(PR-6)>0.15,
   f"‖她−我‖={abs(PL-1.0)+abs(PT-0.02)+abs(PR-6):.4f}", "不是我装的")

def err(**kw):
    return float(np.mean([closed_loop(TGT,PL,PT,PR,seed=s,**kw)["final_err"] for s in range(20)]))

print("\n【判据5】★ 硬依赖：耳朵坏了闭环必须失效")
e_ok=err(ear=EAR_OK); e_dmg=err(ear=EAR_DAMAGED); e_deaf=err(ear=EAR_DEAF)
print(f"   耳正常 {e_ok*100:5.2f}%   受损(不含基频) {e_dmg*100:5.2f}%   聋 {e_deaf*100:5.2f}%")
ok(5, e_dmg>2.5*e_ok and e_deaf>2.5*e_ok, "受损/聋 都 > 正常 2.5 倍",
   "★ 她真的在用耳朵改口（★33/★44 那笔账这次正面验收）")

print("\n【判据6】★ REAL pitch-shift：偏移反馈 → 反向补偿且不补满")
res={}
for sh in [-0.10,0.0,0.10]:
    f=float(np.mean([closed_loop(TGT,PL,PT,PR,shift=sh,seed=s)["f0_final"] for s in range(24)]))
    res[sh]=f; print(f"   反馈{sh:+.0%} → 她发出 {f:6.1f} Hz（目标{TGT:.0f}）偏差 {f/TGT-1:+.1%}")
ok(6, res[0.10]<res[0.0]<res[-0.10], "反馈抬高→她降；反馈降低→她升",
   "★ 反向补偿（REAL pitch-shift reflex）")
comp=abs(res[0.10]-res[0.0])/TGT
ok("6b 补偿不完全", 0.02<comp<0.16, f"偏移10% → 她只补 {comp*100:.1f}%", "REAL：补偿通常不满")

print("\n【判据7】★ REAL DAF：破坏在 ~200ms【最大】，更长反而减弱（非单调）")
ds=[0,50,100,150,200,300,400]; es=[err(daf_ms=float(d)) for d in ds]
for d,e in zip(ds,es): print(f"   延迟{d:>3}ms → 终误 {e*100:5.2f}%")
k7=int(np.argmax(es))
ok(7, ds[k7]==200 and es[-1]<es[k7]*0.85, f"峰在 {ds[k7]}ms（REAL 是 200ms），400ms 已回落",
   "★ 长延迟被当成别人的声音，不再是自己的反馈")

print("\n【判据8】语音抑制 corollary discharge：听自己比听别人钝")
e_sup=err(self_suppress=True)
ok(8, e_sup>e_ok, f"抑制时 {e_sup*100:.2f}% > 正常 {e_ok*100:.2f}%")

print("\n【判据9】★ oracle：切断【产出→感知】通路 → λ 的调节作用消失")
off=[score_loop(TGT,l,PT,PR,seeds=8,oracle=False) for l in LAMG]
on =[score_loop(TGT,l,PT,PR,seeds=8) for l in LAMG]
k9=int(np.argmax(off))
ok(9, not(0<k9<len(off)-1) and (max(off)-min(off))<0.05,
   f"关掉后 λ 全范围仅 {min(off):+.2f}~{max(off):+.2f}（跨度{max(off)-min(off):.3f}）",
   "★ 听不到自己 → 改无可改")
ok("9b 有真反馈时 λ 必须有内部峰", 0<int(np.argmax(on))<len(on)-1,
   f"峰 λ={LAMG[int(np.argmax(on))]}（内部），跨度 {max(on)-min(on):.3f}")

print("\n【判据10】交叉：θ 拿去当 λ 用 → 变差")
c=score_loop(TGT,PT,PT,PR,seeds=30); hh=score_loop(TGT,PL,PT,PR,seeds=30)
ok(10, c<hh, f"θ当λ {c:+.4f} < 她自己的 {hh:+.4f}", "不是同一个旋钮")

print("\n【判据11】语后聋：没有反馈，产出会漂走")
d5=drift_mean(TGT,5); d40=drift_mean(TGT,40)
ok(11, d40>d5*1.8, f"说5次偏 {d5*100:.2f}% → 说40次偏 {d40*100:.2f}%", "★ REAL 语后聋言语退化")
wf=float(np.mean([closed_loop(TGT,PL,PT,PR,seed=s)["final_err"] for s in range(40)]))
ok("11b 有闭环就不漂", wf<d40, f"闭环 {wf*100:.2f}% << 无反馈 {d40*100:.2f}%")

print("\n"+"="*74); print(f"判据 {sum(1 for _,c in RES if c)}/{len(RES)}"); print("="*74)
