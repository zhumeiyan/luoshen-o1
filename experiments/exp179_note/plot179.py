#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","WenQuanYi Zen Hei"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False
D="/data/workspace/luoshen-o1/experiments/exp179_note"
b=json.load(open(D+"/result179b.json",encoding="utf-8"))
c=json.load(open(D+"/result179c.json",encoding="utf-8"))
fig,ax=plt.subplots(2,2,figsize=(13,9))
# a 衰减
A=b["A_decay"]; lams=[e["lambda"] for e in A]; bits=[e["bits"] for e in A]
ax[0,0].plot(range(len(lams)),bits,"o-",color="#c0392b",lw=2,label="内化·记忆衰减")
ax[0,0].axhline(b["baseline_no_note"],ls="--",color="#2c3e50",label="无笔记基线 %.3f"%b["baseline_no_note"])
ax[0,0].axhline(b["note_bits"],ls=":",color="#27ae60",label="外化·完整笔记 %.3f"%b["note_bits"])
ax[0,0].set_xticks(range(len(lams))); ax[0,0].set_xticklabels([str(x) for x in lams])
ax[0,0].set_xlabel("衰减率 λ（0=笔记，越大越健忘）"); ax[0,0].set_ylabel("bits/字符（越低越准）")
ax[0,0].set_title("(a) 记了但忘掉大半，比从没记更糟"); ax[0,0].legend(fontsize=8); ax[0,0].grid(alpha=.3)
# b 容量
A2=b["A2_capacity"]; fr=[e["frac"] for e in A2]; bb=[e["bits"] for e in A2]
ax[0,1].plot(fr,bb,"s-",color="#2980b9",lw=2)
ax[0,1].axhline(b["baseline_no_note"],ls="--",color="#2c3e50")
ax[0,1].axhline(b["note_bits"],ls=":",color="#27ae60")
ax[0,1].set_xscale("log"); ax[0,1].set_xlabel("内化容量（保留条数比例）"); ax[0,1].set_ylabel("bits/字符")
ax[0,1].set_title("(b) 容量越小越接近“没记”"); ax[0,1].grid(alpha=.3)
# c 笔记形式效率
B=b["B_forms"]; names=[e["form"] for e in B]; eff=[e["bits_per_kb"] for e in B]
cols=["#27ae60" if e==max(eff) else "#7f8c8d" for e in eff]
ax[1,0].barh(range(len(names)),eff,color=cols)
ax[1,0].set_yticks(range(len(names))); ax[1,0].set_yticklabels(names,fontsize=9)
ax[1,0].invert_yaxis(); ax[1,0].set_xlabel("每 KB 笔记换回的 bits（越高越省）")
ax[1,0].set_title("(c) 抄原文是最浪费的笔记，编号+摘抄最省"); ax[1,0].grid(alpha=.3,axis="x")
for i,v in enumerate(eff): ax[1,0].text(v+.005,i,"%.3f"%v,va="center",fontsize=9)
# d 稳健性
al=[r["ALPHA"] for r in c]; ex=[r["lam2.0"]-r["baseline"] for r in c]
ex2=[r["lam0.5"]-r["baseline"] for r in c]
ax[1,1].plot(range(len(al)),ex,"o-",color="#c0392b",label="λ=2.0 超出基线")
ax[1,1].plot(range(len(al)),ex2,"s-",color="#e67e22",label="λ=0.5 超出基线")
ax[1,1].axhline(0,color="k",lw=1)
ax[1,1].set_xticks(range(len(al))); ax[1,1].set_xticklabels([str(a) for a in al])
ax[1,1].set_xlabel("平滑系数 α"); ax[1,1].set_ylabel("bits − 无笔记基线（>0 = 比没记更糟）")
ax[1,1].set_title("(d) 5 档 α 全部复现"); ax[1,1].legend(fontsize=8); ax[1,1].grid(alpha=.3)
plt.tight_layout(); plt.savefig(D+"/render179.png",dpi=110); print("ok render179.png")
