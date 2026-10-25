#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★47 修测量层：真 pitch tracker（YIN-like + 逐周期）
================================================================
★★ 起因：★46 可信度扫描把"学会了"打碎，根源在【测量层】

  病灶1  F0 测成 2 倍
     f0_base [110, 138, 170] → 测得 [219, 275, 339] ≈ 2×
     ★ 亚谐波锁定：自相关在 T/2 处也高 → 取到半周期

  病灶2  jitter 恒 0
     参数 [0, 0.005, 0.02, 0.05] → 全测出 0，只有 0.08 才 0.0053
     ★★ 真因（我查到的）：帧 30ms / hop 10ms → 相邻帧重叠 2/3
        → 相邻帧 F0 高度相关 → diff 被平滑 → jitter 恒 0
     ★ 且自相关 lag 是整数：F0=200Hz 时 T=80 samples
        真人 jitter 0.9% = 0.72 samples < 1 sample 量化步长
        → 物理上就测不出

★ 修法
  ① CMNDF（累积均值归一化差分函数，YIN 的核心）
     ★ 它取【第一个】低于阈值的局部最小，天然抗亚谐波
     ★ 普通自相关取全局最大 → 容易被 2T 处的峰骗
  ② 抛物线插值 → 亚采样精度（可到 ~0.1 sample）
  ③ jitter 改用【逐周期】T 序列，不是相邻帧 F0
     T_i = 峰[i+1] - 峰[i]，jitter = mean|ΔT| / mean(T)

★★★ 验证方式：合成注入 ground truth
     ★ 自己造一个已知 F0、已知 jitter 的信号
     ★ 看测量能不能【恢复】已知值
     ★ 这是唯一能证明"测量层修好了"的办法 —— 不能靠看真音频觉得合理
