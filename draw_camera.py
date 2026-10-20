# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import json
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"
fig,ax=plt.subplots(figsize=(9.2,4.8),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.8); ax.axis("off")
# 左：你 —— 大虚线圈（稀）+ 中心实心（密）
ax.add_patch(Circle((2.4,2.5),1.35,fc="none",ec="#5a5a5e",lw=2.2,ls=(0,(5,3))))
ax.add_patch(Circle((2.4,2.5),0.36,fc=OR,ec="none"))
# 右：摄像头 —— 同样大小，整个实心（处处一样密）
ax.add_patch(Circle((7.6,2.5),1.35,fc="#6e6e72",ec="none"))
# 极短标签
ax.text(2.4,0.72,"你",color=W,fontsize=15,ha="center")
ax.text(7.6,0.72,"它",color=W,fontsize=15,ha="center")
plt.tight_layout(); plt.savefig("感官桥/符号_v30_摄像头.png",dpi=110,facecolor=BG); print("ok")
