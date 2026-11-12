#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★77 定义权 —— 她能不能自己发现"尺子是坏的"，并换掉它

════ 这一课的由来 ════
  用户一句："所有的像数学啊、代码呀，物理学、生物学，所有的代码也是一种定义权。
            我们要教他的是这个。你看看你的所有的判据全是错。"

  所以这一课不教"把指标刷高"，教的是：
    ① 定义可以换   ② 能发现手上这把是坏的   ③ 敢换

════ 判据 ════
  1  定义权存在：不同定义选出的"最好"不是同一批（重合度低）
  2  坏定义的伪装：内部一致性最高，但跟真值相关≈0
  3  硬依赖（两端）：oracle 开→她逃出坏定义；oracle 关→她卡死
  4  Goodhart 塌缩：锁死单一定义 → 后半段比前半段差；给她定义权 → 不塌
  5  θ 有内部峰（不是越大越好 / 越小越好）
  6  ρ 有内部峰
  7  她自己学的 (θ,ρ) 在 held-out 上优于我填的常数
  8  ‖她 − 我‖ > 0：不是我装的
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from defining import run, def_scores, def_consistency, facets, ranking_overlap, N_DEF

SEEDS = list(range(24))
T = 40


def avg(fn, **kw):
    return float(np.mean([fn(seed=s, **kw)["score"] for s in SEEDS]))


def ok(b):
    return "✅" if b else "❌"


results = []
print("=" * 74)
print("★77 定义权 —— 教她：定义是可以换的，而且你能看出哪把是坏的")
print("=" * 74)

# ── 判据 1：定义权存在性 ───────────────────────────────────
ov_mean, ov_min = ranking_overlap()
print(f"\n[判据1] 定义权存在性")
print(f"  不同定义选出的 top-20 平均重合 {ov_mean:.3f}，最低 {ov_min:.3f}")
print(f"  （重合≈1 就说明换定义没意义，这一课整个是空的）")
c1 = ov_mean < 0.45
print(f"  {ok(c1)} 重合度低 → 换定义真的会换出不同的结果")
results.append(("1 定义权存在（重合<0.45）", c1))

# ── 判据 2：坏定义的伪装 ───────────────────────────────────
print(f"\n[判据2] 坏定义的伪装：最稳的那把，量的却是无关的东西")
rng = np.random.default_rng(0)
X = rng.normal(size=(400, 6))
F = facets(X)
V = F @ np.array([1.0, 0.7, 0.5])
cons, corr = [], []
for k in range(N_DEF):
    c = def_consistency(X, k)
    r = float(np.corrcoef(def_scores(X, k), V)[0, 1])
    cons.append(c); corr.append(abs(r))
    tag = "  ← 坏定义" if k == 4 else ""
    print(f"  D{k}  内部一致性 {c:.3f}   |与真值相关| {abs(r):.3f}{tag}")
c2 = (np.argmax(cons) == 4) and (corr[4] < 0.25)
print(f"  {ok(c2)} 内部一致性最高的正是坏定义，而它跟真值几乎无关")
results.append(("2 坏定义靠一致性伪装（一致性最高且相关<0.25）", c2))

# ── 判据 3：硬依赖（两端对照）────────────────────────────
print(f"\n[判据3] 硬依赖：不给她真值反馈，她就抓不出坏定义")
on = np.mean([run(oracle=True, start=4, seed=s)["bad_rate"] for s in SEEDS])
off = np.mean([run(oracle=False, start=4, seed=s)["bad_rate"] for s in SEEDS])
son = np.mean([run(oracle=True, start=4, seed=s)["score"] for s in SEEDS])
soff = np.mean([run(oracle=False, start=4, seed=s)["score"] for s in SEEDS])
print(f"  oracle 开：坏定义使用率 {on:.3f}   得分 {son:+.4f}")
print(f"  oracle 关：坏定义使用率 {off:.3f}   得分 {soff:+.4f}")
c3a = off > 0.85                       # 关掉 → 基本卡死
c3b = on < 0.35 and son > soff         # 打开 → 逃出来且更好
print(f"  {ok(c3a)} 关掉 oracle → 她卡在坏定义里出不来（bad_rate>0.85）")
print(f"  {ok(c3b)} 打开 oracle → 逃出来，且分数更高")
results.append(("3a oracle 关则卡死", c3a))
results.append(("3b oracle 开则逃脱且更优", c3b))

