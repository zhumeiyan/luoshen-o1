#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Immunity · 免疫与野败 —— 怎么救一个陷在局部最优里的种群
==========================================================

★ 上一层的真问题（★64 的结论）
--------------------------------
过度特化陷阱：孩子从"妈妈已经练熟的解"出发，
反而【全面劣于】从随机起点出发，而且离妈妈越近害得越狠。

父母越精通，其解越是困在局部最优 —— 子女从这个起点出发更难长出新东西。

这正是生物界两个真实机制要解决的问题：

  【野败】1970 年，李必湖在海南发现一株野生稻雄性不育株"野败"。
         栽培稻经过几千年驯化，基因库极窄，育种卡死。
         袁隆平把【远缘野生】的遗传物质引进来 —— 不是从最近的亲本，
         而是从一个野生的、未特化的、甚至"看起来更差"的源。
         结果：三系法杂交水稻成立。
         → 遗传瓶颈的解法不是继续优化，是【引入远缘多样性】。

  【抗体】免疫系统面对从没见过的抗原，不靠微调已有抗体，
         而是 V(D)J 重组：把基因片段库【重新拼接】出海量新组合，
         再体细胞高频突变 + 克隆选择 + 亲和力成熟。
         而且有【记忆】：二次遇到同一抗原，应答快得多、强得多。
         → 多样性的生成靠【重组】，不靠【微调】。

★ 这一层做的事
--------------
  1 近亲繁殖（对照）  继续从特化亲本微调 → 看是不是真的卡死
  2 野败引入          掺入完全野生的、未特化的遗传物质 → 能不能破局
  3 抗体式重组        从多个来源各取片段拼起来 → 对比单点微调
  4 记忆              同一抗原二次应答 → 是不是更快

★ 继承 ★50：监测，不限制。不规定该长成什么样。
★ 硬依赖（★33/★44/★62/★64）：无 genome 抛错，不许回退默认。
"""

import numpy as np

from core.genome import NoGenomeError
from core.visual_learn import multi_whitening_loss


# ---------------------------------------------------------------- 基础
def _scales(k, smin=0.6, smax=24.0):
    return list(np.geomspace(smin, smax, k))


def _loss(frames, ecc, scales, w):
    return multi_whitening_loss(frames, ecc, scales, w)[0]


def affinity_mature(frames, ecc, scales, w0, rounds=6, seed=0,
                    greedy=True):
    """★★ 亲和力成熟：体细胞高频突变 + 选择（克隆选择）。

    greedy=True  → 只接受改进（克隆选择：高亲和力的克隆被保留扩增）
    greedy=False → 随机漂移（对照：没有选择压力）
    """
    rng = np.random.default_rng(seed)
    w = [float(x) for x in w0]
    best = _loss(frames, ecc, scales, w)
    hist = [best]
    for _ in range(rounds):
        improved = False
        for i in range(len(w)):
            base = w[i]
            cur = best
            for step in (0.6, 0.25, 0.08):
                for sgn in (1, -1):
                    v = float(np.clip(base * (1.0 + sgn * step)
                                      + sgn * 0.02, -3.0, 3.0))
                    old = w[i]
                    w[i] = v
                    d = _loss(frames, ecc, scales, w)
                    if d < cur - 1e-9:
                        cur, base, improved = d, v, True
                    w[i] = old
                w[i] = base
            best = cur
        hist.append(best)
        if not improved:
            break
    return [float(x) for x in w], hist


# ---------------------------------------------------------------- 野败
def wild_introduce(w_domestic, ratio, seed=0, wild_range=(-3.0, 3.0)):
    """★★ 野败：把一部分驯化位点替换成【完全野生】的随机值。

    ratio = 野生占比。0 = 纯驯化（继续近亲），1 = 全野生（丢掉一切）。
    ★ 生物真实：野败不是全盘替换，是【远缘渐渗】——只引入关键片段。
    """
    rng = np.random.default_rng(seed)
    w = [float(x) for x in w_domestic]
    n = len(w)
    k_wild = int(round(ratio * n))
    if k_wild <= 0:
        return list(w), []
    idx = rng.choice(n, size=k_wild, replace=False)
    for i in idx:
        w[i] = float(rng.uniform(*wild_range))
    return w, sorted(int(i) for i in idx)


# ---------------------------------------------------------------- 抗体式重组
def vdj_recombine(parents, n_seg=4, seed=0):
    """★★ V(D)J 式重组：把多个来源的权重【分段拼接】，而不是微调。

    ★ 关键区别：
        微调   = 在已有解周围小步动（★63 的发育）
        重组   = 从不同来源各取一段，拼出一个从未存在过的组合
    后者能同时改变多个位点，跳出单点微调够不到的区域。
    """
    rng = np.random.default_rng(seed)
    k = len(parents[0])
    seg = max(1, k // n_seg)
    out = []
    for s in range(n_seg):
        lo, hi = s * seg, min((s + 1) * seg, k)
        if lo >= hi:
            break
        src = parents[int(rng.integers(0, len(parents)))]
        out.extend([float(x) for x in src[lo:hi]])
    while len(out) < k:
        src = parents[int(rng.integers(0, len(parents)))]
        out.append(float(src[len(out)]))
    return out[:k]


# ---------------------------------------------------------------- 免疫记忆
class ImmuneSystem:
    """★ 抗体记忆：见过一次抗原，第二次应答应更快、更强。"""

    def __init__(self):
        self.memory = {}      # antigen -> {"weights": [...], "loss": float}

    def primary(self, antigen, frames, ecc, scales, k, rounds=6, seed=0,
                n_cand=6):
        """初次应答：从零生成一批候选（含重组），选最好的。"""
        rng = np.random.default_rng(seed)
        pool = [[float(rng.uniform(0.1, 0.5)) for _ in range(k)]
                for _ in range(3)]
        best_w, best_l = None, float("inf")
        n_eval = 0
        for i in range(n_cand):
            w0 = vdj_recombine(pool, n_seg=4, seed=seed * 31 + i)
            w, h = affinity_mature(frames, ecc, scales, w0,
                                   rounds=rounds, seed=seed + i)
            n_eval += len(h) * k
            if h[-1] < best_l:
                best_l, best_w = h[-1], w
        self.memory[antigen] = {"weights": list(best_w), "loss": best_l,
                                "evals": n_eval}
        return best_w, best_l, n_eval

    def secondary(self, antigen, frames, ecc, scales, k, rounds=6, seed=0,
                  n_cand=6):
        """二次应答：从【记忆库】出发，而不是从零。"""
        mem = self.memory.get(antigen)
        if mem is None:
            raise NoGenomeError(f"没见过抗原 {antigen}，无从回忆")
        rng = np.random.default_rng(seed)
        pool = [mem["weights"],
                [float(rng.uniform(0.1, 0.5)) for _ in range(k)],
                [float(x) + rng.normal(0, 0.1) for x in mem["weights"]]]
        best_w, best_l = None, float("inf")
        n_eval = 0
        for i in range(n_cand):
            w0 = vdj_recombine(pool, n_seg=4, seed=seed * 31 + i)
            w, h = affinity_mature(frames, ecc, scales, w0,
                                   rounds=rounds, seed=seed + i)
            n_eval += len(h) * k
            if h[-1] < best_l:
                best_l, best_w = h[-1], w
        if best_l < mem["loss"]:
            self.memory[antigen] = {"weights": list(best_w),
                                    "loss": best_l, "evals": n_eval}
        return best_w, best_l, n_eval
