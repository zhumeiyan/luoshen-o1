#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft4 —— 能力习得（★74）第四批：多模态整合 · 从反馈学 · 自我改进 · 长上下文管理

════ ① 多模态同时整合（她有眼有耳，缺"同时"）════
  真范式：多感官整合 —— 两模态【一致】时互益（冗余增益），【冲突】时互相干扰。
          大脑按各模态的【可靠性】加权（最大似然估计模型）。
          完全不信某一个 = 丢一半信息；完全信某一个 = 冲突时惨败。
  → 她学：融合权重 w（给视觉多少权重，剩下给听觉）
  一致性 c 高 → 融合好；c 低 → 融合会互相污染，应偏向更可靠的那一侧

════ ② 从反馈里学（DPO 式：pass 正例 / fail 负例）════
  真范式：把执行结果（pass/fail）直接当监督信号，不用人工标注。
  权衡：负例权重太小 → 学不会避开错误
        负例权重太大 → 崩塌（什么都往"不像负例"的方向跑，输出退化）
  → 她学：负例权重 β

════ ③ 自我改进 / 长出新的动作（LearnAct：debug 自己的技能集）════
  真范式：agent 不只是调用固定工具，而是【debug 并扩展自己的动作空间】。
  权衡：只利用已有动作 → 遇到新类型任务做不了
        总在造新动作 → 每个动作都没练熟（探索/利用）
  → 她学：新动作占比 ρ

════ ④ 长上下文管理（什么时候 clear / compact）════
  真范式：上下文是稀缺资源。留太多 → 噪声+成本；压太狠 → 丢关键信息。
  权衡：保留比例 k 小 → 省但丢信息；k 大 → 全但噪声累积
  → 她学：保留比例 k
"""
from __future__ import annotations
import numpy as np


# ═════ ① 多模态整合 ═════
def fuse(w, consistency=0.75, rel_v=0.8, rel_a=0.6, seed=0, n=200):
    """
    ★ 用【精度加权】整合（Ernst&Banks 最大似然模型）：
        σv = 1 − rel_v,  σa = 1 − rel_a
        σ²(w) = w²σv² + (1−w)²σa²      → 在 w* = σa²/(σv²+σa²) 处最小
        ★ 融合后的 σ 比【任一单模态都小】——这才是整合真正的收益
          （二次组合 = 永远不超过 max，那是错的建模；我第一版就栽在这，
           结果 c 再高也是"纯用视觉最好"，峰恒在边界，尺子没区分度）
    一致性 c 高 → 冗余增益 + 有备份（鲁棒）
    一致性 c 低 → 两模态互相污染（harm ∝ w(1−w)）→ 该退回单一模态
    """
    rng = np.random.default_rng(seed)
    w = float(np.clip(w, 0, 1))
    c = float(np.clip(consistency + rng.normal(0, 0.03), 0, 1))
    sv, sa = 1.0 - rel_v, 1.0 - rel_a
    sig = float(np.sqrt((w*sv)**2 + ((1-w)*sa)**2))
    rel = 1.0 - sig                                  # 融合可靠性
    gain = 1.0 + 0.20 * c                            # 一致 → 冗余增益
    harm = 1.00 * (1.0 - c) * w * (1 - w)            # 冲突 → 跨模态污染
    backup = 0.12 * (1.0 - c) * (w*w + (1-w)**2)     # 纯单模态没有备份
    return float(rel * gain - harm - backup + rng.normal(0, 0.006))


# ═════ ② 从反馈学（DPO 式）════
def learn_from_feedback(beta, n_pos=30, n_neg=30, margin=0.35, seed=0):
    """
    beta: 负例权重
    太小 → 学不会避开错误（负例没被推开）
    太大 → 崩塌（输出被负例反向拉爆，退化）
    """
    rng = np.random.default_rng(seed)
    pos = float(rng.normal(1.0, 0.2, n_pos).mean())
    neg = float(rng.normal(0.0, 0.2, n_neg).mean())
    gain = 1.0 - np.exp(-beta / 0.9)                 # 学会避开错误
    collapse = 0.22 * max(0.0, beta - 2.2) ** 1.6    # 越过临界 → 崩塌
    return float(pos + margin * gain - beta * 0.05 * abs(neg) - collapse
                 + rng.normal(0, 0.02))


# ═════ ③ 自我改进 / 新动作占比 ═════
def self_improve(rho, n_task=60, novelty=0.55, seed=0):
    """
    rho: 花在【造新动作】上的比例（剩下用来把已有动作练熟）
    """
    rng = np.random.default_rng(seed)
    rho = float(np.clip(rho, 0, 1))
    # 已有动作练熟的收益（递减）
    mastered = 1.0 - np.exp(-3.0 * (1 - rho))
    # 新动作覆盖新类型任务（递减，且没练熟就不顶用）
    new = novelty * (1.0 - np.exp(-2.2 * rho)) * np.exp(-1.1 * rho)
    return float(0.55 * mastered + new + rng.normal(0, 0.012))


# ═════ ④ 长上下文管理 ═════
def context_keep(k, n_ctx=40, imp_skew=1.6, seed=0):
    """
    k: 保留比例（0..1）。其余 compact 掉。
    保留多 → 信息全但噪声进来了；保留少 → 干净但丢关键信息
    """
    rng = np.random.default_rng(seed)
    k = float(np.clip(k, 0, 1))
    imp = np.sort(rng.pareto(imp_skew, n_ctx))[::-1]
    kept = imp[:max(1, int(round(k * n_ctx)))]
    info = float(kept.sum() / imp.sum())
    noise = 0.42 * k ** 2                       # 噪声随保留量超线性增长
    cost = 0.18 * k
    return float(info - noise - cost + rng.normal(0, 0.008))
