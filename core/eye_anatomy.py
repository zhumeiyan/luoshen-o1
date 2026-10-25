#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
眼球到底是什么：按真人眼球组成 + 怎么接大脑，一层一层拆
================================================================
用户：「直接往人类上想，眼球到底有什么组成部分，再加上后端如何接大脑。」

★ 光走的路（REAL，几何光学 + 解剖）：
    角膜 cornea  +43 D  固定，不可调（主要折射，因为空气/角膜 n 差最大）
      ↓ 前房 aqueous
    虹膜 pupil   孔径 2~8 mm（调光量，不调焦）
      ↓
    晶状体 lens  +19 D  可调！睫状肌 → 变厚 → 屈光度增到约 +30 D（年轻人）
      ↓ 玻璃体 vitreous
    视网膜 retina  感光（在最后面）

★ 视网膜不是均匀胶片（REAL）：
    视杆 rod   约 9200 万  暗光、无色、周边为主
    视锥 cone   约 600 万  明光、三色（L/M/S）、集中在中央凹
    中央凹 fovea：只有视锥，无视杆；血管绕开；中心凹 pit
    视盘 optic disc：神经穿出 → 【没有感光细胞】→ 真盲点
                    位置：中心颞侧约 15°，约 5.7°×7.5°
    ★ 脊椎动物的视网膜是【反的】：血管和神经在感光细胞【前面】
      → 所以必然有盲点。章鱼（头足类）是正的，没盲点。
      → 这是一个真实的拓扑手性差异。

★ 后端怎么接大脑（REAL）：
    神经节细胞 约 100 万  ← 视锥 600 万 + 视杆 9200 万 压缩到 100 万
      ★ 中央凹几乎 1:1，周边约 20:1 → 压缩不是均匀的
      ↓ 视神经
    视交叉 optic chiasma  ★ 鼻侧纤维【交叉】到对侧，颞侧【不交叉】
      → 左视野进右脑，右视野进左脑
      ★ 这是身体左右分离的解剖根源，是真实的结构手性
      ↓
    LGN 外侧膝状体
      ↓
    V1 视皮层   视网膜拓扑映射 retinotopy + 【中央放大 cortical magnification】
      ★ 中央 1° 视角占的皮层面积，是周边同样 1° 的几十倍

★ 六条外眼肌（REAL）：
    内/外直肌 → 水平；上/下直肌 → 垂直+旋转；上/下斜肌 → 旋转为主
    ★ 滑车神经 CN IV：支配【上斜肌】，是唯一从脑干背侧发出
      且【完全交叉】的脑神经 —— 左滑车神经支配【右】眼上斜肌
      ★ 这是真实的解剖手性：唯一完全交叉的脑神经

★ 眼一直在动（REAL，三种微动 + 扫视）：
    震颤 tremor ~90 Hz
    漂移 drift  0.1~0.5 °/s
    微跳视 microsaccade 1~2 Hz，3~30 arcmin
    扫视 saccade ~3 Hz，持续 = 20 + 2.1×幅度(°) ms（main sequence，REAL）
    ★ 扫视抑制 saccadic suppression：扫视期间视觉被压制约 50~100 ms
    ★ 固定像消退 Troxler：图像完全稳定贴在视网膜上 1~3 秒就消退变灰
      → 所以【不动就看不见】。微动是生理必需，不是噪声。

★ Listing 定律（REAL）：
    任意注视方向，眼球的【旋转 torsion】由注视方向唯一决定（半角规则）
    小角度近似：τ ≈ -(θh · θv)/2
    扫视【期间】会瞬时违反，然后以时间常数约 70~150 ms 恢复
    ★ 这个瞬时违反是【时间维度】的、定向的、正反不对称的

provenance：所有解剖/光学/神经生理数值 = REAL（教科书与文献）
            torsion 违反的幅度 = 模型参数（明确标注）
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 眼球光学常数 ----------------
P_CORNEA = 43.0            # D，角膜（固定）
P_LENS_MIN = 19.0          # D，晶状体完全放松
P_LENS_MAX = 30.0          # D，晶状体最大调节（年轻人）
AXIAL = 24.0               # mm，眼轴
N_EYE = 1.336              # 眼内介质折射率（简化眼）

