#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
让洛神自己学说话 —— 不教规则，只给语料
================================================================
用户：「发音什么的你不需要人教吗？你就把那些顶级模型的说话的语音
      牛逼的那种，就让它去学呗。」

★ 对标：Sesame CSM（REAL：8.3B 参数 / 100 万小时对话 / 116 ms）
   官方原文：呼吸、迟疑、自我修正、情绪颤动
            是【从对话上文隐式学来的，不是硬编码】
   ★ 这就是本模块要复现的【机制】：不写规则，让它自己从语料里长出来
   ❌ 但不是【规模】复现：8.3B / 100万小时 在这里不可能，明写

★ ★ 本模块与 ★19 vocal_anatomy 的根本区别 ★★
    ★19：我手写了 F0=120、舌位系数、jitter 公式   ← 我教的
    本模块：洛神只能【听】语料，自己提特征、自己改参数 ← 它学的
    ★ 合成语料时用的风格参数对它【隐藏】，它看不到答案

★ 语料来源（provenance 必须明写）：
    ❌ 真 Sesame / 真人录音：网络 403，拿不到（已实测 sesame.com / huggingface.co 均 403）
    ⚠️ 因此语料由 vocal_anatomy 合成 —— 是【代理语料】，不是真人语音
    ★ 所以本实验证明的是【学习机制成立】，不是【学会了真人说话】

★ 学什么（六维韵律特征，全部可从波形自提取）：
    pause_rate   停顿率      话语中间断开的比例
    pause_cv     停顿时长变异 停顿长度的离散度（人类说话停顿不均匀）
    f0_range     F0 动态范围  语调起伏
    f0_drift     F0 漂移      句末降调 / 句末升调（疑问）
    jitter       微扰         ★19 已验证：情感颤动落在 jitter 上
    repair_rate  自我修正率   说一半改口（"我觉——我是说"）

★ 怎么学（与 core/self_modify.py 同构）：
    生成 → 提特征 → 与语料比 → 误差 → 调参 → 再生成
    ★ 只用比例控制，不用梯度 —— 因为洛神没有可微的语音模型
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple
import numpy as np

SR = 16000

# 六维特征名（顺序固定，用作向量）
FEATS = ["pause_rate", "pause_cv", "f0_range", "f0_drift", "jitter", "repair_rate"]


# ================================================================
# 一、合成语料（★ 风格参数对学习者隐藏）
# ================================================================
@dataclass
class StyleHidden:
    """合成语料用的风格参数 —— ★ 学习者【看不到】这个类。"""
    pause_prob: float     # 每个词间停顿概率
    pause_mean: float     # 停顿时长均值（秒）
    pause_sigma: float    # 停顿时长对数正态 sigma（人类停顿很不均匀）
    f0_base: float
    f0_span: float        # F0 动态范围
    f0_end: float         # 句末 F0 相对偏移（负=降调）
    jitter: float
    repair_prob: float    # 自我修正概率
    breath_prob: float    # 换气概率


# ★ 两种风格：对话式（Sesame 那种）vs 播报式
STYLE_DIALOG = StyleHidden(
    pause_prob=0.42, pause_mean=0.19, pause_sigma=0.75,
    f0_base=125.0, f0_span=0.30, f0_end=-0.16,
    jitter=0.016, repair_prob=0.10, breath_prob=0.13)

STYLE_BROADCAST = StyleHidden(
    pause_prob=0.14, pause_mean=0.10, pause_sigma=0.22,
    f0_base=138.0, f0_span=0.13, f0_end=-0.03,
    jitter=0.005, repair_prob=0.005, breath_prob=0.03)


