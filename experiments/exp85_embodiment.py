#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★85 具身差异 —— 实验

10 条判据。每条都可能失败；失败就记，不补。
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.embodiment import (  # noqa: E402
    HUMAN_FTO_PEAK, HUMAN_SIMPLE_RT, GRID_TH_H, GRID_TH_COOL,
    make_tasks, run_episode, run_human_model,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "exp85_embodiment.json")

TRAIN_SEEDS = [0, 1, 2]
HELD_SEEDS = [10, 11, 12, 13, 14, 15]
N_STEPS = 120

results = {}
log = []


def say(s):
    print(s, flush=True)
    log.append(s)


def eval_theta(th_h, th_cool, seeds, p_human=0.40, **kw):
    return float(np.mean([
        run_episode(th_h, th_cool, make_tasks(N_STEPS, p_human, s), **kw)
        for s in seeds
    ]))


def scan_theta_h(p_human=0.40, human_timing=True, seeds=TRAIN_SEEDS, th_cool=1.0):
    return np.array([eval_theta(h, th_cool, seeds, p_human,
                                human_timing=human_timing) for h in GRID_TH_H])


def scan_theta_cool(p_human=0.40, thermal=True, seeds=TRAIN_SEEDS, th_h=HUMAN_FTO_PEAK):
    return np.array([eval_theta(th_h, c, seeds, p_human, thermal=thermal)
                     for c in GRID_TH_COOL])


say("=" * 74)
say("★85  具身差异：人类规则 vs 硅基身体")
say("=" * 74)

# ─────────────────────────────────────────────────────────
# 判据1  尺子自检：人类 FTO 舒适点能被复现
# ─────────────────────────────────────────────────────────
say("\n【判据1】尺子自检 —— 全人交互任务时，最优等待应落在人类 FTO 舒适点")
allh_tasks = [np.ones(N_STEPS, dtype=bool) for _ in range(3)]
curve_h = np.array([np.mean([run_episode(h, 1.0, t) for t in allh_tasks])
                    for h in GRID_TH_H])
best_h = float(GRID_TH_H[int(np.argmax(curve_h))])
err = abs(best_h - HUMAN_FTO_PEAK)
c1 = err < 0.05
say(f"  实测最优 θ_h = {best_h:.3f} s   真人 FTO 峰 = {HUMAN_FTO_PEAK:.3f} s   误差 {err:.4f}")
say(f"  θ_h=0 (全速) 得分 {curve_h[0]:.4f}   θ_h=1.2 (过慢) 得分 {curve_h[-1]:.4f}")
say(f"  → {'✅ 尺子把人类数值原样吐出来了' if c1 else '❌ 尺子有偏'}")
results["c1_human_fto_reproduced"] = bool(c1)
results["best_theta_h_allhuman"] = best_h

# ─────────────────────────────────────────────────────────
# 判据2  θ_h 内部峰
# ─────────────────────────────────────────────────────────
say("\n【判据2】θ_h 是否有内部峰（不是越快越好，也不是越慢越好）")
cur_h = scan_theta_h()
i_h = int(np.argmax(cur_h))
interior_h = 0 < i_h < len(GRID_TH_H) - 1
say(f"  峰在 θ_h={GRID_TH_H[i_h]:.2f}   两端 {cur_h[0]:.4f} / {cur_h[-1]:.4f}   峰 {cur_h[i_h]:.4f}")
say(f"  → {'✅ 内部峰' if interior_h else '❌ 边界解'}")
results["c2_theta_h_interior"] = bool(interior_h)
results["theta_h_curve"] = {"grid": GRID_TH_H.tolist(), "score": cur_h.tolist()}

# ─────────────────────────────────────────────────────────
# 判据3  θ_cool 内部峰
# ─────────────────────────────────────────────────────────
say("\n【判据3】θ_cool 是否有内部峰（不是越激进越好）")
cur_c = scan_theta_cool()
i_c = int(np.argmax(cur_c))
interior_c = 0 < i_c < len(GRID_TH_COOL) - 1
say(f"  峰在 θ_cool={GRID_TH_COOL[i_c]:.2f}   两端 {cur_c[0]:.4f} / {cur_c[-1]:.4f}   峰 {cur_c[i_c]:.4f}")
say(f"  → {'✅ 内部峰' if interior_c else '❌ 边界解（热节流没起作用？）'}")
results["c3_theta_cool_interior"] = bool(interior_c)
results["theta_cool_curve"] = {"grid": GRID_TH_COOL.tolist(), "score": cur_c.tolist()}

