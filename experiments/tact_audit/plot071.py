#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","DejaVu Sans"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

r=json.load(open("/data/workspace/luoshen-o1/result_071.json",encoding="utf-8"))
rb=json.load(open("/data/workspace/luoshen-o1/result_071b.json",encoding="utf-8"))
rc=json.load(open("/data/workspace/luoshen-o1/result_071c.json",encoding="utf-8"))
fig,ax=plt.subplots(2,3,figsize=(16,9))
o=r["out_of_sample"]; i=r["in_sample"]

# 1 样本内 vs 样本外
p=ax[0,0]
labels=["L","M","P"]; inn=[i["recall"][a]*100 for a in labels]
out=[o["by_axis"][a]["recall"]*100 if o["by_axis"][a]["recall"] is not None else 0 for a in labels]
x=np.arange(3); w=0.38
p.bar(x-w/2,inn,w,label="样本内 · 29 例校准集（用来造关键词的那批）",color="#c0392b")
p.bar(x+w/2,out,w,label="样本外 · 坐标库自带 580 条示例",color="#2c7fb8")
for k,(a,b) in enumerate(zip(inn,out)):
    p.text(k-w/2,a+1.5,f"{a:.1f}",ha="center",fontsize=9)
    p.text(k+w/2,b+1.5,f"{b:.1f}",ha="center",fontsize=9)
p.set_xticks(x); p.set_xticklabels(labels); p.set_ylabel("召回率 %"); p.set_ylim(0,110)
p.set_title("① 95.7% 是设计拟合，不是泛化",fontsize=12,fontweight="bold")
p.legend(fontsize=8,loc="upper right"); p.grid(axis="y",alpha=.3)

# 2 可达性
p=ax[0,1]
n_sub=117; n_reach=35
p.bar(["有关键词规则\n(可达)"], [n_reach], color="#27ae60")
p.bar(["无规则\n(结构上到不了)"], [n_sub-n_reach], color="#95a5a6")
p.text(0,n_reach+2,f"{n_reach}\n{ n_reach/n_sub*100:.1f}%",ha="center",fontsize=11,fontweight="bold")
p.text(1,n_sub-n_reach+2,f"{n_sub-n_reach}\n{(n_sub-n_reach)/n_sub*100:.1f}%",ha="center",fontsize=11,fontweight="bold")
p.set_ylabel("子坐标数"); p.set_ylim(0,132)
p.set_title("② 117 个子坐标里，70% 没有规则",fontsize=12,fontweight="bold")
p.grid(axis="y",alpha=.3)

# 3 可达坐标召回分布
p=ax[0,2]
per=r["per_code"]
import importlib.util
spec=importlib.util.spec_from_file_location("t","/data/workspace/tact_real/tact_run.py")
tr=importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)
reach={c for c,_ in tr.M_RULES}|{c for c,_ in tr.P_RULES}
vals=[per[c]["exact"]/per[c]["n"]*100 for c in reach if c in per]
p.hist(vals,bins=np.arange(0,101,10),color="#8e44ad",edgecolor="white")
p.axvline(np.median(vals),color="#c0392b",ls="--",label=f"中位 {np.median(vals):.0f}%")
p.set_xlabel("该坐标自身 5 条示例的召回 %"); p.set_ylabel("坐标数")
p.set_title(f"③ 连“有规则”的 35 个也不稳：{sum(1 for v in vals if v==0)} 个全 0",fontsize=12,fontweight="bold")
p.legend(fontsize=9); p.grid(axis="y",alpha=.3)

# 4 oracle 对照
p=ax[1,0]
names=["引擎\n(原样)","LOO\n最近邻","LOO\n词表","随机\n基线","重排\n关键词"]
vals=[o["recall_all"]*100, rb["oracle_nn"]["exact"]*100, rb["oracle_vocab"]["exact"]*100,
      rb["oracle_nn"]["random_exact"]*100, r["negative_control_shuffle"]["recall"]*100]
cols=["#c0392b","#e67e22","#f1c40f","#95a5a6","#34495e"]
b=p.bar(names,vals,color=cols)
for k,v in enumerate(vals):
    p.text(k,v+0.3,f"{v:.2f}",ha="center",fontsize=10,fontweight="bold")
p.set_ylabel("精确码召回 %"); p.set_ylim(0,12)
p.set_title("④ 公平性：oracle 也很低 → 不能只怪引擎",fontsize=12,fontweight="bold")
p.grid(axis="y",alpha=.3)

# 5 阈值扫描
p=ax[1,1]
sw=r["definition_neardup_sweep"]
p.plot([s["thr"] for s in sw],[s["frac"]*100 for s in sw],"o-",color="#16a085",lw=2)
p.set_xlabel("定义近重复判定阈值 (char-3gram Jaccard)"); p.set_ylabel("近重复坐标对占比 %")
p.set_title("⑤ 坐标之间并不冗余（≈0.4%，且不随阈值塌陷）",fontsize=12,fontweight="bold")
p.grid(alpha=.3)

# 6 自审
p=ax[1,2]
lab=[f"有实测锚\n{rc['falsifiable']} 条",f"纯规范性陈述\n{rc['n_unique']-rc['falsifiable']} 条"]
p.bar(lab,[rc["falsifiable"],rc["n_unique"]-rc["falsifiable"]],color=["#27ae60","#c0392b"])
p.text(0,rc["falsifiable"]+3,f"{rc['frac']*100:.1f}%",ha="center",fontsize=12,fontweight="bold")
p.text(1,rc["n_unique"]-rc["falsifiable"]+3,f"{(1-rc['frac'])*100:.1f}%",ha="center",fontsize=12,fontweight="bold")
p.set_ylabel("判据条数"); p.set_ylim(0,240)
p.set_title(f"⑥ 同一把尺子量自己：{rc['n_unique']} 条里 1/3 无实测锚",fontsize=12,fontweight="bold")
p.grid(axis="y",alpha=.3)

plt.suptitle("071 · 分类法的可证伪性：样本内 95.7% 与样本外 4.83%",fontsize=15,fontweight="bold")
plt.tight_layout(rect=[0,0,1,0.96])
out="/data/workspace/luoshen-o1/fig/071_falsifiable.png"
plt.savefig(out,dpi=130); print("saved",out)
