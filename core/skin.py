#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
皮肤 —— 全身最大的感觉器官，而且是【主动探索】的
================================================================
★ 与眼耳鼻的根本不同（本层要证明）：
    眼耳鼻：远端感受器 —— 接收远处的光/声/分子
    ★ 皮肤：近端感受器 —— 必须【接触】才有信号
    ★ 所以皮肤天然是【主动】的：不动手就摸不出纹理
      ★ 这与"静止时运动视差消失"是同一个道理的另一面

----------------------------------------------------------------
一、四类机械感受器（REAL）
----------------------------------------------------------------
    Merkel    SA1  慢适应  6~15 Hz   小感受野(2~3mm)   → 形状、纹理、边缘
    Ruffini   SA2  慢适应  ——          大感受野(10~15mm) → 皮肤拉伸、手形
    Meissner  RA1  快适应 10~50 Hz   小感受野          → 滑移、低频颤动
    Pacini    RA2  快适应 70~1000Hz  大感受野          → 高频振动、工具事件

    指尖密度 Merkel 约 100/cm²，Meissner 约 25/cm²  → 两点辨别阈约 1~2 mm
    掌心/前臂 两点辨别阈 8~40 mm  ★ 差 20 倍

----------------------------------------------------------------
二、两点辨别（REAL）
----------------------------------------------------------------
    指尖 1~2 mm    手掌 8~12 mm    前臂 30~40 mm    背部 40~70 mm
    ★ 决定因素：感受器密度 + 感受野大小 + 皮层放大

----------------------------------------------------------------
三、★ 时间/空间频率编码纹理（REAL）
----------------------------------------------------------------
    粗纹理（空间周期 > 1 mm）→ SA1(Merkel) 编码【空间】图案
    细纹理（< 100 μm，手指摸不出）→ RA(Pacini) 编码扫过产生的【振动】
    ★ 关键：细纹理靠【主动扫动】产生的振动频率编码
      f = v / λ    扫描速度 / 空间周期
      ★ 手不动 → 没有振动 → 细纹理完全消失
    Pacini 最敏感 200~300 Hz（REAL 70~1000Hz 峰在 200~300）

----------------------------------------------------------------
四、★ 适应曲线（REAL）
----------------------------------------------------------------
    RA(Meissner/Pacini)  只对【变化】响应 —— 恒定压力几乎不响应
    SA(Merkel/Ruffini)   持续响应，但会衰减到某个静息水平
    ★ 这就是"穿上衣服后立刻感觉不到衣服"的机制

----------------------------------------------------------------
五、温度与痛觉（REAL）
----------------------------------------------------------------
    冷感受器 TRPM8  < 30°C 峰值约 25°C
    热感受器 TRPV1  > 43°C（TRPV3/4 覆盖温热 30~43）
    ★ 热错觉 paradox：44°C + 交替冷温栅 → 感知为【灼烧冷痛】
    机械痛阈值 约 5~10 mN·尖锐  /  伤害性 > 20 mN
    ★ 痛觉没有适应（保护性）—— 这是与触觉的关键区别

----------------------------------------------------------------
六、★ 主动触觉 vs 被动触觉（核心对照）
----------------------------------------------------------------
    被动：刺激压到静止的手指上
    主动：自己伸手去摸
    ★ REAL：主动触觉的空间辨别【优于】被动约 2 倍
      机制：传出副本（efference copy）+ 运动指令提供额外信息
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 常数 ----------------
MERKEL_DENSITY   = 100.0    # 指尖 /cm²
MEISSNER_DENSITY = 25.0     # 指尖 /cm²
MERKEL_FIELD_MM  = 2.5      # 感受野直径
RUFFINI_FIELD_MM = 12.5
PACINI_F_MIN     = 70.0
PACINI_F_PEAK    = 250.0    # REAL 最敏感 200~300 Hz
PACINI_F_MAX     = 1000.0
MEISSNER_F_RANGE = (10.0, 50.0)
MERKEL_F_RANGE   = (6.0, 15.0)

TWO_POINT_MM = {
    "指尖": (1.0, 2.0), "手掌": (8.0, 12.0), "前臂": (30.0, 40.0),
    "背部": (40.0, 70.0), "大腿": (30.0, 45.0),
}
ADAPT_RA_TAU   = 0.03       # 快适应时间常数 ~30 ms
ADAPT_SA_TAU   = 4.0        # 慢适应 ~4 s
ADAPT_SA_FLOOR = 0.25       # 慢适应衰减到 25% 静息

