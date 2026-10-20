# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, json
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; G="#8a8a8a"
d=json.load(open("参数库/国际标准.json"))
items=sorted(d["iso15008_px"].items(), key=lambda x:-x[1])
names=[k for k,_ in items]; px=[v for _,v in items]
fig,ax=plt.subplots(figsize=(9.6,7.0),facecolor=BG); ax.set_facecolor(BG)
y=range(len(items))[::-1]
cols=[OR if v>=12 else ("#c8c8c8" if v>=9 else "#5a2a12") for v in px]
ax.barh(list(y), px, color=cols, height=.62)
ax.axvline(12, color="#d0d0d0", ls="--", lw=1.6)
ax.text(12.4, len(items)-.6, "ISO 最低 12'  ", color="#d0d0d0", fontsize=11)
ax.axvline(20, color="#9a9a9a", ls=":", lw=1.4)
ax.text(20.4, len(items)-.6, "ISO 推荐 20'", color="#9a9a9a", fontsize=11)
ax.set_yticks(list(y)); ax.set_yticklabels(names,color=W,fontsize=11.5)
for i,v in zip(y,px):
    ax.text(v+.5, i, f"{v:.1f}px", color=G, fontsize=10, va="center")
ax.set_xlabel("ISO 15008 最低字符高度（12 弧分）在这台设备上等于多少像素",color=G,fontsize=10.5)
ax.set_title("同一个国际标准，在不同设备上要不同的像素数",color=W,fontsize=16,pad=14)
ax.text(0.02,0.015,"橙=达标  灰=偏低  暗=不达标（Pico 4 只有 5.8px）",
        transform=ax.transAxes,color=G,fontsize=10)
ax.tick_params(colors=G); [s.set_color("#2a2a2c") for s in ax.spines.values()]
plt.tight_layout(); plt.savefig("感官桥/符号_v27_国际标准.png",dpi=110,facecolor=BG); print("ok")
