#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★47 惊吓反射层 —— 爆炸就是惊吓
================================================================
★★★ 用户洞察（本轮的起因）
    "知道了，为什么爆炸了，爆炸是惊吓。"

★ 我 ★46 修的那个 bug：低频通道滤波器数值爆炸（rms 4.4e15）
    我加的修法 = 【后置检查】：输出 > 20× 原始峰值 → 判失效，置零
    ★ 这是【丢弃】，不是【保护】

★ 用户点破的：生物早就有这个机制 —— 惊吓反射
    输入超出动态范围 → 不是丢弃，是【前置衰减 + 全身动员】

★★ 所以我 ★46 的修法其实是"重新发现了生命已有的机制，但做成了劣化版"
    生物：前置衰减（镫骨肌反射 60ms 潜伏，衰减 15dB）→ 信息保留（压缩）
    我的：后置置零                                    → 信息全丢

★ 本轮要验证的对照（三方案）
    ① 无保护          → 溢出/爆炸
    ② 后置置零（★46）  → 停爆炸，但信息全丢
    ③ 前置增益控制（生物式，带潜伏期） → 不爆炸，信息保留

★ 惊吓反射真参数（REAL）
    通路   耳蜗核 → 脑桥尾侧网状核(PnC) → 脊髓，仅 3~4 突触
    潜伏期 人类 10~30 ms    ★ 远快于皮层听觉反应(~100ms)
    阈值   80~90 dB SPL 以上才惊跳
    PPI    前脉冲(弱) 先到 → 抑制惊吓 30~70%
           有效间隔 30~500 ms，★ 最优 120 ms
           PPI 缺失 = 感觉门控缺陷（精神分裂症）
    习惯化 重复刺激 → 幅度下降

★ 关键：惊吓是【脑干】通路，绕过皮层，所以快
    ★ 这跟 ★28 前庭 VOR(10ms) << 视觉(80ms) 是同一个道理
