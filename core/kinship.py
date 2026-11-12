#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kinship —— 亲缘与同源（用群体遗传学当尺子，量顶级 AI）

════ 这不是考卷，是一把尺子 ════
  上一课（★79）我学到：环境不由我设计，由自然科学给。
  这一课更进一步：**连被测量的对象都不是我造的** ——
  是 Grok 4 Heavy 的四人辩论、Anthropic 的 generator/evaluator。

  尺子来自群体遗传学，三条：

  ① 数量遗传学的表型分解   P = G + E
     个体误差 = 同源项（群体共有）+ 特异项（个体独立）
     聚合只能消掉特异项，消不掉同源项。**这是定理，不是假设。**

  ② 近交衰退 / 有效种群大小 Ne
     增加个体数 N ≠ 增加遗传多样性。
     全是同一祖先的克隆，N 再大，Ne ≈ 1，有害等位基因清除不掉。

  ③ 远缘引入（袁隆平的野败）
     打破同源项的唯一办法：引入【没有这个偏差】的远缘个体。
     代价是它个体精度差一点（野生嘛）。

════ 要诊断的三个真实主张 ════
  A Grok：4 个 agent 并行辩论，幻觉 12% → 4.2%（降 65%）
         但 AI Intelligence Index 49 < GPT-5.4/Gemini 57
         CJR 引用幻觉 94%，catch ratio 0.72（不是好的纠错者）
  B Anthropic：generator/evaluator 分离
         但官方明说 "the evaluator is still an LLM that is inclined to
         be generous towards LLM-generated outputs"
         成本 单agent $9/20min → 三agent $200/6h（20倍）
  C 伯克利 MASFT（arXiv 2503.13657）：5 系统 150+ 任务，18 种失败模式
         AppWorld 故障率 86.7%；改角色规范的干预只提升 14%
"""

from __future__ import annotations
import numpy as np

# 真实世界：每个 agent 对同一问题给出一个估计
# x_j = θ + s(同源) + e_j(特异)


def group_estimate(N, omega, sigma_s, sigma_i, sigma_o, sigma_so=0.0, theta=0.0,
                   debate_gain=0.0, rng=None, reps=400):
    """
    N      群体规模（Grok Heavy = 16）
    omega  远缘（野败）比例
    sigma_s 同源偏差强度  —— ★ 所有同源个体共享，聚合消不掉
    sigma_i 同源个体的特异噪声
    sigma_o 远缘个体的特异噪声（野生，通常更差）
    sigma_so 远缘族群自己的同源偏差 —— ★ 连锁累赘（linkage drag）
       真实育种里野败不是万能的：野生亲本在带来优良抗性基因的同时，
       也带来一整套野生不良性状，必须多次回交才能剔除。
       没有这一项，"全野生 ω=1.0"会数学上永远最优 —— 那是错的模型。
    debate_gain 辩论对特异项的削减（互相抓离谱错误，但对同源项无效）
    """
    rng = rng or np.random.default_rng(0)
    n_out = int(round(N * omega))
    n_in = N - n_out
    errs = np.empty(reps)
    for r in range(reps):
        s = rng.normal(0.0, sigma_s)              # 同源偏差：整群共享一个
        vals = []
        if n_in > 0:
            vals.append(theta + s + rng.normal(0, sigma_i * (1 - debate_gain), n_in))
        if n_out > 0:
            s_o = rng.normal(0.0, sigma_so)          # 野生族群自己的系统性偏差
            vals.append(theta + s_o + rng.normal(0, sigma_o * (1 - debate_gain), n_out))
        v = np.concatenate(vals)
        errs[r] = abs(np.mean(v) - theta)
    return float(np.mean(errs))


def error_floor(N, sigma_s, sigma_i, rng=None, reps=400):
    """无野败时，N→∞ 的误差地板：应收敛到 sigma_s（同源项消不掉）"""
    rng = rng or np.random.default_rng(1)
    return group_estimate(N, 0.0, sigma_s, sigma_i, sigma_i, rng=rng, reps=reps)
