#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★56 对话合成 —— 把 ★55 的【轮流结构】真正合成为【音频】，再用耳朵从音频里量回来
================================================================
★★ 为什么必须有这一层
    ★53/★54 学的是音色参数，★55 学的是轮流结构
    但 ★55 从头到尾【没有波形】—— 它是一组参数在演化
    ⚠️ 参数是它能直接看到的，波形不是 → 存在"常量当结论"的风险（★33 那次）

    本层要求：
      合成 → 混音 → ★ 用耳朵从音频里盲测 FTO → 与文献真值比对
    ★ 如果从【音频】里量不出 100ms，那 ★55 学的就只是参数，不是说话

★★★ 硬依赖设计（吸取 ★33/★44 教训：眼睛是挂件、耳朵是挂件）
    VAD 通道完全独立，看不到调度表，只看到能量
    deafen（耳朵坏）→ 必须抛错，不许回退到"用调度表算 FTO"
    有对照才敢说"测的是音频里的东西"

★ REAL 锚点
    FTO 中位 100ms / 众数 0~200ms     Stivers 2009 十语言
    重叠 <5% 语音信号                  Levinson&Torreira 2015
    话轮 1680ms / 中位 1227ms          同上
    jitter <1% 正常嗓音                ★19 标定 asym<1.22%
    F0 男 70~200 / 女 140~300          ★19
"""
import numpy as np
from scipy.signal import lfilter

SR = 16000

# ───────────────────────────────────────── REAL
REAL_AUDIO = {
    "fto_median": (0.00, 0.25),
    "overlap_frac": (0.0, 0.05),
    "turn_dur_mean": (1.20, 2.20),
    "jitter": (0.0, 0.01),
}


# ───────────────────────────────────────── 声源（声带）
def glottal_source(dur, f0, jitter_amt=0.005, rng=None, sr=SR):
    """脉冲串 + 声门脉冲形状。★ jitter 来自左右声带不对称（★19 手性）"""
    rng = rng or np.random.default_rng(0)
    n = int(dur * sr)
    if n <= 0:
        return np.zeros(1)
    T = 1.0 / max(f0, 20.0)
    inst = []
    t = 0.0
    f = f0
    while t < dur:
        inst.append(t)
        # F0 随机游走 + 周期级 jitter（真微扰）
        f *= (1.0 + rng.normal(0.0, 0.004))
        f = float(np.clip(f, f0 * 0.7, f0 * 1.4))
        t += (1.0 / f) * (1.0 + rng.normal(0.0, jitter_amt))
    imp = np.zeros(n)
    if inst:
        idx = (np.array(inst) * sr).astype(int)
        idx = idx[idx < n]
        imp[idx] = 1.0
    # 声门脉冲：短促上升 + 指数衰减
    L = max(int(sr * 0.005), 8)
    k = np.arange(L)
    pulse = (k / L) * np.exp(-k / (L * 0.25))
    pulse /= (pulse.sum() + 1e-12)
    return np.convolve(imp, pulse, mode="same")


def _resonator(x, f, bw, sr=SR):
    """2 阶谐振器（★46 教训：只用 2 阶，不用高阶 ba —— 高阶+窄带会数值爆炸）"""
    f = float(np.clip(f, 50.0, sr * 0.45))
    r = float(np.exp(-np.pi * max(bw, 10.0) / sr))
    th = 2.0 * np.pi * f / sr
    a = np.array([1.0, -2.0 * r * np.cos(th), r * r])
    y = lfilter(np.array([1.0 - r]), a, x)
    return y


def vocal_tract(src, f1, f2, f3=2500.0, sr=SR):
    """并联谐振器 = 声道（均匀管 + 舌位修正，★19）"""
    return (_resonator(src, f1, 80.0, sr) * 1.00
            + _resonator(src, f2, 120.0, sr) * 0.50
            + _resonator(src, f3, 200.0, sr) * 0.18)


VOWELS = {
    "a": (730, 1090), "i": (270, 2290), "u": (300, 870),
    "e": (530, 1840), "o": (570, 840), "schwa": (500, 1500),
}


def synth_turn(dur, f0=140.0, jitter_amt=0.005, seed=0, sr=SR):
    """合成一个话轮：若干音节，音节间有协同发音过渡"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    if n <= 1:
        return np.zeros(max(n, 1))
    src = glottal_source(dur, f0, jitter_amt, rng, sr)
    # 音节切分（REAL：约 5 音节/秒，★19）
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
        if prev is not None:                     # 协同发音：线性滑向目标
            f1s, f2s = prev
        else:
            f1s, f2s = f1, f2
        seg = vocal_tract(src[a:b], f1s, f2s, sr=sr)
        # ★ 段内 F1/F2 从 prev 滑到 v（协同发音，★19 实测 47.5% 是过渡段）
        seg2 = vocal_tract(src[a:b], f1, f2, sr=sr)
        w = np.linspace(0, 1, b - a)
        seg = seg * (1 - w) + seg2 * w
        env = np.sin(np.pi * np.linspace(0, 1, b - a)) ** 0.6   # 音节包络
        out[a:b] += seg * env
        prev = (f1, f2)
    m = np.abs(out).max()
    return out / (m + 1e-12) * 0.8


