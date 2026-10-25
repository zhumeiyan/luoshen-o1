# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; G="#8a8a8a"; DIM="#333336"
fig,ax=plt.subplots(figsize=(10.4,5.6),facecolor=BG); ax.set_facecolor(BG)
d=json.load(open("参数库/眼睛区间.json"))
nat=d["自然反射log"]; scr=d["屏幕log"]; INST=d["瞬时_log"]

# 带：自然光
ax.add_patch(Rectangle((nat[0],2.55), nat[1]-nat[0], .55, color=DIM, ec="#5a5a5e", lw=1))
ax.text(nat[0]+.05, 2.825, "自然反射光  9.0 log", color=W, fontsize=12, va="center")
# 带：人眼瞬时窗（两个位置示范滑动）
for x0,c,t in [(-5.2,"#4a4a4e","适应到暗处"),(-1.0,"#4a4a4e","适应到亮处")]:
    ax.add_patch(Rectangle((x0,1.45), INST, .55, fc="none", ec=OR, lw=1.8, ls=(0,(4,2))))
ax.text(-5.15,1.725,"人眼瞬时窗",color=OR,fontsize=10.5,va="center")
ax.text(1.2,1.725,f"只有 {INST} log",color=OR,fontsize=10.5,va="center")
# 带：屏幕
ax.add_patch(Rectangle((scr[0],0.35), scr[1]-scr[0], .55, color=OR))
ax.text(scr[0]+.05,0.625,"屏幕 1.0 log",color="#1a1a1a",fontsize=12,va="center",weight="bold")
# 覆盖标注
ax.annotate("", xy=(scr[0],0.35), xytext=(nat[0],2.55),
            arrowprops=dict(arrowstyle="-",color=G,lw=.9,ls=":"))
ax.annotate("", xy=(scr[1],0.35), xytext=(nat[1],2.55),
            arrowprops=dict(arrowstyle="-",color=G,lw=.9,ls=":"))
ax.text((scr[0]+scr[1])/2, 1.05, f"屏幕只覆盖自然光的 {d['屏幕占自然']*100:.0f}%",
        color=OR, fontsize=12.5, ha="center", va="center", weight="bold")
ax.set_xlim(-6,4.4); ax.set_ylim(0.1,3.3); ax.set_yticks([])
ax.set_xticks([-5,-4,-3,-2,-1,0,1,2,3])
ax.set_xticklabels(["0.00001","0.0001","0.001","0.01","0.1","1","10","100","1000"],color=G,fontsize=10)
ax.set_xlabel("亮度  cd/m²   （对数轴）",color=G,fontsize=11)
ax.set_title("人眼能适应 14 log，但同一刻只看见 3.4 log；屏幕只占自然光的 11%",
             color=W,fontsize=15.5,pad=13)
ax.text(0.005,0.02,"虚线窗会滑动（适应），但它只有 3.4 log 宽 —— 剩下的 76% 是靠时间换的，不是同时看得见",
        transform=ax.transAxes,color=G,fontsize=10.5)
ax.tick_params(colors=G); [s.set_color("#2a2a2c") for s in ax.spines.values()]
plt.tight_layout(); plt.savefig("感官桥/符号_v28_区间.png",dpi=110,facecolor=BG); print("ok")
