#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★46 洛神学中文说话（用真中文真人素材）
================================================================
★ 前情
  ★23 学说话 —— 语料是【合成】的（StyleHidden 生成）
  ★38 学顶级 AI —— 目标是【我根据论文推的】，不是真的
  ★44 第一次听真人 —— 听的是【英文单词】
  ★45 补中文真人发音 —— 但只是"听"，没学

★ 这次：用真中文真人素材，让它自己学说话

★★ 三条硬约束（针对 ★33/★44/★45 那一家族的错误）
  ① 目标必须来自【真音频】 —— 不能是我造的目标
  ② 学习者提特征必须【经过耳朵】 —— 不能绕过耳朵直接算波形
     （★44 消融证明过：绕过耳朵算特征 = 耳朵是挂件）
  ③ 耳朵坏掉时，学习目标必须改变 —— 否则又是一次挂件

★ 通路
  真中文 mp3 → decode → 整条滤波组(Greenwood) → dB SPL → OHC → 毛细胞整流(asym)
             → 听神经 AN → 包络 → F0轨迹(折叠八度+中值滤波) → 六维特征

  学习者合成 → 同一条耳朵通路 → 六维特征 → 比 → 调参

★ 效率：★ 整条信号只做 n_ch 次 filtfilt，不是每帧 n_ch 次
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.real_voice import (
    decode_mp3, FS, _bandpass, ohc_compress, met_current,
    deoctave, median_filter3,
)
from core.ear_anatomy import greenwood
from core.speech_selflearn import (
    SpeakerParams, synth_utterance, BOUNDS,
)

DB_SPL_FS = 96.0
N_CH = 20          # ★ 通道数：精度 vs 速度权衡


