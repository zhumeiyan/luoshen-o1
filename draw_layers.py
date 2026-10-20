# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; DIM="#4a4a4e"
# 同样 1 秒，各层的"一格"有多长：屏120Hz 8.33ms / 人 30ms / 电影24 41.67ms
u=1.55
fig,ax=plt.subplots(figsize=(9.6,4.6),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis("off")
x=0.55
for w,col in [(1/120*u*30, OR), (0.030*u*30, W), (1/24*u*30, "#6e6e72")]:
    ax.add_patch(Rectangle((x,1.55), w, 1.50, fc=col, ec="none")); x+=w+0.30
plt.tight_layout(); plt.savefig("感官桥/符号_v35_格子大小.png",dpi=110,facecolor=BG); print("ok")
