# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = os.path.dirname(os.path.abspath(__file__))
FP = "/usr/share/fonts/truetype/wenquanyi/wqy-micro-hei.ttc"
if os.path.exists(FP):
    font_manager.fontManager.addfont(FP)
    plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

b = json.load(open(os.path.join(OUT, "result_101b.json")))
c = json.load(open(os.path.join(OUT, "result_101c.json")))
d = json.load(open(os.path.join(OUT, "result_101d.json")))
e = json.load(open(os.path.join(OUT, "result_101e.json")))

fig, ax = plt.subplots(2, 3, figsize=(19, 10.5))
fig.suptitle("101 · 主动扫视靠什么看清：不是看得多，是跳得对", fontsize=16, y=0.985)

# --- (0,0) 101b 主结果 ---
A = ax[0, 0]
modes = ["P+ACTIVE", "N+ACTIVE", "P+FIXED", "N+FIXED"]
lbl = ["周边+主动", "盲动", "周边+不动", "不动(基线)"]
acc = [b[m]["acc"] for m in modes]
kp = [b[m]["n_kp"] for m in modes]
x = np.arange(4)
A.bar(x - 0.2, acc, 0.4, color="#2b7bba", label="识别率")
A.bar(x + 0.2, np.array(kp) / max(kp), 0.4, color="#e08214", label="累积特征(归一)")
for i, (a_, k_) in enumerate(zip(acc, kp)):
    A.text(i - 0.2, a_ + 0.02, f"{a_:.3f}", ha="center", fontsize=9)
    A.text(i + 0.2, k_ / max(kp) + 0.02, f"{k_:.0f}", ha="center", fontsize=9)
A.axhline(1 / 8, color="gray", ls="--", lw=1)
A.text(3.45, 1 / 8 + 0.02, "随机 1/8", fontsize=8, color="gray", ha="right")
A.set_xticks(x); A.set_xticklabels(lbl, fontsize=10)
A.set_ylim(0, 1.18); A.set_title("① 主结果：三者缺一不可 (T=6)", fontsize=12)
A.legend(fontsize=8, loc="upper left")

# --- (0,1) C1 假引导 ---
A = ax[0, 1]
k1 = list(c["C1_sham"].keys())
v1 = [c["C1_sham"][k]["acc"] for k in k1]
l1 = ["真引导", "假引导\n(同样跳数)", "盲动", "不动"]
cols = ["#2b7bba", "#c0392b", "#e08214", "#7f8c8d"]
bars = A.bar(l1, v1, color=cols)
for bb, v in zip(bars, v1):
    A.text(bb.get_x() + bb.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)
A.axhline(1 / 8, color="gray", ls="--", lw=1)
A.set_ylim(0, 1.18)
A.set_title("② 假引导：坏引导比没引导更糟", fontsize=12)
A.set_ylabel("识别率", fontsize=9)

# --- (0,2) C4 引导质量剂量 ---
A = ax[0, 2]
ks = sorted(c["C4_scramble"].keys())
ps = [float(k.split("=")[1]) for k in ks]
vs = [c["C4_scramble"][k]["acc"] for k in ks]
A.plot(ps, vs, "o-", color="#2b7bba", lw=2, ms=7, label="识别率")
A.axhline(1 / 8, color="gray", ls="--", lw=1, label="随机 1/8")
A.set_xlabel("显著性图被打乱的比例", fontsize=10)
A.set_ylabel("识别率", fontsize=9)
A.set_ylim(0, 1.1)
A.set_title("③ 引导质量剂量：随信息破坏单调下降", fontsize=12)
A.legend(fontsize=8)

# --- (1,0) C3 预算剂量 ---
A = ax[1, 0]
Ts = [1, 2, 3, 4, 6, 8, 12]
for mode, col, mk in [("GUIDED", "#2b7bba", "o"), ("BLIND", "#e08214", "s"),
                      ("FIXED", "#7f8c8d", "^")]:
    vs = [c["C3_budget"][f"T={t}"][mode]["acc"] for t in Ts]
    A.plot(Ts, vs, mk + "-", color=col, lw=2, ms=6, label=mode)
A.axhline(1 / 8, color="gray", ls="--", lw=1)
A.set_xlabel("采样预算 T（扫视次数）", fontsize=10)
A.set_ylabel("识别率", fontsize=9)
A.set_ylim(0, 1.1)
A.set_title("④ 预算剂量：不动者看到死也不涨", fontsize=12)
A.legend(fontsize=9)

# --- (1,1) 101e 剂量曲线 ---
A = ax[1, 1]
LV = e["_meta"]["LEVELS"]
det = [e[f"{lv:.2f}"]["det"]["mean"] for lv in LV]
sto = [e[f"{lv:.2f}"]["stoch"]["mean"] for lv in LV]
A.plot(LV, det, "o-", color="#2b7bba", lw=2, ms=6, label="确定性输入")
A.plot(LV, sto, "s--", color="#e08214", lw=2, ms=6, label="随机输入(同均值)")
A.axhline(e["_none"]["mean"], color="#c0392b", ls=":", lw=2, label="完全无感官")
A.axvspan(0.08, 0.12, color="yellow", alpha=0.25)
A.text(0.10, 1.9, "相变区\n0.08→0.12", fontsize=9, ha="center", color="#8a6d00")
A.set_xlabel("感官信号强度（均值）", fontsize=10)
A.set_ylabel("capacity 偏度", fontsize=9)
A.set_title("⑤ 感官剂量：阈值后彻底平坦", fontsize=12)
A.legend(fontsize=8)

# --- (1,2) 101e 相邻斜率 + 生态组 ---
A = ax[1, 2]
jm = e["jumps"]
sl = [abs(j["per_unit"]) for j in jm]
xs = [f"{j['frm']:.2f}\n→{j['to']:.2f}" for j in jm]
cols2 = ["#c0392b" if j["sig"] else "#95a5a6" for j in jm]
A.bar(xs, sl, color=cols2)
A.set_yscale("log")
A.set_ylabel("每单位斜率（对数）", fontsize=9)
A.set_title("⑥ 相邻跳变：阈值处斜率 −36（红色=显著）", fontsize=12)
A.tick_params(axis="x", labelsize=7)

plt.tight_layout(rect=[0, 0, 1, 0.965])
p = "/data/workspace/luoshen-o1/fig/101_saccade.png"
plt.savefig(p, dpi=135)
print("saved", p)