# ---------------- REAL 视网膜 ----------------
RODS = 92_000_000
CONES = 6_000_000
GANGLION = 1_000_000       # 瓶颈！
FOVEA_DEG = 1.2            # 中央凹直径（度）
BLIND_CENTER_DEG = 15.0    # 盲点中心距中心凹（度，颞侧）
BLIND_W, BLIND_H = 5.7, 7.5  # 盲点大小（度）

# ---------------- REAL 时间参数 ----------------
SACC_BASE_MS = 20.0
SACC_SLOPE = 2.1           # ms/度，main sequence
TORSION_TAU_MS = 100.0     # torsion 恢复到 Listing 平面的时间常数（REAL 70~150）


# ============================================================ 光学
def lens_power(accom=0.0):
    """调节量 accom 0~1 → 晶状体屈光度。"""
    return P_LENS_MIN + (P_LENS_MAX - P_LENS_MIN) * float(np.clip(accom, 0, 1))


def total_power(accom=0.0):
    return P_CORNEA + lens_power(accom)


def cauchy_n(wl_nm, A=1.3208, B=3100.0):
    """n(λ) = A + B/λ²，λ 单位 nm（A、B 拟合到 ~589nm 时 n≈1.336）。"""
    return A + B / (wl_nm ** 2)


def focus_shift_mm(wl_nm, accom=0.0):
    """波长 wl 的焦点相对 589nm 参考的位移（mm）。

    纵向色差 LCA：真实人眼短波(约430)到长波(约680)约 1.8~2.4 D。
    """
    n0 = cauchy_n(589.0)
    n1 = cauchy_n(wl_nm)
    # 屈光力 ∝ (n-1) 的一阶近似
    P0 = total_power(accom) * (n0 - 1.0) / (N_EYE - 1.0)
    P1 = total_power(accom) * (n1 - 1.0) / (N_EYE - 1.0)
    # 像方焦距 f = n / P （mm，P 单位 D = 1/m → 转 mm）
    f0 = n0 / (P0 / 1000.0)
    f1 = n1 / (P1 / 1000.0)
    return f1 - f0


def lca_diopters(wl_lo=430.0, wl_hi=680.0, accom=0.0):
    """纵向色差（D）：真实约 1.8~2.4 D。"""
    n0 = cauchy_n(589.0)
    d0 = total_power(accom) * (n0 - 1.0) / (N_EYE - 1.0)
    d1 = total_power(accom) * (cauchy_n(wl_lo) - 1.0) / (N_EYE - 1.0)
    d2 = total_power(accom) * (cauchy_n(wl_hi) - 1.0) / (N_EYE - 1.0)
    return abs(d1 - d2)


# ============================================================ 视网膜
def cone_density(ecc_deg):
    """视锥密度随离心度衰减（REAL 大致趋势：中央凹峰值，快速下降）。"""
    return np.exp(-(np.asarray(ecc_deg, float) / 4.0) ** 2) * 0.6 + 0.02


def rod_density(ecc_deg):
    """视杆密度：中央凹【为零】，约 20° 处峰值（REAL）。"""
    e = np.asarray(ecc_deg, float)
    peak = np.exp(-((e - 20.0) / 12.0) ** 2)
    return peak * (1.0 - np.exp(-(e / 2.0) ** 2))   # e→0 时归零


def in_blind_spot(x_deg, y_deg):
    """盲点：中心在颞侧 15°（x 为鼻颞轴）。REAL 5.7°×7.5° 椭圆。"""
    dx = (np.asarray(x_deg, float) - BLIND_CENTER_DEG) / (BLIND_W / 2)
    dy = np.asarray(y_deg, float) / (BLIND_H / 2)
    return (dx ** 2 + dy ** 2) <= 1.0


def ganglion_compression(ecc_deg):
    """视锥/视杆 → 神经节细胞 的压缩比（REAL：中央凹≈1:1，周边≈20:1）。"""
    e = np.asarray(ecc_deg, float)
    return 1.0 + 19.0 * (1.0 - np.exp(-(e / 8.0) ** 2))


# ============================================================ 后端接大脑
def hemifield(x_deg):
    """视交叉：x<0 视野 → 右脑；x>0 → 左脑。REAL 鼻侧交叉。"""
    return np.where(np.asarray(x_deg, float) < 0, "R", "L")


