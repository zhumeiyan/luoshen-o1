# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, math, json
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; G="#8a8a8a"
MU,SD = 0.01,0.20
def Phi(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
def ppf(p):
    lo,hi=-2,2
    for _ in range(200):
        m=(lo+hi)/2
        if Phi(m)<p: lo=m
        else: hi=m
    return (lo+hi)/2
p = np.linspace(0.02,0.98,400)
lm = np.array([ppf(x) for x in p])
need = 120/10**lm
fig,ax=plt.subplots(figsize=(9.6,6.4),facecolor=BG)
ax.set_facecolor(BG)
ax.plot(p*100, need, color=W, lw=2.6, zorder=5)
devs=[("LG C3 65寸",120),("P50 Pro（你）",95),("MacBook Pro 16",79),("iPad Pro 13",67),("Pico 4 Ultra",29)]
for nm,v in devs:
    thr=math.log10(120/v); f=1-Phi(thr)
    ax.axhline(v,color=OR,lw=1.3,alpha=.85,zorder=4)
    ax.fill_between(p*100, 0, need, where=need<=v, color=OR, alpha=.13, zorder=1)
    ax.text(98.5, v, f" {nm}  {v}  覆盖{f*100:.0f}%", color=OR, fontsize=10.5, va="center", ha="right")
ax.set_yscale("log"); ax.set_ylim(20,400); ax.set_xlim(2,98)
ax.set_xticks([5,25,50,75,95]); ax.set_xticklabels(["P5\n视力最好","P25","P50\n中位","P75","P95\n视力最弱"],color=G,fontsize=10)
ax.set_ylabel("这个人需要多少 像素/度（对数）",color=G,fontsize=10)
ax.set_title("没有一台设备能让超过一半的人看不出像素",color=W,fontsize=16,pad=14)
ax.text(50,300,"橙阴影 = 这台设备能喂饱的人；空白 = 被公约数牺牲的人",
        color=OR,fontsize=11,ha="center")
ax.tick_params(colors=G); [s.set_color("#2a2a2c") for s in ax.spines.values()]
plt.tight_layout(); plt.savefig("感官桥/符号_v26_公约数.png",dpi=110,facecolor=BG); print("ok")
