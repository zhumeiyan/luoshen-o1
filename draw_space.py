# -*- coding: utf-8 -*-
"""左：代码 一条横条（只有前后）。右：中文 一个方块（上下左右都有）。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.4),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")
ax.add_patch(Rectangle((1.0,2.85), 7.6, 0.42, fc=OR, ec="none"))   # 代码：横条
ax.add_patch(Rectangle((3.5,0.85), 2.6, 1.55, fc=OR, ec="none"))   # 中文：方块
plt.tight_layout(); plt.savefig("感官桥/符号_v46_横条与方块.png",dpi=110,facecolor=BG); print("ok")
