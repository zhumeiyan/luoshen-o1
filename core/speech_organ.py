#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
speech_organ —— 发声器官（真的合成出波形，不是模拟）

════ 为什么要有这个 ════
  之前所有"说话"层都是机制（turn_taking / vocal），没有声音。
  这一课：她真的合成出波形，再用自己的耳朵听回来，自己判对错。

════ 源—滤波器模型（source-filter，语音学标准模型）════
  声源（喉）：声带振动 → 基频 F0 轮廓 + jitter（周期间抖动）+ shimmer
  声道（腔）：共振峰滤波器 F1/F2/F3，随元音移动
  韵律（脑）：F0 走向、短语起伏、停顿、能量包络

  中文是声调语言 —— 四条声调的 F0 走向是物理事实：
    T1 阴平 高平    T2 阳平 升    T3 上声 降升    T4 去声 降

════ ★ 修过的挂件 ════
  第一版里 pause_len / voiced_target / jitter 三个参数【完全不起作用】
  （★33 眼睛挂件、★44 耳朵挂件的老毛病）。
  这一版三个都接上了，且各管一件事、互不重叠：
    pause_len     → 停顿段的真实时长（影响 sil / pause_med）
    voiced_target → 气声比例（影响 voiced 检出率）
    jitter        → 声带周期间抖动（影响 f0_std）
