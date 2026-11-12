#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instrument —— 测量（★79）

════ 为什么这一课不自查也会对 ════
  前面几课我反复栽在同一个坑：环境是我设计的，我一不小心就把"权衡"
  写没了（增益和污染同向 → 数学上不可能有权衡）。第六次了。

  这一课的解法：**环境不由我设计，由自然科学给。**

  三条硬定律，全是真的，不是我编的参数：

  ① 奈奎斯特–香农采样定理
     fs < 2·f_max → 高频折叠成低频假峰（混叠）。定理，不是假设。

  ② Gabor / 时频不确定性  Δt·Δf ≥ 1/(4π)
     频率分辨率 Δf ≈ 1/T_win，时间分辨率 Δt ≈ T_win。
     想频率准就要长窗，想抓住瞬态就要短窗。**乘积有下限。**

  ③ Allan 方差的碗形曲线
     白噪声：平均 K 段 → 抖动 ∝ 1/√K（改善）
     1/f 噪声：段间相关（慢漂移），平均不改善，观测越久越被带偏
     → 存在【最优平均次数】，不是"平均越多越好"

════ 真实的关键：连续长记录，不是 K 次独立采样 ════
  观测是一条连续记录（长 K·T_win），切成 K 段。
  白噪声在段间独立 → 平均改善 √K。
  1/f 噪声在段间相关（慢漂移）→ 平均不改善，且总时长越久漂移越大。
  ★ 这是 Allan 碗形的物理来源。改成独立采样这个效应就没了（我第一版就错了）。

════ 她要操控的三个旋钮 ════
  fs_mult  采样率（相对奈奎斯特 2·f_max）
  T_win    单段观测窗长（秒）
  K        平均段数
  预算 B = fs · T_win · K = 总样本数，三者抢同一份预算