"""
from __future__ import annotations
import numpy as np

FS = 16000


# =================================================================
# 一、惊吓反射（脑干通路）
# =================================================================
STARTLE_LATENCY_MS = 20.0      # 人类 10~30 ms 的中位（REAL）
STARTLE_THRESH_DB = 85.0       # 惊吓阈值 80~90 dB SPL（REAL）
CORTEX_LATENCY_MS = 100.0      # 皮层听觉反应 ~100 ms（对照用）


def startle_amplitude(db_spl: float, threshold: float = STARTLE_THRESH_DB,
                      slope: float = 0.06) -> float:
    """
    ★ 惊吓幅度-强度曲线：阈值以下 = 0，以上近线性增长后饱和
      REAL：80~90 dB 起跳，110+ dB 饱和
    """
    if db_spl <= threshold:
        return 0.0
    return float(np.tanh(slope * (db_spl - threshold)))


def startle_latency(db_spl: float,
                    base: float = STARTLE_LATENCY_MS) -> float:
    """
    ★ 强度越高潜伏期越短（REAL：强刺激募集更快）
      85 dB → ~30 ms，120 dB → ~12 ms
    """
    if db_spl <= STARTLE_THRESH_DB:
        return np.inf
    return float(base * (1.0 - 0.35 * np.tanh((db_spl - 85.0) / 25.0)))


# =================================================================
# 二、PPI（前脉冲抑制）——★ 感觉门控
# =================================================================
def ppi_ratio(isi_ms: float, prepulse_db: float = 70.0,
              pulse_db: float = 115.0) -> float:
    """
    ★ 前脉冲抑制：弱刺激先到 → 强刺激的惊吓被抑制
      REAL：
        有效窗口 30~500 ms
        ★ 最优 120 ms（抑制 30~70%）
        <30 ms 无效（前脉冲还在传导中，来不及门控）
        >500 ms 无效（门控已关闭，这叫 prepulse facilitation 反而易化）
    """
    if isi_ms < 30.0 or isi_ms > 500.0:
        return 0.0            # 无抑制
    # 以 120 ms 为峰的高斯窗
    peak, width = 120.0, 130.0
    shape = float(np.exp(-((isi_ms - peak) ** 2) / (2 * width ** 2)))
    # 前脉冲越明显（相对主脉冲）抑制越强
    gap = max(0.0, pulse_db - prepulse_db)
    depth = float(np.clip(0.15 + 0.035 * gap, 0.0, 0.70))
    return depth * shape


def startle_with_ppi(pulse_db: float, prepulse_db: float | None = None,
                     isi_ms: float = 0.0) -> float:
    """★ 有前脉冲时的实际惊吓幅度"""
    a = startle_amplitude(pulse_db)
    if prepulse_db is None:
        return a
    return a * (1.0 - ppi_ratio(isi_ms, prepulse_db, pulse_db))


# =================================================================
# 三、习惯化
# =================================================================
def habituation(n_trials: int, db_spl: float,
                rate: float = 0.12, floor: float = 0.25) -> np.ndarray:
    """
    ★ 重复刺激 → 惊吓幅度下降（habituation）
      REAL：10~20 次后降到基线的 30~50%
      ★ 但突然换一个更强的刺激会 dishabituate（去习惯化）
    """
    base = startle_amplitude(db_spl)
    if base <= 0:
        return np.zeros(n_trials)
    out = []
    for i in range(n_trials):
        decay = floor + (1.0 - floor) * np.exp(-rate * i)
        out.append(base * decay)
    return np.array(out)


def dishabituation(hab_amplitude: float, new_db: float, old_db: float) -> float:
    """★ 去习惯化：新刺激明显更强 → 惊吓恢复"""
    if new_db <= old_db + 5.0:
        return hab_amplitude
    boost = float(np.clip((new_db - old_db) / 30.0, 0.0, 1.0))
    return hab_amplitude + (startle_amplitude(new_db) - hab_amplitude) * boost


# =================================================================
# 四、★★★ 三方案对照：无保护 / 后置置零 / 前置增益控制
# =================================================================
def unprotected(x: np.ndarray, ceiling: float = 1e6) -> np.ndarray:
    """
    ① 无保护：信号直接进入后续处理
      ★ 超范围就溢出（这就是 ★46 的爆炸）
    """
    y = x * 1e4          # 模拟"后续模块放大"
    y = np.where(np.abs(y) > ceiling, np.sign(y) * np.inf, y)
    return y


def post_clip(x: np.ndarray, ceiling: float = 1e6,
              src_peak_mult: float = 20.0) -> tuple:
    """
    ② 后置置零（★46 的修法）：处理完发现超范围 → 整段判失效置零
      ★ 停止了爆炸，但【信息全丢】
    """
    y = x * 1e4
    src = float(np.abs(x).max()) + 1e-12
    bad = bool(np.abs(y).max() > src_peak_mult * src * 1e4 / 1e4)
    bad = bool(np.abs(y).max() > ceiling)
    return (np.zeros_like(y) if bad else y), bad


def pre_gain_control(x: np.ndarray, latency_ms: float = 60.0,
                     attack_db: float = 15.0, ceiling: float = 1e6,
                     fs: int = FS, tau_ms: float = 30.0) -> tuple:
    """
    ③ ★ 前置增益控制（生物式，镫骨肌反射）
      ★ 关键区别：在【进后续模块之前】衰减，且有【潜伏期】
        → 潜伏期内会有短暂过冲（REAL：这就是大声第一下特别震的原因）
        → 潜伏期后衰减到位
      ★ 信息【保留】（只是压缩了），不是丢弃
    """
    n = len(x)
    lat = int(latency_ms * fs / 1000.0)
    tau = max(1.0, tau_ms * fs / 1000.0)
    # 包络检测
    win = max(1, int(5 * fs / 1000))
    env = np.array([float(np.sqrt((x[max(0, i - win):i + win] ** 2).mean()))
                    for i in range(0, n, win)])
    if len(env) == 0:
        return x * 1e4, 0.0
    env = np.maximum(env, 1e-9)
    lvl = 20.0 * np.log10(env)
    ref_lvl = np.percentile(lvl, 90)
    # 超过参考电平的部分要被压掉 attack_db
    excess = np.maximum(0.0, lvl - ref_lvl)
    atten_db = attack_db * (excess / max(attack_db, 1e-9)) ** 0.5
    atten_db = np.minimum(atten_db, attack_db)
    # ★ 潜伏期：衰减是逐步建立的一阶过程，不是瞬间
    g_db = np.zeros(len(atten_db))
    for i in range(1, len(g_db)):
        g_db[i] = g_db[i - 1] + (atten_db[i] - g_db[i - 1]) * (win / tau)
    # 前 lat 个样本完全没衰减（★ 这就是过冲）
    g_db[:max(1, lat // win)] = 0.0
    gain = 10.0 ** (-g_db / 20.0)
    gain_up = np.repeat(gain, win)[:n]
    if len(gain_up) < n:
        gain_up = np.concatenate([gain_up, np.full(n - len(gain_up), gain_up[-1])])
    y = x * gain_up * 1e4
    bad = bool(np.abs(y).max() > ceiling)
    return y, bad


def info_retained(y: np.ndarray) -> float:
    """
    ★ 信息保留度：非 NaN、非 inf、非常数 的样本占比
      ★ 置零会让它降到 0，压缩不会
    """
    if len(y) == 0:
        return 0.0
    finite = np.isfinite(y)
    if not finite.any():
        return 0.0
    nonzero = np.abs(y[finite]) > 1e-12 * max(np.abs(y[finite]).max(), 1e-12)
    return float(nonzero.mean())
