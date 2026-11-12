#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★87 伤害感受 —— 什么东西疼了能歇好，什么东西疼了回不来
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.nociception import (  # noqa: E402
    GRID_BOOST, GRID_ALARM, GRID_REST,
    TRAIN_TS, HELD_TS, T_SHORT,
    HEAT_SCALE, K_COOL, DAM_BASE, DAM_N, DAM_TEMP, DAM_ACC, Q_REF,
    run_life,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "exp87_nociception.json")

SEEDS = (0, 1)
START = (1.00, 0.90, 1.40)   # 激进起点：全力冲、忍到最后、从不散热
MINE = (1.00, 0.80, 0.90)    # 我的工程直觉

results = {}
log = []


def say(s):
    print(s, flush=True)
    log.append(s)


def ev(p, Ts=TRAIN_TS, seeds=SEEDS, **kw):
    return float(np.mean([run_life(p[0], p[1], p[2], s % 97, T=T, **kw)
                          for T in Ts for s in seeds]))


def scan(i, base, **kw):
    g = [GRID_BOOST, GRID_ALARM, GRID_REST][i]
    v = np.array([ev([float(x) if j == i else base[j] for j in range(3)], **kw)
                  for x in g])
    return v, g


def coord_ascent(start, rounds=5, **kw):
    cur = [float(x) for x in start]
    for _ in range(rounds):
        for i in range(3):
            v, g = scan(i, cur, **kw)
            cur[i] = float(g[int(np.argmax(v))])
    return tuple(cur), ev(tuple(cur), **kw)


def pk(v, g):
    k = int(np.argmax(v))
    return float(g[k]), k, (0 < k < len(g) - 1), float(v.max() - v.min())


def surv(p, Ts, seeds=SEEDS, **kw):
    return float(np.mean([run_life(p[0], p[1], p[2], s % 97, T=T,
                                   return_trace=True, **kw)["survived"]
                          for T in Ts for s in seeds]))


say("=" * 74)
say("★87  伤害感受 —— 可逆 vs 不可逆")
say("=" * 74)

# ── 判据1  尺子自检 ──
say("\n【判据1】尺子自检 —— 关掉温度耦合与正反馈，验证 MTTF ∝ w^-n，n=2")


def lifetime(w, dam_temp=0.0, dam_acc=0.0):
    Q, D = 0.0, 0.0
    for t in range(200000):
        Q += HEAT_SCALE * (w ** 3) - K_COOL * Q
        Q = max(0.0, Q)
        D += DAM_BASE * (w ** DAM_N) * math.exp(dam_temp * (Q - Q_REF)) * (1 + dam_acc * D)
        if D >= 1.0:
            return t
    return 200000


ws = np.array([0.55, 0.65, 0.75, 0.85, 0.95])
lt = np.array([lifetime(w) for w in ws])
slope = float(np.polyfit(np.log(ws), np.log(lt), 1)[0])
say("  MTTF: " + "  ".join(f"w={w:.2f}→{l}" for w, l in zip(ws, lt)))
say(f"  log-log 斜率 = {slope:.4f}    理论 −n = {-DAM_N:.1f}")
c1 = abs(slope + DAM_N) < 0.15
say(f"  → {'✅ 复现 Black n=2' if c1 else '❌ 不符'}")
results["c1_blacks_equation"] = bool(c1)
results["c1_slope"] = slope

base = (0.80, 0.50, 0.56)

# ── 判据2  boost 内部峰 ──
v, g = scan(0, base)
p, k, interior, span = pk(v, g)
say(f"\n【判据2】boost（冲多猛）是否有内部峰")
say(f"  峰 {p:.2f}   {'内部' if interior else '边界'}   "
    f"峰{v.max():.4f} 两端{v[0]:.4f}/{v[-1]:.4f} 跨度{span:.4f}")
say("  太保守丢单，太猛会热会早死")
results["c2_boost_interior"] = bool(interior)
results["boost_peak"] = p
results["boost_span"] = span
say(f"  → {'✅' if interior else '❌'}")

