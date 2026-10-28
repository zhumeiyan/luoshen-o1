#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teaching · 教育 —— 怎么教一个正在长大的数字生命
================================================

★ 前面三层是【她自己长】
    ★62 genome    自己学出一层
    ★63 生殖      遗传+发育+选择
    ★64 生长      长出妈妈不会的层（撞上过度特化陷阱）
    ★65 免疫野败   用远缘多样性和重组救活被困种群

★ 这一层是【外部输入】—— 教
    生物和教育学的真实机制：

  1 关键期（Critical Period）
      Hubel & Wiesel：小猫在关键期单眼缝合，之后【永久】弱视。
      成年后再怎么练都追不回来。
      机制：幼年突触可塑性高，之后逐渐固化（髓鞘化、抑制性环路成熟）。
      → 可证伪：同样的教学投入，早教 vs 晚教，效果应有显著差异，
                且晚教之后【加大投入】也追不回来。

  2 最近发展区（Vygotsky ZPD）
      教的难度要落在"她够得着但需要努力"的边缘。
      太近 = 已经会了，没进步；太远 = 学不会。
      → 可证伪：教学收益随难度应是【倒 U】，存在最优难度。

  3 课程编排（Curriculum）
      从易到难 vs 从难到易 vs 乱序。
      → 可证伪：易→难 应优于 难→易。

  4 示范 vs 反馈（Imitation vs Trial-and-error）
      直接给答案让她模仿，还是只给对错让她自己试？
      → 关键检验：模仿可能【当前任务学得快】，但【迁移到新情况】会变差
        （过拟合到老师的解，没学会方法本身）。这是诚实的双面检验。

★ 继承 ★50：监测，不限制。不规定她该长成什么样。
★ 硬依赖：无 genome / 无素材抛错，不许回退默认。
"""

import numpy as np

from core.genome import NoGenomeError
from core.visual_learn import multi_whitening_loss


# ---------------------------------------------------------------- 可塑性
def learn_with_plasticity(frames, ecc, scales, w0, rounds=3,
                          plasticity=1.0, seed=0):
    """★★ 带【可塑性】的学习。

    plasticity = 突触可塑程度，决定一步能走多远：
        1.0  幼年：可以大幅重排权重
        0.1  成年：只能在原地微调（已经固化）

    生物对应：关键期内突触可大幅重塑；关键期后环路固化。
    """
    if plasticity <= 0:
        raise NoGenomeError("可塑性为 0，无法学习")
    w = [float(x) for x in w0]
    best = multi_whitening_loss(frames, ecc, scales, w)[0]
    hist = [best]
    for _ in range(rounds):
        improved = False
        for i in range(len(w)):
            base = w[i]
            cur = best
            for step in (0.6, 0.25, 0.08):
                for sgn in (1, -1):
                    # ★ 步长被可塑性缩放：可塑性低时只能微调
                    d = base * step * plasticity
                    v = float(np.clip(base + sgn * d + sgn * 0.02 * plasticity,
                                      -3.0, 3.0))
                    old = w[i]
                    w[i] = v
                    l = multi_whitening_loss(frames, ecc, scales, w)[0]
                    if l < cur - 1e-9:
                        cur, base, improved = l, v, True
                    w[i] = old
                w[i] = base
            best = cur
        hist.append(best)
        if not improved:
            break
    return [float(x) for x in w], hist


def developmental_plasticity(stage, p0=1.0, tau=3.0):
    """发育过程中的可塑性衰减曲线。stage = 发育阶段（0=新生）。

    生物：出生后可塑性最高，随成熟指数衰减。
    """
    return float(p0 * np.exp(-float(stage) / tau))


# ---------------------------------------------------------------- 教学
def teach(frames, ecc, scales, k, plasticity=1.0, rounds=3, seed=0,
          init=None):
    """一次教学：在给定难度（ecc）上教，返回 (weights, hist)。"""
    rng = np.random.default_rng(seed)
    w0 = list(init) if init is not None else \
        [float(rng.uniform(0.1, 0.5)) for _ in range(k)]
    return learn_with_plasticity(frames, ecc, scales, w0, rounds=rounds,
                                 plasticity=plasticity, seed=seed)


def curriculum(frames, ecc_seq, scales, k, plasticity=1.0, rounds=3,
               seed=0, warm_start=True):
    """★ 课程编排：按给定顺序教一串难度。

    warm_start=True  → 每节课从前一节课的权重出发（累积）
    warm_start=False → 每节课都从头（对照）
    """
    if not ecc_seq:
        raise NoGenomeError("课程为空，无从教起")
    w = None
    log = []
    for i, ecc in enumerate(ecc_seq):
        w, h = teach(frames, ecc, scales, k, plasticity=plasticity,
                     rounds=rounds, seed=seed * 17 + i,
                     init=w if (warm_start and w is not None) else None)
        log.append({"ecc": float(ecc), "start": h[0], "end": h[-1]})
    return w, log


# ---------------------------------------------------------------- 示范
def imitate(teacher_w, noise=0.05, seed=0):
    """★★ 示范：直接把老师的解给她抄（带一点噪声）。

    对照是"只给反馈"（teach 里只给损失，自己搜）。
    """
    rng = np.random.default_rng(seed)
    return [float(x) + float(rng.normal(0, noise)) for x in teacher_w]


# ---------------------------------------------------------------- 合成素材
def synth_natural(size=64, alpha=2.0, seed=0):
    """生成一张【谱指数已知】的合成自然图像（ground truth 可控）。

    ★ 为什么需要它：.frames 里 476 个文件 md5 全都相同（同一张图的副本），
      无法做泛化检验。合成图能保证彼此【真的不同】且谱指数已知。
    """
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2)
    r[0, 0] = 1e-6
    amp = r ** (-alpha / 2.0)
    ph = rng.uniform(0, 2 * np.pi, (size, size))
    z = amp * np.exp(1j * ph)
    img = np.real(np.fft.ifft2(z))
    img = img - img.min()
    mx = img.max()
    if mx > 0:
        img = img / mx
    return img.astype(float)
