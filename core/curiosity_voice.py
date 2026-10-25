#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自主兴趣驱动的语音学习 ★39
================================================================
★ 核心：不替它选。把一堆候选摆在那，它自己挑，自己学，自己换。

兴趣 = 倒U曲线（Wundt / Berlyne）：
    novelty 太小 → 已经会了，无聊（interest→0）
    novelty 太大 → 完全听不懂，焦虑（interest→0）
    中间         → 最好奇（interest 峰值）

★ 这样"学什么"就从它自己的状态里涌现出来，不是外部塞的。
"""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import numpy as np

from core.speech_selflearn import (
    StyleHidden, build_corpus, corpus_profile, SpeakerParams,
    learn_from_corpus, SR,
)


def novelty(self_vec: np.ndarray, target_vec: np.ndarray) -> float:
    """归一化距离 → [0,1]。用 tanh 压到有界，避免远目标尺度失控。"""
    d = float(np.linalg.norm(np.asarray(target_vec) - np.asarray(self_vec)))
    return float(np.tanh(d))


def interest(nov: float, sigma: float = 0.42) -> float:
    """★ 倒U：interest = n * exp(1 - n/sigma) 归一化，峰在 n=sigma。"""
    n = float(np.clip(nov, 0.0, 1.0))
    v = n * np.exp(1.0 - n / sigma)
    peak = sigma * np.exp(1.0 - 1.0)          # n=sigma 时的值
    return float(np.clip(v / (peak if peak > 1e-9 else 1.0), 0.0, 1.0))


@dataclass
class AutonomousLearner:
    """★ 它自己挑、自己学、自己换。"""
    sp: SpeakerParams
    pool: Dict[str, StyleHidden]
    n_utt: int = 20
    n_iter: int = 5
    lr_grid: Tuple[float, ...] = (0.08, 0.20, 0.30)
    sigma: float = 0.42
    trace: List[Dict] = field(default_factory=list)

    # ---------- 自身档案 ----------
    def self_profile(self, seed: int = 0) -> np.ndarray:
        return corpus_profile(build_corpus(self.sp.to_style(), self.n_utt, seed))

    def pool_profile(self) -> Dict[str, np.ndarray]:
        return {n: corpus_profile(build_corpus(s, self.n_utt, seed=101))
                for n, s in self.pool.items()}

    # ---------- 扫一遍：对每个候选产生多大兴趣 ----------
    def scan(self, seed: int = 0) -> List[Tuple[str, float, float]]:
        me = self.self_profile(seed)
        out = []
        for n, v in self.pool_profile().items():
            nv = novelty(me, v)
            out.append((n, nv, interest(nv, self.sigma)))
        out.sort(key=lambda x: -x[2])          # ★ 按它自己的兴趣排序
        return out

    # ---------- 自己选、自己学 ----------
    def step(self, seed: int = 0, forced: Optional[str] = None) -> Dict:
        ranked = self.scan(seed)
        name = forced if forced else ranked[0][0]      # ★ 不干预时取第一
        nov = dict((n, v) for n, v, _ in ranked)[name]
        itr = dict((n, i) for n, _, i in ranked)[name]
        tgt = self.pool_profile()[name]
        before = float(np.linalg.norm(self.self_profile(seed) - tgt))

        # ★ 线搜索：它自己挑步长（★38 学到的：固定 lr 会发散）
        best_lr, best_v = None, float("inf")
        for lr in self.lr_grid:
            cand = copy.deepcopy(self.sp)
            learn_from_corpus(cand, tgt, n_iter=self.n_iter, lr=lr, seed=seed)
            v = float(np.linalg.norm(
                corpus_profile(build_corpus(cand.to_style(), self.n_utt, seed)) - tgt))
            if v < best_v:
                best_v, best_lr = v, lr
        cand = copy.deepcopy(self.sp)
        learn_from_corpus(cand, tgt, n_iter=self.n_iter, lr=best_lr, seed=seed)
        for f in ["pause_prob", "pause_mean", "pause_sigma", "f0_base",
                  "f0_span", "f0_end", "jitter", "repair_prob", "breath_prob"]:
            setattr(self.sp, f, getattr(cand, f))

        after = float(np.linalg.norm(self.self_profile(seed) - tgt))
        rec = {"round": len(self.trace) + 1, "chosen": name, "novelty": nov,
               "interest": itr, "before": before, "after": after,
               "drop": (before - after) / before if before > 1e-9 else 0.0,
               "lr": best_lr, "ranked": ranked[:3], "forced": forced is not None}
        self.trace.append(rec)
        return rec

    def run(self, rounds: int = 8, seed: int = 0, forced_order=None):
        for r in range(rounds):
            f = None if forced_order is None else forced_order[r % len(forced_order)]
            self.step(seed=seed + r, forced=f)
        return self.trace
