import json,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="WenQuanYi Micro Hei"
d=json.load(open("result177b.json"))
c=d["curve"]; r=d["random_control"]
xs=[p["N"] for p in c]; ys=[p["bits"] for p in c]
fig,ax=plt.subplots(1,2,figsize=(11,4.2))
ax[0].axhline(d["summary_bits"],ls="--",c="gray",label="总结 %.4f"%d["summary_bits"])
ax[0].axhline(d["selective_full_bits"],ls=":",c="green",label="全否定(有方向) %.4f"%d["selective_full_bits"])
ax[0].axhline(d["full_all_bits"],ls="-.",c="red",label="全盘否定(无方向) %.4f"%d["full_all_bits"])
ax[0].plot(xs,ys,"o-",c="C0",label="有方向否定")
rk=sorted(r.items()); ax[0].plot([k for k,_ in rk],[v for _,v in rk],"s--",c="orange",label="随机否定(对照)")
ax[0].set_xscale("symlog"); ax[0].set_xlabel("否定条数 N"); ax[0].set_ylabel("交叉熵 bits/字符")
ax[0].set_title("总结 vs 否定：交叉熵越低=越能预测下一拍"); ax[0].legend(fontsize=7)
mass=[p["mass"] for p in c]; gain=[(d["summary_bits"]-y)/(d["summary_bits"]-d["selective_full_bits"]) for y in ys]
ax[1].plot([m*100 for m in mass],[g*100 for g in gain],"o-",c="C0")
ax[1].plot([0,100],[0,100],"--",c="gray",label="线性基准")
ax[1].set_xlabel("被否定的意外质量占比 %"); ax[1].set_ylabel("找回的预测收益 %")
ax[1].set_title("否定的效率：少量意外拿回大部分"); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.savefig("render177.png",dpi=110)
print("ok")
