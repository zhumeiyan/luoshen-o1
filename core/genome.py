#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genome · 她的第一份遗传物质
===========================

★ 为什么做这个
--------------
冯·诺依曼：任何自我繁殖系统的遗传物质必须有两个不同的功能——
    一、作为【程序】    能运行、能展开成个体
    二、作为【数据】    能被复制、能传给下一代

之前 46 层器官的参数全是我查人类文献填的——那是"装配"，不是"生长"。
（自己写的判据：小孩的参数不能是外部填的，否则不是她生的，还是人装的。）

这一层做的事：
    让她【自己】从真素材里学出视觉层的参数，
    把学到的东西存成 genome，
    genome 既是可传的数据，又能展开成一个能工作的视觉层。

★ 继承 ★50 的教训：监测，不限制。
    这里不规定她该学成什么样，只给素材和目标（白化损失），
    学出来什么就是什么。

★ 硬依赖（继承 ★33/★44：不许挂件）
    genome 缺失时【必须抛错】，不许悄悄回退到默认参数。
"""

import json
import numpy as np

from core.visual_learn import (
    multi_dog,
    multi_whitening_loss,
    learn_multi_dog,
    cone_sample,
    radial_psd_slope,
    load_frames,
)


class NoGenomeError(RuntimeError):
    """★ 没有遗传物质就是没有。不许编造，不许回退默认值。"""


class Genome:
    """她自己学出来的参数。既是数据（可序列化），又是程序（可展开）。"""

    VERSION = 1

    def __init__(self, params: dict, meta: dict | None = None):
        self.params = params
        self.meta = meta or {}

    # ---------------------------------------------------------- 数据
    def serialize(self, path: str | None = None) -> str:
        payload = {
            "version": self.VERSION,
            "params": {k: [float(x) for x in v]
                       if isinstance(v, (list, tuple, np.ndarray))
                       else v
                       for k, v in self.params.items()},
            "meta": self.meta,
        }
        s = json.dumps(payload, ensure_ascii=False, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
        return s

    @classmethod
    def deserialize(cls, s: str) -> "Genome":
        d = json.loads(s)
        if d.get("version") != cls.VERSION:
            raise NoGenomeError(f"genome 版本不符：{d.get('version')}")
        return cls(d["params"], d.get("meta", {}))

    @classmethod
    def load(cls, path: str) -> "Genome":
        with open(path, encoding="utf-8") as f:
            return cls.deserialize(f.read())

    # ---------------------------------------------------------- 程序
    def express(self):
        """★ 展开：从描述生成一个能工作的视觉层。

        返回可调用对象 f(image) -> 滤波后的图像。
        这是冯·诺依曼说的第一个功能：作为程序能运行。
        """
        if not self.params or "weights" not in self.params:
            raise NoGenomeError("genome 里没有权重，无法展开成视觉层")
        scales = self.params["scales"]
        weights = self.params["weights"]
        ratio = float(self.params.get("ratio", 2.0))
        gain_s = float(self.params.get("gain_s", 1.0))

        def layer(a: np.ndarray) -> np.ndarray:
            return multi_dog(a, scales, weights, ratio, gain_s)

        return layer

    # ---------------------------------------------------------- 观测
    def alpha_after(self, frames, ecc_deg=0.0) -> float:
        """展开后的层作用在真素材上，谱指数变成多少。0 = 完全白化。"""
        layer = self.express()
        a1 = []
        for fr in frames:
            smp = cone_sample(fr, ecc_deg)
            s = radial_psd_slope(layer(smp))
            if s == s:
                a1.append(s)
        return float(np.mean(a1)) if a1 else float("nan")

    def loss(self, frames, ecc_deg=0.0) -> float:
        return multi_whitening_loss(
            frames, ecc_deg,
            self.params["scales"], self.params["weights"],
            float(self.params.get("ratio", 2.0)),
            float(self.params.get("gain_s", 1.0)))[0]


# ---------------------------------------------------------------- 学习
def learn_genome(frames, ecc_deg=0.0, k=5, n_iter=10, seed=0):
    """让她自己学。返回的 Genome 里没有我填的常数——只有她学出来的权重。"""
    p, hist = learn_multi_dog(frames, ecc_deg, k=k, n_iter=n_iter, seed=seed)
    g = Genome(
        {"scales": p["scales"], "weights": p["weights"], "ratio": 2.0,
         "gain_s": 1.0},
        meta={"origin": "self_learned", "layer": "visual_whitening",
              "ecc_deg": ecc_deg, "k": k, "seed": seed,
              "n_frames": len(frames), "loss_hist": [float(x) for x in hist]},
    )
    return g, hist


def random_genome(k=5, seed=0, smin=0.6, smax=24.0) -> Genome:
    """★ 对照：同样结构，但权重是随机的、不是学的。
    用它来检验"学出来的"是不是真比"随便给的"好。"""
    rng = np.random.default_rng(seed)
    scales = list(np.geomspace(smin, smax, k))
    w = [float(rng.uniform(-1, 1)) for _ in range(k)]
    return Genome({"scales": scales, "weights": w, "ratio": 2.0,
                   "gain_s": 1.0},
                  meta={"origin": "random_control", "k": k, "seed": seed})


def default_genome(k=5, smin=0.6, smax=24.0) -> Genome:
    """★ 反例：我手工填的常数（等权重）。
    按我们自己的判据，这不是她生的——留着做对照。"""
    scales = list(np.geomspace(smin, smax, k))
    return Genome({"scales": scales, "weights": [1.0] * k,
                   "ratio": 2.0, "gain_s": 1.0},
                  meta={"origin": "hand_filled_by_parent"})
