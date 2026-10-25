# -*- coding: utf-8 -*-
"""差不多 = 圈内。但每帧都合格，一串就漂出去了。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import numpy as np
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.4),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")
# 原点 + 容差圈
ax.add_patch(Rectangle((1.05,1.62),0.62,0.62,fc=OR,ec="none"))
c=Circle((1.36,1.93),0.95,fc="none",ec=OR,lw=1.4,ls=(0,(5,4)))
ax.add_patch(c)
# 一串点，越走越偏（每步都在容差内，累积后出圈）
# 只给三个点：圈内(合格) → 圈边 → 圈外(漂出)
for x,y,s2 in [(2.30,1.93,0.19),(3.10,2.06,0.19),(3.95,2.30,0.19)]:
    ax.add_patch(Rectangle((x,y-s2/2),s2,s2,fc=OR,ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v43_当作一.png",dpi=110,facecolor=BG); print("ok")
