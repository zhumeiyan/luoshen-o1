# -*- coding: utf-8 -*-
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in ["WenQuanYi Micro Hei", "Noto Sans CJK SC"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

d = json.load(open(os.path.join(ROOT, "result_081.json"), encoding="utf-8"))
try:
    c = json.load(open(os.path.join(ROOT, "result_081c.json"), encoding="utf-8"))
except Exception:
    c = None

A = d["part_a"]
names = ["align_only\n只有A=B", "uniform_only\n只有A≠B", "chase\n相互追逐", "random_walk\n瞎走"]
pos = [A[k]["pos_cos"]["mean"] for k in ["align_only", "uniform_only", "chase", "random_walk"]]
delta = [A[k]["delta"]["mean"] for k in ["align_only", "uniform_only", "chase", "random_walk"]]
intra = [A[k]["intra"]["mean"] for k in ["align_only", "uniform_only", "chase", "random_walk"]]

B = d["part_b_paired"]["rows"]
bps = [r["p_flip"] for r in B]
bsk = [r["skew"] for r in B]
bbase = d["part_b_paired"].get("base", {}).get("skew", 0.2376)

fig, ax = plt.subplots(2, 2, figsize=(11.5, 7.6))

# ① pos_cos：碰上了吗
x = np.arange(4)
b = ax[0, 0].bar(x, pos, color=["#c0392b", "#7f8c8d", "#27ae60", "#95a5a6"])
ax[0, 0].axhline(1.0, ls="--", c="r", lw=1)
ax[0, 0].text(3.35, 1.02, "碰上(=1)", color="r", fontsize=8)
ax[0, 0].set_xticks(x); ax[0, 0].set_xticklabels(names, fontsize=8)
ax[0, 0].set_ylabel("pos_cos", fontsize=9)
ax[0, 0].set_title("① 两个点碰上了吗\n只有追逐恒不到 1（0.5396）", fontsize=10)
for i, v in enumerate(pos):
    ax[0, 0].text(i, v + 0.02, f"{v:.4f}", ha="center", fontsize=8)

# ② delta 与 intra 双判据
w = 0.38
ax[0, 1].bar(x - w/2, delta, w, label="delta（可分结构）", color="#2980b9")
ax[0, 1].bar(x + w/2, intra, w, label="intra（类内重合度）", color="#e67e22")
ax[0, 1].axhline(1.0, ls=":", c="k", lw=1)
ax[0, 1].set_xticks(x); ax[0, 1].set_xticklabels(names, fontsize=8)
ax[0, 1].legend(fontsize=8)
ax[0, 1].set_title("② 单看 delta：坍缩得分最高(1.0024)\n但 intra=1.0000 → 个体归零", fontsize=10)

# ③ 引擎 p_flip 剂量
ax[1, 0].plot(bps, bsk, "o-", color="#8e44ad")
for r in B:
    flag = "*" if (r["ci_lo"] > 0 or r["ci_hi"] < 0) else ""
    ax[1, 0].text(r["p_flip"], r["skew"] + 0.012,
                  f'+{r["diff_vs_base"]:.3f}{flag}', ha="center", fontsize=8)
ax[1, 0].set_xlabel("p_flip（A≠B 强度 / 违背预测的概率）", fontsize=9)
ax[1, 0].set_ylabel("容量偏度（结构）", fontsize=9)
ax[1, 0].set_title("③ 可预测性越高，结构越弱\n0.2376 → 0.4715，剂量单调，CI 全正", fontsize=10)

# ④ Part C 阴性 + 正向对照
if c:
    rows = c["C1"]["rows"]
    nm = [r["name"] for r in rows]
    dd = [r["diff_vs_base"] for r in rows]
    lo = [r["ci_lo"] for r in rows]
    hi = [r["ci_hi"] for r in rows]
    xx = np.arange(len(nm))
    ax[1, 1].bar(xx, dd, color=["#16a085" if not (l > 0 or h < 0) else "#c0392b" for l, h in zip(lo, hi)])
    ax[1, 1].errorbar(xx, dd, yerr=[[dd[i] - lo[i] for i in range(len(dd))],
                                    [hi[i] - dd[i] for i in range(len(dd))]], fmt="none", ecolor="k", capsize=3)
    ax[1, 1].axhline(0, c="k", lw=1)
    ax[1, 1].set_xticks(xx); ax[1, 1].set_xticklabels(nm, fontsize=9)
    ax[1, 1].set_ylabel("Δ 偏度 vs 抽象硬件", fontsize=9)
    ax[1, 1].set_title("④ 换能器的化学缺陷全部无效应\n（正向对照：amp=0 时存活 4/8 → 通路是活的）", fontsize=10)

plt.tight_layout()
op = os.path.join(ROOT, "fig", "081_chase.png")
plt.savefig(op, dpi=130)
print("saved", op, os.path.getsize(op))
