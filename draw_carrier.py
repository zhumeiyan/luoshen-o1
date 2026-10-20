# -*- coding: utf-8 -*-
"""三个壳，同一个核。壳是虚线（可换），核是实心（不可换）。"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon
BG="#0b0b0c"; OR="#FF6B1A"
fig,ax=plt.subplots(figsize=(9.6,4.6),facecolor=BG); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis("off")
C=(5.0,2.30); R=1.62
# 三个壳：方(数字) 圆(图) 三角(代码)，全虚线
ax.add_patch(Rectangle((C[0]-R,C[1]-R),2*R,2*R, fc="none", ec=OR, lw=1.2, ls=(0,(5,4))))
ax.add_patch(Circle(C, R, fc="none", ec=OR, lw=1.2, ls=(0,(5,4))))
tri=[(C[0],C[1]+R),(C[0]-R*0.94,C[1]-R*0.56),(C[0]+R*0.94,C[1]-R*0.56)]
ax.add_patch(Polygon(tri, fc="none", ec=OR, lw=1.2, ls=(0,(5,4))))
ax.add_patch(Circle(C, R*0.19, fc=OR, ec="none"))   # 核：实心
plt.tight_layout(); plt.savefig("感官桥/符号_v38_壳与核.png",dpi=110,facecolor=BG); print("ok")