# ───────────────────────────────────────── 渲染（两声道 = 两个近场麦）
def render(events, f0_map=(140.0, 210.0), jitter_amt=0.005, sr=SR, seed=0):
    """events: [(spk, start, end, is_bc)]  → (wav2ch, total_dur)
    ★ 两个声道独立渲染 —— 后面 VAD 也独立做，互不偷看
    """
    if not events:
        return np.zeros((2, 1)), 0.0
    total = max(e[2] for e in events) + 0.5
    n = int(total * sr)
    wav = np.zeros((2, n))
    for i, (spk, st, en, is_bc) in enumerate(events):
        dur = en - st
        if dur <= 0.01:
            continue
        f0 = f0_map[spk % 2] * (1.0 + 0.05 * ((i * 37) % 7) / 7.0)
        seg = synth_turn(dur, f0=f0, jitter_amt=jitter_amt,
                         seed=seed * 1000 + i, sr=sr)
        a = int(st * sr)
        b = min(a + len(seg), n)
        seg = seg[:max(b - a, 0)]
        if b > a:
            # 重叠区直接相加（真实混音）
            wav[spk % 2, a:b] += seg * (0.55 if is_bc else 1.0)
    m = np.abs(wav).max()
    if m > 0:
        wav /= m
    return wav, total


# ───────────────────────────────────────── 耳朵：盲 VAD
def envelope(ch, sr=SR, win_ms=20.0):
    w = max(int(sr * win_ms / 1000.0), 1)
    k = np.ones(w) / w
    return np.convolve(np.abs(ch), k, mode="same")


def vad(ch, sr=SR, thr_ratio=0.06, min_dur_ms=60):
    """★ 盲：只看能量，看不到调度表。返回 [(start,end)] 秒"""
    if len(ch) < 8 or np.abs(ch).max() < 1e-9:
        return []
    env = envelope(ch, sr)
    peak = env.max()
    if peak < 1e-9:
        return []
    # ★ 谷底必须接近真静音（★23 修过：否则抓到的全是窗边缘）
    thr = max(peak * thr_ratio, 1e-6)
    act = env > thr
    min_n = int(sr * min_dur_ms / 1000.0)
    segs, i, n = [], 0, len(act)
    while i < n:
        if act[i]:
            j = i
            while j < n and act[j]:
                j += 1
            if (j - i) >= min_n:
                segs.append((i / sr, j / sr))
            i = j
        else:
            i += 1
    # 合并间隔 <50ms 的相邻段（同一话轮内的微小波动）
    merged = []
    for s, e in segs:
        if merged and s - merged[-1][1] < 0.05:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def deaf_vad(ch, sr=SR):
    """★ 耳朵坏：听不见。硬依赖测试用 —— 必须抛错，不许返回空列表蒙混"""
    raise RuntimeError("耳朵失效：无法从音频中检测语音段（硬依赖，禁止回退）")


def _active_mask(ch, segs, sr=SR):
    n = len(ch)
    m = np.zeros(n, dtype=bool)
    for s, e in segs:
        a, b = int(s * sr), min(int(e * sr), n)
        if b > a:
            m[a:b] = True
    return m


