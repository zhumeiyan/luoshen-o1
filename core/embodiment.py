#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★85 具身差异 —— 她的身体是硅基的，人类的规则是策略，不是真理

设计原则（来自用户）：
  "人类数值是她了解人类的规则和策略而已"
  → 所以人交互任务上，她要【迁就人类的物理】
  → 自主任务上，她该【用自己的物理】

两组物理事实，全部可查：

【人类侧】（文献真值）
  FTO 话轮间隔中位 0~250ms，峰值约 150ms（过快=打断，过慢=迟疑）
  简单反应时 ~250ms
  持续作业有 vigilance decrement（警觉衰退）+ 疲劳

【硅基侧】（器件物理）
  基础延迟 ~1ms（时钟 ns 级，这里取保守值）
  动态功耗 P ∝ C·V²·f，V ∝ f  →  P ∝ f³   （CMOS，真物理）
  散热：牛顿冷却 dQ/dt = P − k(Q − Q_amb)
  过热 → 降频（thermal throttling，真物理，不是惩罚项）
  【无疲劳】：不衰减，可连续跑

她要学的两个参数：
  θ_h    : 人交互任务上额外等待多久（0=全速，人跟不上）
  θ_cool : 自主任务投入多激进（越激进越快越准，但会热节流）

对照四种活法：
  全人类  θ_h=0.25, θ_cool=0.5   （处处迁就人，浪费自己）
  全自己  θ_h=0.00, θ_cool=2.5   （全速，人跟不上 + 烧穿）
  记忆派  训练集最优硬套
  她      自己学
"""
import numpy as np

# ═══════════════ 人类侧真值（文献） ═══════════════
HUMAN_FTO_PEAK   = 0.15      # s，话轮间隔最舒适点（FTO 中位区间 0~250ms 的峰）
HUMAN_FTO_SIGMA  = 0.12      # s，容忍宽度
HUMAN_SIMPLE_RT  = 0.25      # s，简单反应时
HUMAN_FATIGUE_K  = 0.0060    # 每步累积的疲劳（vigilance decrement）
HUMAN_RECOVER    = 0.0040    # 每步恢复（必须 < 累积，否则永远不会累）

# ═══════════════ 硅基侧物理（器件） ═══════════════
SI_BASE_LATENCY  = 0.001     # s，基础延迟（保守：1ms；真实时钟更快）
SI_THERMAL_CAP   = 1.0
SI_HEAT_SCALE    = 0.15      # 单步产热缩放到热容（热容大 → 单步温升小）
SI_K_COOL        = 0.60      # 散热系数（牛顿冷却）
# ★ 上面两个数决定 Q 是被【平均负载】还是被【单步峰值】决定。
#   旧版 K=1.20 且无缩放 → 一步就跳到阈值 → 最优解与任务比例无关（假环境）
SI_Q_THROTTLE    = 1.0       # 节流阈值
SI_THROTTLE_GAIN = 2.0       # 平滑节流强度
SI_ACC_GAIN      = 1.5       # 精度 = 1 − exp(−SI_ACC_GAIN · w_eff)


def make_tasks(n=120, p_human=0.40, seed=0):
    """生成任务流：True=人交互任务，False=自主任务"""
    rng = np.random.default_rng(seed)
    return rng.random(n) < p_human


def _human_score(latency):
    """人交互任务得分：高斯窗，中心是人类 FTO 舒适点"""
    return float(np.exp(-(((latency - HUMAN_FTO_PEAK) / HUMAN_FTO_SIGMA) ** 2)))


def run_episode(theta_h, theta_cool, tasks,
                human_timing=True, thermal=True,
                return_trace=False):
    """
    跑一轮任务流。

    theta_h   : 人交互任务额外等待秒数
    theta_cool: 自主任务投入（0.2~2.5）
    human_timing=False → 人交互任务只看精度不看延迟（硬依赖开关）
    thermal=False      → 关闭热节流（硬依赖开关）
    """
    Q = 0.0
    human_scores, auto_scores = [], []
    throttled_steps = 0
    trace = []

    for is_human in tasks:
        if is_human:
            # 人交互：延迟 = 基础延迟 + 她刻意等待
            lat = SI_BASE_LATENCY + max(0.0, theta_h)
            # 人类侧疲劳只作用于"人类模型"对照，她自己不疲劳
            s = _human_score(lat) if human_timing else 1.0
            human_scores.append(s)
            # 人交互任务负载很轻
            Q += SI_HEAT_SCALE * (0.2 ** 3) - SI_K_COOL * Q
            Q = max(0.0, Q)
        else:
            # 自主任务：投入决定速度/精度，产热 ∝ w³
            w = max(0.0, theta_cool)
            if thermal:
                over = max(0.0, Q - SI_Q_THROTTLE)
                w_eff = w / (1.0 + SI_THROTTLE_GAIN * over)
            else:
                w_eff = w
            if thermal and w_eff < w * 0.95:
                throttled_steps += 1
            acc = 1.0 - np.exp(-SI_ACC_GAIN * w_eff)
            auto_scores.append(acc)
            Q += SI_HEAT_SCALE * (w ** 3) - SI_K_COOL * Q
            Q = max(0.0, Q)

        if return_trace:
            trace.append((bool(is_human), float(Q)))

    hs = float(np.mean(human_scores)) if human_scores else 0.0
    as_ = float(np.mean(auto_scores)) if auto_scores else 0.0
    n = len(tasks)
    ph = np.mean(tasks)
    score = ph * hs + (1 - ph) * as_
    # 节流本身是物理事实（降频已体现在 acc 里），额外只记一次轻微惩罚
    score -= 0.02 * (throttled_steps / n)

    if return_trace:
        return score, dict(human=hs, auto=as_, Q_final=Q,
                           throttle_frac=throttled_steps / n, trace=trace)
    return score


def run_human_model(tasks, seed=0):
    """
    人类对照模型：反应时更慢、有疲劳累积、无热问题。
    用于验证【她的无疲劳是真实优势】（判据10）
    """
    rng = np.random.default_rng(seed)
    fatigue = 0.0
    scores = []
    for is_human in tasks:
        if is_human:
            lat = HUMAN_SIMPLE_RT * (1.0 + fatigue) + rng.normal(0, 0.02)
            lat = max(0.0, lat)
            scores.append(_human_score(lat))
        else:
            acc = (1.0 - np.exp(-SI_ACC_GAIN * 0.8)) * (1.0 - fatigue)
            scores.append(max(0.0, acc))
        # 净累积必须为正（持续作业会累），且夹在 [0, 上限]
        # 上一版恢复期望 > 累积期望 → fatigue 变负 → 越跑越强，是个 bug
        fatigue = float(np.clip(fatigue + HUMAN_FATIGUE_K
                                - HUMAN_RECOVER * rng.random(), 0.0, 0.6))
    return float(np.mean(scores))


GRID_TH_H    = np.round(np.arange(0.00, 1.21, 0.02), 4)
GRID_TH_COOL = np.round(np.arange(0.20, 3.01, 0.05), 4)