"""

from __future__ import annotations
import numpy as np


def _pink(N, rng, alpha=1.0):
    """1/f 噪声 —— 频域 1/sqrt(f) 整形。低频功率巨大，这是真实的"""
    if N < 4:
        return rng.normal(0, 1, N)
    f = np.fft.rfftfreq(N)
    f = np.maximum(f, f[1])
    spec = 1.0 / np.power(f, alpha / 2.0)   # alpha=1 flicker / alpha=2 随机游走
    ph = rng.uniform(0.0, 2.0 * np.pi, len(f))
    x = np.fft.irfft(spec * np.exp(1j * ph), N)
    sd = np.std(x)
    return x / sd if sd > 1e-12 else x


def make_signal(fs, T, seed, f1=11.0, f2=31.0, snr=3.0, pink_ratio=0.5,
                transient=True, alpha=1.5):
    N = max(16, int(round(fs * T)))
    t = np.arange(N) / fs
    # ★ 整周期采样：把频率吸附到最近的 FFT bin。
    #   真实测量的标准做法 —— 否则非整数周期的正弦残留 ∝1/N 会盖过
    #   噪声本身的 1/√N，Allan 斜率就测不准（我第一版就栽在这）。
    df = fs / N
    f1 = max(df, round(f1 / df) * df)
    f2 = max(df, round(f2 / df) * df)
    rng = np.random.default_rng(seed)
    sig = np.sin(2 * np.pi * f1 * t) + 0.6 * np.sin(2 * np.pi * f2 * t)
    t_true = -1.0
    if transient:
        tc = float(rng.uniform(0.15, 0.85) * T)
        w = 0.02
        sig = sig + 2.0 * np.exp(-((t - tc) ** 2) / (2 * w * w))
        t_true = tc
    w_n = rng.normal(0, 1, N)
    p_n = _pink(N, rng, alpha)
    noise = np.sqrt(max(0.0, 1 - pink_ratio)) * w_n + np.sqrt(pink_ratio) * p_n
    noise = noise / (np.std(noise) + 1e-12)
    sig = sig + noise * (np.std(sig) / max(snr, 1e-6))
    return t, sig, t_true, (f1, f2)


def _parabolic(mag, i):
    if i <= 0 or i >= len(mag) - 1:
        return float(i)
    a, b, c = mag[i - 1], mag[i], mag[i + 1]
    d = a - 2 * b + c
    return float(i) + (0.0 if abs(d) < 1e-15 else 0.5 * (a - c) / d)


def estimate_freq(sig, fs, f_lo=5.0, f_hi=45.0):
    """
    Hann 窗 → FFT → 局部极大峰 → 抛物插值
    ★ f_hi 必须卡在奈奎斯特以内，否则混叠区会被当成真峰搜到
    ★ f_lo = 高通：真实测量都会滤掉 1/f 主导的低频段，否则盖过信号峰
    """
    f_hi = min(f_hi, 0.98 * fs / 2.0)
    x = sig - np.mean(sig)
    if len(x) < 8:
        return None
    w = np.hanning(len(x))
    sp = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), 1.0 / fs)
    lo = int(np.searchsorted(fr, f_lo))
    hi = int(np.searchsorted(fr, f_hi))
    if hi - lo < 6:
        return None
    seg = sp[lo:hi]
    cand = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]]
    cand.sort(key=lambda i: -seg[i])
    chosen = []
    for i in cand:
        if all(abs(i - j) >= 3 for j in chosen):     # 主瓣不重复计数
            chosen.append(i)
        if len(chosen) == 2:
            break
    if len(chosen) < 2:
        return None
    chosen.sort()
    df = fr[1] - fr[0]
    out = []
    for j in chosen:
        k = lo + j
        out.append((fr[0] + _parabolic(sp, k) * df))
    return sorted(out)


def detect_transient(rms_list, seg_len_s, t_true, thr=1.15):
    """
    ★ 跨段比较，不是段内绝对阈值。
      瞬态能量固定，段越长 → 背景能量 ∝T_win 越大 → 瞬态段 RMS 越接近其他段。
      ratio = max(rms)/median(rms)  随 T_win 增大而趋向 1 → 越来越检不出。
      这就是 Gabor 极限在时域的那一半，是数学，不是我的设定。
    """
    r = np.asarray(rms_list, dtype=float)
    if len(r) < 2 or t_true < 0:
        return 0.0, 0.0
    med = float(np.median(r))
    k = int(np.argmax(r))
    ratio = float(r[k] / (med + 1e-9))
    seg_true = int(t_true / seg_len_s)
    if seg_true >= len(r):
        seg_true = len(r) - 1
    ok = 1.0 if (ratio > thr and abs(k - seg_true) <= 0) else 0.0
    fp = 1.0 if (ratio > thr and abs(k - seg_true) > 0) else 0.0
    return ok, fp


def measure(fs, T_win, K, seed=0, f1=11.0, f2=31.0, snr=3.0,
            pink_ratio=0.5, transient=True, f_max=40.0, alpha=1.5):
    """
    连续长记录 → 切 K 段。
      · 频率：各段 FFT 取中位（长窗准）
      · 瞬态：跨段 RMS 比较（短窗才抓得住）
      · 零偏：全部样本均值（真值 0）—— ★ Allan 碗形的作用对象
              白噪声 ∝1/√N 改善；1/f 慢漂移不改善，观测越久越被带偏
    """
    T_tot = T_win * K
    _, sig, t_true, (f1a, f2a) = make_signal(fs, T_tot, seed, f1, f2, snr, pink_ratio, transient, alpha)
    n_seg = int(round(T_win * fs))
    if n_seg < 8 or n_seg * K > len(sig):
        return {"freq_err": 1.0, "trans": 0.0, "fp": 1.0, "bias_err": 1.0}
    fests, rms_list = [], []
    for k in range(K):
        s_ = sig[k * n_seg: (k + 1) * n_seg]
        fr = estimate_freq(s_, fs)
        if fr:
            fests.append(fr)
        rms_list.append(float(np.sqrt(np.mean(s_ ** 2))))
    if len(fests) < 1:
        return {"freq_err": 1.0, "trans": 0.0, "fp": 1.0, "bias_err": 1.0}
    A = np.array(fests)
    est1 = np.median(A[:, 0])
    est2 = np.median(A[:, -1]) if A.shape[1] > 1 else est1
    fe = float(np.mean([abs(est1 - f1a) / f1a, abs(est2 - f2a) / f2a]))
    ok, fp = detect_transient(rms_list, T_win, t_true)
    sd = float(np.std(sig))
    be = float(abs(np.mean(sig)) / (sd + 1e-9))     # 零偏（真值 0）/ 信号尺度
    return {"freq_err": fe, "trans": ok, "fp": fp, "bias_err": be}


def score(fs_mult, T_win, K, B=4096.0, f_max=40.0, **kw):
    fs = fs_mult * 2.0 * f_max
    cost = fs * T_win * K
    m = measure(fs, T_win, K, f_max=f_max, **kw)
    s = (0.40 * float(np.exp(-3.0 * m["freq_err"]))
         + 0.30 * m["trans"]
         + 0.30 * float(np.exp(-40.0 * m["bias_err"]))
         - 0.15 * m["fp"])
    pen = 0.8 * max(0.0, cost / B - 1.0)
    return float(s - pen), cost, m