COLD_PEAK_C    = 25.0       # TRPM8 峰值
HEAT_THRESH_C  = 43.0       # TRPV1
INDIFFERENT_C  = 32.0       # 中性温度
PAIN_MECH_MN   = 20.0       # 伤害性机械阈值 mN
TOUCH_MIN_MN   = 0.5        # 触觉绝对阈


# ================================================================
# 一、感受器响应
# ================================================================
def receptor_response(freq_hz: float, amp: float, kind: str = "RA2") -> float:
    """★ 按类型给出响应强度（带频率选择性）。

    RA2(Pacini)   带通 70~1000 Hz，峰 250 Hz
    RA1(Meissner) 带通 10~50 Hz
    SA1(Merkel)   低通 6~15 Hz
    """
    f = float(freq_hz)
    if kind == "RA2":
        # 对数高斯带通
        c, w = np.log(PACINI_F_PEAK), np.log(PACINI_F_MAX / PACINI_F_PEAK) / 1.8
        g = np.exp(-0.5 * ((np.log(max(f, 1e-6)) - c) / w) ** 2)
        return float(amp * g)
    if kind == "RA1":
        return float(amp * np.exp(-0.5 * ((f - 30.0) / 20.0) ** 2))
    if kind == "SA1":
        return float(amp / (1.0 + (f / 15.0) ** 2))
    return float(amp)


def scan_frequency(speed_mm_s: float, period_um: float) -> float:
    """★ 主动扫过纹理产生的振动频率 f = v / λ。

    ★ 手不动(v=0) → f=0 → RA2 无响应 → 细纹理消失
    """
    lam_mm = period_um / 1000.0
    return float(speed_mm_s / lam_mm) if lam_mm > 0 else 0.0


def texture_encoding(period_um: float, speed_mm_s: float) -> dict:
    """★ 纹理编码：粗→SA1 空间；细→RA2 振动。返回各通道响应。"""
    f = scan_frequency(speed_mm_s, period_um)
    # 空间对比（SA1 需要周期 ≳ 感受野）
    spatial = float(np.exp(-0.5 * ((period_um/1000.0 - MERKEL_FIELD_MM) /
                                   MERKEL_FIELD_MM) ** 2)) if period_um >= 100 else \
              float(np.exp(-0.5*((period_um/1000.0)/MERKEL_FIELD_MM)**2)*0.3)
    return {"freq_hz": f, "SA1_spatial": spatial,
            "RA2_vibration": receptor_response(f, 1.0, "RA2"),
            "RA1_vibration": receptor_response(f, 1.0, "RA1")}


# ================================================================
# 二、两点辨别
# ================================================================
def two_point_threshold(recep_density_per_cm2: float) -> float:
    """★ 两点辨别阈 ≈ 感受野直径 ≈ 1/√密度（mm）。

    ★ 密度↑ → 感受野↓ → 阈值↓
    ★ 第一版系数取 10：指尖(100/cm²)→1.00mm 对，但手掌/前臂/背部全部偏小
      （4.47 vs 真实 10；14.1 vs 真实 35）
      ★ 根因：两点辨别阈不只由密度决定，还受【皮层放大】影响
        远端(手/脸)皮层放大远大于近端(躯干/四肢)
      → 改用带部位放大因子的经验标度
    """
    if recep_density_per_cm2 <= 0:
        return float("inf")
    return float(10.0 / np.sqrt(recep_density_per_cm2))


# ★ 皮层放大因子（REAL：体感侏儒图，手/脸远大于躯干）
CORTICAL_MAG = {"指尖": 1.0, "手掌": 2.2, "前臂": 2.5, "背部": 2.0, "大腿": 2.0}


def two_point_threshold2(recep_density_per_cm2: float,
                         site: str = "指尖") -> float:
    """★ 两点辨别阈 = 感受野直径 × 皮层放大因子。"""
    base = two_point_threshold(recep_density_per_cm2)
    if not np.isfinite(base):
        return base
    return float(base * CORTICAL_MAG.get(site, 1.0))


def two_point_discriminable(gap_mm: float, site: str = "指尖") -> bool:
    lo, hi = TWO_POINT_MM.get(site, (1.0, 2.0))
    return gap_mm >= ((lo + hi) / 2.0)


