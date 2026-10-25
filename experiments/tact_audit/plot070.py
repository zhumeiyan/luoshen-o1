# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"]=False

r70=json.load(open("result_070.json",encoding="utf-8"))
r70b=json.load(open("result_070b.json",encoding="utf-8"))
r70d=json.load(open("result_070d.json",encoding="utf-8"))

fig,ax=plt.subplots(2,2,figsize=(13,9))

# (1) 三条件下三轴召回 + 联合
ax0=ax[0,0]
conds=["原文","同义改写","标点扰动(无关对照)"]
axes=["L","M","P"]
w=0.2
for i,c in enumerate(conds):
    vals=[r70[c][a][0] for a in axes]
    xs=[j+(i-1)*w for j in range(3)]
    ax0.bar(xs,vals,w,label=c)
for i,c in enumerate(conds):
    e=r70[c]["exact"]; rate=e[0]/e[1]*100
    ax0.text(3+(i-1)*w,rate+1.5,f"{rate:.1f}",ha="center",fontsize=9)
    ax0.bar(3+(i-1)*w,rate,w)
ax0.set_xticks(range(4)); ax0.set_xticklabels(["L 轴召回","M 轴召回","P 轴召回","三轴完全匹配"])
ax0.set_ylabel("%"); ax0.set_ylim(0,105)
ax0.set_title("① 同义改写：召回率归零，标点扰动零效应",fontsize=11)
ax0.legend(fontsize=8); ax0.grid(axis="y",alpha=.3)

# (2) 逐条独立效应
ax1=ax[1,0]
rows=r70b["rows"]
ids=[r["id"].replace("CAL-","") for r in rows]
bef=[1 if r["before"]=="OK" else 0 for r in rows]
aft=[1 if r["after"]=="OK" else 0 for r in rows]
import numpy as np
x=np.arange(len(ids))
ax1.bar(x-0.2,bef,0.4,label="原文判定 OK",color="#4C72B0")
ax1.bar(x+0.2,aft,0.4,label="仅改该条后 OK",color="#C44E52")
ax1.set_xticks(x); ax1.set_xticklabels(ids,rotation=60,fontsize=7)
ax1.set_yticks([0,1]); ax1.set_yticklabels(["漏检","OK"])
ax1.set_title("② 逐条独立：12 条翻转，幸存 2 条是 golden 全空",fontsize=11)
ax1.legend(fontsize=8); ax1.grid(axis="y",alpha=.3)

# (3) 剂量-反应
ax2=ax[0,1]
fd=r70d["fixed_denominator"]
ks=[f["k"] for f in fd]; rr=[f["rate"] for f in fd]
ax2.plot(ks,rr,"o-",color="#C44E52",lw=2,label="固定分母(n=12)")
agg=r70d.get("aggregate",[])
ax2.plot([a["k"] for a in agg],[a["rate"] for a in agg if a["rate"] is not None],
         "s--",color="gray",alpha=.6,label="分母随 k 缩小(有偏)")
ax2.axhline(0.1667,ls=":",color="b",alpha=.5)
ax2.set_xlabel("累积替换的语义等价关键词数 k"); ax2.set_ylabel("翻转率")
ax2.set_ylim(0,1.05); ax2.set_title("③ 剂量-反应：k=6 时 12/12 全部翻转",fontsize=11)
ax2.legend(fontsize=8); ax2.grid(alpha=.3)

# (4) 翻转所需最少替换数
ax3=ax[1,1]
ns=[n["first"] if n["first"] else n["K"] for n in r70d["per_case"]]
ax3.hist(ns,bins=range(1,8),align="left",color="#55A868",edgecolor="k")
ax3.axvline(sum(ns)/len(ns),color="r",ls="--",label=f"均值 {sum(ns)/len(ns):.2f}")
ax3.set_xlabel("该条翻转所需的最少词替换数"); ax3.set_ylabel("样例数")
ax3.set_xticks(range(1,8))
ax3.set_title("④ 每条都有有限阈值：1~6 个词",fontsize=11)
ax3.legend(fontsize=8); ax3.grid(axis="y",alpha=.3)

plt.tight_layout()
plt.savefig("070_tact.png",dpi=130)
print("saved 070_tact.png")