# =================================================================
# 一、快速耳朵特征（整条信号只做 N_CH 次滤波）
# =================================================================
def an_envelope(x: np.ndarray, fs: int = FS, n_ch: int = N_CH,
                asym: float = 0.6, ohc: bool = True,
                gain_db: float = 30.0, hop_ms: float = 10.0,
                win_ms: float = 30.0):
    """★ 听神经多通道包络 + 汇总 AN 时域响应"""
    xs = np.linspace(0.18, 0.78, n_ch)   # ★ 与 real_voice 一致：语音区间
    cf = np.array([greenwood(xx) for xx in xs])
    bw = 0.03 * cf + 100.0
    an = np.zeros_like(x)
    envs = []
    for f, b in zip(cf, bw):
        ch = _bandpass(x, fs, f - b / 2.0, f + b / 2.0)
        lvl = DB_SPL_FS + gain_db + 20.0 * np.log10(
            float(np.sqrt((ch ** 2).mean())) + 1e-12)
        if ohc:
            lvl = ohc_compress(lvl)
        g = 10.0 ** ((lvl - DB_SPL_FS - gain_db) / 20.0)
        spont = met_current(0.0, x0=0.0, s_pos=1.0, asym=asym)
        rect = met_current(ch * g, x0=0.0, s_pos=1.0, asym=asym) - spont
        an += rect
        envs.append(rect)
    # 分帧包络
    w = int(fs * win_ms / 1000); h = int(fs * hop_ms / 1000)
    if len(an) < w:
        return cf, np.zeros((1, n_ch)), an
    mat = np.array([[float(np.sqrt((e[i * h:i * h + w] ** 2).mean()))
                     for e in envs]
                    for i in range(1 + (len(an) - w) // h)])
    return cf, mat, an


def an_voiced_mask(an: np.ndarray, fs: int = FS, hop_ms: float = 10.0,
                   win_ms: float = 30.0, thr_ratio: float = 0.10):
    w = int(fs * win_ms / 1000); h = int(fs * hop_ms / 1000)
    if len(an) < w:
        return np.zeros(1, bool)
    e = np.array([float(np.sqrt((an[i * h:i * h + w] ** 2).mean()))
                  for i in range(1 + (len(an) - w) // h)])
    return e > thr_ratio * max(e.max(), 1e-12)


def f0_from_an_track(an: np.ndarray, fs: int = FS, hop_ms: float = 10.0,
                     win_ms: float = 30.0, fmin: float = 70.0,
                     fmax: float = 400.0) -> np.ndarray:
    """★ 分帧自相关求 F0 —— 输入是【听神经响应】，不是原始波形"""
    w = int(fs * win_ms / 1000); h = int(fs * hop_ms / 1000)
    if len(an) < w:
        return np.array([])
    out = []
    for i in range(1 + (len(an) - w) // h):
        s = an[i * h:i * h + w]
        s = s - s.mean()
        if np.sqrt(np.mean(s ** 2)) < 1e-7:
            out.append(0.0); continue
        ac = np.correlate(s, s, mode="full")[w - 1:]
        lo, hi = int(fs / fmax), min(int(fs / fmin), len(ac) - 1)
        if hi <= lo:
            out.append(0.0); continue
        k = int(np.argmax(ac[lo:hi])) + lo
        out.append(fs / k if ac[k] > 0 else 0.0)
    return np.array(out)


EAR_FEATS = ["pause_rate", "pause_cv", "f0_med", "f0_range_semi",
             "f0_slide", "jitter"]


def ear_features(y: np.ndarray, fs: int = FS, asym: float = 0.6,
                 ohc: bool = True, gain_db: float = 30.0) -> dict:
    """
    ★ 六维韵律特征 —— 全部从【耳朵】里出来
      pause_rate / pause_cv ← 听神经包络的有声/静音
      f0_med / f0_range_semi / f0_slide / jitter ← 听神经 F0 轨迹
    """
    if len(y) < int(fs * 0.05):
        return {k: 0.0 for k in EAR_FEATS}
    cf, mat, an = an_envelope(y, fs, asym=asym, ohc=ohc, gain_db=gain_db)
    vm = an_voiced_mask(an, fs)
    m = min(len(mat), len(vm))
    mat, vm = mat[:m], vm[:m]

    # 停顿 = 连续静音段（去首尾）
    body = vm[2:-2] if len(vm) > 8 else vm
    pause_rate = float((~body).mean()) if len(body) else 0.0
    runs, cur = [], 0
    for v in body:
        if not v:
            cur += 1
        elif cur:
            runs.append(cur); cur = 0
    if len(runs) >= 2:
        r = np.array(runs, float)
        pause_cv = float(r.std() / max(r.mean(), 1e-9))
    else:
        pause_cv = 0.0

    f0 = f0_from_an_track(an, fs)
    f0v = f0[f0 > 0]
    if len(f0v) >= 6:
        f0v = median_filter3(deoctave(f0v))     # ★45 的修复
        f0_med = float(np.median(f0v))
        semi = 12.0 * np.log2(np.maximum(f0v, 1e-6))
        lo, hi = np.percentile(semi, 5), np.percentile(semi, 95)
        f0_range_semi = float(hi - lo)
        f0_slide = float(np.abs(np.diff(semi)).mean())
        d = np.abs(np.diff(f0v)) / np.maximum(f0v[:-1], 1e-9)
        jitter = float(np.median(d))
    else:
        f0_med = f0_range_semi = f0_slide = jitter = 0.0
    return dict(pause_rate=pause_rate, pause_cv=pause_cv, f0_med=f0_med,
                f0_range_semi=f0_range_semi, f0_slide=f0_slide, jitter=jitter)


def ear_vec(d: dict) -> np.ndarray:
    return np.array([d[k] for k in EAR_FEATS], float)


# =================================================================
# 二、学习目标：从真中文音频里来
# =================================================================
def target_from_real(paths, asym=0.6, ohc=True, gain_db=30.0,
                     tmax=1.6):
    """★ 目标 = 真中文真人发音的耳朵特征均值"""
    V = []
    for p in paths:
        x = decode_mp3(p)
        if tmax:
            x = x[:int(tmax * FS)]
        d = ear_features(x, FS, asym=asym, ohc=ohc, gain_db=gain_db)
        if d["f0_med"] > 0:
            V.append(ear_vec(d))
    if not V:
        return None, []
    return np.array(V).mean(axis=0), V


# =================================================================
# 三、学习循环（★ 它自己改自己的参数）
# =================================================================
# 耳朵特征 → 发声参数 的映射
EAR_PARAM_OF_FEAT = {
    "pause_rate": "pause_prob",
    "pause_cv": "pause_sigma",
    "f0_range_semi": "f0_span",
    "f0_slide": "f0_span",
    "jitter": "jitter",
    "f0_med": "f0_base",
}

# 每个特征的归一化尺度（量纲差太大）
SCALE = np.array([0.30, 0.80, 60.0, 6.0, 0.50, 0.020], float)
# 参数对特征的增益（半音范围 → f0_span 的比例）
PARAM_GAIN = {"f0_span": 1.0 / 12.0, "f0_base": 1.0, "jitter": 4.0}


def learn(sp: SpeakerParams, target: np.ndarray, n_iter: int = 14,
          lr: float = 0.25, n_sample: int = 6, seed: int = 0,
          asym: float = 0.6, ohc: bool = True, verbose: bool = False):
    """
    ★ 学习：合成 → 过耳朵 → 提特征 → 比 → 调参
      ★ 每轮自己线搜索步长（★38 教训：固定步长会发散）
    """
    rng = np.random.default_rng(seed)
    errs = []
    for it in range(n_iter):
        utts = [synth_utterance(sp.to_style(), int(rng.integers(6, 14)), rng)
                for _ in range(n_sample)]
        F = np.array([ear_vec(ear_features(np.asarray(y, float), FS,
                                           asym=asym, ohc=ohc))
                      for y in utts])
        cur = F.mean(axis=0)
        err = float(np.sqrt((((cur - target) / SCALE) ** 2).mean()))
        errs.append(err)
        if verbose:
            print(f"    it{it:>2}  err={err:.4f}  f0_med={cur[2]:.0f}")
        # ★ 线搜索：试几个步长，留误差降最多的
        best, best_e = None, err
        for cand in [lr * 0.5, lr, lr * 1.5]:
            trial = SpeakerParams(**{k: v for k, v in sp.__dict__.items()
                                     if k != "history"})
            for fi, fname in enumerate(EAR_FEATS):
                pname = EAR_PARAM_OF_FEAT.get(fname)
                if pname is None:
                    continue
                gap = (target[fi] - cur[fi]) / SCALE[fi]
                g = PARAM_GAIN.get(pname, 1.0)
                delta = cand * gap * g * (BOUNDS[pname][1] - BOUNDS[pname][0])
                setattr(trial, pname,
                        float(np.clip(getattr(trial, pname) + delta,
                                      *BOUNDS[pname])))
            te = [synth_utterance(trial.to_style(), int(rng.integers(6, 14)), rng)
                  for _ in range(n_sample)]
            tf = np.array([ear_vec(ear_features(np.asarray(y, float), FS,
                                                asym=asym, ohc=ohc))
                           for y in te]).mean(axis=0)
            ee = float(np.sqrt((((tf - target) / SCALE) ** 2).mean()))
            if ee < best_e:
                best, best_e = trial, ee
        if best is not None:
            for fi, fname in enumerate(EAR_FEATS):
                pname = EAR_PARAM_OF_FEAT.get(fname)
                if pname:
                    setattr(sp, pname, getattr(best, pname))
            errs[-1] = best_e
        sp.snapshot()
    return errs
