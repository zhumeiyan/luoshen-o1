#!/usr/bin/env python3
import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = "/data/workspace/luoshen-o1/experiments/exp196_eye_memory"
R = json.load(open(OUT + "/result196.json"))
C = json.load(open(OUT + "/collapse196.json"))

fig, ax = plt.subplots(2, 2, figsize=(13, 9))

# (0,0) A: 动力学阶数 -> k*
names = list(R["A_order"].keys())
ks = [R["A_order"][n]["kstar"] for n in names]
gains = [max(d["gain"] for d in R["A_order"][n]["curve"]) for n in names]
b = ax[0, 0].bar(range(len(names)), ks, color=["#4C72B0", "#DD8452", "#8C8C8C", "#8C8C8C"])
for i, (v, g) in enumerate(zip(ks, gains)):
    ax[0, 0].text(i, v + 0.06, f"k*={v}\ngain={g:.3f}", ha="center", fontsize=9)
ax[0, 0].set_xticks(range(len(names)))
ax[0, 0].set_xticklabels(["AR1\n(纯梯度)", "AR2\n(带惯性)", "AR3", "AR4"], fontsize=9)
ax[0, 0].set_ylabel("最优记忆深度 k*")
ax[0, 0].set_title("A. 动力学阶数 → 记忆深度\n梯度世界 k*=1，有惯性 k*=2", fontsize=11)
ax[0, 0].set_ylim(0, 3.2)
ax[0, 0].grid(axis="y", alpha=0.3)

# (0,1) B: 坍缩 —— gain vs r/tau
for tau in ["5", "10", "20", "40", "80"]:
    xs_, ys_ = [], []
    for x in ["0.05", "0.1", "0.2", "0.4", "0.8", "1.6"]:
        d = C["collapse_grid"][x][tau]
        xs_.append(d["r_over_tau"])
        ys_.append(d["gain_mean"])
    ax[0, 1].plot(xs_, ys_, "o-", label=f"τ={tau}", alpha=0.8)
ax[0, 1].axhline(0, color="k", lw=0.8, ls="--")
ax[0, 1].set_xscale("log")
ax[0, 1].set_xlabel("采样间隔 / 世界相关时间  r/τ")
ax[0, 1].set_ylabel("记忆增益（准确率 − 频率基线）")
ax[0, 1].set_title(f"B. 坍缩：增益只由 r/τ 决定\n组内/组间 = {C['collapse_ratio']:.3f}（越小越坍缩）", fontsize=11)
ax[0, 1].legend(fontsize=8)
ax[0, 1].grid(alpha=0.3)

# (1,0) C: 门坎 —— r/τ 超过 1 记忆归零
xs_sorted = ["0.05", "0.1", "0.2", "0.4", "0.8", "1.6"]
gm = [C["group_mean_by_x"][x] for x in xs_sorted]
sp = [C["spread_within_x"][x] for x in xs_sorted]
xv = [float(x) for x in xs_sorted]
ax[1, 0].errorbar(xv, gm, yerr=sp, fmt="o-", capsize=4, color="#C44E52", lw=2)
ax[1, 0].axvline(1.0, color="#DD8452", ls="--", lw=2)
ax[1, 0].text(1.05, max(gm) * 0.75, "r/τ = 1\n采样慢过世界变化\n记忆归零", fontsize=9, color="#DD8452")
ax[1, 0].axhline(0, color="k", lw=0.8, ls="--")
ax[1, 0].set_xscale("log")
ax[1, 0].set_xlabel("r/τ")
ax[1, 0].set_ylabel("记忆增益")
ax[1, 0].set_title("C. 记忆的门坎：采样慢过世界 → 记忆一文不值", fontsize=11)
ax[1, 0].grid(alpha=0.3)

# (1,1) D: k* 分布 —— 深度几乎恒定
allk = []
for tau, row in R["B_sampling"].items():
    for r, d in row.items():
        allk.append(d["kstar"])
for kk, v in R["C_agent"].items():
    allk.append(v["kstar"])
vals, cnts = np.unique(allk, return_counts=True)
ax[1, 1].bar(vals, cnts, color="#55A868")
for v, c in zip(vals, cnts):
    ax[1, 1].text(v, c + 0.2, str(c), ha="center", fontsize=10)
ax[1, 1].set_xlabel("最优记忆深度 k*")
ax[1, 1].set_ylabel("出现次数")
ax[1, 1].set_title("D. 记忆深度几乎恒定在 1–2 拍\n变的不是「记多久」，是「记了值不值」", fontsize=11)
ax[1, 1].set_xticks(vals)
ax[1, 1].grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig(OUT + "/render196.png", dpi=130)
print("saved", OUT + "/render196.png")
print("k* 分布:", dict(zip(vals.tolist(), cnts.tolist())))