def cortical_mag(ecc_deg, M0=15.0, e0=1.5):
    """中央放大（REAL：V1 上偏心 e 处每度对应的皮层长度 ∝ 1/(e+e0)）。"""
    e = np.asarray(ecc_deg, float)
    return M0 / (e + e0)


# ============================================================ 眼动
def saccade_duration_ms(amp_deg):
    """main sequence（REAL）：持续 = 20 + 2.1 × 幅度 ms。"""
    return SACC_BASE_MS + SACC_SLOPE * float(amp_deg)


def torsion_listing(theta_h_deg, theta_v_deg):
    """Listing 半角规则（REAL 小角度）：τ ≈ -(θh·θv)/2。"""
    return -(np.asarray(theta_h_deg, float) * np.asarray(theta_v_deg, float)) / 2.0


class Saccade:
    """一次扫视：torsion 瞬时违反 Listing，然后指数恢复。

    ★ 手性来源（REAL 解剖）：
        上斜肌由 CN IV 支配 —— 唯一完全交叉的脑神经
        下斜肌由 CN III 支配 —— 不交叉
        → 两组肌肉的支配不对称 → 扫视期间的 torsion 违反
          【方向依赖】且【正反不对称】
    """

    def __init__(self, from_h, to_h, from_v=0.0, to_v=0.0,
                 viol_gain=0.06, asym=0.45, tau_ms=TORSION_TAU_MS):
        self.h0, self.h1 = float(from_h), float(to_h)
        self.v0, self.v1 = float(from_v), float(to_v)
        self.amp = float(np.hypot(self.h1 - self.h0, self.v1 - self.v0))
        self.dur = saccade_duration_ms(self.amp)
        self.tau = float(tau_ms)
        # ★ 违反幅度 ∝ 幅度；方向由扫视方向决定；asym 是交叉支配的不对称度
        self.viol_gain = float(viol_gain)
        self.asym = float(asym)

    def violation_peak(self):
        """违反峰值（度）。正向右上、负向左下 → 幅度不同（asym）。"""
        dh = self.h1 - self.h0
        # 水平分量主导：向右 vs 向左 的违反幅度不同（CN IV 交叉支配）
        base = self.viol_gain * self.amp
        return base * (1.0 + self.asym * np.sign(dh))

    def torsion(self, t_ms):
        """torsion(t)：Listing 目标 + 瞬时违反（升-降双指数）。"""
        th = np.interp(np.clip(t_ms, 0, self.dur), [0, self.dur], [self.h0, self.h1])
        tv = np.interp(np.clip(t_ms, 0, self.dur), [0, self.dur], [self.v0, self.v1])
        target = torsion_listing(th, tv)
        A = self.violation_peak()
        rise = 1.0 - np.exp(-np.asarray(t_ms, float) / (self.dur / 3.0))
        decay = np.exp(-np.maximum(np.asarray(t_ms, float) - self.dur, 0) / self.tau)
        return target + A * rise * decay

    def suppression(self, t_ms):
        """扫视抑制：返回【敏感度保留比例】1=正常，0=完全压制。

        ★ 第一版写反了：exp(-((t-c)/w)^2) 在 t=c 处取最大值 1，
          被当成 suppression 就变成"扫视时最清晰"。
          正确：敏感度 = 1 - depth × 高斯，扫视正中最暗。
        """
        t = np.asarray(t_ms, float)
        c = self.dur / 2.0
        w = self.dur * 0.55 + 22.0          # 半宽：使 <0.5 的窗口落在 50~100 ms
        return 1.0 - 0.92 * np.exp(-((t - c) / w) ** 2)

    def shape(self, t_ms):
        """违反的【脉冲形状】项（升-降双指数），与扫视方向无关。

        ★ 关键：把 shape 单独暴露出来，是为了从时间反演残差里
           【减掉】它。否则"先快升后慢降"这种任何因果脉冲都有的
           时间不对称，会被误当成手性（第三版踩过）。
        """
        t = np.asarray(t_ms, float)
        rise = 1.0 - np.exp(-t / (self.dur / 3.0))
        decay = np.exp(-np.maximum(t - self.dur, 0) / self.tau)
        return rise * decay


def troxler_fade(t_ms, fix_t0_ms=1200.0):
    """固定像消退（REAL：完全稳定像 1~3 秒消退）。返回可见度。"""
    t = np.asarray(t_ms, float)
    return np.exp(-np.maximum(t - fix_t0_ms, 0) / 800.0)
