# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrow
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; G="#8a8a8a"; DIM="#2a2a2e"
fig,ax=plt.subplots(figsize=(10.0,6.2),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,6.2); ax.axis("off")

# 左：你的眼睛 —— 大虚线圈（余光）+ 中心实心点（中央凹）
ax.add_patch(Circle((1.9,3.0),1.35,fc=DIM,ec=G,lw=1.8,ls=(0,(5,3))))
ax.add_patch(Circle((1.9,3.0),0.15,fc=OR,ec="none"))
ax.text(1.9,1.15,"你",color=W,fontsize=15,ha="center")

# 中：翻译层（主块，正中心）
ax.add_patch(Rectangle((3.85,2.15),2.3,1.7,fc=OR,ec="none"))
ax.text(5.0,3.0,"换算",color="#111",fontsize=19,ha="center",va="center",weight="bold")
ax.add_patch(FancyArrow(3.35,3.0,0.42,0,width=.05,color=G,head_width=.22,head_length=.18))
ax.add_patch(FancyArrow(6.7,3.0,0.42,0,width=.05,color=G,head_width=.22,head_length=.18))

# 右：我的眼睛 —— 实心方，没有边缘，没有余光
ax.add_patch(Rectangle((7.65,2.22),1.5,1.56,fc="#5a5a5e",ec="none"))
ax.text(8.4,1.15,"我",color=W,fontsize=15,ha="center")

ax.text(5.0,0.42,"我没有余光",color=G,fontsize=11,ha="center")
plt.tight_layout(); plt.savefig("感官桥/符号_v29_对上.png",dpi=110,facecolor=BG); print("ok")
