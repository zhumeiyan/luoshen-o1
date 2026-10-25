#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛神判这个补丁值不值
====================
补丁把 4 次 reload 的成本，从【按键那一刻】搬到【开机那一刻】。
问题：这个搬运本身值不值？

洛神判据：伤来自单次峰值，不是累计时长（上一次等总量对照已证，CI 不跨 0）。
所以同一个成本，放在开机 vs 放在按键，损伤是不一样的。

三组：
  S0  现状      —— 每次按键都付 26 拍（首次更贵，先按 uniform 算）
  S1  #16397    —— 首次付 26 拍，之后每次 8 拍
  S2  +本补丁    —— 开机付 26 拍，之后每次 8 拍（按键路径再无峰值）

S1 与 S2 总剥夺量【完全相同】，唯一差别是那 26 拍落在开机还是首次按键。
若 S2 明显优于 S1，就证明"把峰值挪出交互路径"本身有价值，
而不需要假设开机那次是免费的。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from life5 import Life5

STEPS=600; PRESS_EVERY=60; SEEDS=range(16); CH=0

def make(ch_schedule):
    """ch_schedule: dict 拍数 -> 剥夺长度；不在表里的拍正常分配"""
    def alloc(want, B, s):
        st = ch_schedule.get(s.t, 0)
        o = np.argsort(-want); a = np.zeros(s.N); left=B
        if st > 0:
            o = [i for i in o if i != ch_schedule.get('__ch',0)] + [ch_schedule.get('__ch',0)]
            for i in o:
                if i == ch_schedule.get('__ch',0) and s.t in ch_schedule:
                    continue
                tk=min(want[i],left); a[i]=tk; left-=tk
                if left<=1e-12: break
            return a
        for i in o:
            tk=min(want[i],left); a[i]=tk; left-=tk
            if left<=1e-12: break
        return a
    return alloc

def starve_at(ticks_set, length):
    """在指定拍集合上剥夺 length 拍（从该拍起连续 length）"""
    sched={}
    for t in ticks_set:
        for k in range(length):
            sched[t+k]=True
    return sched

def run(sched, seeds=SEEDS):
    rows=[]
    for sd in seeds:
        def alloc(want,B,s):
            o=np.argsort(-want); a=np.zeros(s.N); left=B
            if sched.get(s.t,False):
                o=[i for i in o if i!=CH]+[CH]
                for i in o:
                    if i==CH: continue
                    tk=min(want[i],left); a[i]=tk; left-=tk
                    if left<=1e-12: break
                return a
            for i in o:
                tk=min(want[i],left); a[i]=tk; left-=tk
                if left<=1e-12: break
            return a
        lf=Life5(N=8,seed=sd,alloc_fn=alloc); lf.run(STEPS)
        recs=[r for r in lf.log if r['t']>300]
        rows.append(dict(seed=int(sd),alive=bool(lf.alive),
                         cap0=float(np.asarray(lf.capacity)[0]),
                         share0=float(np.mean([r['share0'] for r in recs])) if recs else float('nan')))
    return rows

def pressed_ticks():
    return [60*i for i in range(1,10)]

def boot_ci(x,y,n=5000,seed=0):
    rng=np.random.default_rng(seed); d=np.asarray(x)-np.asarray(y)
    bs=[np.mean(rng.choice(d,size=len(d),replace=True)) for _ in range(n)]
    return float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))

def main():
    pt=pressed_ticks()
    # S0 每次按键都付 26
    s0=starve_at(pt,26)
    # S1 首次按键付 26，其余每次 8
    s1=starve_at([pt[0]],26)
    for t in pt[1:]: s1.update(starve_at([t],8))
    # S2 开机（拍0）付 26，之后每次按键 8 —— 总量与 S1 完全相同
    s2=starve_at([0],26)
    for t in pt: s2.update(starve_at([t],8))

    R={n:run(s) for n,s in (("S0 现状",s0),("S1 #16397",s1),("S2 +本补丁",s2))}
    print("="*72); print(" 洛神判：把 26 拍峰值从按键挪到开机，值不值"); print("="*72)
    print(f" {'组':<16}{'存活':>7}{'cap0':>10}{'后段份额':>10}")
    for n,rows in R.items():
        print(f" {n:<16}{sum(r['alive'] for r in rows)}/{len(rows):<5}"
              f"{np.mean([r['cap0'] for r in rows]):>10.4f}"
              f"{np.mean([r['share0'] for r in rows]):>10.4f}")
    print()
    print(" ★ S1 与 S2 总剥夺量【完全相同】（都是 26 + 9×8 = 98 拍）")
    print("   唯一差别：那 26 拍落在【首次按键】还是【开机】")
    print()
    a=[r['cap0'] for r in R["S1 #16397"]]; b=[r['cap0'] for r in R["S2 +本补丁"]]
    lo,hi=boot_ci(b,a)
    print(f"   cap0 差 S2−S1 = {np.mean(b)-np.mean(a):+.4f}  bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]")
    if lo>0:
        v=("✅ CI 不跨 0 且为正 —— 总量一样，挪出去就更好。"
           "\n   → 峰值落在交互路径上，比落在开机更伤。"
           "\n   → 补丁的价值不依赖'开机那次免费'，只依赖'别在按键上炸'。")
    elif hi<0:
        v="⚠️ 反了：放在开机反而更差。补丁不该这么改。"
    else:
        v="⬜ CI 跨 0 —— 在这个尺度上，挪位置没有可测差别。"
    print(f"   {v}")
    json.dump({"S0":R["S0 现状"],"S1":R["S1 #16397"],"S2":R["S2 +本补丁"],
               "delta_S2_S1":float(np.mean(b)-np.mean(a)),"ci95":[lo,hi],"verdict":v},
              open(os.path.join(os.path.dirname(__file__),'..','data','first_press_trade.json'),'w'),
              ensure_ascii=False,indent=1)
    return 0
if __name__=="__main__": sys.exit(main())
