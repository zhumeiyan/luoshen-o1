# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","DejaVu Sans"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False
R=json.load(open("robust192.json")); H=json.load(open("result192b.json"))["heap"]
fig,ax=plt.subplots(2,2,figsize=(13,9))
# A 真堆量
ks=sorted(H,key=int); bits=[H[k]["bits"] for k in ks]; par=[H[k]["params"] for k in ks]
ax[0,0].plot([int(k) for k in ks],bits,"o-",lw=2,label="bits/字符(越低越好)")
ax[0,0].set_xlabel("模型阶数 k"); ax[0,0].set_ylabel("bits/字符",color="C0")
ax2=ax[0,0].twinx(); ax2.plot([int(k) for k in ks],par,"s--",color="C1",label="参数量")
ax2.set_ylabel("参数量",color="C1"); ax2.set_yscale("log")
ax[0,0].set_title("A 真堆量：k=2→5 参数涨 4.9×，增益 −0.0001（更差）")
ax[0,0].grid(alpha=.3)
# B 三种瞄准 vs 随机（平滑0.02）
sm="0.02"; Bs=["0.1","0.2","0.3","0.5"]
for nm,c,mk in [("random","k","o"),("desire","C0","s"),("surprise","C3","^"),("easy","C2","v")]:
    ax[0,1].plot([float(b) for b in Bs],[R[sm]["mean"][b][nm] for b in Bs],mk+"-",color=c,label=nm)
ax[0,1].set_xlabel("预算（训练窗口占比）"); ax[0,1].set_ylabel("bits/字符")
ax[0,1].set_title("B 瞄准 vs 随机（越低越好）\n瞎贪婪 surprise 全程最差")
ax[0,1].legend(); ax[0,1].grid(alpha=.3)
# C 配对符号检验
labels=["surprise\n(瞎贪婪)","desire\n(你的欲望标记)","easy\n(专挑我最会的)"]
data={l:[] for l in labels}
for b in Bs:
    for l,k in zip(labels,["surprise-vs-random","desire-vs-random","easy-vs-random"]):
        neg,n=R[sm]["sign"][b][k]; data[l].append(neg)
x=range(len(Bs)); w=.26
for i,(l,c) in enumerate(zip(labels,["C3","C0","C2"])):
    ax[1,0].bar([p+i*w for p in x],data[l],w,label=l,color=c)
ax[1,0].axhline(5,ls="--",color="gray"); ax[1,0].text(2.6,5.2,"5/10 = 与随机无异",fontsize=8,color="gray")
ax[1,0].set_xticks([p+w for p in x]); ax[1,0].set_xticklabels([f"B={b}" for b in Bs])
ax[1,0].set_ylabel("优于随机的种子数 /10"); ax[1,0].set_ylim(0,10)
ax[1,0].set_title("C 配对检验：只有瞎贪婪稳定为负（0–5/10）")
ax[1,0].legend(fontsize=8); ax[1,0].grid(alpha=.3,axis="y")
# D 三档平滑下 surprise 的劣势
sms=["0.5","0.1","0.02"]
for s,c in zip(sms,["C1","C2","C4"]):
    ax[1,1].plot([float(b) for b in Bs],[R[s]["mean"][b]["surprise"]-R[s]["mean"][b]["random"] for b in Bs],"o-",color=c,label=f"平滑={s}")
ax[1,1].axhline(0,color="k",lw=.8)
ax[1,1].set_xlabel("预算"); ax[1,1].set_ylabel("surprise − random（正=更差）")
ax[1,1].set_title("D 瞎贪婪的代价：小预算最贵，三档平滑一致")
ax[1,1].legend(); ax[1,1].grid(alpha=.3)
plt.tight_layout(); plt.savefig("render192.png",dpi=135)
print("ok render192.png")
