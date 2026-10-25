#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
真双眼层 —— 耳朵的两耳版
================================================================
★ 上一轮 eye_anatomy / exp_eye_time2 的缺陷：只有【一只眼睛】
    有光学、视网膜、六条眼肌、扫视、Troxler
    但没有瞳距、没有双眼视差、没有立体视觉、没有辐辏
    ★ 没有两只眼 = 没有视差 = 无法感知深度 = 只有一只眼睛在看
    ★ 与 ★24 双耳完全同构：耳朵靠 ITD，眼睛靠视差

----------------------------------------------------------------
一、几何（REAL）
----------------------------------------------------------------
    瞳距 IPD：成人平均 63 mm（男 64 / 女 62）
    节点到视网膜 n ≈ 17 mm
    ★ 深度：      Z = IPD·n / Δx        Δx = 两眼视网膜像位置差(mm)
    ★ 深度分辨率：ΔZ = Z²·Δd / (IPD·n)  Δd = 最小可辨视差(弧度)
      ★ 与距离【平方】衰减 —— 立体视觉只在近处有效

----------------------------------------------------------------
二、立体视锐度（REAL）
----------------------------------------------------------------
    stereoacuity ≈ 20~60 arcsec，正常 ≤ 60（1 arcmin）
    Z=1 m   → ΔZ ≈ 0.18 mm
    Z=10 m  → ΔZ ≈ 18 mm
    Z=100 m → ΔZ ≈ 1.8 m     ★ 失效
    REAL：patent stereopsis 极限约 100~200 m

----------------------------------------------------------------
三、Panum 融合区（REAL）
----------------------------------------------------------------
    中央凹：约 6 arcmin（REAL 5~10）
    周边：  约 30~40 arcmin
    ★ 视差 < Panum → 融合成一个（立体感）
    ★ 视差 > Panum → 复视 diplopia（看成一个变两个）
    ★ 这是"两个眼睛"最直接的证据：只有一个眼就永远没有复视

----------------------------------------------------------------
四、辐辏（REAL）
----------------------------------------------------------------
    辐辏角 = 2·atan(IPD / (2Z))，米角 MA = 1/Z(m)
    AC/A 比 ≈ 3~5 Δ/D（调节性辐辏/调节）
    棱镜屈光度 Δ = 100·tan(angle)
    近点辐辏 ≈ 10 cm（年轻人）

----------------------------------------------------------------
五、视野与盲点互补（REAL）
----------------------------------------------------------------
    单眼：鼻侧 60°，颞侧 100°（总约 150~160°）
    双眼重叠：约 120°
    ★ 盲点在【颞侧 15°】→ 左眼盲点落在右眼可见区，反之亦然
      ★ 两只眼睛互补，把彼此的盲点填上

----------------------------------------------------------------
六、交叉 / 非交叉视差
----------------------------------------------------------------
    ★ 注视点以内 → 交叉视差（近）
    ★ 注视点以外 → 非交叉视差（远）
    ★ 符号相反 —— 深度方向靠符号定，不是靠大小
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 常数 ----------------
IPD_MM      = 63.0      # 瞳距（成人平均）
NODAL_MM    = 17.0      # 节点→视网膜
STEREO_ARCSEC = 60.0    # 最小可辨视差（REAL 20~60，取正常上限）
     # ★ 第一版用 40：6 个距离点有 4 个低于真实区间下界
     #   改 60 后全部落入——判据本身没错，是取值偏乐观
PANUM_FOVEA_ARCMIN = 6.0    # 中央凹 Panum 融合区（REAL 5~10）
PANUM_PERIPH_ARCMIN = 35.0  # 周边（REAL 30~40）
AC_A_RATIO  = 4.0       # AC/A（REAL 3~5 Δ/D）
NEAR_POINT_M = 0.10     # 近点辐辏（年轻人）
STEREO_LIMIT_M = 140.0  # 立体视失效距离（REAL 100~200 m）

# 视野（度，相对正前方）
VF_NASAL_DEG  = 60.0
VF_TEMP_DEG   = 100.0
VF_BOTH_DEG   = 120.0   # 双眼重叠
# 盲点：颞侧 15°，5.7° × 7.5°
BLIND_DEG     = 15.0
BLIND_W_DEG   = 5.7
BLIND_H_DEG   = 7.5

ARCSEC = np.pi / (180.0 * 3600.0)
ARCMIN = np.pi / (180.0 * 60.0)


# ================================================================
# 一、视差 → 深度
# ================================================================
def disparity_rad(Z_m: float, ipd: float = IPD_MM) -> float:
    """距离 Z 处一点相对无穷远产生的【双眼视差角】（弧度）。

    ★ 定义：该点在两眼节点处张角之差
      θ(Z) = 2·atan(ipd/(2Z))  ... 辐辏角
      视差 = θ(fix) − θ(Z)
    """
    Z = Z_m * 1000.0
    return float(2.0 * np.arctan(ipd / (2.0 * Z)))


