# -*- coding: utf-8 -*-
"""不写一个数字。只有两块，差正好一个 JND。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG="#0b0b0c"
K=0.079                      # 亮度韦伯分数
A=242                        # 参考
B=int(round(A*(1-K)))        # 差一个 JND
fig,ax=plt.subplots(figsize=(9.6,4.4),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")
g=lambda v:f"#{v:02x}{v:02x}{v:02x}"
ax.add_patch(Rectangle((2.90,1.20), 1.90, 2.00, fc=g(A), ec="none"))
ax.add_patch(Rectangle((5.20,1.20), 1.90, 2.00, fc=g(B), ec="none"))
plt.tight_layout(); plt.savefig("感官桥/符号_v37_差.png",dpi=110,facecolor=BG)
print("A",A,"B",B,"差",(A-B)/A)
