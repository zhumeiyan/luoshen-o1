#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ["WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "Noto Sans CJK SC"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

D = os.path.dirname(os.path.abspath(__file__))
os.chdir(D)

gated = json.load(open("claim_log_gated.json", encoding="utf-8"))
raw = json.load(open("claims_raw.json", encoding="utf-8"))

fig, ax = plt.subplots(2, 3, figsize=(16, 9.5))

# --- (0,0) 可追溯性缺口 ---
a = ax[0, 0]
n_all = 110
n_no_ci = sum(1 for u in raw["unparsed_reports"] if u["reason"] == "no_parsable_CI")
n_claim = len(raw["claims"])
a.bar(["有可解析CI\n的报告", "无可解析CI\n的报告"], [n_all - n_no_ci, n_no_ci],
      color=["#4c78a8", "#b0b0b0"])
for i, v in enumerate([n_all - n_no_ci, n_no_ci]):
    a.text(i, v + 1.5, str(v), ha="center", fontsize=12, fontweight="bold")
a.set_ylabel("报告数")
a.set_title("① 可追溯性缺口：110 份报告里\n只有 %d 份能抽出数值 CI" % (n_all - n_no_ci),
            fontsize=11)
a.set_ylim(0, 118)

# --- (0,1) 名义显著 vs 校正后存活 ---
a = ax[0, 1]
nom = sum(1 for c in raw["claims"] if c["ci_excludes_zero"])
bhr = sum(1 for c in raw["claims"] if c.get("reject_bh", False))
bonf = sum(1 for c in raw["claims"] if c.get("reject_bonf", False))
a.bar(["名义\n不跨0", "BH-FDR\n后", "Bonferroni\n后"], [nom, bhr, bonf],
      color=["#72b7b2", "#f58518", "#e45756"])
for i, v in enumerate([nom, bhr, bonf]):
    a.text(i, v + 0.2, str(v), ha="center", fontsize=12, fontweight="bold")
a.set_title("② 回溯子集(n=%d)：校正后掉多少" % len(raw["claims"]), fontsize=11)
a.set_ylabel("断言数")
a.set_ylim(0, max(nom, bhr, bonf) + 2.5)

# --- (0,2) 前瞻断言日志：22 条 ---
a = ax[0, 2]
npass = sum(1 for c in gated if c["PASS"])
nbh = sum(1 for c in gated if c["reject_bh"])
nnom = sum(1 for c in gated if c.get("ci_lo") is not None and (c["ci_lo"] > 0 or c["ci_hi"] < 0))
a.bar(["名义", "BH-FDR", "三闸全过"], [nnom, nbh, npass],
      color=["#72b7b2", "#f58518", "#54a24b"])
for i, v in enumerate([nnom, nbh, npass]):
    a.text(i, v + 0.3, str(v), ha="center", fontsize=12, fontweight="bold")
a.set_title("③ 前瞻断言日志(n=%d)：\nG1/G2/G3 拦下 %d 条" % (len(gated), len(gated) - npass),
            fontsize=11)
a.set_ylim(0, max(nnom, nbh, npass) + 3)

# --- (1,0) q 值分布 ---
a = ax[1, 0]
qs = sorted(c["q_bh"] for c in gated if c.get("q_bh") is not None)
ys = [-math.log10(max(q, 1e-300)) for q in qs]
cols = ["#54a24b" if c["PASS"] else "#e45756" for c in sorted(
    gated, key=lambda c: c["q_bh"]) if c.get("q_bh") is not None]
a.bar(range(len(ys)), ys, color=cols)
a.axhline(-math.log10(0.05), color="k", ls="--", lw=1.2)
a.text(0.5, -math.log10(0.05) + 1.2, "q=0.05", fontsize=9)
a.set_xlabel("断言（按 q 升序）")
a.set_ylabel("-log10(q)")
a.set_title("④ BH-FDR 后 q 值分布\n绿=过闸 红=被拦", fontsize=11)

# --- (1,1) G4 稳健性 ---
a = ax[1, 1]
burns = [0, 20, 50, 100, 200, 400]
closed = [0.164098, 0.142586, 0.125558, 0.103676, 0.076096, 0.045511]
openv = [0.0079131, 0.00071858, 0.00099121, 0.00091236, 0.00075771, 0.00074516]
a.plot(burns, closed, "o-", color="#54a24b", lw=2, label="closed(相倚·真学习)")
a.plot(burns, openv, "s-", color="#e45756", lw=2, label="open(相继·估计器假象)")
a.axhline(0, color="k", lw=0.8)
a.set_xlabel("burn-in 拍数")
a.set_ylabel("学到的 fg")
a.set_title("⑤ G4 稳健性闸：换分析变体后\n真效应剩 63%，假象只剩 12%", fontsize=11)
a.legend(fontsize=8)
a.set_yscale("log")

# --- (1,2) 被拦原因统计 ---
a = ax[1, 2]
from collections import Counter
cnt = Counter()
for c in gated:
    for r in c.get("gate_reasons", []):
        cnt[r.split(":")[0]] += 1
for c in raw["claims"]:
    for r in c.get("gate_reasons", []) if "gate_reasons" in c else []:
        cnt[r.split(":")[0]] += 1
labels = {"G1_FAIL": "G1 效应量", "G2_FAIL": "G2 多重比较",
          "G3_FAIL": "G3 数据充足", "G4_FAIL": "G4 稳健性"}
ks = [k for k in ["G1_FAIL", "G2_FAIL", "G3_FAIL", "G4_FAIL"] if cnt.get(k)]
vs = [cnt[k] for k in ks]
if ks:
    a.barh([labels[k] for k in ks], vs, color=["#4c78a8", "#f58518", "#e45756", "#b279a2"][:len(ks)])
    for i, v in enumerate(vs):
        a.text(v + 0.3, i, str(v), va="center", fontsize=11, fontweight="bold")
a.set_title("⑥ 各闸拦截次数", fontsize=11)
a.set_xlabel("次数")

plt.tight_layout()
plt.savefig("fig128.png", dpi=110, bbox_inches="tight")
print("saved fig128.png")