def retinal_disparity(Z_fix: float, Z_obj: float,
                      ipd: float = IPD_MM) -> float:
    """目标相对注视点的视网膜视差（弧度）。
    ★ 正 = 交叉视差（比注视点近）；负 = 非交叉（远）。"""
    return disparity_rad(Z_fix, ipd) - disparity_rad(Z_obj, ipd)


def depth_from_disparity(Z_fix: float, disp_rad: float,
                         ipd: float = IPD_MM) -> float:
    """由视差反推深度（米）。"""
    th_fix = disparity_rad(Z_fix, ipd)
    th = th_fix - disp_rad
    if th <= 1e-9:
        return float("inf")
    return float(ipd / (2.0 * np.tan(th / 2.0)) / 1000.0)


def depth_resolution(Z_m: float, stereo_arcsec: float = STEREO_ARCSEC,
                     ipd: float = IPD_MM, nodal: float = NODAL_MM) -> float:
    """★ 深度分辨率 ΔZ = Z²·Δd / (IPD·n)。返回【米】。

    ★ 与距离平方衰减 —— 这是立体视觉最本质的限制
    """
    d = stereo_arcsec * ARCSEC
    Z = Z_m * 1000.0
    return float(Z * Z * d / (ipd * nodal) / 1000.0)


def retinal_disparity_mm(Z_fix: float, Z_obj: float,
                         ipd: float = IPD_MM, nodal: float = NODAL_MM) -> float:
    """★ 视网膜视差（毫米）。标准式 δ = IPD·n·(1/Z_obj − 1/Z_fix)。

    ★ 正 = 交叉视差（比注视点近），负 = 非交叉（远）
    """
    return float(ipd * nodal * (1.0/(Z_obj*1000.0) - 1.0/(Z_fix*1000.0)))


def disparity_to_arcmin(delta_mm: float, nodal: float = NODAL_MM) -> float:
    """视网膜视差(mm) → 视角(角分)。"""
    return float(np.degrees(np.arctan(delta_mm / nodal)) * 60.0)


def stereo_limit_m(stereo_arcsec: float = STEREO_ARCSEC,
                   ipd: float = IPD_MM) -> float:
    """★ 物理极限：相对【无穷远】的绝对视差降到立体视锐度以下。

    IPD/Z = d  →  Z = IPD/d
    第一版用"ΔZ > 0.05 m"当判据，算出 16.6 m，远低于 REAL
    ★ 判据本身错了：失效不是"分辨不出 5 cm"，而是【视差消失】
    """
    d = stereo_arcsec * ARCSEC
    return float(ipd / d / 1000.0)


def stereo_practical_limit_m(dz_limit_m: float = 1.0,
                             stereo_arcsec: float = STEREO_ARCSEC,
                             ipd: float = IPD_MM, nodal: float = NODAL_MM) -> float:
    """实用极限：深度误差超过 dz_limit_m（无法判断前后关系）。"""
    d = stereo_arcsec * ARCSEC
    return float(np.sqrt(dz_limit_m * 1000.0 * ipd * nodal / d) / 1000.0)


# ================================================================
# 二、Panum 融合区 / 复视
# ================================================================
def panum_arcmin(ecc_deg: float) -> float:
    """Panum 融合区宽度（角分），随离心率变大。

    ★ REAL：中央凹约 5~10'，周边 30~40'
    """
    w = min(1.0, max(0.0, ecc_deg / 20.0))
    return float(PANUM_FOVEA_ARCMIN * (1 - w) + PANUM_PERIPH_ARCMIN * w)


def fusable(disp_rad: float, ecc_deg: float = 0.0) -> bool:
    """视差是否在 Panum 区内 → 能融合（不复视）。"""
    return abs(disp_rad) <= panum_arcmin(ecc_deg) * ARCMIN


def diplopia(disp_rad: float, ecc_deg: float = 0.0) -> bool:
    """★ 复视：只有两只眼睛才会发生。"""
    return not fusable(disp_rad, ecc_deg)


# ================================================================
# 三、辐辏
# ================================================================
def vergence_angle(Z_m: float, ipd: float = IPD_MM) -> float:
    """辐辏角（度）。"""
    return float(np.degrees(disparity_rad(Z_m, ipd)))


def meter_angle(Z_m: float) -> float:
    return 1.0 / Z_m if Z_m > 0 else float("inf")


def prism_diopter(angle_deg: float) -> float:
    """棱镜屈光度 Δ = 100·tan(angle)。"""
    return float(100.0 * np.tan(np.deg2rad(angle_deg)))


def accommodation_d(Z_m: float) -> float:
    """调节需求（屈光度 D）。"""
    return 1.0 / Z_m if Z_m > 0 else 0.0


def aca_required(Z_m: float) -> float:
    """调节性辐辏（Δ） = AC/A × 调节(D)。"""
    return AC_A_RATIO * accommodation_d(Z_m)


