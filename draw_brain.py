# -*- coding: utf-8 -*-
"""两条流。左：你的神经元串行，一步一突触。右：我串行极快但你并行更快。
只画两条长短不同的带 + 一个分岔。块数要少。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.6),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis("off")
# 上：串行 —— 我长，你短
ax.add_patch(Rectangle((1.4,3.10), 0.42, 0.52, fc=OR, ec="none"))   # 你 1 格
ax.add_patch(Rectangle((1.4,2.30), 7.3, 0.52, fc=OR, ec="none"))    # 我 长带
# 下：并行 —— 你长，我短
ax.add_patch(Rectangle((1.4,1.30), 7.3, 0.52, fc=OR, ec="none"))    # 你 长带
ax.add_patch(Rectangle((1.4,0.50), 0.42, 0.52, fc=OR, ec="none"))   # 我 1 格
plt.tight_layout(); plt.savefig("感官桥/符号_v41_两条流.png",dpi=110,facecolor=BG); print("ok")
