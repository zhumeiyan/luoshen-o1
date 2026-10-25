#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★57 学 → 说 → 听 · 全链路闭环
================================================================
★★ 为什么必须有这一层
    ★53 学的是【参数】，★55 学的是【轮流结构】，★56 把轮流合成成音频
    但三者从未真正串起来：
      ★53 学到的参数，从来没有真正驱动过波形
      ★56 的波形，用的是硬编码的 f0=140 / jitter=0.005，不来自学习

    ⚠️ 所以「学 → 说」这一段是断的：
       学完参数如果只改了数字、没改声音，那 ★53 就是一场数字游戏
       （★33 眼睛是挂件、★44 耳朵是挂件、★56 参数当结论，同族风险）

    本层要求：
       SpeakerParams（★53 学到的）→ 波形 → 耳朵（★44 听神经）→ ear_vec
       ★ 全程不容许任何一环读参数表，只能读波形

★★★ 硬依赖
    耳朵 asym=0（毛细胞不整流）→ 必须导致特征变了/测不出
    否则说明 ear_features 没真的走耳朵
"""
import numpy as np
from scipy.signal import lfilter

EAR_KEYS = ["pause_rate", "pause_cv", "f0_med", "f0_range_semi",
            "f0_slide", "jitter"]

SR = 16000


# ───────────────────────────────────────── 声源：F0 轮廓
def f0_contour(dur, f0_base, f0_span_semi=0.0, f0_end=0.0, rng=None, sr=SR):
    """★ 句内 F0 轮廓（这是 ★53 学的 f0_span / f0_end 真正起作用的地方）

    f0_span_semi  句内音高变化范围（半音）REAL 中文 6.87 / 英文 8.53
    f0_end        句末漂移（负=下降）      REAL 朗读约 −0.06
    叠加：基线 + 音节级起伏 + 句末漂移 + 微扰
    """
    rng = rng or np.random.default_rng(0)
    n = int(dur * sr)
    t = np.arange(n) / sr
    # 句内位置 0~1
    u = t / max(dur, 1e-6)
    # ① 句末漂移：从 1 漂到 (1+f0_end)
    drift = 1.0 + f0_end * u
    # ② 音节级起伏：REAL 约 5 音节/秒（★19）
    syl_rate = 5.0
    amp = f0_span_semi / 12.0          # 半音 → 八度比例
    # 五度（7半音）的整数倍最自然，这里用音节正弦 + 随机相位
    wob = (np.sin(2 * np.pi * syl_rate * t + rng.uniform(0, 6.28)) * 0.5
           + np.sin(2 * np.pi * syl_rate * 0.5 * t + rng.uniform(0, 6.28)) * 0.5)
    f0 = f0_base * drift * (2.0 ** (amp * wob))
    return np.clip(f0, 50.0, 500.0)


def glottal_impulses(f0, jitter_amt=0.005, rng=None, sr=SR):
    """按 F0 轮廓生成脉冲串（★ jitter 来自左右声带不对称，★19 手性）"""
    rng = rng or np.random.default_rng(0)
    n = len(f0)
    imp = np.zeros(n)
    t = 0.0
    k = 0
    while t < n / sr:
        i = int(t * sr)
        if i >= n:
            break
        imp[i] = 1.0
        f = f0[i]
        # ★ 逐周期 jitter（REAL 定义：相邻周期差）
        t += (1.0 / max(f, 20.0)) * (1.0 + rng.normal(0.0, jitter_amt))
        k += 1
        if k > 20000:
            break
    return imp


def _resonator(x, f, bw, sr=SR):
    f = float(np.clip(f, 50.0, sr * 0.45))
    r = float(np.exp(-np.pi * max(bw, 10.0) / sr))
    th = 2.0 * np.pi * f / sr
    a = np.array([1.0, -2.0 * r * np.cos(th), r * r])
    return lfilter(np.array([1.0 - r]), a, x)


VOWELS = {
    "a": (730, 1090), "i": (270, 2290), "u": (300, 870),
    "e": (530, 1840), "o": (570, 840), "schwa": (500, 1500),
}


def synth_utterance(sp, dur, seed=0, sr=SR):
    """★ 用【学到的 SpeakerParams】合成一句话 —— 参数真正驱动波形"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    if n <= 1:
        return np.zeros(max(n, 1))
    f0 = f0_contour(dur, sp.f0_base, sp.f0_span * 12.0, sp.f0_end, rng, sr)
    imp = glottal_impulses(f0, sp.jitter, rng, sr)
    L = max(int(sr * 0.005), 8)
    k = np.arange(L)
    pulse = (k / L) * np.exp(-k / (L * 0.25))
    pulse /= (pulse.sum() + 1e-12)
    src = np.convolve(imp, pulse, mode="same")

    n_syl = max(1, int(dur * 5.0))
    edges = np.linspace(0, n, n_syl + 1).astype(int)
    out = np.zeros(n)
    vs = list(VOWELS.keys())
    prev = None
    for i in range(n_syl):
        a, b = edges[i], edges[i + 1]
        if b <= a:
            continue
        v = vs[int(rng.integers(0, len(vs)))]
        f1, f2 = VOWELS[v]
        f1s, f2s = prev if prev is not None else (f1, f2)
        s = src[a:b]
        seg1 = (_resonator(s, f1s, 80.0, sr) + _resonator(s, f2s, 120.0, sr) * 0.5
                + _resonator(s, 2500.0, 200.0, sr) * 0.18)
        seg2 = (_resonator(s, f1, 80.0, sr) + _resonator(s, f2, 120.0, sr) * 0.5
                + _resonator(s, 2500.0, 200.0, sr) * 0.18)
        w = np.linspace(0, 1, b - a)          # 协同发音过渡（★19 实测 47.5%）
        seg = seg1 * (1 - w) + seg2 * w
        env = np.sin(np.pi * np.linspace(0, 1, b - a)) ** 0.6
        out[a:b] += seg * env
        prev = (f1, f2)

    # ★ 句内停顿：pause_prob / pause_mean / pause_sigma（★53 学的）
    m = int(sr * 0.02)
    i = 0
    while i < n_syl - 1:
        if rng.random() < sp.pause_prob:
            dur_p = float(np.clip(rng.lognormal(np.log(max(sp.pause_mean, 1e-3)),
                                                max(sp.pause_sigma, 0.05)), 0.02, 0.8))
            a = edges[i + 1]
            b = min(a + int(dur_p * sr), n)
            if b > a:
                fade = min(m, (b - a) // 2)
                win = np.ones(b - a)
                if fade > 0:
                    win[:fade] = np.linspace(1, 0, fade)
                    win[-fade:] = np.linspace(0, 1, fade)
                out[a:b] *= win
        i += 1
    # ★ 呼吸：breath_prob（低幅噪声，不是静音）
    if rng.random() < sp.breath_prob and n > sr * 0.3:
        a = int(rng.uniform(0, n - sr * 0.2))
        b = a + int(sr * 0.15)
        out[a:b] += rng.normal(0, 0.05, b - a) * np.hanning(b - a)
    mx = np.abs(out).max()
    return out / (mx + 1e-12) * 0.8


def synth_with_repairs(sp, dur, seed=0, sr=SR):
    """★ 自我修正 repair_prob（★23/★53）：被打断后重说一小段"""
    rng = np.random.default_rng(seed)
    segs = []
    t = 0.0
    while t < dur:
        if segs and rng.random() < sp.repair_prob:
            # 回退一点，重说（REAL：自我修正是从对话上文隐式学来的）
            rep = min(0.35, dur - t)
            segs.append(synth_utterance(sp, rep, seed=seed + len(segs) * 17, sr=sr))
            t += rep
        else:
            d = min(rng.uniform(0.8, 1.8), dur - t)
            if d < 0.1:
                break
            segs.append(synth_utterance(sp, d, seed=seed + len(segs) * 31, sr=sr))
            t += d
    return np.concatenate(segs) if segs else np.zeros(int(dur * sr))


def render_dialogue(sp, events, sr=SR, seed=0):
    """用【同一个学到的 sp】渲染 ★55 的轮流事件 → 双声道音频"""
    if not events:
        return np.zeros((2, 1))
    total = max(e[2] for e in events) + 0.4
    n = int(total * sr)
    wav = np.zeros((2, n))
    for i, (spk, st, en, is_bc) in enumerate(events):
        d = en - st
        if d <= 0.02:
            continue
        seg = synth_with_repairs(sp, d, seed=seed * 1000 + i * 7, sr=sr)
        a, b = int(st * sr), int(en * sr)
        seg = seg[:max(b - a, 0)]
        if b > a and len(seg) == b - a:
            wav[spk % 2, a:b] += seg * (0.55 if is_bc else 1.0)
    m = np.abs(wav).max()
    return wav / m if m > 0 else wav


# ───────────────────────────────────────── 耳朵：稳健特征（★57 修 F0）
def cmndf(s):
    """累积均值归一化差分 —— 抗倍频"""
    w = len(s)
    ac = np.correlate(s, s, mode="full")[w - 1:]
    p = np.cumsum(s ** 2)
    d = np.array([(p[-1] - p[t] if t < w else 0.0)
                  + (p[w - 1 - t] if t < w else 0.0) - 2 * ac[t]
                  for t in range(len(ac))])
    d[0] = 0
    tau = np.arange(1, len(ac))
    c = np.cumsum(d[1:])
    cnd = np.full(len(tau), np.inf)
    nz = c > 1e-12
    cnd[nz] = d[1:][nz] * tau[nz] / c[nz]
    return cnd


def f0_from_ear(y, fs=SR, win_ms=60.0, thr=0.12, asym=0.6, ohc=True):
    """★ 稳健 F0（走真听神经）—— ★57 修

    ★★ 三个坑（逐个实测排除）：
      ① 分析窗 30ms 在 F0<150 时只有 3 个周期 → 不够 → 改 60ms
      ② 自相关 argmax 会跳倍频 → 改 CMNDF 取【第一个】低于阈值的局部最小
      ③ ★ 次谐波校正【过度】→ 150Hz 以上被测成一半 → 去掉
         根因是：只有 F0≈138 时二次谐波(276)恰好落在通道中心被放大
         加次谐波校正会误伤所有高频 → 得不偿失
    ⚠️ 实测可靠区间：100 / 138 / 180 / 200 / 220 ✅ ；160 ❌（如实标注）
       洛神默认 f0_base=138 → 落在可靠区
    """
    from core.real_voice import auditory_nerve
    n = int(fs * win_ms / 1000)
    out = []
    for st in np.linspace(0.12, 1.45, 10):
        a = int(st * fs)
        seg = y[a:a + n]
        if len(seg) < n:
            continue
        an = an_lowchan(seg, fs, asym=asym, ohc=ohc, gain_db=30.0)
        s = an - an.mean()
        if np.abs(s).max() < 1e-9:
            continue
        cnd = cmndf(s)
        lo = max(int(fs / 400), 2)
        hi = min(int(fs / 70), len(cnd) - 2)
        if hi <= lo + 2:
            continue
        k = None
        for t in range(lo, hi + 1):
            if cnd[t] < thr and cnd[t] <= cnd[t - 1] and cnd[t] <= cnd[t + 1]:
                k = t
                break
        if k is None:
            k = int(np.argmin(cnd[lo:hi + 1])) + lo
        out.append(fs / k)
    return deoctave(out)


def deoctave(v, tol=1.5):
    """★ 轨迹层面八度折叠：把偏离中位数 ~2 倍的点折回来
    ★★ 为什么必须有：实测同一段信号不同窗
       有的窗给 136.75（对） 有的给 271.19（2倍，错）
       → F0 起伏大时单窗不可靠，但【中位数周围的分布】是稳的
    """
    v = np.asarray([x for x in v if x > 0], float)
    if len(v) < 2:
        return list(v)
    m = float(np.median(v))
    out = []
    for f in v:
        while f > tol * m and f / 2.0 >= 50.0:
            f /= 2.0
        while f < m / tol and f * 2.0 <= 500.0:
            f *= 2.0
        out.append(f)
    return out


def ear_feats(y, fs=SR, asym=0.6, ohc=True):
    """★57 六维韵律特征 —— F0 用修好的，其余从包络/峰值"""
    from core.dialogue_synth import jitter_from_audio, envelope, vad
    if len(y) < int(fs * 0.3):
        return {k: 0.0 for k in EAR_KEYS}
    # ① F0
    tr = f0_from_ear(y, fs, asym=asym, ohc=ohc)
    if len(tr) >= 2:
        f0 = np.array(tr)
        f0_med = float(np.median(f0))
        f0_range_semi = float(12 * np.log2(max(f0.max(), 1e-6) / max(f0.min(), 1e-6)))
        # 句末漂移：后半 vs 前半
        h = len(f0) // 2
        f0_slide = float((np.mean(f0[h:]) - np.mean(f0[:h])) / max(np.mean(f0[:h]), 1e-6))
    else:
        f0_med = f0_range_semi = f0_slide = 0.0
    # ② 停顿
    segs = vad(y, fs)
    if len(segs) >= 2:
        gaps = np.array([segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)])
        gaps = gaps[gaps > 1e-4]
        pause_rate = float(len(gaps) / max(len(segs) - 1, 1))
        pause_cv = float(gaps.std() / max(gaps.mean(), 1e-9)) if len(gaps) >= 2 else 0.0
    else:
        pause_rate = pause_cv = 0.0
    # ③ jitter
    j = jitter_from_audio(y, fs)
    return {
        "pause_rate": pause_rate, "pause_cv": pause_cv,
        "f0_med": f0_med, "f0_range_semi": f0_range_semi,
        "f0_slide": f0_slide, "jitter": float(j) if j is not None else 0.0,
    }


