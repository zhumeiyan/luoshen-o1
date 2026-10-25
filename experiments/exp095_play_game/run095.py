#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""095 主实验：玩游戏。Stage C 玩法 / D 卡顿 / E 分辨率 / F 渲染-决策预算"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from exp095_play_game import *

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
t0 = time.time()

hand = Hand()
print('hand ok =', hand.ok)

# ---------------- Stage C: 玩法对比（真手） ----------------
print('\n== Stage C 玩法对比 ==')
screen = Screen(keep_history=True)
C = {}
for mode in ['oracle', 'closed', 'blind', 'open']:
    C[mode] = run(n=12, mode=mode, eye=Eye(screen, cols=W_FB),
                  hand=hand if mode != 'oracle' else None,
                  screen=screen, max_steps=150)
    print(f'  {mode:7s} 命中率 {C[mode]["rate"]:.3f}  平均步数 {C[mode]["steps"]:.1f}  末距 {C[mode]["gap"]:.1f}')
R['C_play'] = C

# ---------------- Stage D: 卡顿（渲染延迟 lag 帧） ----------------
print('\n== Stage D 卡顿扫描 ==')
D = {}
for lag in [0, 1, 2, 4, 8, 16, 32]:
    sc = Screen(keep_history=True)
    D[lag] = run(n=12, mode='closed', eye=Eye(sc, cols=W_FB, lag=lag),
                 screen=sc, max_steps=150, hand=None)
    print(f'  lag={lag:3d} 帧  命中率 {D[lag]["rate"]:.3f}  步数 {D[lag]["steps"]:.1f}')
R['D_lag'] = {str(k): v for k, v in D.items()}

# ---------------- Stage E: 分辨率（看得清不清） ----------------
print('\n== Stage E 分辨率扫描 ==')
E = {}
for cols in [800, 400, 200, 100, 50, 25, 12, 6]:
    sc = Screen(keep_history=True)
    E[cols] = run(n=12, mode='closed', eye=Eye(sc, cols=cols),
                  screen=sc, max_steps=150, hand=None)
    print(f'  分辨率 {cols:4d} 列  命中率 {E[cols]["rate"]:.3f}  步数 {E[cols]["steps"]:.1f}')
R['E_res'] = {str(k): v for k, v in E.items()}

# ---------------- Stage F: 渲染 vs 决策的预算权衡 ----------------
# 总时间预算固定；渲染耗时 ∝ 像素列数，决策每帧固定开销。
# 画质越高 → 每帧越贵 → 帧数越少（越卡）。这就是游戏里"画质 vs 帧率"。
print('\n== Stage F 渲染预算 vs 决策预算 ==')
T_TOTAL, RENDER_COST, DECIDE_COST = 4000.0, 0.5, 20.0
F = {}
for wr in [8, 16, 32, 64, 128, 256, 512, 800]:
    per_frame = wr * RENDER_COST + DECIDE_COST
    budget_steps = max(2, int(T_TOTAL / per_frame))
    sc = Screen(keep_history=True)
    # 渲染分辨率 = eye 能看到的列数（画质）
    f = run(n=12, mode='closed', eye=Eye(sc, cols=min(wr, W_FB)),
            screen=sc, max_steps=budget_steps, hand=None)
    f['frames'] = budget_steps
    F[wr] = f
    print(f'  渲染 {wr:4d} 列/帧  可用帧数 {budget_steps:4d}  命中率 {f["rate"]:.3f}')
R['F_budget'] = {str(k): v for k, v in F.items()}

R['elapsed'] = time.time() - t0
json.dump(R, open(os.path.join(OUT, 'result095.json'), 'w'), ensure_ascii=False, indent=1)
print('\n耗时 %.1fs' % R['elapsed'])