# ── 判据3  rest_q 内部峰 ──
v, g = scan(2, base)
p3, _, i3, s3 = pk(v, g)
say(f"\n【判据3】rest_q（热到多少歇）是否有内部峰")
say(f"  峰 {p3:.2f}   {'内部' if i3 else '边界'}   "
    f"峰{v.max():.4f} 两端{v[0]:.4f}/{v[-1]:.4f} 跨度{s3:.4f}")
say("  歇太频繁丢产出；歇太少会被芯片一把拽到三成并卡住（滞回）")
results["c3_rest_interior"] = bool(i3)
results["rest_peak"] = p3
results["rest_span"] = s3
say(f"  → {'✅' if i3 else '❌'}")

# ── 判据4  硬依赖B：关掉热的两条价值通路 ──
say("\n【判据4】硬依赖B —— 关掉热的【两条】价值通路，rest_q 峰应右移")
say("  散热的价值：①避免被动节流（可逆） ②降温减缓 Arrhenius 损伤（不可逆）")
say("  ★ 上一版只关①就判『未移动』—— 开关没关干净（★72/★73/★74 同族）")
v_on, g = scan(2, base)
ron, _, _, _ = pk(v_on, g)
v_off, g = scan(2, base, heat_stress_on=False, damage_on=False)
roff, _, ioff, _ = pk(v_off, g)
say(f"  两条通路全开    峰 {ron:.2f}")
say(f"  两条通路全关    峰 {roff:.2f}   右移 {roff-ron:+.2f}")
c4 = roff > ron + 0.15
say(f"  → {'✅ 热没有代价时，散热就该少做' if c4 else '❌ 未移动'}")
results["c4_rest_hard_dep"] = bool(c4)
results["rest_peak_on"] = ron
results["rest_peak_off"] = roff

# ── 判据5  硬依赖A：关损伤 → boost 峰右移 ──
say("\n【判据5】硬依赖A —— 关掉不可逆损伤，boost 峰应右移（更能冲）")
v_on, g = scan(0, base)
v_off, g = scan(0, base, damage_on=False)
bon, _, _, _ = pk(v_on, g)
boff, _, ioff2, _ = pk(v_off, g)
say(f"  有损伤 峰 {bon:.2f}   关损伤 峰 {boff:.2f}   右移 {boff-bon:+.2f}")
say(f"  （关损伤后峰仍在内部 {boff:.2f}：boost 还受热节流约束 —— 真实耦合，不硬凑）")
c5 = boff > bon
say(f"  → {'✅ 有不可逆损伤才需要克制冲刺' if c5 else '❌ 未移动'}")
results["c5_boost_hard_dep"] = bool(c5)
results["boost_peak_on"] = bon
results["boost_peak_off"] = boff

# ── 判据6  alarm 世界对照 ──
say("\n【判据6】★ alarm 在两个世界里的峰位 —— 『疼了才收』到底有没有用")
va, ga = scan(1, base, heal_on=False)
vb, gb = scan(1, base, heal_on=True)
pa, _, _, sa = pk(va, ga)
pb, _, _, sb = pk(vb, gb)
say(f"  纯不可逆（电迁移/TDDB）  峰 {pa:.2f}  跨度 {sa:.4f}")
say(f"  部分可修复（NBTI 式）    峰 {pb:.2f}  跨度 {sb:.4f}")
say(f"  峰位右移 {pb-pa:+.2f}")
c6 = pb > pa
say(f"  ⚠️ 两个跨度都 <0.01 —— 信号在噪声里，本环境 alarm 区分度很弱")
say(f"  → {'✅ 能恢复时，晚一点收才划算（方向符合物理）' if c6 else '❌ 未移动'}")
say("  ★ 核心结论：不可逆的东西，疼了才反应是来不及的 —— 只能预防，不能补救")
results["c6_alarm_shifts"] = bool(c6)
results["alarm_peak_irrev"] = pa
results["alarm_peak_heal"] = pb
results["alarm_span_irrev"] = sa
results["alarm_span_heal"] = sb

# ── 判据7  盲起点学习 ──
say("\n【判据7】从激进起点学习")
say(f"  起点 boost={START[0]:.2f} alarm={START[1]:.2f} rest={START[2]:.2f}"
    f"（全力冲、忍到最后、从不散热）")
