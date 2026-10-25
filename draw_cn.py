# -*- coding: utf-8 -*-
"""上：中文 一跳 整条到底。下：代码 四跳 三段缝。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.2); ax.axis("off")
ax.add_patch(Rectangle((1.3,2.75), 7.4, 0.55, fc=OR, ec="none"))     # 中文：一跳，整条
for i in range(4):                                                     # 代码：四跳，三段缝
    ax.add_patch(Rectangle((1.3+i*2.3, 1.05), 1.5, 0.55, fc=OR, ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v45_一跳四跳.png",dpi=110,facecolor=BG); print("ok")