"""

from __future__ import annotations
import numpy as np
from scipy.signal import lfilter

SR = 16000

# 中文四声的 F0 走向（归一化，相对基频）
TONE_SHAPES = {
    1: np.array([0.25, 0.25, 0.25, 0.25]),   # 阴平 高平
    2: np.array([-0.30, -0.05, 0.20, 0.45]),  # 阳平 升
    3: np.array([0.05, -0.40, -0.45, 0.10]),  # 上声 降升
    4: np.array([0.45, 0.20, -0.10, -0.40]),  # 去声 降
}
# 元音共振峰 [F1, F2, F3]
VOWELS = {
    'a': [730, 1090, 2440],
    'i': [270, 2290, 3010],
    'u': [300, 870, 2240],
    'e': [530, 1840, 2480],
    'o': [570, 840, 2410],
}
VOWEL_KEYS = list(VOWELS.keys())


def _reson(sig, f, bw):
    r = np.exp(-np.pi * bw / SR)
    theta = 2 * np.pi * f / SR
    a = [1.0, -2 * r * np.cos(theta), r * r]
    b = [(1 - r) * np.sqrt(max(1 - 2 * r * np.cos(2 * theta) + r * r, 1e-9))]
    return lfilter(b, a, sig)



# ★83 修掉发声器官的一个非物理 artifact：
#   旧版音节包络用 hanning —— 两端【精确到 0】。真实语音在音节之间不会静到零，
#   浊音段是持续发声、只有起止有斜坡。这个 artifact 让每个音节边界都出现
#   "假静音帧"，耳朵据此把整段连续语音判成 28% 静音（真值 0）。
#   改：斜坡 + 平台，包络有下限 ENV_FLOOR；只有真停顿才为 0。
BREATH_DB = 20.0        # 清音/擦音比元音低多少 dB（REAL ≈ 20）
GLOTTAL_DB = 36.0       # 声门噪声比浊音源低多少 dB
NOISE_FLOOR_DB = -40.0  # 录音本底比说话低多少 dB（干净录音典型 SNR ≈ 40）
ENV_FLOOR = 0.22


def _win(m, ramp=0.18):
    """音节包络：两端升余弦斜坡 + 中段平台，下限 ENV_FLOOR（不为 0）"""
    if m <= 4:
        return np.ones(m)
    w = np.ones(m)
    r = max(2, int(ramp * m))
    w[:r] = np.sin(np.linspace(0, np.pi / 2, r)) ** 2
    w[-r:] = np.sin(np.linspace(np.pi / 2, 0, r)) ** 2
    return np.clip(w, ENV_FLOOR, 1.0)


def build_timeline(dur, syl_dur, pause_rate, pause_len, rng):
    """按 pause_rate / pause_len 排出【浊音段—停顿段】时间轴"""
    segs = []
    t = 0.0
    while t < dur:
        if rng.random() < pause_rate:
            L = pause_len
            segs.append((t, min(t + L, dur), 'pause'))
            t += L
        else:
            L = syl_dur * (1.0 + 0.25 * rng.standard_normal())
            L = max(L, 0.08)
            segs.append((t, min(t + L, dur), 'voiced'))
            t += L
    return segs


def synthesize(params, dur=3.0, rng=None):
    """
    合成一段中文语音。
    params: f0_base, f0_variation, f0_decl, tone_depth,
            pause_rate, pause_len, voiced_target, jitter
    """
    rng = rng or np.random.default_rng(0)
    n = int(dur * SR)
    p = params
    f0_base = float(p['f0_base'])
    var = float(p['f0_variation'])
    decl = float(p['f0_decl'])
    depth = float(p['tone_depth'])
    jit = float(p['jitter'])
    vt = float(np.clip(p['voiced_target'], 0.2, 0.98))

    segs = build_timeline(dur, 0.22, float(p['pause_rate']),
                          float(p['pause_len']), rng)
    # ★ voiced_target：一部分音节是清音/气声（送气辅音、耳语），无 F0
    #   这是真实语音里 voiced 达不到 100% 的物理原因
    segs = [(a, b, k if k == 'pause' else
             ('breath' if rng.random() > vt else 'voiced')) for a, b, k in segs]

    # ── F0 轮廓 ──
    f0c = np.zeros(n)
    env = np.zeros(n)
    bmask = np.zeros(n, dtype=bool)   # ★83 真值：清音/气声段
    for si, (t0, t1, kind) in enumerate(segs):
        s0 = int(t0 * SR)
        s1 = min(int(t1 * SR), n)
        if s1 <= s0:
            continue
        m = s1 - s0
        if kind == 'pause':
            f0c[s0:s1] = 0.0
            env[s0:s1] = 0.0
            continue
        if kind == 'breath':
            f0c[s0:s1] = 0.0            # 清音：有声但无基频
            mm = m + 2
            # ★ 修过的 bug：气声/清音段能量原本设成浊音的 0.7 —— 太高。
            #   真实语音里清辅音、气声的能量远低于浊音。设高了之后，
            #   气声段经共振峰染色带上准周期性，被耳朵误判成浊音，
            #   导致 voiced 最低只能到 0.694，够不到真人的 0.641。
            env[s0:s1] = _win(m) * 0.22
            bmask[s0:s1] = True
            continue
        frac = si / max(len(segs), 1)
        base = f0_base * (1.0 - decl * frac)
        base *= np.exp(var * rng.standard_normal() * 0.5)
        tone = TONE_SHAPES[int(rng.integers(1, 5))]
        t = np.linspace(0, 1, m)
        shape = np.interp(t, np.linspace(0, 1, 4), tone) * depth
        # ★ jitter：声带周期间抖动（真声都有），直接加在 F0 上
        if jit > 0:
            shape = shape + jit * 3.0 * rng.standard_normal(m)
        f0c[s0:s1] = base * np.exp(shape)
        mm = m + 2
        env[s0:s1] = _win(m)

    # ── 声源：脉冲串（含 jitter 已在 F0 上）+ 气声噪声 ──
    voiced_mask = f0c > 20
    src = np.zeros(n)
    if voiced_mask.any():
        phase = np.zeros(n)
        inc = np.where(voiced_mask, f0c / SR, 0.0)
        phase[1:] = np.cumsum(inc[1:])
        k = np.floor(phase)
        dk = np.diff(k)
        cross = np.where(dk >= 1)[0] + 1
        if len(cross) > 1:
            pul = np.zeros(n)
            pul[cross] = 1.0
            from scipy.signal import fftconvolve
            ker = np.hanning(61)
            src = fftconvolve(pul, ker, mode='same')
    # ★ voiced_target：目标浊音占比越低 → 气声噪声越大（清音/送气多）
    # 清音/气声：湍流噪声源（REAL：擦音比元音低约 20dB，不是 55dB）
    #   旧版 breath 段只有 0.0168 的全局噪声 → 实测比浊音低 55dB，
    #   耳朵因此根本分不清"气声"和"静音"。这一版给真湍流源。
    # ★ 清音/气声：湍流噪声源，幅度【相对】浊音源标定（不是拍常数）
    #   旧版只有 0.0168 的全局噪声 → 实测比浊音低 55dB（非物理）。
    #   REAL：擦音/送气比元音低约 20dB。
    sv = float(np.sqrt((src[voiced_mask] ** 2).mean())) if voiced_mask.any() else 0.0
    src = src + sv * 10 ** (-GLOTTAL_DB / 20.0) * rng.standard_normal(n)  # 声门噪声

    # ── 声道：共振峰随时间移动 ──
    nv = max(len(segs), 2)
    vseq = [VOWELS[VOWEL_KEYS[int(rng.integers(0, len(VOWEL_KEYS)))]] for _ in range(nv)]
    xs = np.linspace(0, 1, nv)
    f1 = np.interp(np.linspace(0, 1, n), xs, [v[0] for v in vseq])
    f2 = np.interp(np.linspace(0, 1, n), xs, [v[1] for v in vseq])
    f3 = np.interp(np.linspace(0, 1, n), xs, [v[2] for v in vseq])

    y = np.zeros(n)
    nb = 8
    bs = n // nb
    for b in range(nb):
        s0 = b * bs
        s1 = n if b == nb - 1 else (b + 1) * bs
        seg = src[s0:s1]
        y[s0:s1] = _reson(_reson(_reson(seg, f1[s0], 80) * 0.9, f2[s0], 110) * 0.7, f3[s0], 160) * 0.5

    # ★ REAL：唇辐射特性 —— 一阶微分（+6dB/oct）。
    #   旧版缺这一项：宽带湍流源(清音/擦音)被三级窄带共振器压掉约 35dB，
    #   结果清音和静音落在同一电平(都 -60dB)，耳朵根本分不开。
    #   真实发声：唇辐射把高频抬起来，擦音才回得来。
    y = np.diff(y, prepend=0.0)
    # ★ 清音/擦音的湍流源【不】走整个声道滤波器（源-滤波器理论：
    #   擦音噪声在收窄处产生，只有收窄点前面的腔体共振，后面的不参与）。
    #   旧版把它送进三级窄带共振器 → 被压掉 35dB，和静音同一电平，无法区分。
    if bmask.any():
        yv = float(np.sqrt((y[voiced_mask] ** 2).mean())) if voiced_mask.any() else 0.0
        nz = rng.standard_normal(int(bmask.sum()))
        nz = np.diff(nz, prepend=0.0)          # 高频加重（擦音谱以高频为主）
        nz = nz / (np.std(nz) + 1e-12)
        y[bmask] = y[bmask] + nz * yv * 10 ** (-BREATH_DB / 20.0)
    y = y * env
    # ★ REAL：真实录音永远有本底噪声（房间/电路），静音段不是数字 0。
    #   旧版静音是精确的 0 → 静音与气声差 200dB，问题被人为简化了；
    #   加上本底后，静音 ≈ 比说话低 NOISE_FLOOR_DB，才跟真实世界同构。
    # ★ 幅度【相对】说话声压标定：本底比说话低 NOISE_FLOOR_DB
    #   （不能拍绝对常数 —— 三级共振器把信号衰减了约 1000×，
    #     绝对常数会让本底反过来盖过说话。这是上一版踩的坑。）
    sy = float(np.sqrt((y ** 2).mean()))
    y = y + sy * 10 ** (NOISE_FLOOR_DB / 20.0) * rng.standard_normal(n)
    rms = np.sqrt((y ** 2).mean())
    if rms > 1e-8:
        y = y / rms * 0.098       # 真语音实测 rms 中位 0.098
    meta = {'f0_contour': f0c, 'voiced_mask': voiced_mask,
            'n_pause': sum(1 for s in segs if s[2] == 'pause'),
            'n_seg': len(segs),
            # ★83 新增：sil_mask 是【真值】—— 只有测不准的耳朵，没有测不准的真值。
            #   验尺子必须拿 ground truth，不能拿"看起来合理"当对。
            'sil_mask': (env == 0.0), 'breath_mask': bmask}
    return y, meta


DEFAULT_PARAMS = {
    'f0_base': 182.0, 'f0_variation': 0.31, 'f0_decl': 0.10,
    'tone_depth': 0.30, 'pause_rate': 0.25, 'pause_len': 0.13,
    'voiced_target': 0.79, 'jitter': 0.02,
}
