# -*- coding: utf-8 -*-
"""125b · 补做：共同存活子集去污染 + 撤掉输液后的真实死因 + fg 边界细扫"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5
SEEDS = list(range(24))

def skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1)/max(c.mean(),1e-12))

def drip(steps, seed, drip=0.05, fg=0.0):
    lf = Life5(N=8, seed=seed, fg=fg)
    for _ in range(steps):
        if not lf.alive: break
        lf.step(); lf.E = min(lf.Emax, lf.E + drip)
    return lf

# ---- A. 共同存活子集：只比两组都活下来的 seed ----
print("=== A. 共同存活子集（去掉死亡筛选污染）===")
rows = {}
for name, fn in [('自觅食', lambda sd: Life5(N=8, seed=sd).run(800) or None),
                 ('输液fg=0', lambda sd: drip(800, sd))]:
    rows[name] = {}
    for sd in SEEDS:
        lf = Life5(N=8, seed=sd).run(800) if name=='自觅食' else drip(800, sd)
        rows[name][sd] = (bool(lf.alive), skew(lf) if lf.alive else None)
common = [sd for sd in SEEDS if rows['自觅食'][sd][0] and rows['输液fg=0'][sd][0]]
a = np.array([rows['自觅食'][sd][1] for sd in common])
b = np.array([rows['输液fg=0'][sd][1] for sd in common])
d = a - b
se = d.std(ddof=1)/np.sqrt(len(d))
print(f"  共同存活 seed 数 = {len(common)}/{len(SEEDS)}")
print(f"  自觅食偏度 {a.mean():.4f}   输液偏度 {b.mean():.4f}")
print(f"  配对差 Δ={d.mean():+.4f}  SE={se:.4f}  95%CI [{d.mean()-1.96*se:+.4f}, {d.mean()+1.96*se:+.4f}]")
print(f"  CI 跨0 = {(d.mean()-1.96*se)*(d.mean()+1.96*se) < 0}")

# ---- B. 撤掉输液：真实死因 ----
print("\n=== B. 撤掉输液后（fg 决定一切）===")
for fg, label in [(0.0,'fg=0 无觅食能力'), (0.030,'fg=0.030 能觅食')]:
    al, tk = [], []
    for sd in SEEDS[:12]:
        lf = drip(600, sd, fg=fg)          # 先输液 600 拍
        t0 = lf.t
        while lf.alive and lf.t-t0 < 1500:
            lf.step()                       # 撤掉输液
        al.append(float(lf.alive)); tk.append(lf.t-t0)
    print(f"  {label:16s} 撤后存活 {np.mean(al):.3f} ({int(np.sum(al))}/12)  平均撑 {np.mean(tk):.0f} 拍")

# ---- C. fg 边界细扫 ----
print("\n=== C. fg 死亡边界细扫 ===")
for fg in [0.005,0.006,0.007,0.008,0.009,0.010,0.012]:
    al = [float(Life5(N=8,seed=sd,fg=fg).run(800).alive) for sd in SEEDS]
    print(f"  fg={fg:.3f}  存活 {np.mean(al):.3f} ({int(np.sum(al))}/24)")

json.dump(dict(common_n=len(common), forage=float(a.mean()), dripv=float(b.mean()),
               delta=float(d.mean()), se=float(se),
               ci=[float(d.mean()-1.96*se), float(d.mean()+1.96*se)]),
          open('result125b.json','w'), ensure_ascii=False, indent=1)
