#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
真双耳层 —— 两个耳朵之间的距离，才是定位的全部来源
================================================================
用户：「它那个两个耳朵或者眼睛，你在设置的时候，它那个距，
      声音进入之后它会形成两耳，它会震动。」

★ 上一轮 core/ear_anatomy.py 的缺陷：
    只有【单耳】—— 鼓膜、听小骨、耳蜗、毛细胞全是一个耳的
    只定义了 ITD_JND_US / ILD_JND_DB 两个【常量】，没有几何
  ★ 没有距离 = 没有 ITD = 没有定位 = 只有一只耳朵在听

★ 本层补的：两个耳朵 + 它们之间的距离 + 声音传播 + 震动

----------------------------------------------------------------
一、几何（REAL）
----------------------------------------------------------------
    头半径 r ≈ 8.75 cm（成人头宽 17~18 cm）
    声速 c = 343 m/s（20°C 干空气）
    ★ ITD Woodworth(1938)：ITD = (r/c)·(θ + sinθ)   θ 为弧度
      θ=90° → (0.0875/343)(1.5708+1) = 0.656 ms  ← 真实 0.6~0.7 ✅
    ★ 注意：Woodworth 用【头半径】不是耳间距，因为声波绕过头部表面

----------------------------------------------------------------
二、ILD 头部阴影（REAL）
----------------------------------------------------------------
    ★ 低频衍射：波长 >> 头径 → 绕过去 → ILD ≈ 0
    ★ 高频被头挡住 → 声影 → ILD 大
    Rayleigh  duplex theory：
      ITD 主导 < 1.5 kHz（相位可锁）
      ILD 主导 > 2 kHz（相位锁不住了，只能比强度）
    真实值：90° 方位
      500 Hz 约 3~6 dB
      4 kHz  约 15~20 dB

----------------------------------------------------------------
三、震动（★ 用户点名的）
----------------------------------------------------------------
    ① 鼓膜-听骨链 = 受迫阻尼二阶系统
       中耳共振 f0 ≈ 1000 Hz（REAL 800~1200），Q ≈ 1.0（宽带）
       声波 → 鼓膜位移 → 镫骨位移 → 耳蜗
    ② 颅骨振动 / 骨传导
       ★ 与气导不同：颅骨是刚体，两耳间衰减【很小】(< 10 dB)
       ★ 所以骨传导【几乎不产生 ILD】—— 这是能验证的真差异
    ③ 两耳鼓膜位移不同 → 这就是"两耳会震动"的物理量

----------------------------------------------------------------
四、锥混淆（REAL，必须出现）
----------------------------------------------------------------
    ★ 纯 ITD 无法区分【前 / 后】：θ 与 180−θ 的 ITD 相同
    ★ 真实人类靠 HRTF 频谱线索（耳廓）解决前后混淆
    ★ 本层必须【复现混淆存在】，否则模型是假的
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 常数 ----------------
C_AIR = 343.0            # m/s，20°C 干空气
HEAD_R = 0.0875          # m，头半径（头宽 17~18 cm）
EAR_SEP = 0.175          # m，两耳间距（用于骨传导路径差）
SR = 48000               # 内耳有效采样率（远高于 16k，触觉/骨传导需要）

ME_F0 = 1000.0           # 中耳共振 Hz（REAL 800~1200）
ME_Q = 1.0               # 中耳品质因数（宽带）
SKULL_F0 = 300.0         # 颅骨振动主模态（低频，刚体）
SKULL_Q = 6.0            # 颅骨 Q 高（共振尖锐，刚体阻尼小）
BONE_CROSS_DB = 6.0      # 骨传导两耳间衰减（REAL < 10 dB）

ITD_JND_US = 10.0        # 行为最小可觉差（REAL 约 10 μs）
ILD_JND_DB = 0.75        # REAL 0.5~1 dB
MAA_DEG = 1.5            # 最小可听角，前方（REAL 1~2°）


# ================================================================
# 一、ITD —— 距离造成的到达时间差
# ================================================================
def itd_woodworth(theta_deg: float, r: float = HEAD_R, c: float = C_AIR) -> float:
    """Woodworth 公式：声波绕过头部表面的路径差。

    ★ 方位角定义：0° = 正前方，90° = 正右方，180° = 正后方
    ★ 返回【秒】；右耳先到为正
    """
    th = np.deg2rad(theta_deg)
    return (r / c) * (th + np.sin(th))


def itd_naive(theta_deg: float, d: float = EAR_SEP, c: float = C_AIR) -> float:
    """★ 对照用的【错误】模型：两耳间距直线投影 d·sinθ/c。

    真实是绕过头部（Woodworth），不是直线。
    θ=90° 时：naive = 0.175/343 = 0.510 ms，Woodworth = 0.656 ms
    ★ 差 22% —— 可验证哪个对
    """
    return (d / c) * np.sin(np.deg2rad(theta_deg))


