# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
a=json.load(open("result221.json")); b=json.load(open("result221b.json")); c=json.load(open("result221c.json"))

fig,ax=plt.subplots(2,2,figsize=(13,9))
# 1 污染率扫描
rs=a["rho_scan"]; rho=[r["rho"] for r in rs]
ax[0,0].plot(rho,[r["err_self"] for r in rs],"k--",lw=2,label="自评基线（不开医院）")
ax[0,0].plot(rho,[r["err_hospital"] for r in rs],"o-",color="#c0392b",lw=2,label="AI医院（无溯源）")
ax[0,0].axvspan(0.5,1.0,color="#c0392b",alpha=0.08)
ax[0,0].annotate("失效区：医院=自评",xy=(0.75,0.12),fontsize=10,color="#c0392b")
ax[0,0].set_xlabel("污染率 ρ（搜来的病历中 AI 造的占比）"); ax[0,0].set_ylabel("错误率")
ax[0,0].set_title("① 医院在 ρ>0.5 后退化成自评",fontsize=12); ax[0,0].legend(); ax[0,0].grid(alpha=.3)

# 2 溯源精度门槛
qs=c["qscan"]; q=[x["q"] for x in qs]
ax[0,1].plot(q,[x["err"] for x in qs],"o-",color="#2980b9",lw=2,label="错误率")
ax[0,1].plot(q,[x["conf"] for x in qs],"s-",color="#e67e22",lw=2,label="置信度")
ax[0,1].axvline(0.7,color="#c0392b",ls=":",lw=2); ax[0,1].annotate("门槛 q≈0.7",xy=(0.71,0.85),color="#c0392b",fontsize=10)
ax[0,1].set_xlabel("溯源标记精度 q"); ax[0,1].set_ylabel("")
ax[0,1].set_title("② 溯源是硬门槛：q<0.7 白做",fontsize=12); ax[0,1].legend(); ax[0,1].grid(alpha=.3)

# 3 库规模：错不变，确信错暴涨
ns=c["nscan"]; N=[str(x["N"]) for x in ns]
ax[1,0].plot(N,[x["err"] for x in ns],"o-",color="#7f8c8d",lw=2,label="错误率（不动）")
ax[1,0].plot(N,[x["cerr"] for x in ns],"s-",color="#c0392b",lw=2,label="确信的错误（涨54%）")
ax[1,0].set_xlabel("病例库规模 N（ρ=0.7，无溯源）")
ax[1,0].set_title("③ 加大库：不降错，只让你更确信地错",fontsize=12); ax[1,0].legend(); ax[1,0].grid(alpha=.3)

# 4 多模型共识饱和
cs=a["consensus"]; K=[x["K"] for x in cs]
for rc,col in [(0.0,"#27ae60"),(0.1,"#2980b9"),(0.3,"#e67e22"),(0.5,"#c0392b")]:
    ax[1,1].plot(K,[x[f"rc{rc}"] for x in cs],"o-",color=col,lw=2,label=f"共同偏差 ρc={rc}")
    ax[1,1].axhline(rc,color=col,ls=":",alpha=.6)
ax[1,1].set_xscale("log",base=2); ax[1,1].set_xlabel("参与共识的模型数 K（对数）"); ax[1,1].set_ylabel("多数投票错误率")
ax[1,1].set_title("④ 加模型撞天花板：饱和在 ρc（TACT κ=0.945 的解释）",fontsize=12)
ax[1,1].legend(fontsize=9); ax[1,1].grid(alpha=.3)

plt.tight_layout(); plt.savefig("render221.png",dpi=110); print("[ok] render221.png")