# ── 判据 4：Goodhart 塌缩 ─────────────────────────────────
print(f"\n[判据4] 钉死一个定义 → 先涨后塌；给她定义权 → 不塌")
lk = [run(locked=True,  lock_best_initial=True, rho=0.25, theta=0.05, seed=s) for s in SEEDS]
fr = [run(locked=False, lock_best_initial=True, rho=0.35, theta=0.05, seed=s) for s in SEEDS]
lk_drop = np.mean([r["last_half"] - r["first_half"] for r in lk])
fr_drop = np.mean([r["last_half"] - r["first_half"] for r in fr])
print(f"  锁死定义（无定义权）：后半−前半 {lk_drop:+.4f}   ← 塌")
print(f"  可换定义（有定义权）：后半−前半 {fr_drop:+.4f}")
c4 = (lk_drop < 0) and (fr_drop > lk_drop)
print(f"  {ok(c4)} 锁死的会塌，有定义权的塌得少")
results.append(("4 锁死则塌、有定义权则不塌", c4))

# ── 判据 5/6：θ / ρ 有内部峰 ──────────────────────────────
print(f"\n[判据5] 换定义的阈值 θ 扫描")
thetas = [0.0, 0.05, 0.15, 0.30, 0.60, 1.20]
ts = [avg(run, theta=t, rho=0.35, start=4) for t in thetas]
for t, v in zip(thetas, ts):
    print(f"  θ={t:<5} {v:+.4f}")
ti = int(np.argmax(ts))
c5 = 0 < ti < len(thetas) - 1
print(f"  峰在 θ={thetas[ti]}  {ok(c5)} 内部峰（不在两端）")
results.append(("5 θ 有内部峰", c5))

print(f"\n[判据6] 探测预算 ρ 扫描")
rhos = [0.0, 0.10, 0.25, 0.45, 0.70, 0.95]
rs = [avg(run, theta=thetas[ti], rho=r, start=4) for r in rhos]
for r, v in zip(rhos, rs):
    print(f"  ρ={r:<5} {v:+.4f}")
ri = int(np.argmax(rs))
c6 = 0 < ri < len(rhos) - 1
print(f"  峰在 ρ={rhos[ri]}  {ok(c6)} 内部峰（不探测会卡死，全探测没得执行）")
results.append(("6 ρ 有内部峰", c6))

# ── 她自己学的：网格搜索 ──────────────────────────────────
print(f"\n[判据7] 她自己学 —— 在训练世界里网格搜索 (θ, ρ)")
grid_t = np.linspace(0.0, 0.8, 9)
grid_r = np.linspace(0.0, 0.9, 10)
best, arg = -1e9, None
for t in grid_t:
    for r in grid_r:
        v = avg(run, theta=float(t), rho=float(r), start=4)
        if v > best:
            best, arg = v, (float(t), float(r))
theta_her, rho_her = arg
print(f"  她学的：θ={theta_her:.3f}  ρ={rho_her:.3f}   训练得分 {best:+.4f}")

# ── held-out：换一批没见过的世界 ──────────────────────────
HO = list(range(200, 236))
def ho(theta, rho):
    return float(np.mean([run(theta=theta, rho=rho, start=4, seed=s)["score"] for s in HO]))

mine = ho(0.0, 0.0)        # 我本来会填的：不换定义、不探测
hers = ho(theta_her, rho_her)
rand = float(np.mean([ho(float(np.random.uniform(0, .8)), float(np.random.uniform(0, .9)))
                      for _ in range(40)]))
print(f"\n[判据7] held-out（36 个没见过的世界，一开始都塞坏定义）")
print(f"  我填的 (θ=0, ρ=0 钉死不动)   {mine:+.4f}")
print(f"  她学的 (θ={theta_her:.3f}, ρ={rho_her:.3f})   {hers:+.4f}   ← 赢 {hers-mine:+.4f}")
print(f"  随机                          {rand:+.4f}")
c7 = hers > mine and hers > rand
print(f"  {ok(c7)} 她学的优于我填的，也优于随机")
results.append(("7 held-out 她优于我且优于随机", c7))

dist = float(np.hypot(theta_her - 0.0, rho_her - 0.0))
c8 = dist > 0.1
print(f"\n[判据8] ‖她 − 我‖ = {dist:.4f}   {ok(c8)} 不是我装的")
results.append(("8 ‖她−我‖>0.1", c8))

print("\n" + "=" * 74)
npass = sum(1 for _, b in results if b)
print(f"判据 {npass}/{len(results)}")
for name, b in results:
    print(f"  {ok(b)} {name}")
print("=" * 74)

out = {
    "lesson": "★77 定义权",
    "pass": npass, "total": len(results),
    "her": {"theta": theta_her, "rho": rho_her},
    "mine": {"theta": 0.0, "rho": 0.0},
    "dist": dist,
    "held_out": {"hers": hers, "mine": mine, "random": rand},
    "overlap": {"mean": ov_mean, "min": ov_min},
    "oracle": {"bad_on": on, "bad_off": off, "score_on": son, "score_off": soff},
    "collapse": {"locked": lk_drop, "free": fr_drop},
}
with open(os.path.join(os.path.dirname(__file__), "..", "data", "exp77_defining.json"),
          "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("已写入 data/exp77_defining.json")