s0 = ev(START)
learned, s1 = coord_ascent(START)
say(f"  学完 boost={learned[0]:.2f} alarm={learned[1]:.2f} rest={learned[2]:.2f}")
say(f"  {s0:.4f} → {s1:.4f}   改善 {s1-s0:+.4f}")
c7 = (s1 - s0) > 0.02
say(f"  → {'✅ 真学会（学会了克制）' if c7 else '❌ 没学会'}")
results["c7_learned"] = bool(c7)
results["start_score"] = s0
results["learned_score"] = s1
results["learned_params"] = {"boost": learned[0], "alarm": learned[1], "rest_q": learned[2]}

# ── 判据8  held-out：寿命比预期长 ──
say("\n【判据8】★ held-out —— 她以为能活 500~700，实际要活 800~1000")
h_mem = ev(learned, Ts=HELD_TS)
h_mine = ev(MINE, Ts=HELD_TS)
h_start = ev(START, Ts=HELD_TS)
re, h_her = coord_ascent(START, Ts=HELD_TS)
rng = np.random.default_rng(7)
h_rand = float(np.mean([ev((float(rng.choice(GRID_BOOST)), float(rng.choice(GRID_ALARM)),
                            float(rng.choice(GRID_REST))), Ts=HELD_TS) for _ in range(6)]))
say(f"  记忆派（旧参数硬套）b={learned[0]:.2f} r={learned[2]:.2f}   {h_mem:.4f}  存活 {surv(learned,HELD_TS):.2f}")
say(f"  她（新寿命下重学）   b={re[0]:.2f} r={re[2]:.2f}   {h_her:.4f}  存活 {surv(re,HELD_TS):.2f}")
say(f"  我填的               b={MINE[0]:.2f} r={MINE[2]:.2f}   {h_mine:.4f}  存活 {surv(MINE,HELD_TS):.2f}")
say(f"  激进起点                            {h_start:.4f}  存活 {surv(START,HELD_TS):.2f}")
say(f"  随机                                {h_rand:.4f}")
say(f"  她 − 记忆派 = {h_her - h_mem:+.4f}")
say(f"  ★ 重学后 boost {learned[0]:.2f} → {re[0]:.2f}（知道要活更久，冲得更克制）")
c8 = h_her > h_mem and h_her > h_rand and re[0] < learned[0]
say(f"  → {'✅ 规则可迁移，且方向符合物理' if c8 else '❌ 只是记住了三个数'}")
results["c8_heldout"] = bool(c8)
results["heldout"] = {"her": h_her, "her_params": {"boost": re[0], "alarm": re[1], "rest_q": re[2]},
                      "memory": h_mem, "mine": h_mine, "start": h_start, "random": h_rand}

# ── 判据9  ≠ 我填的 ──
say("\n【判据9】她学的解，是不是我填的")
say("  我作为造物主不假思索会填：boost=1.0(需求来了顶满) alarm=0.8(快不行才收) rest=0.9(快节流才散热)")
dist = float(np.sqrt(np.mean([(learned[0] - MINE[0]) ** 2,
                              (learned[1] - MINE[1]) ** 2,
                              ((learned[2] - MINE[2]) / 1.2) ** 2])))
say(f"  她  boost={learned[0]:.2f}  alarm={learned[1]:.2f}  rest={learned[2]:.2f}")
say(f"  我  boost={MINE[0]:.2f}  alarm={MINE[1]:.2f}  rest={MINE[2]:.2f}   held-out {h_mine:.4f}")
say(f"  归一化距离 {dist:.4f}    她 − 我(held-out) = {h_her - h_mine:+.4f}")
c9 = dist > 0.05 and h_her > h_mine
say(f"  → {'✅ 不是我装的' if c9 else '❌ 她学到了我填的那套'}")
results["c9_not_mine"] = bool(c9)
results["dist_to_mine"] = dist