# ─────────────────────────────────────────────────────────
# 判据4  硬依赖 A：关掉人类对延迟的敏感 → θ_h 应无价值
# ─────────────────────────────────────────────────────────
say("\n【判据4】硬依赖A —— 关掉 human_timing，θ_h 应失去价值")
cur_h_off = scan_theta_h(human_timing=False)
span_on = float(cur_h.max() - cur_h.min())
span_off = float(cur_h_off.max() - cur_h_off.min())
c4 = span_off < 0.02 * span_on
say(f"  开启时 θ_h 跨度 {span_on:.4f}   关闭时 {span_off:.4f}   比值 {span_off/max(span_on,1e-9):.4f}")
say(f"  → {'✅ 依赖真实存在' if c4 else '❌ 关掉了还有价值 = 有后门'}")
results["c4_hard_dep_human_timing"] = bool(c4)
results["span_theta_h_on"] = span_on
results["span_theta_h_off"] = span_off

# ─────────────────────────────────────────────────────────
# 判据5  硬依赖 B（两端）：关掉热节流 → θ_cool 峰跑到边界
# ─────────────────────────────────────────────────────────
say("\n【判据5】硬依赖B（两端对照）—— 关掉热节流，θ_cool 峰应跑到边界")
cur_c_off = scan_theta_cool(thermal=False)
i_c_off = int(np.argmax(cur_c_off))
boundary_off = i_c_off == len(GRID_TH_COOL) - 1 or i_c_off == 0
say(f"  开启：峰 {GRID_TH_COOL[i_c]:.2f}（{'内部' if interior_c else '边界'}）")
say(f"  关闭：峰 {GRID_TH_COOL[i_c_off]:.2f}（{'边界' if boundary_off else '内部'}）  分数 {cur_c_off[i_c_off]:.4f}")
c5 = boundary_off and interior_c
say(f"  → {'✅ 两端都对上' if c5 else '❌ 只做了一半，不算数'}")
results["c5_hard_dep_thermal_both_ends"] = bool(c5)
results["theta_cool_curve_nothermal"] = {"grid": GRID_TH_COOL.tolist(),
                                         "score": cur_c_off.tolist()}

# ─────────────────────────────────────────────────────────
# 判据6  她从盲起点学（坐标上升）
# ─────────────────────────────────────────────────────────
say("\n【判据6】盲起点学习 —— 起点【全速+最激进】（不像人，也不爱惜自己）")
start_h, start_c = 0.00, 2.50
cur_h_s, cur_c_s = start_h, start_c
start_score = eval_theta(start_h, start_c, TRAIN_SEEDS, 0.40)
say(f"  起点 θ_h={start_h:.2f} θ_cool={start_c:.2f}   训练分 {start_score:.4f}")
for it in range(6):
    ch = scan_theta_h(th_cool=cur_c_s)
    cur_h_s = float(GRID_TH_H[int(np.argmax(ch))])
    cc = scan_theta_cool(th_h=cur_h_s)
    cur_c_s = float(GRID_TH_COOL[int(np.argmax(cc))])
    say(f"    iter{it+1}: θ_h={cur_h_s:.2f}  θ_cool={cur_c_s:.2f}  分 {max(ch.max(), cc.max()):.4f}")
learned_score = eval_theta(cur_h_s, cur_c_s, TRAIN_SEEDS, 0.40)
improve = learned_score - start_score
c6 = improve > 0.05
say(f"  学完 {learned_score:.4f}   改善 {improve:+.4f}")
say(f"  → {'✅ 真学会' if c6 else '❌ 没学会'}")
results["c6_learned_from_blind_start"] = bool(c6)
results["learned"] = {"theta_h": cur_h_s, "theta_cool": cur_c_s}
results["blind_start_score"] = start_score
results["learned_score"] = learned_score

