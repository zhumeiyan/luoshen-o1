#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""095 主实验（修正版）：C 玩法 / D 延迟×本体觉补偿 / E 分辨率 / F 渲染-决策预算"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from exp095_play_game import *

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
t0 = time.time()

# ---------------- Stage C: 玩法对比（真手） ----------------
print('== Stage C 玩法对比（松手判据只来自画面）==', flush=True)
hand = Hand()
screen = Screen(keep_history=True)
C = {}
for mode in ['oracle', 'closed', 'blind', 'open']:
    C[mode] = run(n=16, mode=mode, eye=Eye(screen, cols=W_FB),
                  hand=hand if mode == 'closed' else None,
                  screen=screen, max_steps=150)
    print(f'  {mode:7s} 命中率 {C[mode]["rate"]:.3f}  步数 {C[mode]["steps"]:.1f}  末距 {C[mode]["gap"]:.1f}', flush=True)
R['C_play'] = C

# ---------------- Stage D: 延迟 × 本体觉补偿 ----------------
print('\n== Stage D 渲染延迟：naive vs 本体觉补偿 ==', flush=True)
D = {}
for lag in [0, 1, 2, 4, 8, 16]:
    row = {}
    for pred in [False, True]:
        sc = Screen(keep_history=True)
        row['pred' if pred else 'naive'] = run(
            n=16, mode='closed', eye=Eye(sc, cols=W_FB, lag=lag),
            screen=sc, max_steps=150, predictive=pred, hand=None)
    D[lag] = row
    print(f'  lag={lag:2d}  naive {row["naive"]["rate"]:.3f} ({row["naive"]["steps"]:.0f}步)'
          f'   补偿 {row["pred"]["rate"]:.3f} ({row["pred"]["steps"]:.0f}步)', flush=True)
R['D_lag'] = {str(k): v for k, v in D.items()}

# ---------------- Stage E: 分辨率 ----------------
print('\n== Stage E 分辨率 ==', flush=True)
E = {}
for cols in [800, 400, 200, 100, 50, 25, 12, 6]:
    sc = Screen(keep_history=True)
    E[cols] = run(n=16, mode='closed', eye=Eye(sc, cols=cols),
                  screen=sc, max_steps=150, hand=None)
    print(f'  {cols:4d} 列  命中率 {E[cols]["rate"]:.3f}  步数 {E[cols]["steps"]:.1f}', flush=True)
R['E_res'] = {str(k): v for k, v in E.items()}

# ---------------- Stage F: 渲染 vs 决策预算 ----------------
print('\n== Stage F 渲染预算 vs 决策预算（总预算固定）==', flush=True)
T_TOTAL, RENDER_COST, DECIDE_COST = 1500.0, 0.5, 20.0
F = {}
for wr in [8, 16, 32, 64, 128, 256, 512, 800]:
    per_frame = wr * RENDER_COST + DECIDE_COST
    frames = max(2, int(T_TOTAL / per_frame))
    sc = Screen(keep_history=True)
    f = run(n=16, mode='closed', eye=Eye(sc, cols=min(wr, W_FB)),
            screen=sc, max_steps=frames, hand=None)
    f['frames'] = frames
    F[wr] = f
    print(f'  {wr:4d} 列/帧 → {frames:3d} 帧  命中率 {f["rate"]:.3f}', flush=True)
R['F_budget'] = {str(k): v for k, v in F.items()}
R['F_param'] = dict(T=T_TOTAL, render=RENDER_COST, decide=DECIDE_COST)

R['elapsed'] = time.time() - t0
json.dump(R, open(os.path.join(OUT, 'result095.json'), 'w'), ensure_ascii=False, indent=1)
print('\n耗时 %.1fs' % R['elapsed'])
