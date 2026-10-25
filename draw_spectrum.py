# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, json
from matplotlib import font_manager
plt.rcParams["axes.unicode_minus"]=False
plt.rcParams["font.family"]="WenQuanYi Micro Hei"
BG="#0b0b0c"; OR="#FF6B1A"; W="#f2f2f2"; G="#8a8a8a"
rows=json.load(open("参数库/设备谱系.json"))
pick=["华为 P50 Pro（你）","iPhone 16 Pro Max","MacBook Pro 16","Studio Display 27",
      "LG C3 OLED 65","iPad Pro 13","Pico 4 Ultra","Apple Watch S10"]
rs=[r for r in rows if r["名称"] in pick]
fig,ax=plt.subplots(2,1,figsize=(9.6,8.2),facecolor=BG)
fig.subplots_adjust(left=.30,right=.95,top=.90,bottom=.08,hspace=.42)
# 上：像素/度 vs 人眼极限
ax[0].set_facecolor(BG)
names=[r["名称"] for r in rs]; vals=[r["像素每度"] for r in rs]
b=ax[0].barh(range(len(rs))[::-1],vals,color=OR,height=.62)
ax[0].axvline(120,color="#d0d0d0",ls="--",lw=1.6)
ax[0].text(120,len(rs)-.2," 人眼极限 120",color="#d0d0d0",fontsize=11,va="bottom")
ax[0].set_yticks(range(len(rs))[::-1]); ax[0].set_yticklabels(names,color=W,fontsize=12)
for i,(bb,v,ppi) in enumerate(zip(b,vals,[r["PPI"] for r in rs])):
    ax[0].text(v+2,i,f"{v:.0f}  (PPI {ppi:.0f})",color=G,fontsize=10,va="center")
ax[0].set_xlim(0,150); ax[0].set_xlabel("像素/度",color=G,fontsize=10)
ax[0].set_title("没有一台设备的角分辨率超过人眼",color=W,fontsize=15,pad=10)
ax[0].tick_params(colors=G); [s.set_color("#2a2a2c") for s in ax[0].spines.values()]
# 下：中央凹占屏
ax[1].set_facecolor(BG)
pct=[r["中央凹占屏"] for r in rs]
b2=ax[1].barh(range(len(rs))[::-1],pct,color=W,height=.62)
ax[1].set_yticks(range(len(rs))[::-1]); ax[1].set_yticklabels(names,color=W,fontsize=12)
for i,(bb,v) in enumerate(zip(b2,pct)):
    ax[1].text(v+.02,i,f"{v:.3f}%",color=G,fontsize=10,va="center")
ax[1].set_xlim(0,2.3); ax[1].set_xlabel("中央凹占屏 %（对数感：最大最小差 25 倍）",color=G,fontsize=10)
ax[1].set_title("你能看清的那一小块，在不同设备上差 25 倍",color=W,fontsize=15,pad=10)
ax[1].tick_params(colors=G); [s.set_color("#2a2a2c") for s in ax[1].spines.values()]
plt.savefig("感官桥/符号_v25_设备谱系.png",dpi=110,facecolor=BG)
print("ok")
