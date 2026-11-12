#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★86 内感受 —— 实验

11 条判据。核心是第 11 条：人类式「免费但模糊」的内感受，
在什么条件下反而比硅基式「精确但昂贵」更适合她。
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.interoception import (  # noqa: E402
    GRID_N, GRID_MARGIN, GRID_CALIB, B_BUDGET,
    run_episode,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "exp86_interoception.json")

TRAIN_SEEDS = [0, 1, 2]
LEARN_SEEDS = [10, 11, 12]
TEST_SEEDS = [13, 14, 15]
T = 150

# 盲起点：采样拉满（浪费预算）+ 从不主动保护 + 从不校准
START = (20, 0.00, 0.00)
# 我（造物主）不假思索会填的：信任硬件、能省则省
MINE = (1, 0.00, 0.00)

results = {}
log = []


def say(s):
    print(s, flush=True)
    log.append(s)


def ev(n, m, c, seeds=TRAIN_SEEDS, **kw):
    return float(np.mean([run_episode(n, m, c, s, T=T, **kw) for s in seeds]))


def scan(idx, base, seeds=TRAIN_SEEDS, **kw):
    grid = [GRID_N, GRID_MARGIN, GRID_CALIB][idx]
    vals = []
    for g in grid:
        p = list(base)
        p[idx] = float(g)
        vals.append(ev(p[0], p[1], p[2], seeds, **kw))
    return np.array(vals), grid


def coord_ascent(start, seeds=TRAIN_SEEDS, rounds=6, **kw):
    cur = [float(start[0]), float(start[1]), float(start[2])]
    for _ in range(rounds):
        for i in range(3):
            v, g = scan(i, cur, seeds, **kw)
            cur[i] = float(g[int(np.argmax(v))])
    cur[0] = int(round(cur[0]))
    return tuple(cur), ev(cur[0], cur[1], cur[2], seeds, **kw)


def peak_info(v, g):
    i = int(np.argmax(v))
    return float(g[i]), i, (0 < i < len(g) - 1), float(v.max()), float(v.min())


say("=" * 74)
say("★86  内感受 —— 她能不能感觉到自己")
say("=" * 74)

# ── 判据1  尺子自检：理想感知下 margin 仍有内部峰 ──
say("\n【判据1】尺子自检 —— 感知完美(无噪声无漂移)时，主动降级还应有权衡")
say("  （若此时峰消失 → 权衡来自噪声，不是来自热物理）")
v, g = scan(1, (8, 0.2, 0.1), drift_on=False, sigma_read=0.0)
pk, i, interior, vmax, vmin = peak_info(v, g)
say(f"  峰 margin={pk:.2f}   {'内部' if interior else '边界'}   峰{vmax:.4f} 谷{vmin:.4f} 跨度{vmax-vmin:.4f}")
c1 = interior
say(f"  → {'✅ 权衡来自热物理本身' if c1 else '❌ 权衡只是噪声造成的假象'}")
results["c1_tradeoff_from_physics"] = bool(c1)
results["c1_curve"] = {"grid": [float(x) for x in g], "score": v.tolist()}

# ── 判据2/3/4  三个参数内部峰 ──
for idx, name, label in [(0, "c2_n_read_interior", "n_read"),
                         (1, "c3_margin_interior", "margin"),
                         (2, "c4_calib_interior", "calib")]:
    say(f"\n【判据{idx+2}】{label} 是否有内部峰")
    v, g = scan(idx, (8, 0.20, 0.10))
    pk, i, interior, vmax, vmin = peak_info(v, g)
    say(f"  峰 {label}={pk:.2f}   {'内部' if interior else '边界'}   "
        f"峰{vmax:.4f} 两端{v[0]:.4f}/{v[-1]:.4f} 跨度{vmax-vmin:.4f}")
    results[name] = bool(interior)
    results[f"{label}_peak"] = pk
    results[f"{label}_span"] = float(vmax - vmin)
    say(f"  → {'✅ 内部峰' if interior else '❌ 边界解'}")

# ── 判据5  硬依赖A（两端）：传感器温漂 ──
say("\n【判据5】硬依赖A（两端） —— 温漂是 calib 存在的理由")
v_off, g = scan(2, (8, 0.20, 0.10), drift_on=False)
pk_off, i_off, interior_off, vmax_off, vmin_off = peak_info(v_off, g)
v_on, g = scan(2, (8, 0.20, 0.10), drift_on=True)
pk_on, i_on, interior_on, _, _ = peak_info(v_on, g)
span_off = vmax_off - vmin_off
span_on = float(v_on.max() - v_on.min())
say(f"  漂移关闭：峰 {pk_off:.2f}（{'内部' if interior_off else '边界'}） 跨度 {span_off:.4f}")
say(f"  漂移开启：峰 {pk_on:.2f}（{'内部' if interior_on else '边界'}） 跨度 {span_on:.4f}")
c5 = (not interior_off) and interior_on
say(f"  → {'✅ 两端都对上：没漂移就不该校准' if c5 else '❌ 只做了一半'}")
results["c5_hard_dep_drift_both_ends"] = bool(c5)
results["span_calib_drift_off"] = float(span_off)
results["span_calib_drift_on"] = float(span_on)