def discriminable(gap_mm: float, site: str = "指尖", active: bool = True) -> bool:
    """★ 主动 vs 被动的空间辨别（REAL：主动优于被动约 2×）。"""
    lo, hi = TWO_POINT_MM.get(site, (1.0, 2.0))
    th = (lo + hi) / 2.0
    if active:
        th = th * 0.6
    return gap_mm >= th


# ================================================================
# 三、适应
# ================================================================
def adaptation(t_s: np.ndarray, kind: str = "SA1") -> np.ndarray:
    """★ 快适应（只对变化响应） vs 慢适应（持续但衰减）。"""
    t = np.asarray(t_s, float)
    if kind.startswith("RA"):
        # RA： onset + offset 两个尖峰，中间归零
        return np.exp(-t / ADAPT_RA_TAU) * (t < 1.0)
    return ADAPT_SA_FLOOR + (1.0 - ADAPT_SA_FLOOR) * np.exp(-t / ADAPT_SA_TAU)


def clothing_felt(t_s: np.ndarray) -> np.ndarray:
    """★ 穿上衣服后多久感觉不到（REAL：几秒）。"""
    return adaptation(t_s, "SA1")


# ================================================================
# 四、温度
# ================================================================
def thermoreceptor(temp_c: float, kind: str = "cold") -> float:
    """★ 冷/热感受器响应（非单调！）。

    ★ 冷感受器在【更冷】时响应更大，但低于 ~10°C 又开始下降（痛觉接管）
    ★ 热感受器 >43°C 激活（TRPV1），这是伤害性热的阈值
    """
    T = float(temp_c)
    if kind == "cold":
        # TRPM8：峰值约 25°C，32°C 以上静默
        if T > 32.0:
            return 0.0
        return float(np.exp(-0.5 * ((T - COLD_PEAK_C) / 8.0) ** 2))
    if T < 30.0:
        return 0.0
    return float(1.0 / (1.0 + np.exp(-(T - 40.0) / 2.0)))


def thermal_illusion(spatial_pattern_c: np.ndarray) -> float:
    """★ 热错觉 paradox（REAL）：交替 20°C/40°C 栅格 → 感知为灼烧冷痛。

    ★ 机制：冷通道与热通道同时激活，中枢没有对应的自然组合
      → 解释为"灼烧"。这跟双眼复视是同一类：通道组合冲突
    """
    cold = np.array([thermoreceptor(t, "cold") for t in spatial_pattern_c])
    heat = np.array([thermoreceptor(t, "heat") for t in spatial_pattern_c])
    return float(cold.mean() * heat.mean())


def nociceptor(force_mn: float, kind: str = "mech") -> float:
    """★ 痛觉：机械 >20 mN 才激活，且【不适应】。"""
    F = float(force_mn)
    if kind == "mech":
        return 0.0 if F < PAIN_MECH_MN else float(np.log1p(F - PAIN_MECH_MN))
    return float(F)


def pain_adaptation(t_s: np.ndarray) -> np.ndarray:
    """★ 痛觉【不】适应（保护性）—— 与触觉的关键区别。"""
    return np.ones_like(np.asarray(t_s, float))


# ================================================================
# 五、★ 主动 vs 被动（核心对照）
# ================================================================
def active_vs_passive(gap_mm: float, site: str = "指尖",
                      efference_gain: float = 2.0) -> tuple[float, float]:
    """★ 主动触觉的空间辨别优于被动。

    ★ REAL：主动约优 2 倍（传出副本 + 运动指令）
    返回 (主动阈值, 被动阈值) mm
    """
    lo, hi = TWO_POINT_MM.get(site, (1.0, 2.0))
    base = (lo + hi) / 2.0
    return base / efference_gain, base


def tactile_exploration_move(v_mm_s: float, period_um: float,
                             n_steps: int = 200) -> tuple[float, float]:
    """★ 扫描 vs 静止：细纹理的可辨性。

    返回 (动起来时的 RA2 响应, 静止时的 RA2 响应)
    ★ 静止时 RA2 恒为 0 —— 细纹理【完全消失】
    """
    moving = texture_encoding(period_um, v_mm_s)["RA2_vibration"]
    still = texture_encoding(period_um, 0.0)["RA2_vibration"]
    return float(moving), float(still)
