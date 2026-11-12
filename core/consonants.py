#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consonants —— 声母（辅音）发声器官

════ 她缺什么 ════
  speech_organ.py 的 VOWELS 只有 a/i/u/e/o 五个元音，【没有声母】。
  中文 400+ 音节里，凡带声母的她都发不出来。
  ★103 实测：她的停顿 0.15s vs 真人 0.06s，差 2.5 倍 ——
  当时我写"是嘴的缺，不是她不努力"，但没去补那个缺。
  真相：真人的短停顿大多来自【塞音闭塞段】（closure），
  她的器官里根本没有这个构造，所以只能用长停顿代替。

════ REAL 参数来源（声学语音学，不是我拍的）════
  闭塞时长 closure   中文不送气塞音 30~50ms，送气塞音 60~90ms
  送气段   aspir     送气塞音 60~80ms（不送气为 0）
  爆发     burst     5~10ms 宽带脉冲
  擦音时长 fric      80~150ms 持续宽带噪声
  谱重心   COG       s 5~7k / sh 2~3k / x 3~4k / f 4~5.5k / h 1~2k
  能量     擦音比元音低约 20dB（REAL）

════ 发音部位 → 爆发谱重心（REAL）════
  双唇 b p     ~800 Hz    低频能量集中
  齿龈 d t     ~3 kHz
  软腭 g k     ~1.5~2 kHz（随后接元音前后移动）