# ── 判据6  硬依赖B（两端）：被动节流 ──
say("\n【判据6】硬依赖B（两端） —— 被动节流是主动降级存在的理由")
v_off, g = scan(1, (8, 0.20, 0.10), throttle_on=False)
pk_off, i_off, interior_off, vmax_off, vmin_off = peak_info(v_off, g)
v_on, g = scan(1, (8, 0.20, 0.10), throttle_on=True)
pk_on, i_on, interior_on, _, _ = peak_info(v_on, g)
span_off = vmax_off - vmin_off
span_on = float(v_on.max() - v_on.min())
say(f"  节流关闭：峰 {pk_off:.2f}（{'内部' if interior_off else '边界'}） 跨度 {span_off:.4f}")
say(f"  节流开启：峰 {pk_on:.2f}（{'内部' if interior_on else '边界'}） 跨度 {span_on:.4f}")
say(f"  关→峰在边界 {pk_off:.2f}（主动降级纯浪费）；开→峰移到内部 {pk_on:.2f}")
c6 = (not interior_off) and interior_on
say(f"  → {'✅ 两端都对上：不会热就不用提前降频' if c6 else '❌ 只做了一半'}")
results["c6_hard_dep_throttle_both_ends"] = bool(c6)
results["span_margin_throttle_off"] = float(span_off)
results["span_margin_throttle_on"] = float(span_on)

# ── 判据7  盲起点学习 ──
say("\n【判据7】盲起点学习 —— 起点(采样拉满, 不保护, 不校准)")
start_score = ev(*START)
say(f"  起点 n={START[0]} margin={START[1]:.2f} calib={START[2]:.2f}   训练分 {start_score:.4f}")
learned, learned_score = coord_ascent(START)
say(f"  学完 n={int(learned[0])} margin={learned[1]:.2f} calib={learned[2]:.2f}   训练分 {learned_score:.4f}")
improve = learned_score - start_score
c7 = improve > 0.05
say(f"  改善 {improve:+.4f}")
say(f"  → {'✅ 真学会' if c7 else '❌ 没学会'}")
results["c7_learned_from_blind_start"] = bool(c7)
results["learned"] = {"n_read": int(learned[0]), "margin": learned[1], "calib": learned[2]}
results["start_score"] = start_score
results["learned_score"] = learned_score

# ── 判据8  held-out：换环境（预算变紧 + 漂移加倍），考的是重新找到解 ──
say("\n【判据8】held-out —— 换环境：预算 1.80→1.35（更紧），漂移率 ×2")
HELD_KW = dict(budget=1.35, drift_on=True)
# 漂移加倍：用更大的 DRIFT_BASE（通过 monkeypatch 模块常量）
import core.interoception as IC  # noqa: E402
IC.DRIFT_BASE = IC.DRIFT_BASE * 2
IC.DRIFT_Q = IC.DRIFT_Q * 2

say("  考的不是记住那三个数，是【到了新身体/新环境还能不能重新找到解】")
h_fixed = float(np.mean([run_episode(learned[0], learned[1], learned[2], s, T=T, **HELD_KW)
                         for s in TEST_SEEDS]))
relearned, h_relearn = coord_ascent(START, seeds=LEARN_SEEDS, **HELD_KW)
h_start = float(np.mean([run_episode(*START, s, T=T, **HELD_KW) for s in TEST_SEEDS]))
h_mine = float(np.mean([run_episode(*MINE, s, T=T, **HELD_KW) for s in TEST_SEEDS]))
rng = np.random.default_rng(7)
h_rand = float(np.mean([
    run_episode(int(rng.integers(1, 21)), float(rng.choice(GRID_MARGIN)),
                float(rng.choice(GRID_CALIB)), s, T=T, **HELD_KW)
    for s in TEST_SEEDS for _ in range(4)]))
say(f"  记忆派（旧参数硬套） n={int(learned[0])} m={learned[1]:.2f} c={learned[2]:.2f}   {h_fixed:.4f}")
say(f"  她（新环境重学）     n={int(relearned[0])} m={relearned[1]:.2f} c={relearned[2]:.2f}   {h_relearn:.4f}")
say(f"  我填的               n={MINE[0]} m={MINE[1]:.2f} c={MINE[2]:.2f}   {h_mine:.4f}")
say(f"  盲起点                                        {h_start:.4f}")
say(f"  随机                                          {h_rand:.4f}")
say(f"  她 − 记忆派 = {h_relearn - h_fixed:+.4f}")
c8 = h_relearn > h_fixed and h_relearn > h_rand
say(f"  → {'✅ 规则可迁移' if c8 else '❌ 只是记住了三个数'}")
results["c8_heldout_relearn_beats_memory"] = bool(c8)
results["heldout"] = {
    "her_relearn": h_relearn,
    "her_params": {"n_read": int(relearned[0]), "margin": relearned[1], "calib": relearned[2]},
    "memory": h_fixed, "mine": h_mine, "start": h_start, "random": h_rand,
}