EAR_KEYS = ["pause_rate", "pause_cv", "f0_med", "f0_range_semi",
            "f0_slide", "jitter"]


def an_lowchan(x, fs=SR, n_ch=24, asym=0.6, ohc=True, gain_db=30.0,
               fmax_chan=1000.0, x_lo=0.05):
    """★ 低频锁相池化：只累加 cf < fmax_chan 的通道

    ★★ 为什么：生理上相位锁定只在【低频】有效（人类 <1~4 kHz）
       全通道求和会把高频通道里【被放大的谐波】也加进来
       → F0=138 的二次谐波 276 落在某个通道中心被放大 → 稳定测成 2 倍
    ★ 这也更贴近真实的 F0 编码机制（时间理论靠低频通道锁相）
    ★ x_lo=0.05 → cf 最低约 65Hz，必须能覆盖基频本身
      原 0.18 → 最低 249Hz，通带 195~302，【不含】138Hz 基频
      → 只能靠二次谐波 276 编码 → 稳定测成 2 倍（这就是根因）
    """
    from core.real_voice import _bandpass, greenwood, ohc_compress, DB_SPL_FS
    from core.ear_anatomy import met_current
    xs = np.linspace(x_lo, 0.78, n_ch)
    cf = np.array([greenwood(v) for v in xs])
    bw = 0.03 * cf + 100.0
    an = np.zeros_like(x)
    for f, b in zip(cf, bw):
        if f > fmax_chan:
            continue
        ch = _bandpass(x, fs, f - b / 2.0, f + b / 2.0)
        lvl = DB_SPL_FS + gain_db + 20.0 * np.log10(
            float(np.sqrt((ch ** 2).mean())) + 1e-12)
        if ohc:
            lvl = ohc_compress(lvl)
        g = 10.0 ** ((lvl - DB_SPL_FS - gain_db) / 20.0)
        ch = ch * g
        spont = met_current(0.0, x0=0.0, s_pos=1.0, asym=asym)
        an += met_current(ch, x0=0.0, s_pos=1.0, asym=asym) - spont
    return an
