import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","DejaVu Sans"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: continue
plt.rcParams["axes.unicode_minus"]=False

D="/data/workspace/luoshen-o1/experiments/exp093_human_door/"
eg=json.load(open(D+"engine093_result.json"))
al=json.load(open(D+"alias_result.json"))
ts=json.load(open(D+"timesample.json"))

fig,ax=plt.subplots(2,3,figsize=(16,9))
fig.suptitle("093 · 换门还是撞门：拦截到底发生在哪一层", fontsize=14)

# 1 门型时间稳定性
names=[u.replace("https://","").split("/")[0][:22] for u in ts]
rates=[sum(1 for x in v if x==200)/len(v) for v in ts.values()]
flips=[sum(1 for i in range(1,len(v)) if (v[i]==200)!=(v[i-1]==200)) for v in ts.values()]
ax[0,0].barh(range(len(names)),rates,color=["#2e7d32" if r>0.5 else "#c62828" for r in rates])
ax[0,0].set_yticks(range(len(names))); ax[0,0].set_yticklabels(names,fontsize=7)
ax[0,0].set_xlabel("6次采样开启率"); ax[0,0].set_title("① 门型：9扇稳定，1扇(api.github)间歇\n翻转次数="+str(max(flips)))
ax[0,0].invert_yaxis()

# 2 UA 无关
ua=json.load(open(D+"ua.json"))
ks=list(ua.keys()); labs=[k.replace("https://","")[:18] for k in ks]
for i,u in enumerate(["curl","chrome","iphone"]):
    ax[0,1].bar(np.arange(len(ks))+i*0.26,[ua[k][u] for k in ks],0.26,label=u)
ax[0,1].set_xticks(np.arange(len(ks))+0.26); ax[0,1].set_xticklabels(labs,rotation=45,fontsize=6,ha="right")
ax[0,1].set_title("② UA探针：三种身份逐位相同\n拦截不看'像不像人'"); ax[0,1].legend(fontsize=8)
ax[0,1].axhline(200,ls="--",c="gray",lw=0.7)

# 3 中断概率剂量反应（阶梯）
dose=eg["dose"]
ax[0,2].plot([d["p"] for d in dose],[d["skew"] for d in dose],"o-",lw=2)
ax[0,2].set_xlabel("门中断概率 p"); ax[0,2].set_ylabel("结构偏度")
ax[0,2].set_title("③ 阶梯不是渐变\np=0→0.9 几乎不变，p=1.0 跳变")
ax[0,2].axvline(0.9,ls=":",c="r")
ax[0,2].annotate("全关才跳",xy=(1.0,dose[-1]["skew"]),xytext=(0.72,0.70),
                 arrowprops=dict(arrowstyle="->"),fontsize=8)

# 4 混叠峰值
ps=sorted(int(k) for k in al); vs=[al[str(p)] for p in ps]
ax[1,0].plot(ps,vs,"o-",lw=2)
ax[1,0].axvline(80,ls="--",c="r",label="信号周期=80")
ax[1,0].set_xlabel("门的开关周期(拍)"); ax[1,0].set_ylabel("偏度")
ax[1,0].set_title("④ 混叠：门周期=信号周期时 z=+5.70\n(可预测性效应仅+0.018)")
ax[1,0].legend(fontsize=8)

# 5 三条件对比
cs=eg["cells"]
order=["open","rand_p50","perio_20","perio_80","closed"]
lab=["稳定开","随机断50%","周期20","周期80(共振)","稳定关"]
ax[1,1].bar(range(5),[cs[k]["skew"] for k in order],
            color=["#1565c0","#42a5f5","#66bb6a","#ffa726","#c62828"])
ax[1,1].set_xticks(range(5)); ax[1,1].set_xticklabels(lab,fontsize=8,rotation=20)
ax[1,1].set_ylabel("偏度"); ax[1,1].set_title("⑤ 门全关才有效应，随机断无所谓")

# 6 H 检验
tt=eg["tests"]
ax[1,2].barh(range(3),[tt[k]["diff"] for k in tt],
             color=["#999" if not tt[k]["sig"] else "#2e7d32" for k in tt])
ax[1,2].set_yticks(range(3)); ax[1,2].set_yticklabels(["H1 随机断vs开","H2 周期vs随机","H3 全关vs开"],fontsize=8)
ax[1,2].set_xlabel("配对差 (CI跨0=不显著)"); ax[1,2].set_title("⑥ H1推翻 / H2小 / H3强")
ax[1,2].axvline(0,c="k",lw=0.8)

plt.tight_layout()
plt.savefig("/data/workspace/luoshen-o1/fig/093_door.png",dpi=120)
print("saved")
