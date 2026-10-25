# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","SimHei"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

r=json.load(open("result187.json",encoding="utf-8"))
rb=json.load(open("robust187.json",encoding="utf-8"))
L=r["layers"]; M=r["matched_control"]; D=r["cum_vs_matched"]
lab=[a["label"].split(" ")[0] for a in L]
x=range(len(L))

fig,ax=plt.subplots(2,2,figsize=(13,9))

# A 预测 & 纠错
a=ax[0,0]
a.plot(x,[e["C2_预测(未见过)"] for e in L],"o-",color="#c0392b",lw=2,label="C2 预测（未见过）")
a.plot(x,[e["C3_纠错AUC"] for e in L],"s-",color="#2980b9",lw=2,label="C3 纠错 AUC")
a.axhline(0.5,ls="--",c="gray",lw=1)
a.text(0.1,0.52,"随机基线 0.5 = 做不到",fontsize=8,color="gray")
a.axvspan(0.6,1.6,color="#f1c40f",alpha=0.25)
a.text(1.1,0.95,"涌现点",fontsize=9,color="#b9770e",ha="center")
a.set_xticks(list(x)); a.set_xticklabels(lab,fontsize=9)
a.set_title("A 能力在叠到 L2 时跃出",fontsize=11); a.legend(fontsize=8); a.grid(alpha=.3)

# B 压缩 & 复现
b=ax[0,1]
b.plot(x,[e["C4_压缩bits"] for e in L],"o-",color="#8e44ad",lw=2,label="C4 压缩 bits（越低越强）")
b.axhline(r["baseline"]["uniform_bits"],ls="--",c="gray",lw=1)
b.text(0.1,r["baseline"]["uniform_bits"]+0.6,"均匀基线 7.54",fontsize=8,color="gray")
b.set_ylabel("bits/字符",fontsize=9)
b2=b.twinx()
b2.plot(x,[e["C1_复现(自身)"] for e in L],"^--",color="#16a085",lw=1.6,label="C1 复现自身")
b2.set_ylabel("复现率",fontsize=9); b2.set_ylim(0.6,1.0)
b.set_xticks(list(x)); b.set_xticklabels(lab,fontsize=9)
b.set_title("B 压缩转正 vs 记忆下降（权衡）",fontsize=11)
b.grid(alpha=.3)
h1,l1=b.get_legend_handles_labels(); h2,l2=b2.get_legend_handles_labels()
b.legend(h1+h2,l1+l2,fontsize=8,loc="center right")

# C 累积 vs 同量随机
c=ax[1,0]
acc=[e["C2_预测(未见过)"] for e in L]; macc=[e["C2_预测(未见过)"] for e in M]
w=0.38
c.bar([i-w/2 for i in x],acc,w,label="累积叠加",color="#c0392b")
c.bar([i+w/2 for i in x],macc,w,label="同量随机对照",color="#95a5a6")
for i in range(len(x)):
    d=acc[i]-macc[i]
    if abs(d)>0.01: c.text(i,max(acc[i],macc[i])+0.02,f"Δ{d:+.3f}",ha="center",fontsize=7.5)
c.set_xticks(list(x)); c.set_xticklabels(lab,fontsize=9)
c.set_title("C 不能被'数据变多'解释的部分",fontsize=11); c.legend(fontsize=8); c.grid(alpha=.3,axis="y")

# D 稳健性
d=ax[1,1]
for row in rb:
    ks=[row[k]["acc"] for k in ["L0","L1","L2","L3"]]
    d.plot(["L0","L1","L2","L3"],ks,"o-",alpha=.45,lw=1.2,
           label=f"k={row['kmax']} s={row['seed']}" if row["kmax"]==3 and row["seed"]==42 else None)
d.set_title(f"D 稳健性：{len(rb)}/{len(rb)} 组复现 L1→L2 阶跃",fontsize=11)
d.set_ylabel("C2 预测准确率",fontsize=9); d.grid(alpha=.3); d.legend(fontsize=8)

plt.suptitle("187 叠加状态时长出能力：涌现点 L1→L2，饱和点 L4 之后",fontsize=13)
plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig("render187.png",dpi=130)
print("ok")