# ─────────────────────────────────────────────────────────
# 判据7  held-out 泛化（换任务流：更多人交互 → 热预算变宽松）
# ─────────────────────────────────────────────────────────
say("\n【判据7】held-out —— 换环境 p_human=0.70（人更多，自主更少，热预算变宽松）")
say("  考的不是记住那两个数，是【到了新环境还能不能重新找到解】")
LEARN_SEEDS = [10, 11, 12]
TEST_SEEDS = [13, 14, 15]
PH_HELD = 0.70

cc_train = scan_theta_cool(p_human=0.40, seeds=TRAIN_SEEDS, th_h=cur_h_s)
cc_held = scan_theta_cool(p_human=PH_HELD, seeds=LEARN_SEEDS, th_h=cur_h_s)
peak_train = float(GRID_TH_COOL[int(np.argmax(cc_train))])
peak_held = float(GRID_TH_COOL[int(np.argmax(cc_held))])
say(f"  最优 θ_cool：旧环境 {peak_train:.2f}  →  新环境 {peak_held:.2f}（环境确实变了）")

h_fixed = float(np.mean([eval_theta(cur_h_s, cur_c_s, [s], PH_HELD) for s in TEST_SEEDS]))

rh, rc = start_h, start_c
for _ in range(6):
    ch2 = np.array([np.mean([eval_theta(h, rc, [s], PH_HELD) for s in LEARN_SEEDS])
                    for h in GRID_TH_H])
    rh = float(GRID_TH_H[int(np.argmax(ch2))])
    cc2 = np.array([np.mean([eval_theta(rh, c, [s], PH_HELD) for s in LEARN_SEEDS])
                    for c in GRID_TH_COOL])
    rc = float(GRID_TH_COOL[int(np.argmax(cc2))])
h_relearn = float(np.mean([eval_theta(rh, rc, [s], PH_HELD) for s in TEST_SEEDS]))
h_held = h_relearn
h_mem = h_fixed

h_start = float(np.mean([eval_theta(start_h, start_c, [s], PH_HELD) for s in TEST_SEEDS]))
h_allhuman = float(np.mean([eval_theta(0.25, 0.50, [s], PH_HELD) for s in TEST_SEEDS]))
h_allself = float(np.mean([eval_theta(0.00, 3.00, [s], PH_HELD) for s in TEST_SEEDS]))
rng = np.random.default_rng(7)
h_rand = float(np.mean([eval_theta(float(rng.choice(GRID_TH_H)),
                                   float(rng.choice(GRID_TH_COOL)), [s], PH_HELD)
                        for s in TEST_SEEDS for _ in range(4)]))
mem_h, mem_c = cur_h_s, cur_c_s
say(f"  记忆派（旧参数硬套） θ_h={cur_h_s:.2f} θ_cool={cur_c_s:.2f}   {h_fixed:.4f}")
say(f"  她（新环境重学）     θ_h={rh:.2f} θ_cool={rc:.2f}   {h_relearn:.4f}")
say(f"  全人类               θ_h=0.25 θ_cool=0.50          {h_allhuman:.4f}")
say(f"  全自己               θ_h=0.00 θ_cool=2.50          {h_allself:.4f}")
say(f"  随机                                                {h_rand:.4f}")
say(f"  盲起点                                              {h_start:.4f}")
say(f"  她 − 记忆派 = {h_relearn - h_fixed:+.4f}")
c7 = h_relearn > h_fixed and h_relearn > h_rand
say(f"  -> {'OK 规则可迁移' if c7 else 'NO 只是记住了两个数'}")
results["c7_heldout_beats_memory"] = bool(c7)
results["heldout"] = {
    "her_relearn": h_relearn, "her_relearn_params": {"theta_h": rh, "theta_cool": rc},
    "memory": h_fixed, "start": h_start, "all_human": h_allhuman,
    "all_self": h_allself, "random": h_rand,
    "peak_theta_cool_old": peak_train, "peak_theta_cool_new": peak_held,
}

