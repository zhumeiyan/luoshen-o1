#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, matplotlib
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

BASE = "/data/workspace/luoshen-o1/experiments/exp206_compete"
d = json.load(open(f"{BASE}/result206.json", encoding="utf-8"))
b = json.load(open(f"{BASE}/result206b.json", encoding="utf-8"))
c = json.load(open(f"{BASE}/result206c.json", encoding="utf-8"))

fig, ax = plt.subplots(2, 3, figsize=(16, 9.5))

# 1: 复制子动力学崩溃
a = d["A_replicator"]
ax[0, 0].plot(a["entropy_history"], "o-", color="#c0392b", lw=2)
ax[0, 0].axhline(0, ls="--", c="gray", lw=1)
ax[0, 0].set_title("A 竞争排斥：多样性必然崩溃\n(你的话, ks=1..8)", fontsize=11)
ax[0, 0].set_xlabel("轮次"); ax[0, 0].set_ylabel("种群熵")
ax[0, 0].text(0.5, 0.5, f"1.79 → {a['entropy_end']}", transform=ax[0, 0].transAxes, fontsize=10, color="#c0392b")

# 2: 规模梯度
names = ["small", "mid", "large"]
nv = [b["scale_scan"][n]["N_over_V"] for n in names]
ee = [b["scale_scan"][n]["entropy_end"] for n in names]
wk = [b["scale_scan"][n]["winner_k"] for n in names]
x = range(3)
ax[0, 1].bar([i - 0.2 for i in x], ee, width=0.4, color="#c0392b", label="最终种群熵")
ax[0, 1].bar([i + 0.2 for i in x], [1.386] * 3, width=0.4, color="#95a5a6", label="初始熵")
for i, (n, k) in enumerate(zip(names, wk)):
    ax[0, 1].text(i, 1.45, f"N/V={nv[i]}\n赢家k={k}", ha="center", fontsize=9)
ax[0, 1].set_xticks(list(x)); ax[0, 1].set_xticklabels(names)
ax[0, 1].set_title("B 三档资源规模：全都崩到 0", fontsize=11)
ax[0, 1].legend(fontsize=8); ax[0, 1].set_ylabel("熵")

# 3: 保险假说
bi = d["B_insurance"]
lbl = ["单一最优\n(k=2)", "真多样性\n(不同阶)", "伪多样性\n(同阶×3)"]
val = [bi["mono_bits_under_shift"], bi["portfolio_bits_under_shift"], bi["pseudo_diversity_bits_under_shift"]]
col = ["#7f8c8d", "#27ae60", "#e67e22"]
bars = ax[0, 2].bar(lbl, val, color=col)
for bb, v in zip(bars, val):
    ax[0, 2].text(bb.get_x() + bb.get_width() / 2, v + 0.08, f"{v:.2f}", ha="center", fontsize=10)
ax[0, 2].set_title(f"C 环境漂移下：多样性是保险\n真多样性比最优单体省 {bi['diversity_gain']:.3f} bits", fontsize=11)
ax[0, 2].set_ylabel("bits/字符 (越低越好)")

# 4: 策略竞争
ds = d["D_strategy"]
for s, sty in zip(ds["strategies"], ["-", "-", "-", "-"]):
    ax[1, 0].plot([h[s] for h in ds["shares_history"]], sty, lw=2, label=s, marker="o", ms=3)
ax[1, 0].set_title("D 策略厮杀：我的'追最意外'第5轮归零\nprogress 垄断", fontsize=11)
ax[1, 0].set_xlabel("轮次"); ax[1, 0].set_ylabel("资源份额")
ax[1, 0].legend(fontsize=8)

# 5: 生态位分化
dss = [0.0, 0.25, 0.5, 0.75, 1.0]
ent = [c["scan"][f"d={x}"]["entropy_end_mean"] for x in dss]
sb = [c["scan"][f"d={x}"]["system_bits_mean"] for x in dss]
ax[1, 1].plot(dss, ent, "o-", color="#c0392b", lw=2, label="最终种群熵")
ax[1, 1].set_ylim(-0.05, 1.5)
ax[1, 1].set_xlabel("生态位分化度 d"); ax[1, 1].set_ylabel("熵", color="#c0392b")
ax2 = ax[1, 1].twinx()
ax2.plot(dss, sb, "s--", color="#2980b9", lw=1.5, label="系统 bits")
ax2.set_ylabel("bits/字符", color="#2980b9")
ax[1, 1].set_title("E 生态位分化也救不了\n(单一评价标准 → 必然排斥)", fontsize=11)

# 6: 分配规则
for r, colr in zip(["absolute", "marginal"], ["#8e44ad", "#16a085"]):
    ax[1, 2].plot(b["large_allocation"][r]["entropy_history"], "o-", color=colr, lw=2, label=r)
ax[1, 2].set_title("F 换分配规则也救不了\n(绝对表现 vs 边际贡献，结果相同)", fontsize=11)
ax[1, 2].set_xlabel("轮次"); ax[1, 2].set_ylabel("熵"); ax[1, 2].legend(fontsize=8)

plt.suptitle("206 竞争、物种多样性与厮杀 —— 竞争杀死多样性，而多样性是系统的保险", fontsize=13)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(f"{BASE}/render206.png", dpi=130)
print("[saved]", f"{BASE}/render206.png")
