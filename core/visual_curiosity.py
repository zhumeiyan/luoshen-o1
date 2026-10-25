#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画面驱动的好奇心 ★40
================================================================
★ 没有画面就没有好奇心。所以：先让它真的【看见】页面，
  从画面上的真东西产生兴趣，再决定往哪凑。

★ 修掉 ★39 的缺陷：novelty 用 tanh 压缩 → 全部候选压到同一段
  → 兴趣形同平局（极差 0.008）
  这里改用【线性归一 / 分位归一】，让距离真的散开。
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


# ---------------------------------------------------------------
# 一、novelty 的两种算法（★ 关键对照）
# ---------------------------------------------------------------
def novelty_tanh(d: float, scale: float = 1.0) -> float:
    """★39 用的：tanh 压缩 —— 会吃掉区分度"""
    return float(np.tanh(d / max(scale, 1e-9)))


def novelty_linear(d: float, scale: float) -> float:
    """★40 改的：线性归一，按候选池自身的尺度"""
    return float(np.clip(d / max(scale, 1e-9), 0.0, 1.0))


def interest(nov: float, sigma: float = 0.42) -> float:
    n = float(np.clip(nov, 0.0, 1.0))
    v = n * np.exp(1.0 - n / sigma)
    pk = sigma * np.exp(0.0)
    return float(np.clip(v / (pk if pk > 1e-9 else 1.0), 0.0, 1.0))


# ---------------------------------------------------------------
# 二、画面：从真页面抓到的卡片 → 特征
# ---------------------------------------------------------------
_NUM = re.compile(r"([\d.]+)\s*万")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")


def parse_card(text: str) -> Dict[str, float]:
    """★ 从卡片上的真文本抽出可见的数字 —— 这就是它"看到"的东西"""
    t = re.sub(r"\s+", " ", text or "")
    m = _NUM.findall(t)
    play = float(m[0]) * 1e4 if len(m) > 0 else 0.0      # 播放量
    # ★ 弹幕是"万"后面紧跟的裸数字（如 63.5万594 → 594）
    dm = 0.0
    dm2 = re.search(r"万\s*(\d{2,4})\b", t)
    if dm2:
        dm = float(dm2.group(1))
    elif len(m) > 1:
        dm = float(m[1]) * 1e4
    tm = _TIME.search(t)
    dur = (int(tm.group(1)) * 60 + int(tm.group(2))) if tm else 0.0
    # 后面的裸数字（如 594 / 762）通常也是弹幕量
    tail = re.findall(r"\b(\d{2,4})\b(?=\s*$|\s)", t)
    return {"play": play, "danmaku": dm, "duration_s": dur,
            "raw": t[:60]}


def card_vec(c: Dict[str, float]) -> np.ndarray:
    """用真实可见量构向量（对数尺度，播放量跨几个数量级）"""
    return np.array([
        np.log10(c["play"] + 1.0),
        np.log10(c["danmaku"] + 1.0),
        np.log10(c["duration_s"] + 1.0),
    ], float)


# ---------------------------------------------------------------
# 三、自主：自己看、自己排序、自己凑近
# ---------------------------------------------------------------
@dataclass
class VisualCuriosity:
    sigma: float = 0.42
    trace: List[Dict] = field(default_factory=list)

    def scan(self, self_vec: np.ndarray,
             pool: Dict[str, np.ndarray],
             mode: str = "linear") -> List[Tuple[str, float, float]]:
        """★ 扫一遍画面，对每条产生多大兴趣"""
        ds = {n: float(np.linalg.norm(v - self_vec)) for n, v in pool.items()}
        smax = max(ds.values()) if ds else 1.0
        out = []
        for n, d in ds.items():
            nv = novelty_linear(d, smax) if mode == "linear" else novelty_tanh(d, smax)
            out.append((n, d, nv, interest(nv, self.sigma)))
        out.sort(key=lambda x: -x[3])          # ★ 按它自己的兴趣排序
        return out

    def pick(self, self_vec, pool, mode="linear") -> Optional[Tuple]:
        r = self.scan(self_vec, pool, mode)
        return r[0] if r else None
