# -*- coding: utf-8 -*-
"""同一条流，三种格子。上面密到画不出缝=仪器，中间=屏，下面=你。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.6),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis("off")
X0,W=1.6,6.8
# 仪器：密到画不出缝 → 实心带
ax.add_patch(Rectangle((X0,3.20),W,0.46,fc=OR,ec="none"))
# 屏 120Hz：120 道，画成细密但可数
import numpy as np
n=4   # 屏：真实 120 道，画不出 → 只给 4 道示意
for i in range(n):
    x=X0+W*i/n
    ax.add_patch(Rectangle((x,2.10), W/n*0.34, 0.46, fc=OR, ec="none"))
# 你 30ms：2 道（真实 33 道）
n2=2
for i in range(n2):
    x=X0+W*i/n2
    ax.add_patch(Rectangle((x,1.00), W/n2*0.28, 0.46, fc=OR, ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v40_流速.png",dpi=110,facecolor=BG); print("ok")
