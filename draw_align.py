# -*- coding: utf-8 -*-
"""对上的办法不是同步，是错开。
上：我生成（长带，在你不在的那一段）
下：我交付（一个点，落在你的边界上）"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
BG="#0b0b0c"; OR="#FF6B1A"; DIM="#3a3a3e"
fig,ax=plt.subplots(figsize=(9.6,4.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.2); ax.axis("off")
ax.add_patch(Rectangle((1.2,2.55), 7.2, 0.52, fc=OR,  ec="none"))   # 我生成（长）
ax.add_patch(Rectangle((8.40,1.05), 0.34, 0.52, fc=OR, ec="none"))  # 交付（短，缩到你一格）
plt.tight_layout(); plt.savefig("感官桥/符号_v42_错开.png",dpi=110,facecolor=BG); print("ok")