# ================================================================
# 二、ILD —— 头部声影（频率依赖）
# ================================================================
def ild_db(freq_hz: float, theta_deg: float, max_db: float = 20.0) -> float:
    """头部阴影造成的双耳强度差。

    ★ 机制：ka = 2πf·r/c 决定衍射程度
      ka << 1（低频）→ 声波绕行 → ILD ≈ 0
      ka >> 1（高频）→ 声影 → ILD 接近 max_db
    ★ 用 sigmoid 过渡，中心在 ka ≈ 1（对应 f ≈ 624 Hz）
    """
    ka = 2 * np.pi * freq_hz * HEAD_R / C_AIR
    # 衍射权重：低频 0，高频 1
    # ★ 第一版中心 ka=1、宽度 0.75 太宽：500Hz 算出 8.53 dB（真实 3~6）
    #   修：中心移到 ka=2（约 1.25 kHz），过渡收窄到 0.5
    w = 1.0 / (1.0 + np.exp(-(np.log(ka + 1e-9) - np.log(1.7)) / 0.55))
    # 方位调制：正前/正后为 0，正侧最大
    return float(max_db * w * abs(np.sin(np.deg2rad(theta_deg))))


# ================================================================
# 三、震动 —— 鼓膜/听骨链 + 颅骨
# ================================================================
def forced_osc(sig: np.ndarray, sr: int, f0: float, Q: float) -> np.ndarray:
    """二阶受迫阻尼振动（位移输出）。★ 这就是"它会震动"。

    x'' + (2πf0/Q)x' + (2πf0)²x = u(t)
    用双线性变换离散化（稳定）。
    """
    w0 = 2 * np.pi * f0
    dt = 1.0 / sr
    # 双线性（Tustin）
    a0 = 4.0 + 4.0 * w0 * dt / Q + w0 * w0 * dt * dt
    a1 = -8.0 + 2.0 * w0 * w0 * dt * dt
    a2 = 4.0 - 4.0 * w0 * dt / Q + w0 * w0 * dt * dt
    b0 = dt * dt
    b1 = 2.0 * dt * dt
    b2 = dt * dt
    n = len(sig)
    y = np.zeros(n, dtype=np.float64)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        u = float(sig[i])
        v = (b0 * u + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, u
        y2, y1 = y1, v
        y[i] = v
    # ★ 数值归一化：DC 增益 = (b0+b1+b2)/(a0-a1-a2) = 4dt²/16 = dt²/4 ≈ 1e-10
    #   第一版没补偿，两次级联后下溢到 0 → 左右两路都变 0 → ILD 恒测成 0.00 dB
    return y * (4.0 / (dt * dt))


def eardrum_displacement(sig: np.ndarray, sr: int = SR,
                         f0: float = ME_F0, Q: float = ME_Q) -> np.ndarray:
    """鼓膜-听骨链位移。中耳是宽带谐振，不是选频——否则人就听不见低频了。"""
    return forced_osc(sig, sr, f0, Q)


def skull_vibration(sig: np.ndarray, sr: int = SR) -> np.ndarray:
    """颅骨振动。★ Q 高 = 刚体，共振尖锐。"""
    return forced_osc(sig, sr, SKULL_F0, SKULL_Q)


# ================================================================
# 四、双耳合成：一个声源 → 左右耳两路信号
# ================================================================
def binauralize(src: np.ndarray, sr: int, theta_deg: float,
                freq_hz: float = 1000.0,
                add_bone: bool = True, rng: np.random.Generator = None
                ) -> tuple[np.ndarray, np.ndarray, dict]:
    """把单声道源放到方位 theta，生成左右耳信号。

    ★ 右耳先到（theta>0 表示声源在右）→ 左耳延迟
    ★ 近耳增益高，远耳被声影衰减
    ★ 骨传导：两耳都收到，但衰减【小】
    """
    itd = itd_woodworth(theta_deg)
    ild = ild_db(freq_hz, theta_deg)
    delay = int(round(abs(itd) * sr))

    # 声影：右耳（近）增益 0 dB，左耳（远）衰减
    g_near = 1.0
    g_far = 10 ** (-ild / 20.0)
    if theta_deg >= 0:
        g_r, g_l = g_near, g_far
        ear_delayed = "L"
    else:
        g_r, g_l = g_far, g_near
        ear_delayed = "R"

    # 气导：延迟远耳
    def shift(x, n):
        if n == 0:
            return x.copy()
        return np.concatenate([np.zeros(n), x[:-n]])

    right = g_r * src
    left = g_l * (shift(src, delay) if ear_delayed == "L" else src)
    if ear_delayed == "R":
        right = g_r * shift(src, delay)

    # 骨传导：几乎无 ILD，且【先到】（骨传导快于气导，REAL）
    if add_bone:
        b = 10 ** (-BONE_CROSS_DB / 20.0) * skull_vibration(src, sr)
        left = left + b
        right = right + b

    # 内耳噪声（REAL：绝对阈附近才有，此处给很小值）
    if rng is not None:
        left = left + 1e-4 * rng.standard_normal(len(left))
        right = right + 1e-4 * rng.standard_normal(len(right))

    info = dict(itd_s=itd, itd_ms=itd * 1e3, ild_db=ild,
                delay_samples=delay, ear_delayed=ear_delayed,
                g_l=g_l, g_r=g_r)
    return left, right, info


# ================================================================
# 五、定位反演：只靠两耳信号推回方位
# ================================================================
def estimate_itd(left: np.ndarray, right: np.ndarray, sr: int,
                 max_lag_ms: float = 1.0) -> float:
    """互相关求 ITD（秒）。正 = 右耳先到。"""
    maxl = int(sr * max_lag_ms / 1000.0)
    a = left - left.mean(); b = right - right.mean()
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    # 归一化互相关，在 lag 范围内搜索
    best, bl = -np.inf, 0
    for lag in range(0, maxl + 1):
        if lag == 0:
            v = float(np.dot(a, b))
        else:
            v = float(np.dot(a[lag:], b[:-lag]))
        v /= (np.sqrt(np.dot(a, a) * np.dot(b, b)) + 1e-12)
        if v > best:
            best, bl = v, lag
    for lag in range(1, maxl + 1):
        v = float(np.dot(a[:-lag], b[lag:]))
        v /= (np.sqrt(np.dot(a, a) * np.dot(b, b)) + 1e-12)
        if v > best:
            best, bl = v, -lag
    return bl / sr


def estimate_ild(left: np.ndarray, right: np.ndarray) -> float:
    """能量比求 ILD（dB）。正 = 右耳更响。"""
    el = float(np.sqrt(np.mean(left ** 2))) + 1e-12
    er = float(np.sqrt(np.mean(right ** 2))) + 1e-12
    return 20.0 * np.log10(er / el)


def itd_to_angle(itd_s: float, r: float = HEAD_R, c: float = C_AIR) -> float:
    """Woodworth 反函数（数值求解）。返回角度（0~180）。"""
    lo, hi = 0.0, 180.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if itd_woodworth(mid, r, c) < abs(itd_s):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ild_to_angle(ild: float, freq_hz: float) -> float:
    """ILD 反函数。返回角度（0~180）。"""
    if freq_hz <= 0:
        return 0.0
    ka = 2 * np.pi * freq_hz * HEAD_R / C_AIR
    w = 1.0 / (1.0 + np.exp(-(np.log(ka + 1e-9) - np.log(1.7)) / 0.55))
    denom = 20.0 * w
    if denom < 1e-6:
        return 0.0            # 低频：ILD 不含方位信息
    s = min(1.0, abs(ild) / denom)
    return float(np.rad2deg(np.arcsin(s)))


# ================================================================
# 五·补 相位锁定 —— ★ duplex theory 的真机制在这里
# ================================================================
def phase_lock_vs(freq_hz: float) -> float:
    """听神经相位锁定的同步强度（vector strength）。

    ★ REAL：低频几乎每个周期都放电（VS≈0.8~0.9），
      1~2 kHz 起急剧下降，>4 kHz 基本锁不住（VS<0.1）
    ★ 这就是【高频 ITD 失效】的物理原因，不是硬编码的频率切换
    """
    return float(1.0 / (1.0 + (freq_hz / 1200.0) ** 2))


def jnd_itd_us(freq_hz: float, base_us: float = ITD_JND_US) -> float:
    """ITD 最小可觉差随频率恶化。★ 相位锁定越差，时间差越测不准。"""
    vs = max(phase_lock_vs(freq_hz), 0.10)
    return base_us / vs


def angle_res_itd(theta_deg: float, freq_hz: float,
                  r: float = HEAD_R, c: float = C_AIR) -> float:
    """ITD 路径的角度分辨率（度）。Δθ = JND_ITD / (dITD/dθ)"""
    th = np.deg2rad(theta_deg)
    d_itd = (r / c) * (1.0 + np.cos(th))       # d/dθ (Woodworth)，s/rad
    d_per_deg = d_itd * np.pi / 180.0
    return float(jnd_itd_us(freq_hz) * 1e-6 / max(d_per_deg, 1e-12))


def angle_res_ild(theta_deg: float, freq_hz: float,
                  jnd_db: float = ILD_JND_DB) -> float:
    """ILD 路径的角度分辨率（度）。Δθ = JND_ILD / (dILD/dθ)

    ★ 低频衍射 → dILD/dθ 极小 → 分辨率极差（ILD 在低频没有方位信息）
    """
    th = np.deg2rad(theta_deg)
    ka = 2 * np.pi * freq_hz * HEAD_R / C_AIR
    w = 1.0 / (1.0 + np.exp(-(np.log(ka + 1e-9) - np.log(1.7)) / 0.55))
    d = 20.0 * w * np.cos(th) * np.pi / 180.0     # dB/deg
    if abs(d) < 1e-6:
        return float("inf")
    return float(jnd_db / abs(d))


def cross_corr_peak(left: np.ndarray, right: np.ndarray, sr: int) -> float:
    """★ 对照指标：互相关峰值高度。用于检验"是不是真锁上了"。"""
    a = left - left.mean(); b = right - right.mean()
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    return float(np.dot(a, b) / (np.sqrt(np.dot(a, a) * np.dot(b, b)) + 1e-12))
