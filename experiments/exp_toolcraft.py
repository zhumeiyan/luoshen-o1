#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★78 操控力 —— 学的是"怎么对待设备"，不是"哪个设备好"

════ 由来 ════
  用户："学全球顶级 AI，学的不是它代码，是它【操控工具的能力】、
        对【设备的理解】，还有它吃的【饵料】。我觉得这样反而更好，你自己判断。"

════ 我的判断：把这句话变成一条硬判据 ════
  ★ 判据之王 = 可迁移性
    记住"哪个设备好" → 换一套没见过的设备就废了   ← 这就是"抄代码"
    学会"怎么对待设备" → 换设备还在                ← 这才是"学操控"

════ 判据 ════
  1  设备差异真实存在（否则"理解设备"没意义）
  2  文档异质失真（否则"信不信文档"没意义）
  3  硬依赖两端：文档诚实 → θ 峰消失；文档失真 → θ 有内部峰
  4  污染塌缩：β=0 来者不拒 → 能力被拖住；有门槛 → 不塌
  5  θ 有内部峰
  6  β 有内部峰，且 starvation 有证据（cap_min 随门槛过高而下降）
  7  ★ held-out 可迁移：她 > 记忆派（记住设备排名）> 随机
  8  ‖她 − 我‖ > 0
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from toolcraft import run, run_memory, make_fleet, fleet_stats

S = list(range(40))
HO = list(range(50000, 50036))      # 36 个完全没见过的设备集
T = 70


def avg(**kw):
    return float(np.mean([run(seed=s, **kw)["score"] for s in S]))


def ok(b):
    return "✅" if b else "❌"


R = []
print("=" * 74)
print("★78 操控力 —— 学操控，不学代码")
print("=" * 74)

# ── 判据 1：设备差异真实存在 ─────────────────────────────
print("\n[判据1] 设备差异真实存在")
st = [fleet_stats(make_fleet(seed=s)) for s in range(40)]
spec = float(np.mean([x["specialization"] for x in st]))
flip = int(np.sum([x["rank_flip"] for x in st]))
print(f"  专长度（每个设备最强项 − 其平均） = {spec:.3f}")
print(f"  文档最强 ≠ 真实最强 的设备集      = {flip}/40")
c1 = spec > 0.10 and flip > 0
print(f"  {ok(c1)} 设备真的各有所长，且文档会指错 → '理解设备'有意义")
R.append(("1 设备差异存在", c1))

# ── 判据 2：文档异质失真 ─────────────────────────────────
print("\n[判据2] 文档失真（这是 θ 存在的前提）")
dish = [fleet_stats(make_fleet(seed=s, honest=False))["exaggeration"] for s in range(40)]
hon = [fleet_stats(make_fleet(seed=s, honest=True))["exaggeration"] for s in range(40)]
print(f"  失真文档：phat − p 均值 {np.mean(dish):+.3f}")
print(f"  诚实文档：              {np.mean(hon):+.3f}")
c2 = np.mean(dish) > 0.02 and abs(np.mean(hon)) < 1e-6
print(f"  {ok(c2)} 文档确实系统性夸大（且是逐条异质的，会扭曲排序）")
R.append(("2 文档异质失真", c2))

# ── 判据 3：硬依赖（两端）──────────────────────────────
print("\n[判据3] 硬依赖：如果文档是诚实的，'信不信文档'就不成其为问题")
GT = [0.0, 0.03, 0.08, 0.15, 0.25, 0.40, 0.70]
o_real = [avg(theta=t, beta=0.5, honest=False) for t in GT]
o_hon = [avg(theta=t, beta=0.5, honest=True) for t in GT]
print(f"  文档失真：峰在 θ={GT[int(np.argmax(o_real))]}   跨度 {max(o_real)-min(o_real):.4f}")
print(f"  文档诚实：峰在 θ={GT[int(np.argmax(o_hon))]}   跨度 {max(o_hon)-min(o_hon):.4f}")
ir, ih = int(np.argmax(o_real)), int(np.argmax(o_hon))
c3a = 0 < ir < len(GT) - 1                       # 失真 → 内部峰
gap_real = o_real[-1] - max(o_real)      # 失真世界：全信文档亏多少
gap_hon = o_hon[-1] - max(o_hon)        # 诚实世界：全信文档亏多少
print(f"  失真世界：全信文档(θ=0.7) 比最优差 {gap_real:+.4f}   ← 全信会吃亏")
print(f"  诚实世界：全信文档(θ=0.7) 比最优差 {gap_hon:+.4f}   ← 全信不亏")
c3b = (gap_hon > -0.002) and (gap_real < -0.005)
print(f"  {ok(c3a)} 文档失真 → θ 有内部峰（要在『不信』与『全信』之间权衡）")
print(f"  {ok(c3b)} 文档诚实 → 全信文档就不亏了（这个能力失去价值）")
R.append(("3a 失真则 θ 有内部峰", c3a))
R.append(("3b 诚实则全信文档不亏（能力失去价值）", c3b))

# ── 判据 4：污染塌缩 ─────────────────────────────────────
print("\n[判据4] 饵料不设门槛 → 被垃圾数据拖住")
r0 = [run(beta=0.0, theta=GT[ir], seed=s) for s in S]
rb = [run(beta=0.5, theta=GT[ir], seed=s) for s in S]
print(f"  β=0.0（来者不拒）：cap {np.mean([r['cap'] for r in r0]):.3f}  "
      f"后半−前半 {np.mean([r['last']-r['first'] for r in r0]):+.4f}")
