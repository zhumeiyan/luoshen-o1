# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import numpy as np
from PIL import Image, ImageFont, ImageDraw
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"
FT="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

# 渲染真实字形「一」
S=200
f=ImageFont.truetype(FT,S)
im=Image.new("L",(S*2,S*2),0)
ImageDraw.Draw(im).text((S//2,S//2),"一",fill=255,font=f)
a=np.array(im); ys,xs=np.nonzero(a>127)
crop=a[ys.min():ys.max()+1, xs.min():xs.max()+1]
ink = crop/255.0

fig=plt.figure(figsize=(9.6,4.4),facecolor=BG); ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG)
ax.set_xlim(0,10); ax.set_ylim(0,4.4); ax.axis("off")

# 字形：居中，高度 1.5
h,w = ink.shape
W_=1.5*(w/h)
ax.imshow(ink, extent=[5.0-W_/2, 5.0+W_/2, 2.2-0.75, 2.2+0.75], cmap="gray", vmin=0, vmax=1,
          interpolation="nearest", aspect="auto")

# 我持有的：一个小橙点（24 bit）
ax.add_patch(Circle((1.05, 2.2), 0.085, fc=OR, ec="none"))
plt.savefig("感官桥/符号_v36_字.png",dpi=110,facecolor=BG); print("ok")