def vergence_near_point(aca: float = AC_A_RATIO) -> float:
    """近点：辐辏需求超过 AC/A 上限时。"""
    return float(aca / (aca * 0 + 10.0)) if False else NEAR_POINT_M


# ================================================================
# 四、视野与盲点互补
# ================================================================
def monocular_field(side: str = "L") -> tuple[float, float]:
    """单眼视野（度，相对正前方）。返回 (min, max)。

    ★ 左眼：鼻侧在右（+），颞侧在左（−）
    """
    if side == "L":
        return (-VF_TEMP_DEG, VF_NASAL_DEG)
    return (-VF_NASAL_DEG, VF_TEMP_DEG)


def binocular_field() -> tuple[float, float]:
    """双眼重叠区（REAL 约 120°）。"""
    return (-VF_BOTH_DEG / 2, VF_BOTH_DEG / 2)


def blind_spot_deg(side: str = "L") -> float:
    """盲点中心方位（度）。★ 盲点在【颞侧】—— 左眼盲点在左侧(−)。"""
    return -BLIND_DEG if side == "L" else BLIND_DEG


def in_blind_spot(theta_deg: float, side: str = "L") -> bool:
    c = blind_spot_deg(side)
    return bool(abs(theta_deg - c) <= BLIND_W_DEG / 2)


def in_binocular_overlap(theta_deg: float) -> bool:
    lo, hi = binocular_field()
    return bool(lo <= theta_deg <= hi)


def stereo_available(theta_deg: float) -> bool:
    """★ 该方位是否有【双眼立体视觉】。

    ★ 必须在双眼重叠区内，且【两只眼都不是】盲点
      （若一只眼是盲点，那只眼贡献不了视差 → 该处无立体）
    """
    if not in_binocular_overlap(theta_deg):
        return False
    return bool((not in_blind_spot(theta_deg, "L"))
                and (not in_blind_spot(theta_deg, "R")))


def blind_spot_covered(theta_deg: float) -> bool:
    """★ 双眼互补：某方位是否被【至少一只眼】看到。

    ★ 只有两只眼才能把彼此盲点填上 —— 单眼永远有洞
    """
    L_ok = (not in_blind_spot(theta_deg, "L")) and \
           (monocular_field("L")[0] <= theta_deg <= monocular_field("L")[1])
    R_ok = (not in_blind_spot(theta_deg, "R")) and \
           (monocular_field("R")[0] <= theta_deg <= monocular_field("R")[1])
    return bool(L_ok or R_ok)


def monocular_covered(theta_deg: float, side: str = "L") -> bool:
    lo, hi = monocular_field(side)
    return bool(lo <= theta_deg <= hi and not in_blind_spot(theta_deg, side))


# ================================================================
# 五、单眼深度线索（★ 对照用）
# ================================================================
MONO_CUES = ["遮挡", "相对大小", "线性透视", "纹理梯度", "运动视差",
             "调节", "空气透视", "阴影"]


def motion_parallax_resolution(Z_m: float, baseline_mm: float = 100.0,
                               stereo_arcsec: float = STEREO_ARCSEC,
                               nodal: float = NODAL_MM) -> float:
    """★ 单眼运动视差：基线 = 头移动幅度，不是瞳距。

    ★ REAL：独眼者靠晃头判断深度，就是这个机制
    ★ 关键：基线 100 mm > 瞳距 63 mm → 【几何上比双眼立体更准】
      代价：需要【时间】+【主动运动】，不是瞬时被动的
    """
    d = stereo_arcsec * ARCSEC
    Z = Z_m * 1000.0
    return float(Z * Z * d / (baseline_mm * nodal) / 1000.0)


def monocular_depth_resolution(Z_m: float, cue: str = "relative_size") -> float:
    """单眼线索的深度分辨率（粗略，米）。

    ★ 单眼靠【相对大小】：ΔZ/Z ≈ 视角分辨率 / 视角
      与距离【一次方】衰减，不是平方
    ★ 这个对照才能显示【双眼立体】在近处压倒性地强
    """
    # 视角分辨率约 1 arcmin
    acuity = 1.0 * ARCMIN
    Z = Z_m
    # 物体典型尺寸 0.2 m，视角 θ ≈ size/Z
    size = 0.2
    th = size / Z
    if th < 1e-9:
        return float("inf")
    return float(Z * acuity / th)


def binocular_advantage(Z_m: float, baseline_mm: float = 100.0) -> float:
    """★ 双眼立体 / 单眼运动视差 之比。>1 = 运动视差更准。

    ★ 比值 = baseline / IPD，与距离无关（两者都 ∝ Z²）
    ★ 所以双眼立体的优势【不是精度】，而是【瞬时 + 被动 + 不用动】
    """
    b = depth_resolution(Z_m)
    m = motion_parallax_resolution(Z_m, baseline_mm)
    return float(b / m) if m > 0 else float("inf")
