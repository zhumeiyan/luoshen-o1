#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
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

here = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(here, "result218.json"), encoding="utf-8"))
b = json.load(open(os.path.join(here, "result218b.json"), encoding="utf-8"))
S, series = d["summary"], d["series"]
WAVES, CUT, LW = d["waves"], d["cut"], d["last_wave"]

COLORS = {"none": "#8a8a8a", "marker": "#c0392b", "cure": "#e08e0b",
          "witness": "#2e86c1", "wild_leaky": "#48c9b0", "wild": "#1e8449"}
LABEL = {"none": "无防御", "marker": "特征识别", "cure": "治疗(自校准)",
         "witness": "见证人+自校准旋钮", "wild_leaky": "野败(残留25%)",
         "wild": "完全野败(结构性不育)"}

fig, ax = plt.subplots(2, 2, figsize=(14, 9))
fig.patch.set_facecolor("#12141a")
for a in ax.flat:
    a.set_facecolor("#1a1d26"); a.grid(alpha=.18, color="#888")
    a.tick_params(colors="#ccc"); a.title.set_color("#fff")
    for sp in a.spines.values(): sp.set_color("#444")

# (1) 时间序列
a = ax[0, 0]
for k in ["none", "marker", "cure", "witness", "wild_leaky", "wild"]:
    y = series[k]
    a.plot(y, color=COLORS[k], lw=2.0 if k in ("wild", "witness") else 1.2,
           alpha=.95 if k in ("wild", "witness", "wild_leaky") else .5,
           label=LABEL[k])
for w in WAVES: a.axvline(w, color="#666", ls=":", lw=.8)
a.axvline(CUT, color="#e74c3c", ls="--", lw=1.4)
a.axvline(LW, color="#e74c3c", ls="-", lw=1.0, alpha=.6)
a.text(CUT + 3, .93, "断供(无外部花粉)", color="#e74c3c", fontsize=9)
a.set_title("威胁占比随时间（四波脉冲 + 断供波）", fontsize=11)
a.set_xlabel("代"); a.set_ylabel("威胁占比")
a.legend(fontsize=8, facecolor="#1a1d26", labelcolor="#ddd", loc="lower right")

# (2) a_min —— 是否解除警戒
a = ax[0, 1]
ks = ["cure", "witness", "wild_leaky", "wild"]
vals = [S[k]["a_min"] for k in ks]
bars = a.bar([LABEL[k] for k in ks], vals, color=[COLORS[k] for k in ks])
a.axhline(1.0, color="#1e8449", ls="--", lw=1)
a.text(3.35, 1.01, "警戒上限(从不解除)", color="#1e8449", fontsize=8, ha="right")
for bb, v in zip(bars, vals):
    a.text(bb.get_x() + bb.get_width()/2, v + .03, f"{v:.3f}",
           ha="center", color="#fff", fontsize=9)
a.set_ylim(0, 1.25); a.set_title("警戒强度最低值（越低=越麻痹）", fontsize=11)
a.set_ylabel("a_min")

# (3) 波峰随波次
a = ax[1, 0]
for k in ["cure", "witness", "wild_leaky", "wild"]:
    a.plot(range(1, 5), S[k]["peaks"], "o-", color=COLORS[k], lw=1.8, label=LABEL[k])
a.set_xticks(range(1, 5)); a.set_xlabel("第几波威胁")
a.set_ylabel("波峰威胁占比")
a.set_title("波峰是否随波次上升（麻痹累积）", fontsize=11)
a.legend(fontsize=8, facecolor="#1a1d26", labelcolor="#ddd")

# (4) 不育度扫描
a = ax[1, 1]
lk = [r["leak"] for r in b]
pk = [r["peak"] for r in b]
am = [r["a_min"] for r in b]
a.plot(lk, pk, "o-", color="#1e8449", lw=2, label="首波峰(左轴)")
a2 = a.twinx(); a2.plot(lk, am, "s--", color="#2e86c1", lw=1.6, label="a_min(右轴)")
a2.tick_params(colors="#2e86c1"); a2.set_ylabel("a_min", color="#2e86c1")
a.axvspan(0.75, 1.0, color="#c0392b", alpha=.15)
a.text(.76, .5, "崩塌区", color="#e88", fontsize=9, rotation=90, va="center")
a.set_xlabel("自校准残留 leak（0=完全野败，1=完全自校准）")
a.set_ylabel("首波峰威胁占比", color="#1e8449")
a.set_title("不育度阈值：不必 100% 不育，但不能 100% 自校准", fontsize=11)

plt.tight_layout()
out = os.path.join(here, "render218.png")
plt.savefig(out, dpi=140, facecolor="#12141a")
print("written", out, os.path.getsize(out))
