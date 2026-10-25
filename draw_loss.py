# -*- coding: utf-8 -*-
"""上下两个同样宽的方块，起点错开。中间那段就是缝。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.2); ax.axis("off")
W=4.6
ax.add_patch(Rectangle((2.0,2.60), W, 0.55, fc=OR, ec="none"))   # A 第N级
ax.add_patch(Rectangle((3.4,1.15), W, 0.55, fc=OR, ec="none"))   # B 第N级（错开）
plt.tight_layout(); plt.savefig("感官桥/符号_v44_缝.png",dpi=110,facecolor=BG); print("ok")
