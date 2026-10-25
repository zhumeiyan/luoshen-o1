#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
本体觉 —— 知道自己的身体在哪，而且【闭着眼也知道】
================================================================
★ 它是【唯一一个不需要外界刺激就能工作】的感官
    眼耳鼻皮肤：需要外部能量（光/声/分子/压力）
    ★ 本体觉：身体自己产生信号 —— 肌肉一收缩就有

----------------------------------------------------------------
一、四类感受器（REAL）
----------------------------------------------------------------
    肌梭 muscle spindle     测肌肉【长度】和【长度变化速度】
        Ia 传入（dynamic）  对速度敏感，约 120 m/s 传导（最快）
        II 传入（static）   对静态长度敏感
        ★ 核袋纤维 nuclear bag / 核链纤维 nuclear chain
    高尔基腱器 GTO          测肌肉【张力】，阈值低但饱和高
        Ib 传入，约 100 m/s
    关节感受器              极端角度才响应 —— 只报极限，不报中间
    皮肤拉伸感受器(Ruffini) 关节角度的辅助线索

----------------------------------------------------------------
二、★ α-γ 共同激活（本层最重要）
----------------------------------------------------------------
    问题：肌肉收缩 → 肌梭变短 → 肌梭放松 → 信号消失
          但此时肌肉明明在收缩！
    ★ 解法：α 运动神经元（驱动肌肉）+ γ 运动神经元（驱动肌梭内纤维）
          同时激活 → 肌梭保持张力 → 收缩期间仍有信号
    ★ 这就是【传出副本】的生物学原型
      ★ 与 ★27 皮肤"主动触觉优于被动"是同一个机制
      ★ 与 efference copy / 前庭的"自己动 vs 世界动"是同一个机制

----------------------------------------------------------------
三、★ 位置觉阈值（REAL）
----------------------------------------------------------------
    手指关节  约 1~2°
    肩/肘     约 2~5°
    膝盖      约 3~5°
    ★ 主动运动（自己动）比被动运动（别人掰）阈值【更低】
      ★ 又一次"主动优于被动"

--------------------------------================================
四、力匹配（REAL）
----------------------------------------------------------------
    自觉用力匹配误差 约 5~10%
    ★ 且系统性偏差：感觉到的力 ≈ k × 实际力，k 约 0.9~1.1
    ★ 疲劳时偏差变大

----------------------------------------------------------------
五、★ 与幻觉的关系（phantom limb）
----------------------------------------------------------------
    截肢后仍感觉肢体存在 —— 因为【皮层地图还在】，只是没有输入
    ★ 证明本体觉的"身体图式"是中枢维持的，不是外周给定的
    ★ 镜像盒疗法：给视觉输入填补缺失的本体觉 → 能缓解幻肢痛

----------------------------------------------------------------
六、★ 前庭 + 本体觉：区分"我动"还是"世界动"
----------------------------------------------------------------
    自己转头：前庭有信号 + 颈部本体觉有信号 → 判定"我动"
    世界转（椅子转你）：前庭有信号 + 颈部无信号 → 判定"世界动"
    ★ 只有前庭一个通道时无法区分（转椅眩晕就是这个）
