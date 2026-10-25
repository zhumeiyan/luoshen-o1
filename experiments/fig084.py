#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

ROOT = os.path.join(os.path.dirname(__file__), "..")
d = json.load(open(os.path.join(ROOT, "result_084.json")))

fig, ax = plt.subplots(2, 3, figsize=(16, 9.5))

# ---- (0,0) Part A: F vs SNR，各 K ----
A = d["partA"]
keys = ["K2", "K4", "K8", "K16", "K64", "radio"]
colors = plt.cm.viridis(np.linspace(0.05, 0.85, len(keys)))
ax0 = ax[0, 0]
for k, c in zip(keys, colors):
    s = [r["snr_db"] for r in A[k]]
    F = [r["F"] for r in A[k]]
    ax0.plot(s, F, "-o", ms=3, lw=1.8 if k == "radio" else 1.2,
             color=c, label=("收音机(连续)" if k == "radio" else f"电报 K={k[1:]}"))
ax0.axhline(0, color="grey", lw=0.8, ls=":")
ax0.set_xlabel("信噪比 SNR (dB)"); ax0.set_ylabel("保真度 F = 1 − MSE/var")
ax0.set_title("① 分辨率 vs 抗噪：K 越大地板越高越脆", fontsize=11)
ax0.legend(fontsize=7.5, loc="lower right"); ax0.grid(alpha=0.3)

# ---- (0,1) Part A': 最优 K 阶梯 ----
ax1 = ax[0, 1]
bA = d["bestA"]
s = [r["snr_db"] for r in bA]
kv = []
for r in bA:
    b = r["best"]
    kv.append(1024 if b == "radio" else int(b[1:]))
ax1.step(s, kv, where="mid", lw=2.2, color="#c0392b")
ax1.set_yscale("log", base=2)
ax1.set_yticks([2, 4, 8, 16, 64, 1024])
ax1.set_yticklabels(["2", "4", "8", "16", "64", "连续"])
ax1.invert_xaxis()
ax1.set_xlabel("信噪比 SNR (dB)"); ax1.set_ylabel("该信噪比下的最优量化阶数 K*")
ax1.set_title("② 最优 K* 随噪声单调下降（阶梯，无例外）", fontsize=11)
ax1.grid(alpha=0.3)

# ---- (0,2) Part B: 电报 vs 收音机，交叉与发散 ----
B = d["partB"]["r1"]
ax2 = ax[0, 2]
s = [r["snr_db"] for r in B["telegraph"]]
Ft = [r["F"] for r in B["telegraph"]]
Fr = [r["F"] for r in B["radio"]]
ax2.plot(s, Ft, "-o", ms=3.5, lw=2, color="#2980b9", label="电报（离散 K=8）")
ax2.plot(s, Fr, "-s", ms=3.5, lw=2, color="#e67e22", label="收音机（连续）")
ax2.axhline(0, color="grey", lw=0.8, ls=":")
i6 = s.index(6.0)
ax2.annotate(f"交叉点 ≈ 6dB\n({Ft[i6]:.4f} vs {Fr[i6]:.4f})",
             xy=(6.0, Ft[i6]), xytext=(10, 0.35), fontsize=8.5,
             arrowprops=dict(arrowstyle="->", lw=1.2))
ax2.annotate("收音机误差无界 → 发散", xy=(-10, Fr[-1]), xytext=(-9, -4.5),
             fontsize=8.5, color="#e67e22",
             arrowprops=dict(arrowstyle="->", lw=1.2, color="#e67e22"))
ax2.annotate("电报误差被码本约束 → 有下界", xy=(-10, Ft[-1]), xytext=(-9.5, 0.55),
             fontsize=8.5, color="#2980b9",
             arrowprops=dict(arrowstyle="->", lw=1.2, color="#2980b9"))
ax2.set_xlabel("信噪比 SNR (dB)"); ax2.set_ylabel("保真度 F")
ax2.set_title("③ 电报的优势区在极低信噪比", fontsize=11)
ax2.legend(fontsize=8.5); ax2.grid(alpha=0.3)

# ---- (1,0) Part D: 冗余收益分离 ----
D = d["partD"]
ax3 = ax[1, 0]
for tag, col, mk in [("tele_hard", "#c0392b", "o"), ("tele_soft", "#8e44ad", "^"),
                     ("radio", "#16a085", "s")]:
    s = [r["snr_db"] for r in D["r1"][tag]["rows"]]
    f1 = [r["F"] for r in D["r1"][tag]["rows"]]
    f15 = [r["F"] for r in D["r15"][tag]["rows"]]
    ax3.plot(s, f1, mk, ms=3, color=col, alpha=0.35, label=f"{tag} r=1")
    ax3.plot(s, f15, "-" + mk, ms=4, lw=1.8, color=col, label=f"{tag} r=15")
ax3.axhline(0, color="grey", lw=0.8, ls=":")
ax3.set_xlabel("信噪比 SNR (dB)"); ax3.set_ylabel("保真度 F")
ax3.set_title("④ 冗余对谁有用：硬判决 < 软判决 < 无判决", fontsize=11)
ax3.legend(fontsize=7.5); ax3.grid(alpha=0.3)

# ---- (1,1) Part D 冗余增益条形 ----
ax4 = ax[1, 1]
i0 = [r["snr_db"] for r in D["r1"]["radio"]["rows"]].index(0.0)
tags = ["硬判决\n(多数投票)", "软判决\n(平均后判决)", "收音机\n(无判决)"]
gain = []
for t in ["tele_hard", "tele_soft", "radio"]:
    g = D["r15"][t]["rows"][i0]["F"] - D["r1"][t]["rows"][i0]["F"]
    gain.append(g)
bars = ax4.bar(tags, gain, color=["#c0392b", "#8e44ad", "#16a085"], alpha=0.85)
for b, g in zip(bars, gain):
    ax4.text(b.get_x() + b.get_width() / 2, g + 0.02, f"+{g:.3f}",
             ha="center", fontsize=10, fontweight="bold")
ax4.set_ylabel("SNR=0dB 时 r:1→15 的保真度增益")
ax4.set_title("⑤ 同样冗余，收益差 3 倍（丢在判决那一步）", fontsize=11)
ax4.grid(alpha=0.3, axis="y")

# ---- (1,2) Part E: 引擎内在结构 ----
E = d["partE"]
ax5 = ax[1, 2]
order = ["none", "telegraph", "radio", "permuted"]
lbl = ["无感官", "电报", "收音机", "收音机\n时序打乱"]
vals = [E[k]["common_skew"] for k in order]
errs = [E[k]["common_sd"] for k in order]
cols = ["#95a5a6", "#2980b9", "#e67e22", "#7f8c8d"]
bars = ax5.bar(lbl, vals, yerr=errs, capsize=4, color=cols, alpha=0.9)
ax5.axhline(E["none"]["common_skew"], color="#95a5a6", ls="--", lw=1.2)
ax5.text(3.35, E["none"]["common_skew"] + 0.004, "无感官基线", fontsize=8, color="#666")
ax5.set_ylabel("内在结构偏度（共同存活子集 n=15）")
ax5.set_title("⑥ 两种通道都刻入结构，但系统不认时序", fontsize=11)
ax5.grid(alpha=0.3, axis="y")

plt.suptitle("实验 084　电报 vs 收音机：离散冗余与连续保真"
             "　（发射功率、噪声功率、总信道次数三者相同）",
             fontsize=13, fontweight="bold", y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.965])
out = os.path.join(ROOT, "fig", "084_telegraph_radio.png")
plt.savefig(out, dpi=150)
print("saved", out, os.path.getsize(out))
