import json,os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"]=["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"]=False
R=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
d=json.load(open(os.path.join(R,"result_074.json"),encoding="utf-8"))
fig,ax=plt.subplots(1,3,figsize=(16,4.6))
# 1 耳 2x2 存活
ge=d["grid_ear"]; labels=["(0,0)\n全断","(0,g)\n内开外断","(1,0)\n外接内断","(1,g)\n全通"]
keys=["0_0.0","0_2.0","1_0.0","1_2.0"]
alive=[1 if ge[k]["alive"] else 0 for k in keys]
cols=["#888","#d62728","#1f77b4","#2ca02c"]
ax[0].bar(labels,alive,color=cols)
ax[0].set_ylim(0,1.25); ax[0].set_ylabel("存活(1/0)"); ax[0].set_title("耳通路：四格存活\n(0,g)渴求空信号致死；(1,0)≡(0,0)")
for i,v in enumerate(alive):
    ax[0].text(i,v+0.05,("存活" if v else f"t={ge[keys[i]]['death_t']}死"),ha="center",fontsize=9)
# 2 剂量：死亡时间 vs gain
dose=d["dose"]; g=[x["gain"] for x in dose]
dt0=[(x["wire0"]["death_t"] if x["wire0"]["death_t"] else 400) for x in dose]
dt1=[(x["wire1"]["death_t"] if x["wire1"]["death_t"] else 400) for x in dose]
ax[1].plot(g,dt0,"o-",color="#d62728",label="wire=0 不接")
ax[1].plot(g,dt1,"s-",color="#2ca02c",label="wire=1 接通")
ax[1].axhline(400,ls="--",c="gray",lw=1)
ax[1].set_xlabel("内部增益 gain"); ax[1].set_ylabel("死亡时间(拍,400=存活)")
ax[1].set_title("wire 效应依赖 gain：\ngain=0 完全无效应，gain≥0.25 即生死之差")
ax[1].legend(fontsize=8)
# 3 信号动态性 CV
cv=d["H4_transducer"]
ax[2].bar(["耳(话筒)","眼(摄像头)"],[cv["ear_cv"],cv["eye_cv"]],color=["#1f77b4","#ff7f0e"])
ax[2].set_ylabel("变异系数 CV"); ax[2].set_title("换能器信号动态性\n耳近恒定 CV=0.06，眼强波动 CV=1.59")
for i,v in enumerate([cv["ear_cv"],cv["eye_cv"]]):
    ax[2].text(i,v+0.04,f"{v:.3f}",ha="center")
plt.tight_layout()
op=os.path.join(R,"fig","074_transducer.png"); os.makedirs(os.path.dirname(op),exist_ok=True)
plt.savefig(op,dpi=130); print("saved",op,os.path.getsize(op))