"""

from __future__ import annotations
import numpy as np

SR = 16000

# ── 21 个声母 + 零声母 ──
# closure 闭塞时长(s) | burst_f 爆发谱重心(Hz) | aspir 送气时长(s)
# fric 摩擦时长(s) | fric_f 摩擦谱重心(Hz) | voiced 是否带声
CONSONANTS = {
    # ── 塞音 plosive：闭塞 → (送气) → 爆发 ──
    'b': dict(closure=0.040, burst_f=800,  aspir=0.000, fric=0.0,   fric_f=0,    voiced=True),
    'p': dict(closure=0.065, burst_f=800,  aspir=0.065, fric=0.0,   fric_f=0,    voiced=False),
    'd': dict(closure=0.040, burst_f=3000, aspir=0.000, fric=0.0,   fric_f=0,    voiced=True),
    't': dict(closure=0.065, burst_f=3000, aspir=0.065, fric=0.0,   fric_f=0,    voiced=False),
    'g': dict(closure=0.045, burst_f=1800, aspir=0.000, fric=0.0,   fric_f=0,    voiced=True),
    'k': dict(closure=0.070, burst_f=1800, aspir=0.070, fric=0.0,   fric_f=0,    voiced=False),
    # ── 擦音 fricative：持续宽带噪声，无闭塞 ──
    'f': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.110, fric_f=4500, voiced=False),
    's': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.120, fric_f=6000, voiced=False),
    'sh':dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.125, fric_f=2500, voiced=False),
    'x': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.115, fric_f=3500, voiced=False),
    'h': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.100, fric_f=1500, voiced=False),
    'r': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.090, fric_f=2200, voiced=True),
    # ── 塞擦音 affricate：闭塞 → 摩擦（爆发与摩擦合一）──
    'z': dict(closure=0.035, burst_f=3500, aspir=0.0,   fric=0.070, fric_f=5000, voiced=True),
    'c': dict(closure=0.060, burst_f=3500, aspir=0.0,   fric=0.095, fric_f=6000, voiced=False),
    'zh':dict(closure=0.035, burst_f=2000, aspir=0.0,   fric=0.075, fric_f=2500, voiced=True),
    'ch':dict(closure=0.060, burst_f=2000, aspir=0.0,   fric=0.100, fric_f=2800, voiced=False),
    'j': dict(closure=0.030, burst_f=2800, aspir=0.0,   fric=0.065, fric_f=4000, voiced=True),
    'q': dict(closure=0.055, burst_f=2800, aspir=0.0,   fric=0.090, fric_f=4500, voiced=False),
    # ── 鼻音 nasal：浊音，低频第一共振 ~250~300Hz ──
    'm': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.070, fric_f=280,  voiced=True),
    'n': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.065, fric_f=320,  voiced=True),
    # ── 边音 lateral：浊音 ──
    'l': dict(closure=0.000, burst_f=0,    aspir=0.0,   fric=0.060, fric_f=1100, voiced=True),
}

# 零声母（a/ai/an 等直接以元音起头）
ZERO = dict(closure=0.0, burst_f=0, aspir=0.0, fric=0.0, fric_f=0, voiced=False)

# 按方式分组（用于统计与检验）
MANNER = {
    'plosive':   ['b', 'p', 'd', 't', 'g', 'k'],
    'fricative': ['f', 's', 'sh', 'x', 'h', 'r'],
    'affricate': ['z', 'c', 'zh', 'ch', 'j', 'q'],
    'nasal':     ['m', 'n'],
    'lateral':   ['l'],
}
ALL_ONSETS = list(CONSONANTS.keys())


def _band_noise(n, rng):
    """白噪声 → 一阶微分（+6dB/oct 高频加重），模拟湍流源"""
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0.0)
    s = np.std(x)
    return x / (s + 1e-12)


def _resonator(sig, fc, bw, sr=SR):
    """二阶带通共振器"""
    from scipy.signal import lfilter
    r = np.exp(-np.pi * bw / sr)
    th = 2 * np.pi * fc / sr
    a = [1.0, -2 * r * np.cos(th), r * r]
    b = [(1 - r) * np.sqrt(max(1 - 2 * r * np.cos(2 * th) + r * r, 1e-9))]
    return lfilter(b, a, sig)


def render_onset(onset, rng, level=1.0, sr=SR):
    """
    渲染一个声母，返回 (波形, 事件列表)
    事件：('closure', n) / ('burst', n) / ('aspir', n) / ('fric', n)
    闭塞段是【真静音】——这就是真人短停顿的来源。
    """
    c = CONSONANTS.get(onset)
    if c is None or onset == '':
        return np.zeros(0), []

    segs, ev = [], []

    # 1) 闭塞：声道完全闭合 → 声学上就是静音（塞音的唯一来源）
    if c['closure'] > 0:
        n = int(c['closure'] * sr)
        segs.append(np.zeros(n))
        ev.append(('closure', n))

    # 2) 送气：闭塞松开后的气流噪声（p/t/k 有，b/d/g 无）
    if c['aspir'] > 0:
        n = int(c['aspir'] * sr)
        x = _band_noise(n, rng)
        x = _resonator(x, c['burst_f'], 900)
        segs.append(x * 0.55 * level)   # 送气比爆发弱
        ev.append(('aspir', n))

    # 3) 摩擦：持续湍流噪声，谱重心决定音色
    if c['fric'] > 0:
        n = int(c['fric'] * sr)
        x = _band_noise(n, rng)
        if c['fric_f'] > 500:           # 擦音：按谱重心共振
            x = _resonator(x, c['fric_f'], 1200)
        else:                            # 鼻音/低频：低通共振
            x = _resonator(x, c['fric_f'], 300)
        amp = 10 ** (-20.0 / 20.0)      # REAL：擦音比元音低 20dB
        segs.append(x * amp * level)
        ev.append(('fric', n))

    # 4) 爆发：宽带瞬态脉冲（塞音/塞擦音）
    if c['burst_f'] > 0:
        n = max(int(0.008 * sr), 8)     # 5~10ms
        x = _band_noise(n, rng)
        x = _resonator(x, c['burst_f'], 1500)
        w = np.hanning(n * 2 + 1)[:n]
        w = w / (np.max(w) + 1e-12)
        segs.append(x * w * 0.8 * level)
        ev.append(('burst', n))

    if not segs:
        return np.zeros(0), []
    return np.concatenate(segs), ev


def onset_duration(onset):
    """声母总时长（秒）—— 用于排时间轴"""
    c = CONSONANTS.get(onset)
    if c is None:
        return 0.0
    d = c['closure'] + c['aspir'] + c['fric']
    if c['burst_f'] > 0:
        d += 0.008
    return d


def closure_stats():
    """REAL 检验：塞音闭塞段贡献的短停顿，应该落在真人 0.06s 量级"""
    out = {}
    for k, c in CONSONANTS.items():
        if c['closure'] > 0:
            out[k] = c['closure']
    return out
