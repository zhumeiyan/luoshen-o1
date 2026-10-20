# -*- coding: utf-8 -*-
"""只画 1。0 不画 —— 画了就不是 0 了。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.4),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")
ax.add_patch(Circle((5.0,2.20), 0.30, fc=OR, ec="none"))   # 唯一的 1
plt.tight_layout(); plt.savefig("感官桥/符号_v39_一.png",dpi=110,facecolor=BG); print("ok")