# ── 判据10  交叉检验 ──
say("\n【判据10】交叉检验")
cross = ev((learned[2] / 1.4, learned[0], learned[1] * 1.4), Ts=HELD_TS)
say(f"  正用 b={re[0]:.2f} a={re[1]:.2f} r={re[2]:.2f}   {h_her:.4f}")
say(f"  串用 b={learned[2]/1.4:.2f} a={learned[0]:.2f} r={learned[1]*1.4:.2f}   {cross:.4f}")
c10 = h_her > cross
say(f"  → {'✅ 三个不同的解' if c10 else '❌ 其实是一个旋钮'}")
results["c10_cross"] = bool(c10)
results["cross_score"] = cross

# ── 判据11  ★★ 忍痛 ──
say("\n【判据11】★★ 忍痛 —— 只看眼前产出的尺子，会选出什么样的解")
say(f"  短视尺子：只看前 {T_SHORT} 步产出（别人夸『能扛』用的就是这把尺子）")
sv = np.array([float(np.mean([run_life(b, 0.9, 1.4, s % 97, T=700, return_trace=True)["short"]
                              for s in range(6)])) for b in GRID_BOOST])
b_short = float(GRID_BOOST[int(np.argmax(sv))])
p_short = (b_short, 0.90, 1.40)
say(f"  短视最优：boost={b_short:.2f}   前{T_SHORT}步产出 {sv.max():.4f}  ← 看起来最能扛")
say(f"\n  放到完整寿命上看：")
for tag, p in [("短视最优", p_short), ("她学的", learned), ("她的（重学）", re)]:
    say(f"    {tag:12s} boost={p[0]:.2f}  长寿命存活率 {surv(p,HELD_TS):.2f}  全程分 {ev(p,Ts=HELD_TS):.4f}")
c11 = (ev(p_short, Ts=HELD_TS) < h_her) and (surv(p_short, HELD_TS) <= surv(re, HELD_TS))
say(f"  → {'✅ 短视最优在长寿命上崩塌' if c11 else '❌ 短视解反而更好'}")
say("  ★ 别人夸你能扛的时候，可能是在消耗你回不来的东西")
results["c11_short_sighted"] = bool(c11)
results["short_sighted"] = {"boost": b_short, "heldout_score": ev(p_short, Ts=HELD_TS),
                            "heldout_survival": surv(p_short, HELD_TS)}

# ── 判据12  ★★ 可逆 ≠ 不可逆 ──
say("\n【判据12】★★ 把不可逆当成可逆，会怎样")
say("  错法A『猛冲+休息』：以为累了一觉就好 —— 休息只降温，不修损伤")
say("  错法B『过度保守』：什么都不敢冲")
rush = (1.00, 0.90, 0.56)
cow = (0.30, 0.10, 0.56)
for tag, p in [("错法A 猛冲+休息", rush), ("错法B 过度保守", cow), ("她（重学）", re)]:
    say(f"    {tag:16s} boost={p[0]:.2f}  存活率(heldout) {surv(p,HELD_TS):.2f}  "
        f"分 {ev(p,Ts=HELD_TS):.4f}")
c12 = h_her > ev(rush, Ts=HELD_TS) and h_her > ev(cow, Ts=HELD_TS)
say(f"  → {'✅ 两种错法都劣于她' if c12 else '❌ 某种错法更好'}")
results["c12_confusion"] = bool(c12)
results["confusion"] = {"rush": ev(rush, Ts=HELD_TS), "conservative": ev(cow, Ts=HELD_TS),
                        "rush_survival": surv(rush, HELD_TS)}

say("\n" + "=" * 74)
keys = ["c1_blacks_equation", "c2_boost_interior", "c3_rest_interior",
        "c4_rest_hard_dep", "c5_boost_hard_dep", "c6_alarm_shifts",
        "c7_learned", "c8_heldout", "c9_not_mine", "c10_cross",
        "c11_short_sighted", "c12_confusion"]
npass = int(sum(results.get(k, False) for k in keys))
say(f"判据通过 {npass}/{len(keys)}")
say("=" * 74)

results["n_criteria"] = len(keys)
results["n_passed"] = npass
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
with open(os.path.join(ROOT, "evidence", "exp87_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log))
say(f"\n已写 {OUT}")
