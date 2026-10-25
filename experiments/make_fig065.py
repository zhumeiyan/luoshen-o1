# -*- coding: utf-8 -*-
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","SimHei"]:
    try:
        fm.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

D=json.load(open("../data/result_065.json",encoding="utf-8"))
fig,ax=plt.subplots(2,3,figsize=(16.5,9.5))
RED="#c1121f"; BLU="#1d3557"; GRY="#8d99ae"; GRN="#2a9d8f"

# (1) 换宿主时点
A=D["A_swap_timing"]; ks=[k for k in A if k!="never"]
xs=[int(k) for k in ks]; loss=[A[k]["loss_pct"]*100 for k in ks]
tr=[A[k]["post_swap_trough"] for k in ks]
a=ax[0,0]; a.plot(xs,loss,"o-",color=RED,lw=2.2,label="换宿主后稳态损失 %")
a.set_xlabel("换宿主时点（拍）"); a.set_ylabel("损失 %",color=RED); a.tick_params(axis="y",labelcolor=RED)
a2=a.twinx(); a2.plot(xs,tr,"s--",color=BLU,lw=1.8,label="谷底产出（绝对）")
a2.set_ylabel("谷底产出",color=BLU); a2.tick_params(axis="y",labelcolor=BLU)
a.set_title("① 跌到底都一样深，\n区别只在爬不爬得回来",fontsize=11,fontweight="bold")
a.grid(alpha=.3)
h1,l1=a.get_legend_handles_labels(); h2,l2=a2.get_legend_handles_labels()
a.legend(h1+h2,l1+l2,fontsize=8,loc="lower right")

# (2) 宿主差异度
B=D["B_host_distance"]; b=ax[0,1]
dk=list(B.keys()); dv=[B[k]["loss_pct"]*100 for k in dk]
b.plot([float(k) for k in dk],dv,"o-",color=RED,lw=2.2)
b.axhline(0,color=GRY,ls=":",lw=1)
b.annotate("d=0 阴性对照\n必须为 0",xy=(0,0),xytext=(0.35,8),fontsize=8,color=GRN,
           arrowprops=dict(arrowstyle="->",color=GRN))
b.set_xlabel("新宿主与旧宿主的差异 d"); b.set_ylabel("损失 %")
b.set_title("② 宿主越不像，界面越用不上",fontsize=11,fontweight="bold"); b.grid(alpha=.3)

# (3) 界面特异度
C=D["C_sigma"]; c=ax[0,2]
ck=list(C.keys()); cv=[C[k]["loss_pct"]*100 for k in ck]
c.plot([float(k) for k in ck],cv,"o-",color=RED,lw=2.2)
c.set_xscale("log"); c.set_xlabel("界面特异度 σ（越小越特异）"); c.set_ylabel("损失 %")
c.set_title("③ 界面越特化，越不可迁移",fontsize=11,fontweight="bold"); c.grid(alpha=.3)

# (4) 多宿主 vs 专一
Dm=D["D_multi_host"]; d=ax[1,0]
nk=["1","2","3"]; ov=[Dm[k]["final_out"] for k in nk]; mv=[Dm[k]["final_match"] for k in nk]
xp=np.arange(3); w=0.38
d.bar(xp-w/2,ov,w,color=RED,label="产出")
d.bar(xp+w/2,mv,w,color=BLU,label="界面匹配度")
for i,(o,m) in enumerate(zip(ov,mv)):
    d.text(i-w/2,o+.01,f"{o:.3f}",ha="center",fontsize=8.5)
    d.text(i+w/2,m+.01,f"{m:.3f}",ha="center",fontsize=8.5)
d.set_xticks(xp); d.set_xticklabels(["专一 (n=1)","n=2","n=3"])
d.set_ylim(0,1.12); d.legend(fontsize=8)
d.set_title("④ 多宿主是劣势不是保险\n（064 处方被推翻）",fontsize=11,fontweight="bold",color=RED)
d.grid(alpha=.3,axis="y")

# (5) 独立性萎缩
E=D["E_independence"]; e=ax[1,1]
ek=["50","200","350"]; iv=[E[k]["ind_at_swap"] for k in ek]; ov2=[E[k]["final_out"] for k in ek]
e.plot([int(k) for k in ek],iv,"o-",color=BLU,lw=2.2,label="换宿主时的独立性")
e.axhline(E["mono_ind"],color=GRY,ls="--",lw=1.4,label="终态独立性下限")
e.set_xlabel("换宿主时点（拍）"); e.set_ylabel("独立性"); e.set_ylim(0,1.05)
e.legend(fontsize=8); e.grid(alpha=.3)
e.set_title("⑤ 共生越深，越换不动",fontsize=11,fontweight="bold")

# (6) 制裁
F=D["F_sanctions"]; f=ax[1,2]
lab=["制裁·合作","制裁·背叛","无制裁·合作","无制裁·背叛"]
key=["san=True,cheat=False","san=True,cheat=True","san=False,cheat=False","san=False,cheat=True"]
sv=[F[k]["self_gain"] for k in key]
cols=[GRN,GRY,GRN,RED]
bars=f.bar(range(4),sv,color=cols)
for i,v in enumerate(sv): f.text(i,v+.015,f"{v:.3f}",ha="center",fontsize=9)
f.set_xticks(range(4)); f.set_xticklabels(lab,fontsize=8.5)
f.set_ylabel("共生体自身收益"); f.set_ylim(0,0.95)
f.set_title("⑥ 背叛有利可图 →\n制裁是共生稳定的必要条件",fontsize=11,fontweight="bold")
f.grid(alpha=.3,axis="y")

plt.suptitle("065 · 共生体：换宿主的代价 —— 界面不可迁移，不是被惩罚",
             fontsize=14.5,fontweight="bold",y=0.985)
plt.tight_layout(rect=[0,0,1,0.955])
plt.savefig("../fig/065_symbiont.png",dpi=150)
print("saved ../fig/065_symbiont.png")
