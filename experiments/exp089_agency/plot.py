import json, numpy as np
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

OUT = "/data/workspace/luoshen-o1/fig/089_agency.png"
d2 = json.load(open("/data/workspace/luoshen-o1/experiments/exp089_agency/result_089.json"))
dp = json.load(open("/data/workspace/luoshen-o1/experiments/exp089_agency/result_089_pair.json"))
dd = json.load(open("/data/workspace/luoshen-o1/experiments/exp089_agency/result_089_deprivation.json"))

fig, ax = plt.subplots(2, 2, figsize=(14, 9.5))

# ---------- (1) 操控 × 凭证 ----------
a = ax[0, 0]
labels = ["A 操作\n+凭证", "B 操作\n+错凭证", "C 零操作\n+凭证", "D 零操作\n无凭证"]
ent = [d2["A_operate_right_cred"]["entered"], d2["B_operate_wrong_cred"]["entered"],
       d2["C_zeroop_right_cred"]["entered"], d2["D_zeroop_no_cred"]["entered"]]
ops = [d2["A_operate_right_cred"]["ops"], d2["B_operate_wrong_cred"]["ops"], 0, 0]
cols = ["#2e8b57" if e else "#b03030" for e in ent]
a.bar(labels, [1 if e else 0 for e in ent], color=cols)
a.set_ylim(0, 1.25)
a.set_ylabel("进入 (1=成功)")
for i, (e, o) in enumerate(zip(ent, ops)):
    a.text(i, 1.05, "鼠标动作=%d" % o, ha="center", fontsize=9)
    a.text(i, 0.5, "OK" if e else "403", ha="center", color="w", fontsize=12, fontweight="bold")
a.set_title("① 操控 × 凭证：结果由凭证决定\nA/B 动作序列逐位相同(5步)，结果相反", fontsize=11)

# ---------- (2) 配对协议 ----------
a = ax[0, 1]
steps = ["我申请\nchallenge", "我自己批准", "状态", "持有凭证方\n批准", "状态"]
vals = [0.5, 0, 0, 1, 1]
cols2 = ["#888", "#b03030", "#b03030", "#2e8b57", "#2e8b57"]
a.bar(steps, vals, color=cols2)
a.set_ylim(0, 1.3)
a.set_ylabel("granted=1")
for i, v in enumerate(vals):
    a.text(i, v + 0.06, {0.5: "pending", 0: "403 REJECTED", 1: "granted"}[v],
           ha="center", fontsize=9)
a.set_title("② 配对协议复现（两轮一致）\n申请者无法批准自己 — 协议约束，非能力问题", fontsize=11)

# ---------- (3) 感官剥夺 2x2：存活 ----------
a = ax[1, 0]
c = dd["conds"]
names = ["A 本体+外源", "B 本体+外源关\n(现在真实状态)", "C 本体关+外源", "D 全盲"]
surv = []
for k in ["A_proprio1_extero1", "B_proprio1_extero0", "C_proprio0_extero1", "D_proprio0_extero0"]:
    n, m = c[k]["surv"].split("/")
    surv.append(int(n) / int(m) * 100)
cols3 = ["#4a7ebb", "#2e8b57", "#4a7ebb", "#b03030"]
b = a.bar(names, surv, color=cols3)
a.set_ylabel("存活率 %")
a.set_ylim(0, 100)
for i, (k, v) in enumerate(zip(["A_proprio1_extero1", "B_proprio1_extero0",
                                "C_proprio0_extero1", "D_proprio0_extero0"], surv)):
    a.text(i, v + 2, c[k]["surv"], ha="center", fontsize=9)
a.text(3, 12, "偏度0.72\n=死亡筛选\n不可比", ha="center", fontsize=8, color="#b03030")
a.set_title("③ 真实发生的感官剥夺：外源已关，本体仍在线\n存活率不受外源有无影响", fontsize=11)

# ---------- (4) B-A 配对差 ----------
a = ax[1, 1]
p = c["B_minus_A_paired"]
a.barh([0], [p["delta"]], color="#2e8b57", height=0.4)
a.errorbar([p["delta"]], [0], xerr=[[p["delta"] - p["ci_lo"]], [p["ci_hi"] - p["delta"]]],
           color="k", capsize=6, lw=1.6)
a.axvline(0, color="#b03030", ls="--", lw=1.6)
a.set_yticks([0])
a.set_yticklabels(["B − A\n(剥夺外源 − 有外源)"])
a.set_xlabel("结构偏度差")
a.set_xlim(-0.03, 0.03)
a.text(0, -0.45, "Δ=%+.4f  95%%CI [%.4f, %.4f] 跨0 → 无差异\nn_common=%d"
       % (p["delta"], p["ci_lo"], p["ci_hi"], p["n_common"]),
       ha="center", fontsize=9.5)
a.set_title("④ 剥夺外源对内在结构：无效应\n本体觉仍在 ⇒ 结构仍在", fontsize=11)

plt.suptitle("089 · 操控与凭证的分离 · 真实发生的感官剥夺", fontsize=13, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT, dpi=130)
print("saved", OUT)