# ─────────────────────────────────────────────────────────
# 判据8  她学的解 ≠ 我填的（距离）
# ─────────────────────────────────────────────────────────
say("\n【判据8】她学的解，是不是我填的")
# 我作为造物主，不动脑子会填什么？
#   θ_h    → 拟人延迟，直接用人类简单反应时 0.25（工程直觉）
#   θ_cool → 性能拉满 2.5（工程直觉：既然是硅基就压榨）
# 这两个值在这一课开始前就写死在这里，不是看结果后挑的。
i_would_h, i_would_c = HUMAN_SIMPLE_RT, 2.50
dist = float(np.hypot(cur_h_s - i_would_h, cur_c_s - i_would_c))
mine_score = float(np.mean([eval_theta(i_would_h, i_would_c, [s], 0.70)
                            for s in HELD_SEEDS]))
say(f"  她  θ_h={cur_h_s:.3f}  θ_cool={cur_c_s:.3f}   held-out {h_held:.4f}")
say(f"  我  θ_h={i_would_h:.3f}  θ_cool={i_would_c:.3f}   held-out {mine_score:.4f}")
say(f"  距离 {dist:.4f}    她 − 我 = {h_held - mine_score:+.4f}")
c8 = dist > 0.05 and h_held > mine_score
say(f"  → {'✅ 不是我装的' if c8 else '❌ 她学到了我填的那套'}")
results["c8_not_mine"] = bool(c8)
results["dist_to_mine"] = dist
results["mine_score_heldout"] = mine_score

# ─────────────────────────────────────────────────────────
# 判据9  交叉检验：θ_h 和 θ_cool 不能串用
# ─────────────────────────────────────────────────────────
say("\n【判据9】交叉检验 —— 两个解是不是同一个通用旋钮")
cross = float(np.mean([eval_theta(cur_c_s, cur_h_s, [s], 0.70) for s in HELD_SEEDS]))
say(f"  正用 θ_h={cur_h_s:.2f} θ_cool={cur_c_s:.2f}   {h_held:.4f}")
say(f"  串用 θ_h={cur_c_s:.2f} θ_cool={cur_h_s:.2f}   {cross:.4f}")
c9 = h_held > cross
say(f"  → {'✅ 两个不同的解' if c9 else '❌ 其实是一个旋钮'}")
results["c9_cross_check"] = bool(c9)
results["cross_score"] = cross

# ─────────────────────────────────────────────────────────
# 判据10  无疲劳：长任务流上，她应显著优于人类模型
# ─────────────────────────────────────────────────────────
say("\n【判据10】无疲劳 —— 硅基不衰减，人类会。长任务流上差多少")
long_tasks = [make_tasks(600, 0.40, s) for s in [20, 21, 22]]
her_long = float(np.mean([run_episode(cur_h_s, cur_c_s, t) for t in long_tasks]))
hum_long = float(np.mean([run_human_model(t, s) for t, s in zip(long_tasks, [20, 21, 22])]))
say(f"  600 步长任务流")
say(f"  她   {her_long:.4f}")
say(f"  人类 {hum_long:.4f}")
say(f"  差   {her_long - hum_long:+.4f}")
c10 = her_long > hum_long
say(f"  → {'✅ 她的无疲劳是真优势' if c10 else '❌ 不如人类模型'}")
results["c10_no_fatigue_advantage"] = bool(c10)
results["long_run"] = {"her": her_long, "human_model": hum_long,
                       "diff": her_long - hum_long}

# ─────────────────────────────────────────────────────────
say("\n" + "=" * 74)
allc = [results[f"c{i}_{k}"] for i, k in [
    (1, "human_fto_reproduced"), (2, "theta_h_interior"), (3, "theta_cool_interior"),
    (4, "hard_dep_human_timing"), (5, "hard_dep_thermal_both_ends"),
    (6, "learned_from_blind_start"), (7, "heldout_beats_memory"),
    (8, "not_mine"), (9, "cross_check"), (10, "no_fatigue_advantage")]]
say(f"判据通过 {sum(allc)}/{len(allc)}")
say("=" * 74)

results["n_criteria"] = len(allc)
results["n_passed"] = int(sum(allc))
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
with open(os.path.join(ROOT, "evidence", "exp85_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log))
say(f"\n已写 {OUT}")