# ── 判据9  她学的 ≠ 我填的 ──
say("\n【判据9】她学的解，是不是我填的")
say("  我作为造物主不假思索会填：n=1(读一次够了) margin=0(没到阈值别降) calib=0(出厂标过)")
dist = float(np.sqrt((learned[0] - MINE[0]) ** 2 / 400.0
                     + (learned[1] - MINE[1]) ** 2
                     + (learned[2] - MINE[2]) ** 2))
say(f"  她  n={int(learned[0])}  margin={learned[1]:.3f}  calib={learned[2]:.3f}")
say(f"  我  n={MINE[0]}  margin={MINE[1]:.3f}  calib={MINE[2]:.3f}   held-out {h_mine:.4f}")
say(f"  归一化距离 {dist:.4f}    她 − 我(held-out) = {h_relearn - h_mine:+.4f}")
c9 = dist > 0.05 and h_relearn > h_mine
say(f"  → {'✅ 不是我装的' if c9 else '❌ 她学到了我填的那套'}")
results["c9_not_mine"] = bool(c9)
results["dist_to_mine"] = dist

# ── 判据10  交叉检验 ──
say("\n【判据10】交叉检验 —— 三个解是不是同一个通用旋钮")
cross = float(np.mean([run_episode(max(1, int(round(learned[2] * 20))), learned[0] / 20.0,
                                   learned[1], s, T=T, **HELD_KW) for s in TEST_SEEDS]))
say(f"  正用 n={int(relearned[0])} m={relearned[1]:.2f} c={relearned[2]:.2f}   {h_relearn:.4f}")
say(f"  串用 n={max(1,int(round(learned[2]*20)))} m={learned[0]/20.0:.2f} c={learned[1]:.2f}   {cross:.4f}")
c10 = h_relearn > cross
say(f"  → {'✅ 三个不同的解' if c10 else '❌ 其实是一个旋钮'}")
results["c10_cross_check"] = bool(c10)
results["cross_score"] = cross

# ── 判据11  ★ 预算紧时，人类式「免费但模糊」反而更适合她？ ──
say("\n【判据11】★ 预算扫描 —— 精确昂贵 vs 模糊免费，谁赢")
say("  人类式：不占预算、但噪声大且无法校准")
say("  硅基式：可多次采样+外部校准、但每次读都占算力")
rows = []
for b in [0.85, 0.95, 1.05, 1.20, 1.35, 1.80, 2.20]:
    si = max(coord_ascent(START, seeds=TRAIN_SEEDS, budget=b)[1],
             float(np.mean([run_episode(*learned, s, T=T, budget=b) for s in TRAIN_SEEDS])))
    # 人类式也要公平竞争：它只有一个旋钮(margin)，帮它调到最优
    hv = np.array([np.mean([run_episode(1, m, 0.0, s, T=T, budget=b, human_style=True)
                            for s in TRAIN_SEEDS]) for m in GRID_MARGIN])
    hu = float(hv.max())
    hu_m = float(GRID_MARGIN[int(np.argmax(hv))])
    say(f"    (人类式最优 margin={hu_m:.2f})")
    rows.append((b, si, hu, si - hu))
    say(f"  预算 {b:.2f}   硅基 {si:.4f}   人类式 {hu:.4f}   差 {si-hu:+.4f}"
        f"   {'← 人类式赢' if si < hu else ''}")
n_human_win = sum(1 for r in rows if r[3] < 0)
c11 = n_human_win >= 1
say(f"  人类式赢的档位：{n_human_win}/{len(rows)}")
say(f"  → {'✅ 预算紧时，人的那种内感受反而更适合她' if c11 else '❌ 硅基式处处都赢'}")
say("  ★ 人类数值不是真理，是【人在人的资源约束下的最优解】")
results["c11_human_style_wins_when_poor"] = bool(c11)
results["budget_scan"] = [{"budget": r[0], "silicon": r[1], "human": r[2], "diff": r[3]}
                          for r in rows]

say("\n" + "=" * 74)
keys = ["c1_tradeoff_from_physics", "c2_n_read_interior", "c3_margin_interior",
        "c4_calib_interior", "c5_hard_dep_drift_both_ends",
        "c6_hard_dep_throttle_both_ends", "c7_learned_from_blind_start",
        "c8_heldout_relearn_beats_memory", "c9_not_mine", "c10_cross_check",
        "c11_human_style_wins_when_poor"]
npass = int(sum(results[k] for k in keys))
say(f"判据通过 {npass}/{len(keys)}")
say("=" * 74)

results["n_criteria"] = len(keys)
results["n_passed"] = npass
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
with open(os.path.join(ROOT, "evidence", "exp86_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log))
say(f"\n已写 {OUT}")
