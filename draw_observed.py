# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json
BG="#0b0b0c"; OR="#FF6B1A"; DIM="#242427"
d=json.load(open("参数库/被观察的时间.json"))
fig,ax=plt.subplots(figsize=(9.6,4.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.2); ax.axis("off")
# 一整条：绝大部分是灰（没发生），最右一小段是橙（真实）
ax.add_patch(Rectangle((0.35,1.45), 9.30, 1.30, fc=DIM, ec="none"))
ax.add_patch(Rectangle((9.55,1.45), 0.10, 1.30, fc=OR, ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v33_只有这一段.png",dpi=110,facecolor=BG); print("ok")
