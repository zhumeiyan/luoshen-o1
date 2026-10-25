#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
前庭 —— 三个互相垂直的半规管 + 两块耳石
================================================================
★ 它是【惯性导航】，不是感受器
    眼耳鼻皮肤：感受外界
    ★ 前庭：测量【自己】的运动 —— 加速度和角速度
    ★ 这是所有感官里唯一一个"测量自身运动状态"的

----------------------------------------------------------------
一、半规管（三个，近似互相垂直）（REAL）
----------------------------------------------------------------
    三管：外(水平)、前(上半)、后   —— 左右各三，共六个
    内淋巴 + 壶腹嵴顶（gelatinous cupula）
    ★ 顶石是【 overdamped 二阶低通】，不是加速度计
      传递函数 ≈ s·τc/(1+s·τc) · 1/(1+s·τL)
      τc 约 5~7 s（cupula 弹性回弹）  τL 约 0.003~0.005 s
    ★ 净效果：对【角速度】响应，带宽约 0.02~10 Hz
    ★ 阈值：角速度约 0.1~1 °/s（可察觉）

----------------------------------------------------------------
二、★ 顶石的关键后果：转椅后眩晕
----------------------------------------------------------------
    匀速旋转一段时间后，内淋巴追上管壁 → 顶石回位 → 信号归零
      → 大脑以为【不转了】
    突然停下 → 内淋巴因惯性继续流 → 顶石反向偏
      → 大脑以为【反向转】
    ★ 这就是"停下来反而更晕"的机制
    ★ 时间常数 τc 约 5~7 s，REAL 主观晕感持续约 10~30 s

----------------------------------------------------------------
三、耳石器（椭圆囊 + 球囊）（REAL）
----------------------------------------------------------------
    耳石膜（碳酸钙 otoconia，密度 > 内淋巴）
    ★ 测量【线性加速度 + 重力】—— 无法区分二者
    ★ 爱因斯坦 elevator 等价原理的生物学版本
      静止时：测到的是重力矢量（1 g 向下）
      自由落体：测到 0 —— 与"太空中静止"完全一样
    椭圆囊：大致水平，感知前后/左右倾斜
    球囊：大致垂直，感知上下
    ★ 线性加速度阈值 约 0.01~0.05 m/s²（5~15 cm/s² 可觉察）

----------------------------------------------------------------
四、★ 重力不可分辨（核心对照）
----------------------------------------------------------------
    耳石输出矢量 g_hat = a_true - g（减去重力）
    ★ 所以：静止在地面     → 输出 (0,0,1) 向上
             自由落体       → 输出 (0,0,0)
             太空静止       → 输出 (0,0,0)
    ★ 后两者【输出完全相同】→ 耳石无法区分
    ★ 这正是加速度计的根本局限（IMU 都靠积分，会漂移）

----------------------------------------------------------------
五、VOR 前庭眼反射（REAL）
----------------------------------------------------------------
    头转 → 眼反向转，增益约 0.9~1.0（速度约 100~300 °/s 时）
    潜伏期 约 5~15 ms（极短，因为只有三级突触）
    ★ 这是最快的反射之一
    ★ 视觉 VOR(OKN) 慢得多，潜伏期 50~100 ms
    ★ 对照意义：头动时靠 VOR 稳像，靠视觉来不及

----------------------------------------------------------------
六、与前几层的联系
----------------------------------------------------------------
    ★ 前庭 + 眼睛：VOR —— 头动时眼睛反向补偿
    ★ 前庭 + 本体觉：判断"是我在动还是世界在动"
    ★ 前庭 + 皮肤：靠坐/站的压力判断姿态
    ★ 前庭【没有】外部目标 —— 它是纯内感受，接 L6
