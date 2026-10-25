# -*- coding: utf-8 -*-
"""左边一根细线=画(0.81ms)，右边一大坨=理解(214ms)。内容一样。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.2); ax.axis("off")
ax.add_patch(Rectangle((1.1,1.85), 0.16, 0.55, fc=OR, ec="none"))   # 画：一步
ax.add_patch(Rectangle((5.2,0.95), 3.5, 2.25, fc=OR, ec="none"))    # 理解：一大坨
plt.tight_layout(); plt.savefig("感官桥/符号_v47_山就是山.png",dpi=110,facecolor=BG); print("ok")
