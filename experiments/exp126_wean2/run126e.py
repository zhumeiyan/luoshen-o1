# -*- coding: utf-8 -*-
"""
126e · 变异组 11/16 存活 —— 但那是我把变异建模成"只能变好"的结果。
真实变异大概率【有害】。本轮让 fg 可为负（负 = 越改越糟），看 #19 反熵增还剩什么。
"""
import sys, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1/core')
from life5 import Life5
SEEDS=list(range(16)); T1,T2,DRIP,FCH=1200,1500,0.05,7

def run(mode, seed, sigma=0.0008, T1=T1, T2=T2):
    """mode: reflect(只能变好) / free(可好可坏) / harmful_only(只坏不好)"""
    lf=Life5(N=8,seed=seed,fg=0.0); rng=np.random.default_rng(seed*7919+13)
    fg=0.0
    for t in range(T1):
        if not lf.alive: break
        lf.fg = max(0.0,fg) if mode=='reflect' else fg
        lf.step()
        lf.E=min(lf.Emax,lf.E+DRIP)
        d=sigma*rng.normal()
        if mode=='reflect':   fg=max(0.0,fg+d)
        elif mode=='free':    fg=fg+d
        elif mode=='harmful': fg=fg-abs(d)
    end = max(0.0,fg) if mode!='reflect' else fg
    lf.fg=end; t0=lf.t
    while lf.alive and lf.t-t0<T2: lf.step()
    return dict(fg=float(fg), end=float(end), alive=bool(lf.alive), ticks=int(lf.t-t0))

print("=== 126e · 变异的三种建模（训练1200 → 撤除1500）===")
print(f"{'建模':<14}{'末期fg':>10}{'撤除后活':>10}{'撑(拍)':>9}")
out={}
for m in ['reflect','free','harmful']:
    rs=[run(m,sd) for sd in SEEDS]
    fg=np.array([r['end'] for r in rs],float); al=np.array([r['alive'] for r in rs],float)
    tk=np.array([r['ticks'] for r in rs],float)
    out[m]=dict(fg=float(fg.mean()),fg_sd=float(fg.std(ddof=1)),alive=float(al.mean()),
                n=int(al.sum()),ticks=float(tk.mean()),
                fg_list=[r['fg'] for r in rs])
    print(f"{m:<14}{fg.mean():10.5f}{int(al.sum()):7d}/16{tk.mean():9.1f}")
print("\n反射壁贡献 = reflect - free 末期fg: %.5f"%(out['reflect']['fg']-out['free']['fg']))
print("free 组 fg 均值 %.5f  标准差 %.5f（对称随机游走，期望应为0）"%(
      out['free']['fg'],out['free']['fg_sd']))
json.dump(out,open('result126e.json','w'),ensure_ascii=False,indent=1)
print("\n[saved] result126e.json")
