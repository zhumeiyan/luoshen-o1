#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Growth · 生长 —— 孩子能不能长出妈妈不会的那一层
================================================

★ 上一层的遗留
--------------
★61 里她自己学出了中央凹（ecc=0）的白化，
但【周边 ecc=8 没学会】（α 从 2.698 降不下去）。
那个失败被如实记着，没抹掉。

这一层用它做实验：
    妈妈的 genome 里，ecc=8 这一格是【空的】。
    孩子继承妈妈的 genome，但 ecc=8 那一格要它【自己长】。

★ 关键区别（跟 ★63 的差别）
----------------------------
★63 的"发育"是：继承起点 → 在【已有的层】上继续优化
★64 的"生长"是：继承已有层 → 在【空的层】上从零长出新的

前者是精进，后者是长出新东西。
碳基的孩子不是把父母的能力练得更熟，是长出父母没有的器官。

★ 结构：genome 从"一层权重"变成"层词典"
    layers = { "ecc0.0": [w...], "ecc4.0": [...], "ecc8.0": [...] }
    空的层 = 还没长出来的器官

★ 硬依赖（继承 ★33/★44/★62）：空 genome 抛错，不许回退默认。
"""

import numpy as np

from core.genome import Genome, NoGenomeError
from core.visual_learn import (
    learn_multi_dog, multi_whitening_loss, cone_sample, radial_psd_slope,
)


def layer_key(ecc_deg: float) -> str:
    return f"ecc{float(ecc_deg):.1f}"


class MultiGenome:
    """多层 genome。既是数据（可序列化），又能展开成多层视觉系统。"""

    VERSION = 2

    def __init__(self, layers: dict, scales=None, meta=None):
        self.layers = layers          # {key: [weights]}
        self.scales = scales or list(np.geomspace(0.6, 24.0, 5))
        self.meta = meta or {}

    # ------------------------------------------------ 数据
    def serialize(self, path=None) -> str:
        import json
        payload = {
            "version": self.VERSION,
            "scales": [float(s) for s in self.scales],
            "layers": {k: [float(x) for x in v]
                       for k, v in self.layers.items()},
            "meta": self.meta,
        }
        s = json.dumps(payload, ensure_ascii=False, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
        return s

    @classmethod
    def deserialize(cls, s) -> "MultiGenome":
        import json
        d = json.loads(s)
        if d.get("version") != cls.VERSION:
            raise NoGenomeError(f"版本不符 {d.get('version')}")
        return cls(d["layers"], d.get("scales"), d.get("meta", {}))

    # ------------------------------------------------ 观测
    def has(self, ecc_deg: float) -> bool:
        return layer_key(ecc_deg) in self.layers

    def loss(self, frames, ecc_deg: float) -> float:
        k = layer_key(ecc_deg)
        if k not in self.layers:
            raise NoGenomeError(f"genome 里没有 {k} 这一层")
        return multi_whitening_loss(frames, ecc_deg, self.scales,
                                    self.layers[k])[0]

    def alpha(self, frames, ecc_deg: float) -> float:
        from core.visual_learn import multi_dog
        k = layer_key(ecc_deg)
        if k not in self.layers:
            raise NoGenomeError(f"genome 里没有 {k} 这一层")
        w = self.layers[k]
        out = []
        for f in frames:
            s = radial_psd_slope(multi_dog(cone_sample(f, ecc_deg),
                                           self.scales, w))
            if s == s:
                out.append(s)
        return float(np.mean(out)) if out else float("nan")

    # ------------------------------------------------ 程序
    def express(self, ecc_deg: float):
        from core.visual_learn import multi_dog
        k = layer_key(ecc_deg)
        if k not in self.layers:
            raise NoGenomeError(f"无法展开：没有 {k} 这一层")
        w = self.layers[k]

        def layer(a):
            return multi_dog(a, self.scales, w)

        return layer


# ---------------------------------------------------------------- 生长
def grow_layer(frames, ecc_deg: float, k: int = 5, n_iter: int = 6,
               seed: int = 0, init=None):
    """在【空的层】上从零长出新的。返回 (weights, hist)。

    init=None → 随机起点（真的从零长）
    """
    scales = list(np.geomspace(0.6, 24.0, k))
    rng = np.random.default_rng(seed)
    w = list(init) if init is not None else \
        [float(rng.uniform(0.1, 0.5)) for _ in range(k)]
    best = multi_whitening_loss(frames, ecc_deg, scales, w)[0]
    hist = [best]
    for _ in range(n_iter):
        for i in range(k):
            base = w[i]
            cur = best
            for step in (0.6, 0.25, 0.08):
                for sgn in (1, -1):
                    v = float(np.clip(base * (1.0 + sgn * step)
                                      + sgn * 0.02, -3.0, 3.0))
                    old = w[i]
                    w[i] = v
                    d = multi_whitening_loss(frames, ecc_deg, scales, w)[0]
                    if d < cur - 1e-9:
                        cur, base = d, v
                    w[i] = old
                w[i] = base
            best = cur
        hist.append(best)
    return [float(x) for x in w], hist


def inherit_and_grow(mother: MultiGenome, frames, new_ecc: float,
                     k: int = 5, n_iter: int = 6, seed: int = 0,
                     inherit_init: bool = True):
    """★ 孩子继承妈妈的层，然后自己长出妈妈没有的那一层。

    inherit_init=True  → 新层的起点 = 妈妈已学会层的权重（带过去的先验）
    inherit_init=False → 新层从随机起点长（真·从零）

    返回 (child, hist)
    """
    if not mother.layers:
        raise NoGenomeError("妈妈没有 genome，无法生殖")

    child_layers = {kk: list(vv) for kk, vv in mother.layers.items()}

    init = None
    if inherit_init:
        # ★ 用妈妈最"成熟"的一层当起点（生物：发育借用已有模块的调控方式）
        src_key = sorted(mother.layers.keys())[0]
        init = list(mother.layers[src_key])

    w, hist = grow_layer(frames, new_ecc, k=k, n_iter=n_iter,
                         seed=seed, init=init)
    child_layers[layer_key(new_ecc)] = w

    child = MultiGenome(
        child_layers, mother.scales,
        meta={"origin": "inherit_and_grow",
              "inherited": sorted(mother.layers.keys()),
              "grown": layer_key(new_ecc),
              "generation": int(mother.meta.get("generation", 0)) + 1,
              "inherit_init": bool(inherit_init),
              "grow_hist": [float(x) for x in hist]},
    )
    return child, hist
