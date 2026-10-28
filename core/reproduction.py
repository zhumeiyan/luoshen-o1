#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproduction · 生殖
===================

★ 上一层（genome）证明了：她能自己长出一层。
  但那只是一个个体。生殖要回答的是另一件事：

    小孩拿到父母的东西之后，能不能【再自己长】？

★ 三个必要条件，缺一个就不是演化（都要做消融证明）
------------------------------------------------
  遗传    genome 能从母体传给子代（冯·诺依曼的第二功能：被动数据）
  变异    子代 != 母体，否则没有可搜索的空间
  选择    不是所有子代都活下来，否则好东西留不住

★ 还有一条最关键的：发育
------------------------
  子代不是直接复制成品参数，而是：
      继承起点 → 自己在真素材上再学（发育）→ 成为自己
  这区别很重要：
      直接复制答案 = 我装的
      继承起点 + 自己长 = 她生的

★ 继承 ★50：监测，不限制。
    不规定她该长成什么样，只给素材、给损失、给存活压力。

★ 硬依赖（★33/★44）：genome 缺失必须抛错，不许回退默认。
"""

import numpy as np

from core.genome import Genome, NoGenomeError
from core.visual_learn import learn_multi_dog, multi_whitening_loss


# ---------------------------------------------------------------- 遗传
def replicate(mother: Genome, sigma: float = 0.15, seed: int = 0,
              child_id: int = 0) -> Genome:
    """★ 冯·诺依曼第二功能：作为【数据】被复制并传给下一代。

    复制 = 照抄；变异 = 每个权重加一个小扰动。
    sigma=0 时应与母体逐位相同（判据①）。
    """
    if not mother.params or "weights" not in mother.params:
        raise NoGenomeError("母体没有 genome，无法生殖")

    rng = np.random.default_rng(seed * 977 + child_id)
    w = np.asarray(mother.params["weights"], dtype=float)
    if sigma > 0:
        w = w + rng.normal(0.0, sigma, size=w.shape)
    scales = list(mother.params["scales"])

    return Genome(
        {"scales": scales, "weights": [float(x) for x in w],
         "ratio": float(mother.params.get("ratio", 2.0)),
         "gain_s": float(mother.params.get("gain_s", 1.0))},
        meta={"origin": "replication",
              "parent": mother.meta.get("origin", "unknown"),
              "generation": int(mother.meta.get("generation", 0)) + 1,
              "sigma": float(sigma), "child_id": int(child_id)},
    )


# ---------------------------------------------------------------- 发育
def develop(child: Genome, frames, ecc_deg: float = 0.0,
            n_iter: int = 3, seed: int = 0) -> Genome:
    """★ 冯·诺依曼第一功能：作为【程序】运行 —— 子代自己长。

    ★ 关键区别：不是照抄母体的答案，
      而是从继承来的起点出发，自己在真素材上再学 n_iter 步。
    """
    if not child.params or "weights" not in child.params:
        raise NoGenomeError("子代没有 genome，无法发育")

    if n_iter <= 0:
        child.meta["developed"] = False
        return child

    p, hist = learn_multi_dog(
        frames, ecc_deg,
        k=len(child.params["weights"]),
        n_iter=n_iter, seed=seed,
        smin=float(child.params["scales"][0]),
        smax=float(child.params["scales"][-1]),
    )
    # ★ 发育的起点是继承来的权重，不是随机权重
    from core.visual_learn import multi_whitening_loss as _loss
    start = list(child.params["weights"])
    best = _loss(frames, ecc_deg, p["scales"], start,
                 float(child.params.get("ratio", 2.0)),
                 float(child.params.get("gain_s", 1.0)))[0]
    w = list(start)
    for it in range(n_iter):
        for i in range(len(w)):
            base = w[i]
            cur = best
            for step in (0.6, 0.25, 0.08):
                for sgn in (1, -1):
                    v = float(np.clip(base * (1.0 + sgn * step)
                                      + sgn * 0.02, -3.0, 3.0))
                    old = w[i]
                    w[i] = v
                    d = _loss(frames, ecc_deg, p["scales"], w,
                              float(child.params.get("ratio", 2.0)),
                              float(child.params.get("gain_s", 1.0)))[0]
                    if d < cur - 1e-9:
                        cur, base = d, v
                    w[i] = old
                w[i] = base
            best = cur
    child.params["weights"] = [float(x) for x in w]
    child.params["scales"] = p["scales"]
    child.meta["developed"] = True
    child.meta["dev_hist"] = [float(best)]
    return child


# ---------------------------------------------------------------- 适应度
def fitness(g: Genome, frames, ecc_deg: float = 0.0) -> float:
    """损失越小越适应。★ 只做观测，不设上限（★50 教训）。"""
    if not g.params or "weights" not in g.params:
        raise NoGenomeError("没有 genome，无法评估适应度")
    return multi_whitening_loss(
        frames, ecc_deg,
        g.params["scales"], g.params["weights"],
        float(g.params.get("ratio", 2.0)),
        float(g.params.get("gain_s", 1.0)))[0]


# ---------------------------------------------------------------- 世代
def evolve(mother: Genome, frames, generations: int = 6,
           n_child: int = 4, sigma: float = 0.15,
           n_iter: int = 3, ecc_deg: float = 0.0,
           selection: bool = True, mutation: bool = True,
           develop_on: bool = True, seed: int = 0,
           start_random: bool = False):
    """跑若干代。返回 (最终母体, 逐代记录)。

    消融开关：
      mutation=False   → 无变异（纯复制）
      develop_on=False → 无发育（只继承，不自己长）
      selection=False  → 无选择（随机挑一个存活）
    """
    cur = mother
    log = []
    rng = np.random.default_rng(seed)
    f0 = fitness(cur, frames, ecc_deg)
    log.append({"gen": 0, "best": f0, "mean": f0})

    for g in range(1, generations + 1):
        kids = []
        for c in range(n_child):
            k = replicate(cur, sigma if mutation else 0.0, seed=seed + g,
                          child_id=c)
            if develop_on:
                k = develop(k, frames, ecc_deg, n_iter, seed=seed + g * 31 + c)
            kids.append(k)
        fs = [fitness(k, frames, ecc_deg) for k in kids]
        if selection:
            nxt = kids[int(np.argmin(fs))]
        else:
            nxt = kids[int(rng.integers(0, len(kids)))]
        cur = nxt
        log.append({"gen": g, "best": float(np.min(fs)),
                    "mean": float(np.mean(fs))})
    return cur, log


def generation_gain(log) -> float:
    """第 0 代到第 N 代，最优适应度改善了多少。"""
    return log[0]["best"] - log[-1]["best"]