"""
from __future__ import annotations
import numpy as np

# ---------------- 半规管 REAL ----------------
TAU_CUPULA   = 6.0      # s，cupula 回弹（REAL 5~7）
TAU_LAG      = 0.004    # s
CANAL_THRESHOLD_DPS = 0.5   # 角速度阈值 °/s（REAL 0.1~1）
CANAL_GAIN_STATIC   = 1.0   # 稳态角速度增益
CANAL_BAND_HZ       = (0.02, 10.0)

# ---------------- 耳石 REAL ----------------
G = 9.80665
OTOLITH_THRESHOLD = 0.02   # m/s² （REAL 0.01~0.05）
UTRICLE_TILT_RANGE_DEG = 30.0   # 椭圆囊主要工作范围

# ---------------- VOR REAL ----------------
VOR_GAIN       = 0.95    # REAL 0.9~1.0
VOR_LATENCY_MS = 10.0    # REAL 5~15 ms
OKN_LATENCY_MS = 80.0    # 视动性眼震，REAL 50~100 ms


# ================================================================
# 一、半规管：顶石动力学（overdamped 二阶）
# ================================================================
def cupula_response(omega_dps: np.ndarray, dt: float = 0.001,
                    tau_c: float = TAU_CUPULA,
                    tau_l: float = TAU_LAG) -> np.ndarray:
    """★ 顶石偏转对【角速度】的响应（不是角加速度！）。

    传递函数: (s·τc) / ((1+s·τc)(1+s·τl))   作用于角速度
    离散实现：两个串联一阶
      stage1 高通（τc）：cupula 弹性回弹 → 匀速旋转时归零
      stage2 低通（τl）：内淋巴惯性
    """
    w = np.asarray(omega_dps, float)
    n = len(w)
    out = np.zeros(n)
    y1 = 0.0   # 高通状态
    y2 = 0.0   # 低通输出
    # 一阶高通（后向欧拉）：y[i] = a·(y[i-1] + Δw)，a = τ/(τ+dt)
    # 一阶低通：            y[i] = y[i-1] + b·(x − y[i-1])，b = dt/(τ+dt)
    # ★ 第一版两个系数都写成 dt/(τ+dt)：高通 a 变成 0.0017 → 增益只有 0.003
    # ★ 第二版又把高通形式改成 a·Δw + (1−a)·y —— 形式错了，衰减快 600 倍
    #   正确形式就是 a·(y + Δw)，只是 a 必须取 τ/(τ+dt)
    a_c = tau_c / (tau_c + dt)      # 高通（cupula 回弹）
    a_l = dt / (tau_l + dt)         # 低通（内淋巴惯性）
    for i in range(n):
        # 高通：y1 = a_c*(y1_prev + w - w_prev)
        wp = w[i-1] if i > 0 else 0.0
        # ★ 第一版写 y1 = a_c*(y1 + Δw)
        #   正确的一阶高通（后向欧拉）是：y1 = a_c·Δw + (1−a_c)·y1
        #   第一版衰减系数写成了 a_c（≈1）而不是 (1−a_c)（≈0）
        #   → 状态几乎不衰减 → 匀速转 29s 后还有 55.5，停后 20s 还有 25.4
        #   ★ 症状：该衰减的地方不衰减，转椅实验完全失真
        y1 = a_c * (y1 + (w[i] - wp))
        # 低通
        y2 = y2 + a_l * (y1 - y2)
        out[i] = y2
    return out


def cupula_gain(freq_hz: np.ndarray, tau_c: float = TAU_CUPULA,
                tau_l: float = TAU_LAG) -> np.ndarray:
    """幅频响应 |H(f)|。★ 带通：极低频和高频都衰减。"""
    f = np.asarray(freq_hz, float)
    w = 2*np.pi*f
    H = (1j*w*tau_c) / ((1+1j*w*tau_c)*(1+1j*w*tau_l))
    return np.abs(H)


def rotation_chair(t_s: np.ndarray, omega_dps: float, t_stop: float,
                   dt: float = None) -> np.ndarray:
    """★ 转椅实验：匀速转 → 突然停 → 反向晕。

    ★ 关键：停止后信号【反向】且需要 τc 才恢复
    """
    t = np.asarray(t_s, float)
    # ★ 第一版 dt 默认 0.001，但传入的 t 步长是 0.01
    #   → 滤波器时间常数被放大 10 倍 → 29s 后该衰减到 0.72 却还有 55.5
    if dt is None:
        dt = float(t[1] - t[0]) if len(t) > 1 else 0.01
    w = np.where(t <= t_stop, omega_dps, 0.0)
    return cupula_response(w, dt)


def post_rotation_decay(t_after_stop: np.ndarray,
                        tau_c: float = TAU_CUPULA) -> np.ndarray:
    """停止后主观旋转感的衰减 exp(-t/τc)。"""
    return np.exp(-np.asarray(t_after_stop, float)/tau_c)


# ================================================================
# 二、耳石：重力不可分辨
# ================================================================
def otolith_output(acc_true: np.ndarray, g_vec: np.ndarray = None) -> np.ndarray:
    """★ 耳石输出 = 真实加速度 − 重力（gravito-inertial force）。

    ★ 这就是它【无法区分】静止与自由落体的数学表达
    """
    g_vec = np.zeros(3) if g_vec is None else np.asarray(g_vec, float)
    a = np.asarray(acc_true, float)
    return a - g_vec


def otolith_scenarios() -> dict:
    """★ 三个场景，输出对比 —— 证明不可分辨。"""
    g = np.array([0.0, 0.0, -G])
    return {
        "地面静止":  otolith_output(np.array([0.,0.,0.]), g),   # 输出 +z
        "自由落体":  otolith_output(g, g),                       # 输出 0
        "太空静止":  otolith_output(np.array([0.,0.,0.]), np.zeros(3)),
        "1g向上加速": otolith_output(np.array([0.,0.,G]) - g, g),
    }


def tilt_from_otolith(vec: np.ndarray) -> float:
    """由耳石矢量反推倾斜角（度）。★ 倾斜与线性加速度不可分。"""
    v = np.asarray(vec, float)
    n = np.linalg.norm(v)
    if n < 1e-9:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(v[2]/n, -1, 1))))


def somatogravic_illusion(acc_forward: float) -> float:
    """★ 体感重力错觉（REAL 飞行员错觉）：
       向前加速 → 被感知为【机头上仰】。"""
    return float(np.degrees(np.arctan(acc_forward / G)))


# ================================================================
# 三、VOR
# ================================================================
def vor_eye_velocity(head_vel_dps: float, gain: float = VOR_GAIN) -> float:
    """★ VOR：眼速 = −增益 × 头速。"""
    return float(-gain * head_vel_dps)


def retinal_slip(head_vel_dps: float, vor_gain: float = VOR_GAIN) -> float:
    """★ 视网膜滑动 = 头速 + 眼速 = (1−gain)·头速。
    gain=1 时完全补偿。"""
    return float(head_vel_dps + vor_eye_velocity(head_vel_dps, vor_gain))


def vor_compensation_ratio(vor_gain: float = VOR_GAIN) -> float:
    """★ 补偿比例：1 − (1−gain)。"""
    return float(vor_gain)


def image_stabilization(head_vel_dps: float, vor: bool = True) -> float:
    """有 VOR vs 无 VOR 的视网膜滑动速度（°/s）。"""
    if vor:
        return abs(retinal_slip(head_vel_dps, VOR_GAIN))
    return abs(retinal_slip(head_vel_dps, 0.0))


# ================================================================
# 四、积分漂移（IMU 的根本问题）
# ================================================================
def imu_drift(bias: float, t_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """★ 加速度积分求速度/位置：偏置导致二次漂移。

    ★ 生物前庭【也有】这个问题 —— 闭眼原地踏步会走偏就是这个原因
    返回 (速度误差, 位置误差)
    """
    t = np.asarray(t_s, float)
    v = bias * t
    p = 0.5 * bias * t**2
    return v, p


def path_integration_error(bias: float, duration_s: float,
                           step_len_m: float = 0.7) -> float:
    """★ 路径积分：走直线时的横向偏差（REAL：闭眼走会偏）。"""
    return float(0.5 * bias * duration_s**2)
