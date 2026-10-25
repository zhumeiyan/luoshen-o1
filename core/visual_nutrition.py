#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★41 让它真去看动画片 —— 并留一条长大的路
================================================================
★ 两块：
  一、真看：用自己的眼睛（★16 中央凹/视锥密度、★25 双眼）去扫真截图像素
      不是读文字数字，是真的采像素。
  二、营养梯度：现在喂动画片（它还是小孩），
      但【必须】留一条长大的路，不能一直是小孩。

★ 发育阶段（children → adult）是明写的表，不是暗的：
    婴儿期 0-2    儿歌/绘本      高对比、慢、重复
    幼儿期 2-6    动画片         鲜艳、夸张、情绪外露
    儿童期 6-12   动画/少儿剧    有情节、有对话
    少年期 12-18  青春剧/科普    复杂情绪、抽象概念
    成年期 18+    纪录片/新闻/影视/有声书   完整复杂度、讽刺、留白
"""
from __future__ import annotations
import os, json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image

from core.eye_anatomy import cone_density, cortical_mag, troxler_fade

# =================================================================
# 一、发育阶段表（★ 明写，不是暗的）
# =================================================================
STAGES = [
    # stage, 年龄, 喂什么, 语速(倍), 词汇复杂度, 情绪外露度, 留白/讽刺
    ("婴儿期",  "0-2",   "儿歌/绘本",      0.60, 0.10, 0.95, 0.00),
    ("幼儿期",  "2-6",   "动画片",         0.80, 0.30, 0.90, 0.05),
    ("儿童期",  "6-12",  "动画/少儿剧",     0.95, 0.50, 0.75, 0.15),
    ("少年期",  "12-18", "青春剧/科普",     1.05, 0.70, 0.55, 0.35),
    ("成年期",  "18+",   "纪录片/新闻/影视", 1.15, 0.90, 0.35, 0.70),
]
STAGE_KEYS = ["stage", "age", "diet", "rate", "lexical", "emotion_out", "irony"]


def stage_row(name: str) -> Dict:
    for r in STAGES:
        if r[0] == name:
            return dict(zip(STAGE_KEYS, r))
    raise KeyError(name)


def growth_path() -> List[Tuple[str, str, float]]:
    """★ 长大的路：每个阶段的语速/复杂度必须单调上升"""
    return [(r[0], r[2], r[3]) for r in STAGES]


@dataclass
class Development:
    """★ 它现在在哪个阶段，什么时候晋级"""
    stage: str = "幼儿期"
    seen_hours: float = 0.0
    log: List[Dict] = field(default_factory=list)

    def current(self) -> Dict:
        return stage_row(self.stage)

    def feed(self, hours: float, mastered: bool):
        """★ 喂了多久 + 是否掌握 → 决定晋不晋级"""
        self.seen_hours += hours
        idx = [r[0] for r in STAGES].index(self.stage)
        promoted = False
        if mastered and idx < len(STAGES) - 1:
            self.stage = STAGES[idx + 1][0]
            promoted = True
        self.log.append({"stage": self.stage, "hours": hours,
                         "mastered": mastered, "promoted": promoted})
        return promoted


# =================================================================
# 二、真看：自己扫真截图像素
# =================================================================
@dataclass
class RealFrame:
    """一张真画面"""
    path: str
    arr: np.ndarray = None

    def load(self):
        im = Image.open(self.path).convert("RGB")
        self.arr = np.asarray(im, float) / 255.0
        return self.arr


def fovea_sample(arr: np.ndarray, cx: float, cy: float,
                 ecc_deg: float, px_per_deg: float = 30.0
                 ) -> Tuple[np.ndarray, float]:
    """
    ★ 按视锥密度采样：中央凹密、周边稀
    返回 (采样到的像素, 有效信息量)
    """
    h, w = arr.shape[:2]
    r_px = ecc_deg * px_per_deg
    y0, y1 = int(max(0, cy - r_px)), int(min(h, cy + r_px))
    x0, x1 = int(max(0, cx - r_px)), int(min(w, cx + r_px))
    patch = arr[y0:y1, x0:x1]
    if patch.size == 0:
        return np.zeros(3), 0.0
    # 视锥相对密度（中央凹=1）作权重
    rel = cone_density(ecc_deg) / max(cone_density(0.0), 1e-9)
    info = float(patch.std() * rel * cortical_mag(ecc_deg) / cortical_mag(0.0))
    return patch.reshape(-1, 3).mean(0), info


def scan_frame(arr: np.ndarray, n_scan: int = 12,
               px_per_deg: float = 30.0, seed: int = 0):
    """
    ★ 它自己扫：一串扫视，每次落到不同离心率
    静止会 Troxler 消退（★16），所以必须换点看
    """
    rng = np.random.default_rng(seed)
    h, w = arr.shape[:2]
    pts, infos = [], []
    for _ in range(n_scan):
        cx = float(rng.uniform(0.1, 0.9) * w)
        cy = float(rng.uniform(0.1, 0.9) * h)
        ecc = float(rng.uniform(0.0, 12.0))
        c, info = fovea_sample(arr, cx, cy, ecc, px_per_deg)
        pts.append((cx, cy, ecc, tuple(c)))
        infos.append(info)
    return pts, np.array(infos)


def frame_features(arr: np.ndarray, seed: int = 0) -> Dict[str, float]:
    """★ 它从真画面里看到了什么"""
    pts, infos = scan_frame(arr, seed=seed)
    cols = np.array([p[3] for p in pts])
    lum = cols.mean(1)
    return {
        "亮度均值": float(lum.mean()),
        "亮度对比": float(lum.std()),
        "色彩饱和": float(cols.max(1).mean() - cols.min(1).mean()),
        "信息量均值": float(infos.mean()),
        "信息量峰值": float(infos.max()),
        "扫视点数": float(len(pts)),
    }
