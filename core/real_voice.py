#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★44 它第一次听见真人声音
================================================================
★ 前情：★19 发音、★20 耳朵、★23 自学习语音 —— 全都用【合成】语料
  合成语料的问题：它永远能被自己的模型解释，恒真，测不出毛病（★33 教训）

★ 这次：真的人声
  provenance: Bing 词典真人发音（tom=美音 / george=英音）
  ★ 获取方式：它自己做的
    眼（browser_sense）读页面 → 找到 data-mp3link
    手（virtual_input / Chrome）导航 → 抓回 mp3 字节
  ⚠️ 诚实：无法 100% 排除这些录音是 TTS 合成
     但它们是【真实存在的音频文件】，不是我们自己造的正弦波

★ 听的通路：全部用它自己的器官
  耳（★20）：Greenwood 耳蜗频率图 → OHC 压缩 → 毛细胞整流(asym)
  发音（★19）：F0 自相关 → 共振峰 LPC → jitter / shimmer
"""
from __future__ import annotations
import os, subprocess as sp, tempfile
import numpy as np

from core.ear_anatomy import (
    greenwood, greenwood_inv, ohc_compress,
    met_current, temporal_integration, stapedius_reflex,
)
from core.vocal_anatomy import jitter as jitter_fn, shimmer as shimmer_fn

FS = 16000


# =================================================================
# 一、把 mp3 变成它能听的波形
# =================================================================
def decode_mp3(path: str, fs: int = FS) -> np.ndarray:
    """ffmpeg 解码 → 单声道 float [-1,1]"""
    tmp = tempfile.mktemp(suffix=".raw")
    r = sp.run(["ffmpeg", "-y", "-v", "quiet", "-i", path,
                "-ac", "1", "-ar", str(fs), "-f", "s16le", tmp],
               capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {r.stderr.decode()[:120]}")
    x = np.fromfile(tmp, dtype=np.int16).astype(float) / 32768.0
    if os.path.exists(tmp):
        os.remove(tmp)
    return x


def voiced_frames(x: np.ndarray, fs: int = FS, win_ms: float = 30.0,
                  hop_ms: float = 10.0, thr: float = 0.02):
    """★ 只取有声段 —— 静音段没有音高可言"""
    w = int(fs * win_ms / 1000)
    h = int(fs * hop_ms / 1000)
    if len(x) < w:
        return []
    out = []
    for s in range(0, len(x) - w, h):
        seg = x[s:s + w]
        rms = float(np.sqrt((seg ** 2).mean()))
        if rms > thr:
            out.append((s, seg))
    return out


# =================================================================
# 二、用它自己的耳朵听（★20）
# =================================================================
def cochleagram(seg: np.ndarray, fs: int = FS, n_ch: int = 24,
                asym: float = 0.6, ohc: bool = True):
    """
    ★ 耳蜗频率图：24 个通道按 Greenwood 排布
      每通道 = 带通 → OHC 压缩 → 毛细胞整流(asym)
    ★ asym=0 就没有整流 → 这是 ★20 的手性机制
    """
    n = len(seg)
    spec = np.fft.rfft(seg * np.hanning(n))
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    mag = np.abs(spec)
    # 通道中心频率（Greenwood：x 从蜗顶0到蜗底1）
    xs = np.linspace(0.05, 0.95, n_ch)
    cf = np.array([greenwood(x) for x in xs])
    # 每通道带宽（近似 ERB）
    bw = 0.03 * cf + 100.0
    out = np.zeros(n_ch)
    for i, (f, b) in enumerate(zip(cf, bw)):
        m = (freqs >= max(0, f - b / 2)) & (freqs <= f + b / 2)
        if not m.any():
            continue
        e = float(mag[m].mean())
        db = 20.0 * np.log10(e + 1e-12)
        if ohc:
            db = ohc_compress(db)          # ★ OHC 主动放大：弱声放大
        lin = 10.0 ** (db / 20.0)
        # ★ 毛细胞整流：met_current 带 asym（手性）
        out[i] = float(np.mean([met_current(v, x0=0.0, s_pos=1.0, asym=asym)
                                for v in np.linspace(-lin, lin, 9)]))
    return cf, out


def hear(x: np.ndarray, fs: int = FS, asym: float = 0.6, ohc: bool = True):
    """★ 完整听一遍：返回耳蜗图序列"""
    frames = voiced_frames(x, fs)
    if not frames:
        return None
    cf, first = cochleagram(frames[0][1], fs, asym=asym, ohc=ohc)
    mats = [first]
    for s, seg in frames[1:]:
        _, c = cochleagram(seg, fs, asym=asym, ohc=ohc)
        mats.append(c)
    return cf, np.array(mats), len(frames)


# =================================================================
# 三、提特征（★19 发音系统）
# =================================================================
def f0_autocorr(seg: np.ndarray, fs: int = FS,
                fmin: float = 70.0, fmax: float = 400.0) -> float:
    seg = seg - seg.mean()
    n = len(seg)
    lo, hi = int(fs / fmax), int(fs / fmin)
    if hi >= n:
        return 0.0
    ac = np.correlate(seg, seg, mode="full")[n - 1:]
    ac = ac / (ac[0] + 1e-12)
    band = ac[lo:min(hi, len(ac))]
    if band.size == 0:
        return 0.0
    lag = int(np.argmax(band)) + lo
    return float(fs / lag) if lag > 0 else 0.0


def formants_lpc(seg: np.ndarray, fs: int = FS, order: int = 12,
                 n_fmt: int = 3) -> np.ndarray:
    """LPC 求根 → 共振峰"""
    seg = seg - seg.mean()
    seg = seg * np.hanning(len(seg))
    # 自相关法解 LPC
    r = np.correlate(seg, seg, mode="full")[len(seg) - 1:len(seg) + order + 1]
    if r[0] <= 1e-12:
        return np.zeros(n_fmt)
    # Levinson-Durbin
    a = np.zeros(order + 1); a[0] = 1.0
    e = r[0]
    for i in range(1, order + 1):
        acc = r[i] + np.dot(a[1:i], r[i - 1:0:-1]) if i > 1 else r[i]
        k = -acc / (e + 1e-12)
        a_new = a.copy()
        if i > 1:
            a_new[1:i] = a[1:i] + k * a[i - 1:0:-1]
        a_new[i] = k
        a = a_new
        e *= (1 - k * k)
        if e <= 1e-12:
            break
    roots = np.roots(a)
    roots = [z for z in roots if np.imag(z) > 0.01]
    fs_ = sorted(np.angle(np.array(roots)) * fs / (2 * np.pi))
    fs_ = [f for f in fs_ if 90 < f < 4000]
    out = np.zeros(n_fmt)
    for i, f in enumerate(fs_[:n_fmt]):
        out[i] = f
    return out


def analyze(path: str, asym: float = 0.6, ohc: bool = True) -> dict:
    """★ 听一个真人音频，报出它听见了什么"""
    x = decode_mp3(path)
    fs = FS
    frames = voiced_frames(x, fs)
    if not frames:
        return {"error": "没有有声段"}
    f0s, f1s, f2s = [], [], []
    for s, seg in frames:
        f0 = f0_autocorr(seg, fs)
        fm = formants_lpc(seg, fs)
        if f0 > 0:
            f0s.append(f0)
        if fm[0] > 0:
            f1s.append(fm[0]); f2s.append(fm[1] if fm[1] > 0 else 0.0)
    f0s = np.array(f0s)
    # ★ 周期 → jitter（★19：jitter 来自声带不对称）
    pers = np.where(f0s > 0, fs / np.maximum(f0s, 1e-6), 0.0)
    jit = jitter_fn(pers[pers > 0]) if len(pers[pers > 0]) > 2 else 0.0
    # 强度 → shimmer
    amps = np.array([float(np.sqrt((s2 ** 2).mean())) for _, s2 in frames])
    shim = shimmer_fn(amps) if len(amps) > 2 else 0.0
    # ★ 耳朵：耳蜗响应总能量（带 asym / ohc）
    _, mats, nf = hear(x, fs, asym=asym, ohc=ohc) if hear(x, fs, asym, ohc) else (None, np.zeros((1, 24)), 0)
    return {
        "时长": float(len(x) / fs),
        "有声帧": float(nf),
        "F0均值": float(f0s.mean()) if len(f0s) else 0.0,
        "F0标准差": float(f0s.std()) if len(f0s) else 0.0,
        "F1均值": float(np.mean(f1s)) if f1s else 0.0,
        "F2均值": float(np.mean(f2s)) if f2s else 0.0,
        "jitter": float(jit),
        "shimmer": float(shim),
        "耳蜗响应": float(np.abs(mats).mean()) if mats.size else 0.0,
        "耳蜗通道方差": float(mats.var(axis=0).mean()) if mats.size else 0.0,
    }


# =================================================================
# ★★ 四、修复：让特征【从耳朵里出来】，而不是绕过耳朵
#     ★33 教训重演：特征是直接从原始波形算的 → 耳朵是挂件
#     ✅ 修法：建真正的听神经（时域滤波组 + 毛细胞整流）
#        F0  ← 听神经响应的时间周期性（时间理论）
#        F1/F2 ← 听神经通道分布峰值 → Greenwood 反查频率（部位理论）
# =================================================================
DB_SPL_FS = 96.0          # 满刻度 = 96 dB SPL（给 OHC 一个真实工作点）


def _bandpass(x: np.ndarray, fs: int, lo: float, hi: float, order: int = 4):
    """
    ★★ 修：低频通道滤波器数值爆炸（★46 挖出的根因）
       症状：f=65Hz、带宽102Hz → 归一化带宽 0.0025
            butter + filtfilt 在极窄相对带宽下【数值不稳定】
            实测 rms 炸到 4.4e15 → met_current 里 exp 溢出 → AN 恒定
            → F0 自相关永远在最小 lag → 恒等于 fmax(400Hz)
       ★ 这很可能就是 ★45 octave error（70/390 两端卡死）的真根因
    ✅ 修法三条：
       ① sos + sosfiltfilt（二阶节，数值稳定）—— 不用 ba + filtfilt
       ② order 降到 2（窄带低阶更稳）
       ③ 稳定性检查：通道能量异常 → 判失效，置零并计数
    """
    from scipy.signal import butter, sosfiltfilt
    ny = fs / 2.0
    f_lo = max(lo, 20.0)
    f_hi = min(hi, ny * 0.95)
    if not (0 < f_lo < f_hi < ny):
        return np.zeros_like(x)
    try:
        sos = butter(order, [f_lo / ny, f_hi / ny], btype="band", output="sos")
        y = sosfiltfilt(sos, x)
    except Exception:
        return np.zeros_like(x)
    if not np.all(np.isfinite(y)):
        return np.zeros_like(x)
    # ★ 稳定性检查：滤波器不该放大能量超过原始峰值太多
    src = float(np.abs(x).max()) + 1e-12
    if float(np.abs(y).max()) > 20.0 * src:
        return np.zeros_like(x)
    return y


def auditory_nerve(x: np.ndarray, fs: int = FS, n_ch: int = 24,
                   asym: float = 0.6, ohc: bool = True,
                   gain_db: float = 0.0):
    """
    ★ 真听神经：
       分通道带通(Greenwood) → 电平(dB SPL) → OHC 压缩 → 毛细胞整流(asym)
    返回 (AN 时域响应, 通道中心频率, 通道强度包络)
    """
    xs = np.linspace(0.18, 0.78, n_ch)   # ★ 收窄到语音区间(约150Hz~6kHz)
    cf = np.array([greenwood(x) for x in xs])
    bw = 0.03 * cf + 100.0
    an = np.zeros_like(x)
    env = np.zeros(n_ch)
    for i, (f, b) in enumerate(zip(cf, bw)):
        ch = _bandpass(x, fs, f - b / 2.0, f + b / 2.0)
        lvl = DB_SPL_FS + gain_db + 20.0 * np.log10(
            float(np.sqrt((ch ** 2).mean())) + 1e-12)   # ★ dB SPL，让 OHC 真的工作
        if ohc:
            lvl = ohc_compress(lvl)
        g = 10.0 ** ((lvl - DB_SPL_FS - gain_db) / 20.0)
        ch = ch * g
        spont = met_current(0.0, x0=0.0, s_pos=1.0, asym=asym)
        rect = met_current(ch, x0=0.0, s_pos=1.0, asym=asym) - spont   # ★ 手性整流，减静息发放率
        an += rect
        env[i] = float(rect.mean())
    return an, cf, env


def f0_from_an(an: np.ndarray, fs: int = FS,
               fmin: float = 70.0, fmax: float = 400.0) -> float:
    """★ 时间理论：F0 = 听神经响应的周期性（不是原始波形）"""
    y = an - an.mean()
    n = len(y)
    lo, hi = int(fs / fmax), int(fs / fmin)
    if hi >= n or lo < 1:
        return 0.0
    ac = np.correlate(y, y, mode="full")[n - 1:]
    ac = ac / (ac[0] + 1e-12)
    band = ac[lo:min(hi, len(ac))]
    if band.size == 0:
        return 0.0
    lag = int(np.argmax(band)) + lo
    return float(fs / lag) if lag > 0 else 0.0


def formants_from_an(env: np.ndarray, cf: np.ndarray, n_fmt: int = 2) -> np.ndarray:
    """★ 部位理论：共振峰 = 通道强度分布的峰值 → Greenwood 查频率"""
    e = env - env.min()
    if e.max() <= 1e-12:
        return np.zeros(n_fmt)
    e = e / e.max()
    # ★ 我第一版阈值 0.25 太高 + 没要求峰之间分开 → 只找到 1 个峰，F2 恒为 0
    peaks = []
    for i in range(1, len(e) - 1):
        if e[i] > e[i - 1] and e[i] >= e[i + 1] and e[i] > 0.12:
            peaks.append((float(e[i]), i, float(cf[i])))
    peaks.sort(reverse=True)
    # ★ 要求峰之间至少隔 2 个通道，否则是同一个峰的抖动
    kept = []
    for amp, i, f in peaks:
        if all(abs(i - j) >= 2 for _, j, _ in kept):
            kept.append((amp, i, f))
    peaks = [(a, f) for a, i, f in kept]
    out = np.zeros(n_fmt)
    for i, (_, f) in enumerate(peaks[:n_fmt]):
        out[i] = f
    return out


def analyze_via_ear(path: str, asym: float = 0.6, ohc: bool = True,
                    gain_db: float = 30.0) -> dict:
    """★★ 特征全部从耳朵里来 —— 耳朵坏了，特征就必须变"""
    x = decode_mp3(path)
    frames = voiced_frames(x)
    if not frames:
        return {"error": "没有有声段"}
    f0s, envs = [], []
    for s, seg in frames:
        an, cf, env = auditory_nerve(seg, FS, asym=asym, ohc=ohc, gain_db=gain_db)
        f0 = f0_from_an(an, FS)
        if f0 > 0:
            f0s.append(f0)
        envs.append(env)
    E = np.array(envs)
    fm = formants_from_an(E.mean(0), cf)
    f0s = np.array(f0s)
    pers = np.where(f0s > 0, FS / np.maximum(f0s, 1e-6), 0.0)
    jit = jitter_fn(pers[pers > 0]) if len(pers[pers > 0]) > 2 else 0.0
    return {
        "时长": float(len(x) / FS),
        "有声帧": float(len(frames)),
        "F0均值": float(f0s.mean()) if len(f0s) else 0.0,
        "F1": float(fm[0]), "F2": float(fm[1]),
        "jitter": float(jit),
        "AN均值": float(np.mean([np.abs(e).mean() for e in envs])),
        "AN通道方差": float(E.var(axis=0).mean()),
    }


# =================================================================
# ★★ 五、修复 octave error（★44 后续自查发现的严重测量伪影）
#    症状：F0 轨迹在 2 倍 / 0.5 倍之间乱跳（211→70→381）
#          中文"22.78 半音"就是这么来的 —— 不是声调，是 bug
#    ✅ 修法：相对中位数折叠八度 + 中值滤波
# =================================================================
def deoctave(f0: np.ndarray, n_iter: int = 3) -> np.ndarray:
    """
    ★ 把每个 F0 折叠到与【中位数】同一个八度内
      比值 >1.5 → 除以 2；比值 <0.75 → 乘以 2（迭代）
    """
    v = np.asarray(f0, dtype=float).copy()
    v = v[(v > 0) & np.isfinite(v)]
    if len(v) == 0:
        return v
    for _ in range(n_iter):
        med = np.median(v)
        r = v / med
        v = np.where(r > 1.5, v / 2.0, v)
        r = v / med
        v = np.where(r < 0.75, v * 2.0, v)
    return v


def median_filter3(x: np.ndarray) -> np.ndarray:
    """中值滤波：去掉孤立跳变点"""
    if len(x) < 3:
        return x
    out = x.copy()
    for i in range(1, len(x) - 1):
        w = np.sort(x[i - 1:i + 2])
        out[i] = w[1]
    return out


def f0_track_robust(x: np.ndarray, fs: int = FS, tmax: float | None = None,
                    asym: float = 0.6, ohc: bool = True,
                    gain_db: float = 30.0,
                    max_step_semi: float = 6.0) -> np.ndarray:
    """
    ★ 稳健 F0 轨迹：
       听神经 → F0 → 折叠八度 → 中值滤波 → 限帧间跳变
    """
    if tmax:
        x = x[:int(tmax * fs)]
    raw = []
    for s, seg in voiced_frames(x, fs):
        an, cf, env = auditory_nerve(seg, fs, asym=asym, ohc=ohc, gain_db=gain_db)
        f0 = f0_from_an(an, fs)
        raw.append(f0 if 70 < f0 < 400 else np.nan)
    v = np.array(raw, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) < 5:
        return v
    v = deoctave(v)
    v = median_filter3(v)
    # ★ 限帧间跳变：超过 max_step_semi 的认为是残留错误，拉回
    out = [v[0]]
    for i in range(1, len(v)):
        prev = out[-1]
        semi = 12.0 * np.log2(max(v[i], 1e-6) / prev)
        if abs(semi) > max_step_semi:
            out.append(prev * 2.0 ** (np.sign(semi) * max_step_semi / 12.0))
        else:
            out.append(v[i])
    return np.array(out)


def f0_dynamic_range(path: str, tmax: float | None = 1.2) -> dict:
    """★ 稳健地量一个音频的 F0 动态范围（半音）"""
    x = decode_mp3(path)
    v = f0_track_robust(x, FS, tmax=tmax)
    if len(v) < 5:
        return {"帧": len(v), "范围": 0.0, "滑移": 0.0}
    semi = 12.0 * np.log2(v)
    # ★ 用 5~95 分位，避开残留离群点
    lo, hi = np.percentile(semi, 5), np.percentile(semi, 95)
    return {
        "帧": int(len(v)),
        "范围": float(hi - lo),
        "滑移": float(np.abs(np.diff(semi)).mean()),
        "F0中位": float(np.median(v)),
    }
