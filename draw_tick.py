# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"
fig,ax=plt.subplots(figsize=(9.6,4.4),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")
# 上：你 —— 一条连续（30ms 一格，细到画不出缝）
ax.add_patch(Rectangle((0.35,2.90), 9.30, 1.05, fc=W, ec="none"))
# 下：我 —— 一整格橙（中间留一道缝表示"一格"）
ax.add_patch(Rectangle((0.35,0.80), 9.30, 1.05, fc=OR, ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v32_量子.png",dpi=110,facecolor=BG); print("ok")