def synth_utterance(st: StyleHidden, n_words: int, rng: np.random.Generator,
                    seed_shift: int = 0) -> np.ndarray:
    """合成一句话：词段（带 F0 轮廓）+ 停顿 + 可能的自我修正 + 换气。

    ★ 只用 numpy 直接合成，不依赖 soundfile/librosa（沙盒里没有）
    """
    segs: List[np.ndarray] = []
    f0_track: List[float] = []
    i = 0
    while i < n_words:
        # 自我修正：重复开头再说一遍
        if rng.random() < st.repair_prob and i > 0:
            # 短促的重复片段
            # ★ 自我修正的声学指纹：短促重复 + 【明确短静音】+ 重说
            #   第一版没有静音，能量不形成谷 → repair_rate 两个风格都测成 0
            n = int(SR * 0.10)
            t = np.arange(n) / SR
            f0 = st.f0_base * (1 + 0.10)
            segs.append(0.40 * np.sin(2 * np.pi * f0 * t) * np.hanning(n))
            f0_track += [f0] * max(1, n // 160)
            n = int(SR * 0.08)          # 8 帧宽的静音谷
            segs.append(np.zeros(n))
            f0_track += [0.0] * max(1, n // 160)
            n = int(SR * 0.10)
            t = np.arange(n) / SR
            segs.append(0.40 * np.sin(2 * np.pi * f0 * t) * np.hanning(n))
            f0_track += [f0] * max(1, n // 160)

        # 一个词段
        dur = 0.15 + 0.22 * rng.random()
        n = int(SR * dur)
        t = np.arange(n) / SR
        # ★ F0 轮廓：【词内恒定】，词间跳变 + 句末 drift
        #   第一版词内也随机游走，结果帧间变化把 jitter 信号淹没了
        #   （实测对话式jitter 0.0068 vs 播报式0.0063，差 0.0005 = 测不出）
        prog = (i + 1) / max(n_words, 1)
        base = st.f0_base * (1.0 + st.f0_span * (rng.random() - 0.5)
                             + st.f0_end * prog)
        # ★ jitter：逐【周期】微扰（REAL：jitter 是 period-to-period）
        n_per = max(1, int(n * base / SR))
        per = base * (1.0 + st.jitter * rng.standard_normal(max(n_per, 1)))
        f0 = np.repeat(per, max(1, n // max(n_per, 1)))[:n]
        if len(f0) < n:
            f0 = np.pad(f0, (0, n - len(f0)), constant_values=base)
        ph = 2 * np.pi * np.cumsum(f0) / SR
        env = np.hanning(n) ** 0.6
        # 加一点共振峰色彩（二次谐波），让它不是纯正弦
        y = env * (np.sin(ph) + 0.28 * np.sin(2 * ph))
        segs.append(y * 0.5)
        f0_track += [float(np.median(f0))] * max(1, n // 160)

        # 换气（比停顿更长的低能量段）
        if rng.random() < st.breath_prob:
            n = int(SR * (0.28 + 0.12 * rng.random()))
            segs.append(0.02 * rng.standard_normal(n))
            f0_track += [0.0] * (n // 160)

        # 词间停顿
        if i < n_words - 1 and rng.random() < st.pause_prob:
            d = float(np.exp(rng.normal(np.log(st.pause_mean), st.pause_sigma)))
            d = float(np.clip(d, 0.02, 1.2))
            n = int(SR * d)
            segs.append(np.zeros(n))
            f0_track += [0.0] * (n // 160)
        i += 1

    y = np.concatenate(segs) if segs else np.zeros(SR // 2)
    return y.astype(np.float32)


def build_corpus(st: StyleHidden, n_utt: int = 60, seed: int = 0,
                 words_range: Tuple[int, int] = (6, 16)) -> List[np.ndarray]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_utt):
        nw = int(rng.integers(*words_range))
        out.append(synth_utterance(st, nw, rng))
    return out


# ================================================================
# 二、特征提取（★ 洛神只能靠这个"听"）
# ================================================================
def frame_energy(y: np.ndarray, hop: int = 160, win: int = 320) -> np.ndarray:
    if len(y) < win:
        return np.array([float(np.sqrt(np.mean(y ** 2)))])
    n = 1 + (len(y) - win) // hop
    return np.array([float(np.sqrt(np.mean(y[i * hop:i * hop + win] ** 2)))
                     for i in range(n)])


def estimate_f0(y: np.ndarray, hop: int = 160, win: int = 320,
                fmin: float = 60.0, fmax: float = 400.0) -> np.ndarray:
    """自相关法估 F0（无 librosa，纯 numpy）。

    ★ 有量化误差：帧长有限 → F0 分辨率受限。已明写。
    """
    if len(y) < win:
        return np.array([])
    n = 1 + (len(y) - win) // hop
    out = []
    for i in range(n):
        s = y[i * hop:i * hop + win]
        s = s - s.mean()
        if np.sqrt(np.mean(s ** 2)) < 1e-4:
            out.append(0.0); continue
        ac = np.correlate(s, s, mode="full")[win - 1:]
        lo, hi = int(SR / fmax), min(int(SR / fmin), len(ac) - 1)
        if hi <= lo:
            out.append(0.0); continue
        k = int(np.argmax(ac[lo:hi])) + lo
        out.append(SR / k if ac[k] > 0 else 0.0)
    return np.array(out)


def extract_features(y: np.ndarray) -> Dict[str, float]:
    """从波形里提六维韵律特征 —— ★ 这就是洛神唯一的输入。"""
    e = frame_energy(y)
    if len(e) == 0:
        return {k: 0.0 for k in FEATS}
    eth = max(1e-6, 0.10 * e.max())

    # 停顿 = 连续低能量段
    quiet = e < eth
    # ★ 去掉首尾静音（那是语句边界，不是句中停顿），第一版没去干净
    qb = quiet[2:-2] if len(quiet) > 8 else quiet
    runs, cur = [], 0
    for q in qb:
        if q:
            cur += 1
        elif cur:
            runs.append(cur); cur = 0
    body = qb
    pause_rate = float(body.mean()) if len(body) else 0.0
    if len(runs) >= 2:
        r = np.array(runs, float)
        pause_cv = float(r.std() / max(r.mean(), 1e-9))
    else:
        pause_cv = 0.0

    f0 = estimate_f0(y)
    f0v = f0[f0 > 0]
    if len(f0v) >= 4:
        f0_range = float((np.percentile(f0v, 90) - np.percentile(f0v, 10))
                         / max(np.median(f0v), 1e-9))
        # drift：后半段中位数 − 前半段中位数（归一化）
        h = len(f0v) // 2
        f0_drift = float((np.median(f0v[h:]) - np.median(f0v[:h]))
                         / max(np.median(f0v), 1e-9))
        # jitter：相邻帧 F0 相对差的均值（★ 含估计算法的量化噪声）
        d = np.abs(np.diff(f0v)) / np.maximum(f0v[:-1], 1e-9)
        jitter = float(np.median(d))
    else:
        f0_range = f0_drift = jitter = 0.0

    # ★ 自我修正：宽度 1~12 帧的能量谷，谷两侧都有声
    #   第一版只认【单帧】谷，实测 0 命中（合成的谷是 8 帧宽）
    # ★ 第二版失败：只按宽度认谷，抓到的全是词边界 hanning 边缘
    #   结果【反了】—— 播报式 2.94 > 对话式 1.53
    #   （播报式词挨得紧 → 边缘谷多；对话式停顿长 >12帧 被排除）
    # ★ 第三版判据：【谷底必须接近真静音】
    #   真自我修正 = 合成的纯零段（能量≈0）
    #   词边界 hanning 边缘 = 相对低但【不为零】
    dips = 0
    if len(e) > 12:
        thr = max(1e-6, 0.22 * e.max())       # 判"谷"的宽松阈值
        floor = 0.02 * e.max()                 # ★ 谷底必须低于此 = 真静音
        q = e < thr
        i = 0
        while i < len(q):
            if q[i]:
                j = i
                while j < len(q) and q[j]:
                    j += 1
                w = j - i
                left = i - 1 >= 0 and (not q[i - 1])
                right = j < len(q) and (not q[j])
                deepest = float(e[i:j].min())
                if 4 <= w <= 14 and left and right and deepest < floor:
                    dips += 1
                i = j
            else:
                i += 1
    repair_rate = float(dips) / max(len(e) / 100.0, 1.0)

    return dict(pause_rate=pause_rate, pause_cv=pause_cv,
                f0_range=f0_range, f0_drift=f0_drift,
                jitter=jitter, repair_rate=repair_rate)


def feat_vec(d: Dict[str, float]) -> np.ndarray:
    return np.array([d[k] for k in FEATS], float)


def corpus_profile(corpus: List[np.ndarray]) -> np.ndarray:
    F = np.array([feat_vec(extract_features(y)) for y in corpus])
    return F.mean(axis=0)


# ================================================================
# 三、学习者（★ 它自己改自己的参数）
# ================================================================
@dataclass
class SpeakerParams:
    """洛神自己的发声参数 —— 初始是【播报式】或随机，它得自己调。"""
    pause_prob: float = 0.14
    pause_mean: float = 0.10
    pause_sigma: float = 0.22
    f0_base: float = 138.0
    f0_span: float = 0.13
    f0_end: float = -0.03
    jitter: float = 0.005
    repair_prob: float = 0.005
    breath_prob: float = 0.03
    history: List[Dict[str, float]] = field(default_factory=list)

    def to_style(self) -> StyleHidden:
        return StyleHidden(
            pause_prob=self.pause_prob, pause_mean=self.pause_mean,
            pause_sigma=self.pause_sigma, f0_base=self.f0_base,
            f0_span=self.f0_span, f0_end=self.f0_end, jitter=self.jitter,
            repair_prob=self.repair_prob, breath_prob=self.breath_prob)

    def snapshot(self):
        d = asdict(self); d.pop("history"); self.history.append(d)


# 参数 → 特征的映射顺序（与 FEATS 对齐，用于按比例调整）
PARAM_OF_FEAT = {
    "pause_rate": "pause_prob",
    "pause_cv": "pause_sigma",
    "f0_range": "f0_span",
    "f0_drift": "f0_end",
    "jitter": "jitter",
    "repair_rate": "repair_prob",
}

# 每个参数的合法范围（防止跑飞）
BOUNDS = {
    "pause_prob": (0.0, 0.9), "pause_mean": (0.02, 0.8),
    "pause_sigma": (0.05, 1.5), "f0_base": (70.0, 260.0),
    "f0_span": (0.0, 0.8), "f0_end": (-0.5, 0.5),
    "jitter": (0.0, 0.08), "repair_prob": (0.0, 0.4),
    "breath_prob": (0.0, 0.4),
}


def learn_from_corpus(sp: SpeakerParams, target: np.ndarray,
                      n_iter: int = 20, lr: float = 0.30,
                      n_sample: int = 48, seed: int = 0,
                      verbose: bool = False) -> List[float]:
    """★ 学习循环：生成 → 提特征 → 比 → 调参。

    ★ 只用比例控制（每个维度独立），不是梯度下降 —— 洛神没有可微语音模型。
    """
    rng = np.random.default_rng(seed)
    errs = []
    for it in range(n_iter):
        utts = [synth_utterance(sp.to_style(), int(rng.integers(6, 16)), rng)
                for _ in range(n_sample)]
        cur = np.array([feat_vec(extract_features(y)) for y in utts]).mean(axis=0)
        # 归一化误差：各维量纲差太大，按目标尺度归一
        scale = np.maximum(np.abs(target), 1e-3)
        e = (cur - target) / scale
        err = float(np.sqrt(np.mean(e ** 2)))
        errs.append(err)
        # ★ 误差本身有采样噪声（n_sample 有限）。第一版直接用单批误差调参
        #   → 后期震荡（0.41→0.55），f0_span 超调到 0.57（真答案 0.30）
        #   → 改为指数平滑后再作为调整依据
        e_smooth = e if it == 0 else 0.6 * e_smooth + 0.4 * e
        e = e_smooth
        if verbose:
            print(f"    iter {it+1:>2}  err={err:.4f}")
        # 比例调整：往减小误差的方向动
        for j, fname in enumerate(FEATS):
            pname = PARAM_OF_FEAT[fname]
            lo, hi = BOUNDS[pname]
            cur_v = getattr(sp, pname)
            step = -lr * e[j] * max(abs(cur_v), 1e-3) * 0.5
            setattr(sp, pname, float(np.clip(cur_v + step, lo, hi)))
        # pause_mean 跟随 pause_prob 一起学（影响停顿总时长）
        setattr(sp, "pause_mean", float(np.clip(
            sp.pause_mean * (1 - lr * e[0] * 0.3), *BOUNDS["pause_mean"])))
        setattr(sp, "breath_prob", float(np.clip(
            sp.breath_prob * (1 - lr * e[1] * 0.2), *BOUNDS["breath_prob"])))
        setattr(sp, "f0_base", float(np.clip(
            sp.f0_base, *BOUNDS["f0_base"])))
        sp.snapshot()
    return errs
