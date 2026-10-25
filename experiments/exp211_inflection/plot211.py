# -*- coding: utf-8 -*-
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC","DejaVu Sans"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: continue
plt.rcParams["axes.unicode_minus"]=False

rows = json.load(open("agg211.json"))
b  = [r["beta"] for r in rows]
H  = [r["Hfin"] for r in rows]
Hs = [r["Hsd"] for r in rows]
HL = [r["Hlast5"] for r in rows]
A  = [r["acc"] for r in rows]
C  = [r["collapse"] for r in rows]

fig, ax = plt.subplots(2,2, figsize=(13,9))

# A: 崩塌率阶梯
ax[0,0].step(b, C, where="post", lw=2.5, color="crimson", marker="o", ms=7)
ax[0,0].axvline(0.02, color="navy", ls="--", lw=2, alpha=.8)
ax[0,0].annotate("拐点 β*≈0.02\n崩塌 4/8 → 0/8", xy=(0.02,4), xytext=(0.35,4.3),
                 fontsize=11, color="navy",
                 arrowprops=dict(arrowstyle="->", color="navy", lw=1.8))
ax[0,0].set_xscale("symlog", linthresh=0.01)
ax[0,0].set_xlabel("独特性权重 β (symlog)"); ax[0,0].set_ylabel("末代崩塌数 / 8 seeds")
ax[0,0].set_title("A  多样性崩塌：台阶在 β=0.02", fontsize=12, fontweight="bold")
ax[0,0].set_ylim(-0.3, 5); ax[0,0].grid(alpha=.3)

# B: 末代熵
ax[0,1].errorbar(b, H, yerr=Hs, marker="o", ms=7, lw=2, capsize=4,
                 color="darkgreen", ecolor="lightgreen")
ax[0,1].plot(b, HL, marker="s", ms=5, lw=1.5, ls=":", color="gray", label="末5代平均")
ax[0,1].axvline(0.02, color="navy", ls="--", lw=2, alpha=.8)
ax[0,1].set_xscale("symlog", linthresh=0.01)
ax[0,1].set_xlabel("独特性权重 β (symlog)"); ax[0,1].set_ylabel("种群熵 (bits)")
ax[0,1].set_title("B  分层度跃变 0.73 → 1.33 (+82%)", fontsize=12, fontweight="bold")
ax[0,1].legend(fontsize=9); ax[0,1].grid(alpha=.3)

# C: 预测力代价
ax[1,0].plot(b, A, marker="o", ms=7, lw=2, color="darkorange")
ax[1,0].axvline(0.02, color="navy", ls="--", lw=2, alpha=.8)
ax[1,0].set_xscale("symlog", linthresh=0.01)
ax[1,0].set_xlabel("独特性权重 β (symlog)"); ax[1,0].set_ylabel("预测准确率")
ax[1,0].set_title("C  代价：一次性付清，之后不加价", fontsize=12, fontweight="bold")
ax[1,0].grid(alpha=.3)
ax[1,0].annotate(f"{A[0]:.4f}", xy=(b[0],A[0]), xytext=(0.15,A[0]+0.006), fontsize=9, color="darkorange")
ax[1,0].annotate(f"{A[2]:.4f}", xy=(b[2],A[2]), xytext=(0.15,A[2]-0.008), fontsize=9, color="darkorange")

# D: 权衡 — 分层度 vs 预测力
ax[1,1].plot(A, H, marker="o", ms=9, lw=0, color="purple")
for i,bb in enumerate(b):
    ax[1,1].annotate(f"β={bb}", (A[i],H[i]), fontsize=8, xytext=(4,4),
                     textcoords="offset points")
ax[1,1].scatter([A[0]],[H[0]], s=220, facecolors="none", edgecolors="red", lw=2.5, label="β=0 (半数崩塌)")
ax[1,1].scatter([A[2]],[H[2]], s=220, facecolors="none", edgecolors="navy", lw=2.5, label="β=0.02 (拐点)")
ax[1,1].set_xlabel("预测准确率 (代价)"); ax[1,1].set_ylabel("种群熵 (分层度)")
ax[1,1].set_title("D  帕累托面：拐点之后全是平台", fontsize=12, fontweight="bold")
ax[1,1].legend(fontsize=9); ax[1,1].grid(alpha=.3)

plt.suptitle("211  拐点：独特性权重 β 的临界值 —— 从原子层 k=0 起步往上厮杀",
             fontsize=14, fontweight="bold")
plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig("render211.png", dpi=130)
print("saved render211.png")
