#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""195: 眼睛为什么必须休息 —— 适应(adaptation) 与 恢复(recovery) 的对抗
模型(解析解):
  注视期 D: 敏感性 s 指数衰减 (适应), 产出 = s * novelty
  扫视期 G: 全盲 (saccadic suppression), 但 s 向 1 恢复
  稳态 s* = (1-e^{-bG}) / (1-e^{-(aD+bG)})
  rate = s* * (1-e^{-aD})/a / (D+G)
检验:
  H1 最优在中间带(两边都死)  H2 休息是功能性的(a=0 时 G*->0)
"""
import numpy as np, json, os
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

def rate(D, G, a, b, nov=1.0):
    if D <= 0: return 0.0
    eD = np.exp(-a*D)
    eG = np.exp(-b*G) if G > 0 else 1.0
    den = 1.0 - eD*eG
    s = 1.0 if abs(den) < 1e-12 else (1.0-eG)/den
    yc = s*(1.0-eD)/a if a > 1e-12 else s*D
    return nov*yc/(D+G)

def scan(a, b, Ds, Gs):
    best = (-1, 0, 0)
    for D in Ds:
        for G in Gs:
            r = rate(D, G, a, b)
            if r > best[0]: best = (r, D, G)
    return best

Ds = np.linspace(0.02, 2.0, 80)
Gs = np.linspace(0.0, 1.0, 81)

# ---- 主扫描: a=1.0, b=1.0 ----
a0, b0 = 1.0, 1.0
best = scan(a0, b0, Ds, Gs)
r_opt, D_opt, G_opt = best

R = np.array([[rate(D, G, a0, b0) for G in Gs] for D in Ds])

# ---- 两边都死的曲线 ----
# 固定最优 G, 扫 D
curve_D = [(float(D), rate(D, G_opt, a0, b0)) for D in Ds]
# 固定最优 D, 扫 G
curve_G = [(float(G), rate(D_opt, G, a0, b0)) for G in Gs]

# ---- 关键对照 H2: a=0 (无适应 -> 休息应变成纯浪费) ----
Gs2 = np.linspace(0.0, 1.0, 101)
ctrl_a0 = [(float(G), rate(D_opt, G, 0.0, b0)) for G in Gs2]
best_a0 = scan(0.0, b0, Ds, Gs)

# ---- 扫描 (a,b) 看 D*/G* 的范围 ----
ab = []
for a in [0.25, 0.5, 1.0, 2.0, 4.0]:
    for b in [0.25, 0.5, 1.0, 2.0, 4.0]:
        r, D, G = scan(a, b, Ds, Gs)
        ab.append(dict(a=a, b=b, D=round(float(D),4), G=round(float(G),4),
                       rate=round(float(r),5),
                       ratio=round(float(D)/float(G),3) if G>0 else None,
                       fps=round(1.0/(float(D)+float(G)),3)))

res = dict(
    main=dict(a=a0, b=b0, D_opt=round(float(D_opt),4), G_opt=round(float(G_opt),4),
              rate_opt=round(float(r_opt),5),
              frame_rate=round(1.0/(float(D_opt)+float(G_opt)),3),
              D_over_G=round(float(D_opt)/float(G_opt),3) if G_opt>0 else None),
    edges=dict(rate_D_to0=round(rate(0.02,G_opt,a0,b0),5),
               rate_D_big=round(rate(2.0,G_opt,a0,b0),5),
               rate_G_to0=round(rate(D_opt,0.0,a0,b0),5),
               rate_G_big=round(rate(D_opt,1.0,a0,b0),5)),
    control_no_adaptation=dict(G_opt=round(float(best_a0[2]),4),
                               rate_opt=round(float(best_a0[0]),5),
                               rate_at_Gmax=round(rate(D_opt,1.0,0.0,b0),5)),
    ab_scan=ab,
    curve_D=[[round(x,4), round(y,6)] for x,y in curve_D],
    curve_G=[[round(x,4), round(y,6)] for x,y in curve_G],
    ctrl_a0=[[round(x,4), round(y,6)] for x,y in ctrl_a0],
)
json.dump(res, open(os.path.join(OUT,"result195.json"),"w"), ensure_ascii=False, indent=1)

# ---- 图 ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
except Exception: pass

fig, ax = plt.subplots(2,2, figsize=(11,8))
im = ax[0,0].imshow(R, origin="lower", aspect="auto", cmap="viridis",
                    extent=[Gs[0],Gs[-1],Ds[0],Ds[-1]])
ax[0,0].plot(G_opt, D_opt, "r*", ms=16, label=f"opt D={D_opt:.2f} G={G_opt:.2f}")
ax[0,0].set_xlabel("G (rest / saccade blind)"); ax[0,0].set_ylabel("D (fixation)")
ax[0,0].set_title("yield rate: optimum in the middle"); ax[0,0].legend(); plt.colorbar(im,ax=ax[0,0])

xs=[c[0] for c in curve_D]; ys=[c[1] for c in curve_D]
ax[0,1].plot(xs,ys,"b-"); ax[0,1].axvline(D_opt,color="r",ls="--")
ax[0,1].set_xlabel("D (fixation length)"); ax[0,1].set_ylabel("yield rate")
ax[0,1].set_title("too short -> all blind; too long -> adapted")

xs=[c[0] for c in curve_G]; ys=[c[1] for c in curve_G]
ax[1,0].plot(xs,ys,"g-"); ax[1,0].axvline(G_opt,color="r",ls="--")
ax[1,0].set_xlabel("G (rest length)"); ax[1,0].set_ylabel("yield rate")
ax[1,0].set_title("no rest -> 0; too much rest -> wasted time")

xs=[c[0] for c in ctrl_a0]; ys=[c[1] for c in ctrl_a0]
ax[1,1].plot(xs,ys,"m-",label="a=0 (no adaptation)"); ax[1,1].set_xlabel("G"); ax[1,1].set_ylabel("yield rate")
ax[1,1].set_title("CONTROL: if nothing fatigues, rest is pure waste"); ax[1,1].legend()
plt.tight_layout(); plt.savefig(os.path.join(OUT,"render195.png"), dpi=110)
print(json.dumps(res["main"], ensure_ascii=False))
print("edges", res["edges"])
print("control a=0:", res["control_no_adaptation"])
