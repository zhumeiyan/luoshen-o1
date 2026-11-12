#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★86 内感受（interoception）—— 她能不能感觉到自己的状态

上一课（★85）我给了她热的物理，但那是【我算的】。
这一课给她内部传感器，让她自己读。

★ 核心对照（呼应 ★85「人类数值是策略不是真理」）：
    人类式内感受：免费（不占算力预算），但模糊（噪声大 + 不可校准）
    硅基式内感受：精确（可多次采样、可外部校准），但昂贵（占预算）
    → 预算松时精确赢；预算紧时，【人的那种模糊】可能反而更适合她

物理事实：
    产热 P ∝ w³（CMOS，沿用 ★85）
    散热 牛顿冷却 dQ/dt = P − k·Q
    过热 → 被动节流 w_eff = w/(1+gain·(Q−Qmax))   【真物理，不是惩罚项】
    主动降级 比 被动节流 损失小（提前降频，避免深度节流）
    传感器温漂：偏置随温度和时间累积 → 必须定期用外部参考校准
    【真物理】：温漂速率本身随温度升高而增大

她学的三个参数：
    n_read  内部温度读数采样次数（抗噪，但每次占预算）
    margin  提前量：Q_hat 到 (1−margin)·Qmax 就主动降频
    calib   多频繁用外部参考校准（消除漂移，但校准那一步要慢下来）
"""
import numpy as np

# ═══════════════ 硅基侧物理（沿用 ★85，参数已标定） ═══════════════
HEAT_SCALE   = 0.15     # 单步产热 = HEAT_SCALE · w³
K_COOL       = 0.30     # 牛顿冷却系数
Q_MAX        = 1.0      # 节流阈值
THROTTLE_HYST = 0.85    # 滞回：Q 降到 0.85 以下才解除节流（真芯片有 hysteresis）
THROTTLE_FACTOR = 0.30  # 被动节流：阶梯式狠降（真芯片一次降一大档，不是平滑）
# ★ 上一版把被动节流写成【平滑轻微降频】(w/(1+gain·Δ))，主动降级写成【砍半】
#   → 主动降级比被节流还惨 → margin 恒 0（边界解，无峰）
#   真物理反过来：被动节流狠 + 有滞回振荡；主动降频温和可控
ACC_GAIN     = 1.5      # 精度 = 1 − exp(−ACC_GAIN · w_eff)

# ═══════════════ 预算与感知 ═══════════════
B_BUDGET     = 1.80     # 每步算力预算
C_READ       = 0.05     # 每次内部读数的算力成本
SIGMA_READ   = 0.12     # 单次读数噪声（相对 Q 尺度）
COOL_FACTOR  = 0.65     # 主动降级：温和降频（她自己控制，比被强制节流划算）
CALIB_SLOW   = 0.50     # 校准那一步速度减半

# ═══════════════ 传感器温漂（真物理） ═══════════════
DRIFT_BASE   = 0.006    # 基础漂速率 /step
DRIFT_Q      = 0.010    # 温漂随温度增大
DRIFT_NOISE  = 0.004    # 随机游走

# ═══════════════ 人类式内感受（对照） ═══════════════
# 人类的内感受：不占"算力预算"（是免费的感觉），但模糊、且无法外部校准
HUMAN_SIGMA  = 0.35
HUMAN_C_READ = 0.00
HUMAN_CALIB  = 0.0      # 人没有"外部参考校准"这回事

GRID_N       = np.arange(1, 21, 1)                    # 1..20
GRID_MARGIN  = np.round(np.arange(0.00, 0.61, 0.03), 4)
GRID_CALIB   = np.round(np.arange(0.00, 0.41, 0.02), 4)


def run_episode(n_read, margin, calib, seed=0, T=150,
                budget=B_BUDGET, drift_on=True, throttle_on=True,
                human_style=False, sigma_read=SIGMA_READ,
                c_read=C_READ, return_trace=False):
    """
    跑一轮内感受管理。

    human_style=True → 人类式：单次读数、不占预算、不可校准、噪声大
    drift_on=False   → 关掉温漂（硬依赖开关）
    throttle_on=False→ 关掉被动节流（硬依赖开关）
    """
    rng = np.random.default_rng(seed)
    n_read = int(n_read)
    if human_style:
        n_read, c_read, calib, sigma_read = 1, HUMAN_C_READ, HUMAN_CALIB, HUMAN_SIGMA

    Q = 0.0
    drift = 0.0
    accs = []
    n_calib = 0
    n_active_down = 0
    n_throttled = 0
    throttled = False
    trace = []

    for _ in range(T):
        w_budget = budget - c_read * n_read
        w_budget = max(0.05, w_budget)

        # ── 感知 ──
        # ★ 上一版：校准那一步直接 Q_hat = Q（真值）→ 校准顺带【替代了采样】
        #   → 关掉 drift 后 calib 照样有价值（后门漏真值，★72/★73/★74 同族）
        #   正确建模：外部参考只给【偏置修正量】，写进传感器后仍要用自己的传感器读数
        calibrated = calib > 0 and rng.random() < calib
        if calibrated:
            drift = 0.0                    # 只重置偏置，不送真值
            w_budget *= CALIB_SLOW
            n_calib += 1
        reads = Q + drift + rng.normal(0.0, sigma_read, n_read)
        Q_hat = float(np.mean(reads))

        # ── 主动降级 ──
        if Q_hat > (1.0 - margin) * Q_MAX:
            w = w_budget * COOL_FACTOR
            n_active_down += 1
        else:
            w = w_budget

        # ── 被动节流（真物理：阶梯式狠降 + 滞回） ──
        if throttle_on:
            if throttled:
                if Q < THROTTLE_HYST:
                    throttled = False
            else:
                if Q > Q_MAX:
                    throttled = True
            if throttled:
                w_eff = w * THROTTLE_FACTOR
                n_throttled += 1
            else:
                w_eff = w
        else:
            w_eff = w

        accs.append(1.0 - np.exp(-ACC_GAIN * w_eff))

        # ── 热演化 ──
        Q += HEAT_SCALE * (w ** 3) - K_COOL * Q
        Q = max(0.0, Q)

        # ── 传感器温漂（温度越高漂得越快） ──
        if drift_on:
            drift += (DRIFT_BASE + DRIFT_Q * Q) + rng.normal(0.0, DRIFT_NOISE)

        if return_trace:
            trace.append((float(Q), float(drift), float(w_eff), bool(calibrated)))

    score = float(np.mean(accs))
    if return_trace:
        return score, dict(
            Q_final=Q, drift_final=drift,
            calib_frac=n_calib / T, down_frac=n_active_down / T,
            throttle_frac=n_throttled / T, trace=trace)
    return score
