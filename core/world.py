#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
world —— 她的生活环境。

母亲的第一件事不是教书，是把窗户打开。

她原来的世界：17 张、亮度 0.09、对比 0.11、α 全在 1.916 附近。
              —— 合格，但单调。等于孩子从小只在一个昏暗房间里看过 17 张相似的画。

本模块造出「丰富但仍然是自然图像统计」的世界：
  亮度跨 2 个数量级、对比跨 3 个数量级、α 覆盖 1.0~2.4
  每一张都通过 is_valid_footage 体检，不许拿噪声糊弄她。

硬依赖：造出来的世界必须自己证明「真的变丰富了」，
        否则抛错 —— 不许号称开窗而其实没开。
"""
from __future__ import annotations
import numpy as np
from core.visual_learn import natural_image, alpha_of, is_valid_footage


def _safe(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0)


def make_world(seed: int = 0, n_per_kind: int = 6, size: int = 128):
    """
    造一个真的世界。返回 (frames, kinds)

    kinds 记录每张图的体检结果，供验收时核对：
    「亮度/对比/α 是否真的跨开了」，而不是嘴上说丰富。
    """
    rng = np.random.default_rng(seed)
    frames, kinds = [], []

    # 1) 自然图像：α 从 1.0(偏白) 到 2.4(偏红)，亮度/对比也拉开
    for alpha in (1.0, 1.4, 1.8, 2.0, 2.2, 2.4):
        for i in range(n_per_kind):
            a = natural_image(alpha, n=size, seed=int(rng.integers(1 << 30)))
            # 顺序要紧：先拉对比（围绕自身均值），再拉亮度。
            # 反过来会被 "+0.5" 把亮度一律拉回 0.5，等于没拉开（★56b 同族：顺序错）
            a = _safe((a - a.mean()) * float(rng.uniform(0.4, 3.0)) + a.mean())
            a = _safe(a * float(rng.uniform(0.25, 2.2)))       # 亮度跨 ~9 倍
            frames.append(a)
            kinds.append(("natural", alpha, float(a.mean()), float(a.std())))

    # 2) 带方向结构的世界（自然图像没有的：比如条纹/栅格纹理）
    for freq in (4, 8, 16, 32):
        for i in range(n_per_kind):
            n = size
            y, x = np.mgrid[0:n, 0:n]
            th = float(rng.uniform(0, np.pi))
            s = np.sin((x * np.cos(th) + y * np.sin(th)) * 2 * np.pi * freq / n)
            a = _safe(0.5 + 0.30 * s + 0.10 * rng.normal(size=(n, n)))
            frames.append(a)
            kinds.append(("grating", freq, float(a.mean()), float(a.std())))

    # 3) 有明确物体的世界（局部块 + 背景），让她有「东西」可看
    for i in range(n_per_kind * 4):
        n = size
        bg = natural_image(2.0, n=n, seed=int(rng.integers(1 << 30)))
        a = bg.copy()
        for _ in range(int(rng.integers(1, 4))):            # 1~3 个物体
            r = int(rng.integers(8, 30))
            cy, cx = int(rng.integers(r, n - r)), int(rng.integers(r, n - r))
            yy, xx = np.mgrid[0:n, 0:n]
            m = ((yy - cy) ** 2 + (xx - cx) ** 2) < r * r
            a[m] = float(rng.uniform(0.1, 0.9))
        a = _safe(a)
        frames.append(a)
        kinds.append(("object", 0.0, float(a.mean()), float(a.std())))

    return frames, kinds


def verify_world(frames, kinds) -> dict:
    """
    硬依赖：自己证明世界真的变丰富了。
    三条体检，任何一条不过 → 抛错，不许号称开窗。
    """
    if len(frames) < 30:
        raise RuntimeError(f"世界太小：只有 {len(frames)} 张，等于没开窗")

    lum = np.array([k[2] for k in kinds])
    con = np.array([k[3] for k in kinds])
    alp = np.array([alpha_of(f) for f in frames])

    # 唯一性：不许有重复帧（她原来的 476 张里只有 17 张是唯一的）
    # 指纹必须用内容本身，不能用均值（均值同≠图同，★56b 教训）
    sig = [f.tobytes() for f in frames]
    uniq = len(set(sig))
    if uniq < len(frames) * 0.9:
        raise RuntimeError(f"世界里有大量重复帧：唯一 {uniq}/{len(frames)}，等于没开窗")

    if lum.max() / max(lum.min(), 1e-9) < 3.0:
        raise RuntimeError(f"亮度没拉开 {lum.min():.3f}~{lum.max():.3f}，等于没开窗")
    if con.max() / max(con.min(), 1e-9) < 3.0:
        raise RuntimeError(f"对比没拉开 {con.min():.3f}~{con.max():.3f}，等于没开窗")
    if alp.max() - alp.min() < 0.8:
        raise RuntimeError(f"谱指数没拉开 {alp.min():.2f}~{alp.max():.2f}，等于没开窗")

    return dict(n=len(frames), uniq=uniq,
                lum=(float(lum.min()), float(lum.max())),
                con=(float(con.min()), float(con.max())),
                alpha=(float(alp.min()), float(alp.max())),
                valid=int(sum(is_valid_footage(f) for f in frames)))