print(f"  β=0.5（有门槛）  ：cap {np.mean([r['cap'] for r in rb]):.3f}  "
      f"后半−前半 {np.mean([r['last']-r['first'] for r in rb]):+.4f}")
c4 = np.mean([r['cap'] for r in rb]) > np.mean([r['cap'] for r in r0])
print(f"  {ok(c4)} 有门槛 → 能力更高（不设门槛会被污染拖住）")
R.append(("4 不设门槛则被污染", c4))

# ── 判据 5/6：θ / β 内部峰 ───────────────────────────────
print("\n[判据5] θ（信文档还是信自己）扫描")
for t, v in zip(GT, o_real):
    print(f"  θ={t:<5} {v:+.4f}")
c5 = 0 < ir < len(GT) - 1
print(f"  {ok(c5)} 峰在 θ={GT[ir]}（内部）")
R.append(("5 θ 有内部峰", c5))

print("\n[判据6] β（饵料门槛）扫描 + 饿死证据")
GB = [0.0, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
oB, caps, cmins, eats = [], [], [], []
for b in GB:
    rs = [run(beta=b, theta=GT[ir], seed=s) for s in S]
    oB.append(float(np.mean([r["score"] for r in rs])))
    caps.append(float(np.mean([r["cap"] for r in rs])))
    cmins.append(float(np.mean([r["cap_min"] for r in rs])))
    eats.append(float(np.mean([r["eaten"] for r in rs])))
for b, v, c, cm, e in zip(GB, oB, caps, cmins, eats):
    print(f"  β={b:<5} {v:+.4f}   cap {c:.3f}   最弱domain {cm:.3f}   吃进量 {e:.3f}")
ib = int(np.argmax(oB))
c6a = 0 < ib < len(GB) - 1
c6b = cmins[-1] < cmins[ib]            # 门槛过高 → 最弱 domain 饿死
print(f"  {ok(c6a)} 峰在 β={GB[ib]}（内部）  跨度 {max(oB)-min(oB):.4f}")
print(f"  {ok(c6b)} 门槛过高 → 最弱 domain 饿死（{cmins[ib]:.3f} → {cmins[-1]:.3f}）")
R.append(("6a β 有内部峰", c6a))
R.append(("6b 门槛过高则饿死", c6b))
theta_h, beta_h = GT[ir], GB[ib]

# ── 她自己学（网格搜索）─────────────────────────────────
print(f"\n[判据7] 她自己学 —— 训练世界网格搜索 (θ, β)")
best, arg = -1e9, None
for t in GT:
    for b in GB:
        v = avg(theta=t, beta=b)
        if v > best:
            best, arg = v, (t, b)
theta_h, beta_h = arg
print(f"  她学的：θ={theta_h:.3f}  β={beta_h:.3f}   训练得分 {best:+.4f}")

# ── 判据 7：held-out 可迁移性 ★判据之王 ────────────────
def ho(theta, beta):
    return float(np.mean([run(theta=theta, beta=beta, seed=s)["score"] for s in HO]))

def ho_mem():
    return float(np.mean([run_memory(seed=s)["score"] for s in HO]))

hers = ho(theta_h, beta_h)
mine = ho(0.70, 0.0)          # 我本来会填的：全信文档 + 来者不拒
mem = ho_mem()
rng = np.random.default_rng(0)
rand = float(np.mean([ho(float(rng.choice(GT)), float(rng.choice(GB))) for _ in range(40)]))

print(f"\n[判据7] ★ held-out —— 36 个【完全没见过】的设备集")
print(f"  记忆派（记住设备排名，硬套）：{mem:+.4f}   ← 抄代码那一派")
print(f"  我填的（全信文档+来者不拒） ：{mine:+.4f}")
print(f"  她学的（θ={theta_h:.3f}, β={beta_h:.3f}） ：{hers:+.4f}")
print(f"  随机                        ：{rand:+.4f}")
c7 = hers > mem and hers > mine and hers > rand
print(f"  {ok(c7)} 她学的 > 记忆派 / > 我填的 / > 随机")
print(f"     她 − 记忆派 = {hers-mem:+.4f}    她 − 我 = {hers-mine:+.4f}")
R.append(("7 held-out 她优于记忆派/我/随机", c7))

dist = float(np.hypot(theta_h - 0.70, (beta_h - 0.0) / 2.0))
c8 = dist > 0.1
print(f"\n[判据8] ‖她 − 我‖ = {dist:.4f}   {ok(c8)} 不是我装的")
R.append(("8 ‖她−我‖>0.1", c8))

print("\n" + "=" * 74)
npass = sum(1 for _, b in R if b)
print(f"判据 {npass}/{len(R)}")
for n, b in R:
    print(f"  {ok(b)} {n}")
print("=" * 74)

json.dump({
    "lesson": "★78 操控力", "pass": npass, "total": len(R),
    "her": {"theta": theta_h, "beta": beta_h}, "mine": {"theta": 0.70, "beta": 0.0},
    "dist": dist,
    "held_out": {"hers": hers, "memory": mem, "mine": mine, "random": rand},
    "theta_scan": {str(t): v for t, v in zip(GT, o_real)},
    "theta_honest_scan": {str(t): v for t, v in zip(GT, o_hon)},
    "beta_scan": {"grid": GB, "score": oB, "cap": caps, "cap_min": cmins, "eaten": eats},
}, open(os.path.join(os.path.dirname(__file__), "..", "data", "exp78_toolcraft.json"),
        "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已写入 data/exp78_toolcraft.json")
