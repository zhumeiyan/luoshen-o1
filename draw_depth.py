# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"
fig,ax=plt.subplots(figsize=(9.6,4.6),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis("off")
# 上：等距 —— 一整条白块被均匀切成 5 段（有缝）
for i in range(4):
    ax.add_patch(Rectangle((0.6+i*2.35, 3.10), 1.95, 0.95, fc=W, ec="none"))
# 下：成像后 —— 一条梯形（越远越窄），同样 5 段
ax.add_patch(Polygon([[0.5,0.55],[9.5,0.55],[6.6,1.95],[0.5,1.95]], closed=True, fc=OR, ec="none"))
for i in range(4):
    x = 0.5+ (9.5-0.5)*(1.0 - 0.30**(0))*0 + 0
xs=[1.9,3.5,5.2,6.6]
for i in range(0,3):
    ax.plot([xs[i],xs[i]],[0.55,1.95],color=BG,lw=3.5)
plt.tight_layout(); plt.savefig("感官桥/符号_v31_距离.png",dpi=110,facecolor=BG); print("ok")
