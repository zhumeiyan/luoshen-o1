# -*- coding: utf-8 -*-
"""078 出图：表征必要性 + 效应特异性 + 时间线"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FIG = os.path.join(ROOT, 'fig'); os.makedirs(FIG, exist_ok=True)
for f in ["WenQuanYi Micro Hei", "SimHei", "Noto Sans CJK SC"]:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams["font.sans-serif"] = [f]; break
    except Exception: continue
plt.rcParams["axes.unicode_minus"] = False

d78  = json.load(open(os.path.join(ROOT, 'evidence/raw_data/representation_078.json')))
d78b = json.load(open(os.path.join(ROOT, 'evidence/raw_data/representation_078b.json')))

fig, ax = plt.subplots(2, 2, figsize=(13, 9.5))

# --- (1) 表征粒度剂量反应 ---
a = ax[0, 0]
rows = d78["rows"]
xs = [r["L"] for r in rows]; ys = [r["mean"] for r in rows]
base = d78["control_no_sense_mean"]
a.axhline(base, color="gray", ls="--", lw=1.5, label=f"无感官基线 {base:.4f}")
a.plot([0 if x == 0 else x for x in xs], ys, "o-", color="#c0392b", lw=2, ms=9,
       label="有感知（真实气象读数）")
a.set_xscale("symlog", linthresh=1)
a.set_xticks([0, 2, 5, 20, 100])
a.set_xticklabels(["0\n无表征", "2\n1bit", "5\n人类带宽", "20", "100"])
a.set_xlabel("表征粒度 L（离散层级数）")
a.set_ylabel("容量偏度（取舍结构）")
a.set_title("① 表征粒度不敏感：无表征下结构已在\nH1 Δ=+0.0596 [+0.034,+0.086]；各 L 与 L=0 全部等价", fontsize=10)
a.legend(fontsize=8); a.grid(alpha=.3)

# --- (2) 效应特异性对照 ---
a = ax[0, 1]
order = ["ctrl_zero", "ctrl_const", "real", "ctrl_perm"]
lbl = {"ctrl_zero": "无感知\n(sal=0)", "ctrl_const": "有输入\n零结构", "real": "真实\n世界结构", "ctrl_perm": "随机置换\n(结构错乱)"}
mean = {r["group"]: r["mean"] for r in d78b["rows"]}
mean["ctrl_zero"] = d78b["baseline_zero"]
cols = ["#95a5a6", "#7f8c8d", "#c0392b", "#2980b9"]
bars = a.bar([lbl[k] for k in order], [mean[k] for k in order], color=cols)
for b, k in zip(bars, order):
    a.text(b.get_x() + b.get_width()/2, b.get_height() + .004,
           f"{mean[k]:.4f}", ha="center", fontsize=9, fontweight="bold")
a.axhline(mean["ctrl_zero"], color="k", ls=":", lw=1)
a.set_ylabel("容量偏度")
a.set_title("② 效应特异性：真实 > 零结构，但 < 随机置换\n★系统不认真实世界结构，只响应数值与通道耦合", fontsize=10)
a.grid(alpha=.3, axis="y")

# --- (3) 时间线（对数）---
a = ax[1, 0]
tl = d78["timeline"]
yrs = [("生命起源\n~38亿年", 3.8e9), ("细菌趋化性\n(无符号感知)", 3.0e9),
       ("计数陶筹\n~公元前8000", 1.0e4), ("楔形数字\n~公元前3100", 5.1e3),
       ("现代数字代码\n~100年", 100)]
a.barh([y[0] for y in yrs], [y[1] for y in yrs], color=["#27ae60", "#27ae60", "#e67e22", "#e67e22", "#c0392b"])
a.set_xscale("log")
a.set_xlabel("距今年数（对数刻度）")
a.set_title(f"③ 感知先于符号 {tl['ratio_low']:.0e}–{tl['ratio_high']:.0e} 倍\n绿色=无符号的感知-响应；橙色/红色=后加的符号层", fontsize=10)
a.grid(alpha=.3, axis="x")

# --- (4) 结构来源分解 ---
a = ax[1, 1]
endog = d78b["baseline_zero"]
sense = d78b["rows"][0]["mean"] - endog
a.pie([endog, sense], labels=[f"引擎内生硬约束\n(稀缺/取舍/不可逆)\n{endog:.4f}  {endog/(endog+sense)*100:.0f}%",
                              f"感知调制\n{sense:+.4f}  {sense/(endog+sense)*100:.0f}%"],
      colors=["#2c3e50", "#e74c3c"], startangle=90,
      textprops=dict(fontsize=9), explode=(0, 0.06))
a.set_title("④ 结构来源分解：感官是【增强】不是【创建】\n80% 来自内生硬约束", fontsize=10)

plt.suptitle("实验 078 · 表征必要性检验：感知先于符号\n"
             "真实换能器读数（8 城气象站）| 16 seeds × 600 拍 | 共同存活子集防死亡筛选",
             fontsize=13, fontweight="bold", y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.955])
p = os.path.join(FIG, "078_representation.png")
plt.savefig(p, dpi=150, bbox_inches="tight")
print("saved:", p, os.path.getsize(p))