"""
from __future__ import annotations
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

FS = 16000


# =================================================================
# 一、CMNDF（YIN 核心）+ 抛物线插值
# =================================================================
def diff_function(x: np.ndarray, w: int) -> np.ndarray:
    """d[k] = Σ (x[i] - x[i+k])² —— 差分函数"""
    d = np.zeros(w)
    for k in range(w):
        diff = x[:w - k] - x[k:w] if k > 0 else x[:w]
        # 用重叠部分，避免长度不等
        n = len(x) - k
        diff = x[:n] - x[k:k + n]
        d[k] = float(np.dot(diff, diff))
    return d


def cmndf(d: np.ndarray) -> np.ndarray:
    """
    ★ 累积均值归一化差分函数 d'[k] = d[k] / ((1/k)·Σ_{j≤k} d[j])
      ★ 这是 YIN 抗亚谐波的关键：
        普通自相关在 2T 处也高；CMNDF 归一化后 T 处的谷更深
    """
    out = np.zeros_like(d)
    run = np.cumsum(d)
    k = np.arange(1, len(d) + 1)
    out[0] = 1.0
    out[1:] = d[1:] / (run[1:] / k[1:])
    out[~np.isfinite(out)] = 1.0
    return out


def parabolic_interp(d: np.ndarray, k: int) -> float:
    """★ 抛物线插值：把整数 lag 细化到亚采样"""
    if k <= 0 or k >= len(d) - 1:
        return float(k)
    a, b, c = d[k - 1], d[k], d[k + 1]
    den = a - 2.0 * b + c
    if abs(den) < 1e-12:
        return float(k)
    shift = 0.5 * (a - c) / den
    if abs(shift) > 1.0:      # ★ 限幅，防止插值飞掉
        shift = np.sign(shift) * 1.0
    return float(k) + shift


def yin_f0(x: np.ndarray, fs: int = FS, fmin: float = 70.0,
           fmax: float = 400.0, thresh: float = 0.15) -> float:
    """
    ★ YIN-like 单帧 F0
      取【第一个】CMNDF 低于 thresh 的局部最小 —— 不是全局最大
    """
    x = np.asarray(x, float)
    n = len(x)
    if n < 64:
        return 0.0
    x = x - x.mean()
    if np.sqrt(np.mean(x ** 2)) < 1e-9:
        return 0.0
    tau_max = min(int(fs / fmin), n // 2)
    tau_min = max(int(fs / fmax), 2)
    if tau_max <= tau_min + 2:
        return 0.0
    # 半帧长度做差分，留出 k 的搜索空间
    w = min(n // 2, tau_max + 2)
    d = diff_function(x, w)
    dd = cmndf(d)
    # ★ 找第一个低于阈值的局部最小
    for k in range(tau_min, min(tau_max, len(dd) - 1)):
        if dd[k] < thresh and dd[k] <= dd[k + 1] and dd[k] <= dd[k - 1]:
            return fs / parabolic_interp(dd, k)
    # 兜底：取最低点（但要报告）
    seg = dd[tau_min:min(tau_max, len(dd))]
    if len(seg) == 0:
        return 0.0
    k = int(np.argmin(seg)) + tau_min
    return fs / parabolic_interp(dd, k) if dd[k] < 0.6 else 0.0


def yin_track(x: np.ndarray, fs: int = FS, win_ms: float = 40.0,
              hop_ms: float = 10.0, fmin: float = 70.0,
              fmax: float = 400.0) -> np.ndarray:
    w = int(fs * win_ms / 1000); h = int(fs * hop_ms / 1000)
    if len(x) < w:
        return np.array([])
    out = []
    for i in range(1 + (len(x) - w) // h):
        out.append(yin_f0(x[i * h:i * h + w], fs, fmin, fmax))
    return np.array(out)


# =================================================================
# 二、逐周期 T 序列 → 真 jitter
# =================================================================
def period_series(x: np.ndarray, fs: int = FS, fmin: float = 70.0,
                  fmax: float = 400.0, smooth_ms: float = 2.0) -> np.ndarray:
    """
    ★ 逐周期：在平滑后的波形上找峰，峰间距 = T
      ★ 这才是 jitter 的正确定义（cycle-to-cycle），不是帧间 F0 差
    """
    x = np.asarray(x, float)
    if len(x) < 256:
        return np.array([])
    x = x - x.mean()
    # 轻度平滑，去掉毛刺造成的假峰
    k = max(1, int(fs * smooth_ms / 1000))
    ker = np.ones(k) / k
    xs = np.convolve(x, ker, mode="same")
    # 找局部峰
    idx = np.where((xs[1:-1] > xs[:-2]) & (xs[1:-1] >= xs[2:]))[0] + 1
    if len(idx) < 4:
        return np.array([])
    # ★ 亚采样：抛物线插值峰位置
    pos = []
    for i in idx:
        if i <= 0 or i >= len(xs) - 1:
            continue
        a, b, c = xs[i - 1], xs[i], xs[i + 1]
        den = a - 2.0 * b + c
        shift = 0.0 if abs(den) < 1e-12 else 0.5 * (a - c) / den
        if abs(shift) > 1.0:
            shift = np.sign(shift) * 1.0
        pos.append(i + shift)
    pos = np.array(pos)
    T = np.diff(pos) / fs                      # 秒
    T = T[(T > 1.0 / fmax) & (T < 1.0 / fmin)]  # 只留合理周期
    return T


def jitter_from_T(T: np.ndarray) -> float:
    """★ jitter = mean|ΔT| / mean(T) —— 标准定义"""
    if len(T) < 4:
        return 0.0
    m = float(np.mean(T))
    if m <= 0:
        return 0.0
    return float(np.mean(np.abs(np.diff(T))) / m)


def shimmer_from_peaks(x: np.ndarray, fs: int = FS, fmin: float = 70.0,
                       fmax: float = 400.0) -> float:
    """★ shimmer（振幅微扰）：相邻周期峰值相对差 —— 顺带做出来"""
    x = np.asarray(x, float)
    if len(x) < 256:
        return 0.0
    xs = x - x.mean()
    k = max(1, int(fs * 2.0 / 1000))
    ker = np.ones(k) / k
    xsm = np.convolve(xs, ker, mode="same")
    idx = np.where((xsm[1:-1] > xsm[:-2]) & (xsm[1:-1] >= xsm[2:]))[0] + 1
    if len(idx) < 4:
        return 0.0
    amps = np.abs(xs[idx])
    T = np.diff(idx) / fs
    ok = (T > 1.0 / fmax) & (T < 1.0 / fmin)
    if ok.sum() < 3:
        return 0.0
    # 只保留构成合法周期的相邻峰对
    a = amps[:-1][ok]
    if len(a) < 3:
        return 0.0
    m = float(np.mean(np.abs(a)))
    return float(np.mean(np.abs(np.diff(a))) / m) if m > 0 else 0.0


# =================================================================
# 三、★ 自我验证：合成注入 ground truth
# =================================================================
# ★ 标准 jitter 定义（Praat local jitter）= mean|ΔT| / mean(T)
#   若注入 T_i = T0(1 + σ·ε_i)，ε 独立标准正态，则
#   mean|ΔT|/mean(T) = σ·E|ε_i − ε_{i−1}| = σ·(2/√π) ≈ 1.128·σ
#   ★ 所以想让【测得值 == 名义 jitter】，注入标准差必须是 σ = jitter/1.128
#   ★ 这两者差 12.8%，不校准就会以为测量有系统偏差
JITTER_SCALE = 2.0 / np.sqrt(np.pi)      # ≈ 1.1284


def synth_glottal(f0: float, jitter: float, dur: float = 0.6, fs: int = FS,
                  n_harm: int = 12, seed: int = 0, shimmer: float = 0.0,
                  calibrate: bool = True):
    """
    ★ 造一个已知 F0、已知 jitter 的信号（ground truth）
      ★ calibrate=True：注入 σ = jitter/1.1284，使测得的标准 jitter ≈ jitter
      ★ calibrate=False：直接注入 σ = jitter（会得到 1.128×jitter）
    """
    rng = np.random.default_rng(seed)
    T0 = 1.0 / f0
    jit_sigma = jitter / JITTER_SCALE if calibrate else jitter
    ts = []
    t = 0.0
    while t < dur:
        eps = rng.standard_normal()
        Ti = T0 * (1.0 + jit_sigma * eps)
        Ti = np.clip(Ti, T0 * 0.5, T0 * 2.0)
        ts.append(t)
        t += Ti
    ts = np.array(ts)
    # 每个周期放一个脉冲（带谐波）
    n = int(dur * fs)
    y = np.zeros(n)
    for i, ti in enumerate(ts):
        amp = 1.0 + shimmer * rng.standard_normal() if shimmer > 0 else 1.0
        c = int(ti * fs)
        if c < 0 or c >= n:
            continue
        # 用一个衰减的谐波堆叠当声门脉冲
        ln = min(int(T0 * fs * 1.5), n - c)
        if ln <= 1:
            continue
        tt = np.arange(ln) / fs
        env = np.exp(-tt / (T0 * 0.4))
        pulse = np.zeros(ln)
        for h in range(1, n_harm + 1):
            pulse += (1.0 / h) * np.sin(2 * np.pi * f0 * h * tt)
        y[c:c + ln] += amp * pulse * env
    return y, ts
