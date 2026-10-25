# -*- coding: utf-8 -*-
import json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False

d = json.load(open("result188.json", encoding="utf-8"))
r = json.load(open("robust188.json", encoding="utf-8"))
g = json.load(open("grid188.json", encoding="utf-8"))

fig, ax = plt.subplots(2, 2, figsize=(13, 9))

# A: Heaps
a0 = ax[0,0]
pts = d["heaps"]["curve"]
N = [p["N"] for p in pts]; V = [p["V"] for p in pts]
a0.plot(N, V, "o-", color="#2b6cb0", lw=2, ms=6, label="实测 V(N)")
K, b = d["heaps"]["K"], d["heaps"]["beta"]
xs = [min(N)*0.9, max(N)*1.05]
a0.plot(xs, [K*x**b for x in xs], "--", color="#c53030", lw=2,
        label="拟合 V=%.2f·N^%.3f" % (K, b))
a0.set_xscale("log"); a0.set_yscale("log")
a0.set_xlabel("见过的字数 N (人生有限)")
a0.set_ylabel("词汇量 V")
a0.set_title("A 词汇增长是次线性的 (Heaps), R²=%.3f\n越学越慢, 人生有限 → V 有限" % d["heaps"]["r2"], fontsize=11)
a0.legend(fontsize=9); a0.grid(alpha=.3)

# B: 权衡
a1 = ax[0,1]
rows = d["compression"]
Vs = [x["actual_V"] for x in rows]
acc = [x["acc"] for x in rows]
red = [x["reduction"] for x in rows]
a1.plot(Vs, acc, "o-", color="#2b6cb0", lw=2, ms=6, label="可预测性 (acc)")
a1.set_xscale("log", base=2)
a1.set_xlabel("词汇量 V (对数)", color="#2b6cb0")
a1.set_ylabel("可被预测的程度", color="#2b6cb0")
a1.tick_params(axis="y", labelcolor="#2b6cb0")
a1.set_ylim(0.2, 0.85)
a2 = a1.twinx()
a2.plot(Vs, red, "s-", color="#c53030", lw=2, ms=6, label="每步有效信息")
a2.set_ylabel("每字符有效信息 (bits)", color="#c53030")
a2.tick_params(axis="y", labelcolor="#c53030")
a1.set_title("B 权衡: 词越少越好预测, 但每步能带的越少\n(两条线方向相反)", fontsize=11)
a1.grid(alpha=.3)

# C: reduction vs V + k*
a3 = ax[1,0]
a3.plot(Vs, red, "o-", color="#2b6cb0", lw=2, ms=7)
mx = max(rows, key=lambda x: x["reduction"])
a3.axvline(mx["actual_V"], color="#c53030", ls="--", lw=1.5)
a3.annotate("峰值 V=%d\n(去掉罕见字反而更密)" % mx["actual_V"],
            xy=(mx["actual_V"], mx["reduction"]),
            xytext=(mx["actual_V"]*2.2, mx["reduction"]*0.55),
            fontsize=9, color="#c53030",
            arrowprops=dict(arrowstyle="->", color="#c53030"))
a3.set_xscale("log", base=2)
a3.set_xlabel("词汇量 V (对数)"); a3.set_ylabel("每字符有效信息 (bits)")
a3.set_title("C 最优词汇量不是最大\n(3 种划分中 2 次峰值在 V=400)", fontsize=11)
a3.grid(alpha=.3)

# D: 策略对比
a4 = ax[1,1]
pb = d["partB"]["results"]
lab = {"pure_explore":"只学不产出","pure_exploit":"只产出不学"}
names = []; vals = []; cols = []
order = ["pure_explore","pure_exploit","alternate","greedy_switch"]
for o in order:
    if o == "alternate":
        best = max([x for x in pb if x["strategy"]=="alternate"], key=lambda x: x["total_gain"])
        names.append("固定交替\na=%d" % best["param"]); vals.append(best["total_gain"]); cols.append("#d69e2e")
    else:
        x = [y for y in pb if y["strategy"]==o][0]
        names.append(lab.get(o,o)); vals.append(x["total_gain"]); cols.append("#c53030" if o=="pure_explore" else "#2b6cb0")
bars = a4.bar(names, vals, color=["#c53030","#2b6cb0","#d69e2e","#38a169"], width=.6)
for bb, v in zip(bars, vals):
    a4.text(bb.get_x()+bb.get_width()/2, v*1.02, "%.0f" % v, ha="center", fontsize=10)
a4.set_ylabel("总产出 (预算 14000)")
a4.set_ylim(0, max(vals)*1.2)
a4.set_title("D 切换赢 9/9 场景\n只学=0, 只产出=8090, 切换=18183 (2.25x)", fontsize=11)
a4.grid(alpha=.3, axis="y")

plt.tight_layout()
plt.savefig("render188.png", dpi=110)
print("saved render188.png")

# 附加: 平台图
fig2, axp = plt.subplots(1,1,figsize=(9,4.5))
gs = g["grid_scan"]
A = [x["a"] for x in gs]; G = [x["gain"] for x in gs]
axp.plot(A, G, "o-", color="#2b6cb0", ms=4, lw=1.5)
axp.axhline(g["greedy"], color="#38a169", ls="--", lw=2, label="自适应切换 %.0f" % g["greedy"])
best = max(gs, key=lambda x: x["gain"])
axp.axvline(best["a"], color="#c53030", ls=":", lw=1.5)
axp.axvspan(10, 18, color="#d69e2e", alpha=.18)
axp.annotate("真实最优 a=%d (非斐波那契)" % best["a"], xy=(best["a"], best["gain"]),
             xytext=(22, best["gain"]*0.985), fontsize=10, color="#c53030",
             arrowprops=dict(arrowstyle="->", color="#c53030"))
axp.text(11.5, min(G)+ (max(G)-min(G))*0.15, "平台 a∈[10,18]\n差异<1%", fontsize=9, color="#975a16")
axp.set_xlabel("固定交替周期 a (每 a 步产出后学 1 步)")
axp.set_ylabel("总产出")
axp.set_title("切换频率不敏感, 存在宽平台 — 重要的是「有切换」, 不是「多频繁」", fontsize=11)
axp.legend(fontsize=9); axp.grid(alpha=.3)
plt.tight_layout(); plt.savefig("render188b.png", dpi=110)
print("saved render188b.png")