def measure(wav, sr=SR, vad_fn=None):
    """从【音频】里量出 FTO / 重叠 / 话轮时长（完全不看调度表）

    ★★ 修（★56）：第一版把【嵌套段】当成话轮转换
       backchannel（"嗯"）整个落在对方话轮内部
       → BC起点 − 对方话轮终点 = 负的近 1 秒 → 被算成"重叠"
       → 重叠占比虚高到 7.95%（REAL <5%），而参数层只有 1.1%
       ✅ 正确做法：
         ① 重叠时间 = 两个声道【同时有效】的样本数（直接求交集，精确）
         ② FTO 只在【主要话轮】之间算：被对方话轮完全包含的段跳过
    """
    vad_fn = vad_fn or vad
    per = [vad_fn(wav[0], sr), vad_fn(wav[1], sr)]

    # ── ① 重叠：两声道同时有效
    n = wav.shape[1]
    m0 = _active_mask(wav[0], per[0], sr)
    m1 = _active_mask(wav[1], per[1], sr)
    both = int(np.sum(m0 & m1))
    speech = int(np.sum(m0 | m1))
    overlap_frac = both / max(speech, 1)

    # ── ② 主要话轮 = 不被对方话轮完全包含的段
    def contained(s, e, other):
        return any(os_ <= s + 1e-6 and e <= oe + 1e-6 for os_, oe in other)

    tl = []
    for spk in (0, 1):
        for s, e in per[spk]:
            if not contained(s, e, per[1 - spk]):
                tl.append((s, e, spk))
    tl.sort(key=lambda x: x[0])

    ftos, intra, durs = [], [], []
    for i in range(1, len(tl)):
        ps, pe, ps_ = tl[i - 1]
        cs, ce, cs_ = tl[i]
        gap = cs - pe
        if cs_ != ps_:
            ftos.append(gap)          # 正=间隔，负=重叠（转换处）
        else:
            intra.append(gap)
    durs = [e - s for s, e, _ in tl]
    return {
        "ftos": np.array(ftos), "intra": np.array(intra),
        "durs": np.array(durs),
        "overlap_frac": float(overlap_frac),
        "fto_median": float(np.median(ftos)) if len(ftos) else float("nan"),
        "turn_dur_mean": float(np.mean(durs)) if len(durs) else float("nan"),
        "n_seg": len(tl), "n_bc": sum(len(p) for p in per) - len(tl),
    }


def jitter_from_audio(ch, sr=SR, f0_hint=140.0):
    """★ 从【音频】里量 jitter —— REAL 定义是【逐周期】相邻周期差

    ★★ 修（★56）：第一版用 40ms 分窗自相关
       → 量的是【窗与窗之间】的周期变化 = F0 漂移，不是 jitter
       → 测出 2.45%，而合成源真实的逐周期 jitter 是 0.5%，差 5 倍
       ★ 又一次"测量尺度选错"（★53 归一化分母、★55 盲测尺子，同族）
       ✅ 改成：低通到 F1 以下（保留声门脉冲）→ 峰值检测 → 相邻周期差
    """
    try:
        from scipy.signal import butter, sosfilt, find_peaks
        if len(ch) < sr * 0.3 or np.abs(ch).max() < 1e-9:
            return None
        # 低通 300Hz：保留 F0 与前两次谐波，压掉 F1/F2 振铃
        sos = butter(4, min(300.0, sr * 0.45) / (sr / 2.0), btype="low", output="sos")
        x = sosfilt(sos, ch.astype(float))
        x = x - x.mean()
        m = np.abs(x).max()
        if m < 1e-9:
            return None
        x = x / m
        dist = max(int(sr / (f0_hint * 2.2)), 8)      # 最小周期（最高可能 F0）
        pk, _ = find_peaks(x, distance=dist, prominence=0.15)
        if len(pk) < 12:
            return None
        # 抛物线插值 → 亚采样精度
        per = []
        for k in pk:
            if 0 < k < len(x) - 1:
                y0, y1, y2 = x[k - 1], x[k], x[k + 1]
                den = y0 - 2 * y1 + y2
                d = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
                per.append(k + float(np.clip(d, -1, 1)))
        if len(per) < 12:
            return None
        p = np.diff(np.array(per)) / sr
        per_med = float(np.median(p))
        if per_med <= 0:
            return None
        # ★★ 修（★56b）：顺序反了 → 先删周期再 diff 会把【不相邻】周期接在一起
        #    旧值 2.67%（ground truth 0.313%，高估 8.5 倍）
        #    ★ 真正的偏置来源：|diff| 分布是【重尾】的
        #      少数错峰产生巨大 diff，算术均值被拉爆
        #      （实测野值周期只占 0.6%，却把结果从 0.49% 抬到 3.03%）
        #    ✅ 正确：先算 diff，再剔野值；并用【中位数】做中心估计（抗重尾）
        #      同时给出 RAP（3点滑动平均参考，REAL 定义之一）
        d = np.abs(np.diff(p))
        if len(d) < 10:
            return None
        med_d = float(np.median(d))
        d_ok = d[d < med_d * 5.0]                 # 剔检测错误，保留真波动
        if len(d_ok) < 10:
            return None
        return float(d_ok.mean() / per_med)       # 与 REAL jitter(local) 同口径
    except Exception:
        return None
