import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","SimHei"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False
r=json.load(open("result207.json"))
Ns=[x["N"] for x in r["perN"]]
kill=[x["kill_bits"] for x in r["perN"]]
ens=[x["ens_bits"] for x in r["perN"]]
avg=[x["avg_bits"] for x in r["perN"]]
ag=[x["top1_agree"] for x in r["perN"]]
js=[x["mean_js"] for x in r["perN"]]
fig,ax=plt.subplots(1,2,figsize=(12,4.4))
ax[0].plot(Ns,kill,"o-",color="#c0392b",label="厮杀（验证集挑最优，其余杀掉）")
ax[0].plot(Ns,ens,"s-",color="#27ae60",label="协作（全体集成）")
ax[0].plot(Ns,avg,"^--",color="#95a5a6",label="平均单种子")
ax[0].axhline(r["full_pool_bits"],color="#2c3e50",ls=":",lw=2,label=f"不撒种子：全量单模型 {r['full_pool_bits']:.3f}")
ax[0].axhline(r["uniform_bits"],color="#bdc3c7",ls="--",label=f"均匀瞎猜 {r['uniform_bits']:.3f}")
ax[0].set_xscale("log",base=2); ax[0].set_xticks(Ns); ax[0].set_xticklabels(Ns)
ax[0].set_xlabel("种子数 N"); ax[0].set_ylabel("bits/字符（越低越好）")
ax[0].set_title("撒 N 个种子：厮杀 vs 协作 vs 不撒种子"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
ax[1].plot(Ns,ag,"o-",color="#2980b9",label="top-1 一致率")
ax[1].axhline(r["random_top1_agree"],color="#bdc3c7",ls="--",label=f"随机基线 {r['random_top1_agree']:.4f}")
ax[1].set_xlabel("种子数 N"); ax[1].set_ylabel("一致率"); ax[1].set_ylim(0,1.05)
ax[1].set_title("种子是趋同，不是厮杀"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
ax1b=ax[1].twinx(); ax1b.plot(Ns,js,"x--",color="#8e44ad",label="分布 JS"); ax1b.set_ylabel("平均 JS")
ax1b.legend(loc="lower right",fontsize=8)
plt.tight_layout(); plt.savefig("render207.png",dpi=130)
print("ok")