"""
from __future__ import annotations
import numpy as np

# ---------------- 传导速度 REAL ----------------
IA_VELOCITY    = 120.0   # m/s（最快）
II_VELOCITY    = 80.0
IB_VELOCITY    = 100.0   # GTO
SPINAL_LEN_M   = 1.0     # 颈→腰 约 1 m

# ---------------- 位置觉阈值 REAL（度） ----------------
POSITION_THRESHOLD_DEG = {
    "手指": (1.0, 2.0), "手腕": (1.5, 3.0), "肘": (2.0, 5.0),
    "肩": (2.0, 5.0), "膝": (3.0, 5.0), "踝": (2.5, 5.0),
}

# ---------------- 肌梭 REAL ----------------
SPINDLE_DENSITY = 20.0    # 每克肌肉（差异很大）
GTO_THRESHOLD_N = 0.1     # GTO 阈值极低
GTO_SATURATION_N = 50.0
FORCE_MATCH_ERR  = 0.08   # 力匹配误差 8%（REAL 5~10%）
FORCE_GAIN_K     = 1.0


# ================================================================
# 一、肌梭：长度 + 速度
# ================================================================
def spindle_response(length: np.ndarray, velocity: np.ndarray,
                     gamma_drive: float = 0.0,
                     k_static: float = 1.0, k_dynamic: float = 4.0
                     ) -> tuple[np.ndarray, np.ndarray]:
    """★ 肌梭两类传入。

    Ia (dynamic)  ∝ 速度为主 + 少量长度
    II (static)   ∝ 长度为主
    ★ gamma_drive：γ 运动神经元驱动的梭内纤维张力
      ★ 没有它，肌肉一收缩肌梭就松了 → 收缩期间信号消失
    """
    L = np.asarray(length, float)
    V = np.asarray(velocity, float)
    eff = L + gamma_drive        # ★ γ 驱动保持梭内张力
    Ia = k_dynamic * V + 0.3 * eff
    II = k_static * eff
    return Ia, II


def alpha_gamma_demo(n: int = 300) -> dict:
    """★ α-γ 共同激活 vs 只有 α（γ=0）的核心对照。"""
    t = np.linspace(0, 3, n)
    # 肌肉长度：从 1.0 缩短到 0.7（收缩）
    L = 1.0 - 0.3 * (t / 3.0)
    V = np.gradient(L, t)
    # ★ α-γ【共同】激活：γ 驱动与 α 驱动【同步增加】，不是常数
    #   第一版 γ 恒取 0.3 → 起点 eff=1.3，终点 eff=1.0，仍掉 23%
    #   ★ 真正的共同激活是 γ(t) = 缩短量(t)，使梭内纤维长度【恒定】
    gamma_ramp = 0.3 * (t / 3.0)          # 与缩短同步
    Ia_no, II_no = spindle_response(L, V, gamma_drive=0.0)
    Ia_ga, II_ga = spindle_response(L, V, gamma_drive=gamma_ramp)
    return {"t": t, "length": L,
            "Ia_no_gamma": Ia_no, "II_no_gamma": II_no,
            "Ia_with_gamma": Ia_ga, "II_with_gamma": II_ga}


# ================================================================
# 二、GTO：张力
# ================================================================
def gto_response(force_n: np.ndarray, hill_n: float = 2.0) -> np.ndarray:
    """★ GTO：低阈值、宽范围、单调饱和。

    ★ 第一版用 F/(F+K)：永远不饱和（100N→0.667, 200N→0.800, 差 0.133）
      改 Hill 形式 F^n/(F^n+K^n)，n=2 → 饱和更明显
      ★ 50N(饱和点) 仍 = 0.5，与 REAL 一致
    """
    F = np.asarray(force_n, float)
    K = GTO_SATURATION_N
    r = (F ** hill_n) / (F ** hill_n + K ** hill_n)
    return np.where(F > GTO_THRESHOLD_N, r, 0.0)


def gto_vs_spindle(force_n: float, length: float) -> tuple[float, float]:
    """★ GTO 测力，肌梭测长 —— 二者互补，缺一不可。"""
    return float(gto_response(np.array([force_n]))[0]), float(length)


# ================================================================
# 三、传导延迟
# ================================================================
def conduction_delay_ms(velocity_m_s: float, length_m: float = SPINAL_LEN_M) -> float:
    return float(length_m / velocity_m_s * 1000.0)


def reflex_arc_delay_ms(velocity_m_s: float = IA_VELOCITY,
                        length_m: float = SPINAL_LEN_M,
                        synapse_ms: float = 1.0) -> float:
    """★ 单突触反射弧：上行 + 突触 + 下行。"""
    return 2 * conduction_delay_ms(velocity_m_s, length_m) + synapse_ms


def latency_table() -> dict:
    return {
        "牵张反射 Ia（单突触）": reflex_arc_delay_ms(IA_VELOCITY),
        "II 通路（多突触）":     reflex_arc_delay_ms(II_VELOCITY, synapse_ms=3.0),
        "GTO Ib（多突触）":      reflex_arc_delay_ms(IB_VELOCITY, synapse_ms=3.0),
        "视觉 VOR":              80.0,
        "前庭 VOR":              10.0,
    }


# ================================================================
# 四、位置觉
# ================================================================
def position_threshold(joint: str = "手指") -> float:
    lo, hi = POSITION_THRESHOLD_DEG.get(joint, (2.0, 5.0))
    return (lo + hi) / 2.0


def discriminable(delta_deg: float, joint: str = "手指",
                  active: bool = True) -> bool:
    """★ 主动 vs 被动：主动阈值更低（REAL）。"""
    th = position_threshold(joint)
    th = th * 0.6 if active else th
    return delta_deg >= th


def joint_angle_error(noise_deg: float = 1.0, n: int = 1000,
                      rng: np.random.Generator = None) -> tuple[float, float]:
    """位置觉误差分布。返回 (均值偏差, 标准差)。"""
    rng = rng or np.random.default_rng(0)
    e = rng.normal(0.0, noise_deg, n)
    return float(np.mean(e)), float(np.std(e))


# ================================================================
# 五、力匹配
# ================================================================
def force_match(actual_n: float, gain: float = FORCE_GAIN_K,
                err: float = FORCE_MATCH_ERR,
                rng: np.random.Generator = None) -> float:
    """★ 自觉用力匹配：感知力 = gain × 实际力 × (1+噪声)。"""
    rng = rng or np.random.default_rng(0)
    return float(actual_n * gain * (1.0 + rng.normal(0, err)))


def force_match_curve(actual: np.ndarray, gain: float = FORCE_GAIN_K
                      ) -> np.ndarray:
    """★ Weber-Fechner：感知 ∝ 实际力（近似线性，大范围略压缩）。"""
    F = np.asarray(actual, float)
    return gain * F


# ================================================================
# 六、幻肢
# ================================================================
def phantom_limb(cortical_map_present: bool = True,
                 peripheral_input: bool = False) -> str:
    """★ 幻肢：皮层地图在、外周输入无 → 仍感觉存在。"""
    if cortical_map_present and not peripheral_input:
        return "幻肢（phantom limb）"
    if cortical_map_present and peripheral_input:
        return "正常"
    return "缺失"


def mirror_box_effect(visual_feedback: bool) -> float:
    """★ 镜像盒疗法：视觉填补缺失的本体觉 → 缓解幻肢痛。"""
    return 0.4 if visual_feedback else 1.0   # 疼痛指数


# ================================================================
# 七、★ 我动 vs 世界动
# ================================================================
def self_vs_world(vestibular_signal: float, neck_proprio: float,
                  threshold: float = 0.2) -> str:
    """★ 判定：前庭 + 颈部本体觉。

    自己转头：两者都有 → "我动"
    被转（椅子转你）：只有前庭 → "世界动"
    ★ 只有前庭单通道时【无法区分】→ 转椅眩晕
    """
    v = abs(vestibular_signal); p = abs(neck_proprio)
    if v > threshold and p > threshold:
        return "我在动"
    if v > threshold and p <= threshold:
        return "世界在动"
    return "静止"


def vection_conflict(vestibular: float, visual: float) -> float:
    """★ 视觉-前庭冲突 → 晕动症（motion sickness）。
    返回冲突强度。"""
    return float(abs(vestibular - visual))
