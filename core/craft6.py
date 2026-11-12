#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft6 —— 能力习得（★76）：多智能体辩论 + 唱反调的批评者
目标：Grok 4 Heavy 那种程度 —— 同一基础模型，并行多实例，辩论收敛。

════ 查证回来的 REAL 数据 ════
  Grok 4 Heavy = 同一 Grok 4，并行最多 16 个实例，各自【独立】推理，
  再 debate-style synthesis 收敛成一个答案（xAI, 2025-07-09）
    AIME 2025      单 91~93%   → Heavy 100%
    HLE with tools 44.4%       → 50.7%
    幻觉率          ~12%        → ~4.2%      降 65%
    AA Omniscience  78% non-hallucination（当时最高）

════ ★ 关键机制：有个专门的批评者 ════
  独立报道（非 xAI 官方）描述四席：队长 / 取材 / 逻辑 / Lucas
  "Lucas exists mainly to disagree with the other three and hunt for
   flaws in their reasoning"
  理由："三个 agent 收敛到一个自信但错误的答案，是典型失败模式；
        一个职责就是反对的 agent，给了系统抓住错误的机会"

════ ★★ 已知死法：AI 回音室 ════
  "If Generator and Judge both come from the same model, their biases may
   reinforce each other ... This is like an 'AI echo chamber' —
   errors are not corrected but amplified"
  → agent 必须【先独立、再辩论】；锚定会毁掉整个机制。
"""

from __future__ import annotations
import numpy as np


def debate(n=4, rho=0.85, lam=0.30, acc=0.88, n_task=400, cost=0.0055, spread=0.45,
           oracle=True, seed=0):
    """
    n   并行实例数
    rho 独立性（1−rho = 锚定比例：直接抄第一个 agent 的答案）
    lam 批评者强度

    ★ 第一版我写坏了：把批评者做成【随机翻转】→ 它不分对错地翻，
      那当然永远是负收益，lam 单调下降、rho 几乎无影响。
      修：批评者必须有【识别能力】——真阳性/假阳性分开，
          且信号质量 ∝ 答案多样性（锚定 → 大家一样 → 无从分辨）。

    流程：
      1. 每个任务有真值 truth ~ Bernoulli(0.5)
      2. n 个 agent 各自以 acc 概率答对（rho<1 时部分直接抄第一个）
      3. 多数派 = maj
      4. 批评者：怀疑 maj 的概率
           真阳性 tpr = λ·g   （g = 多样性带来的分辨力，锚定会毁掉它）
           假阳性 fpr = 0.55·λ²   （λ 越大越爱乱咬）
         → tpr 凹、fpr 凸，所以 λ 有内部峰
      5. 被怀疑 → 翻案为少数派
    """
    rng = np.random.default_rng(seed)
    n = int(max(1, round(n)))
    rho = float(np.clip(rho, 0.0, 1.0))
    lam = float(np.clip(lam, 0.0, 1.0))

    truth = rng.integers(0, 2, n_task)
    # ★ 难度分布：不是每题都一样难
    #   简单题大家全对（批评者没活干），难题分歧大（批评者才有用）
    #   Grok 的 12%→4.2% 是【事实性问答】上的数 —— 那类任务基础错误率高
    diff = rng.random(n_task)
    accs = np.clip(acc + spread / 2.0 - spread * diff, 0.02, 0.995)
    correct_vote = 0.0
    correct_final = 0.0
    halluc = 0.0
    correct_vote_h = np.zeros(n_task); correct_final_h = np.zeros(n_task)
    halluc_h = np.zeros(n_task)

    for t in range(n_task):
        tr = int(truth[t])
        a = float(accs[t])
        # ---- n 个 agent 的答案 ----
        base = tr if rng.random() < a else 1 - tr
        votes = [base]
        for _ in range(n - 1):
            if rng.random() < rho:
                votes.append(tr if rng.random() < a else 1 - tr)
            else:
                votes.append(base)                      # 锚定：抄第一个
        v = np.array(votes, dtype=float)
        p = float(v.mean())                             # 投 1 的比例
        maj = 1 if p >= 0.5 else 0                      # 平局时取 1
        maj_right = int(maj == tr)
        correct_vote += maj_right
        correct_vote_h[t] = maj_right

        # ---- 多样性：辩论的原料 ----
        div = 2.0 * p * (1.0 - p)                       # 0=全一致，0.5=五五开
        g = 0.25 + 2.5 * div                            # 分辨力（锚定 → 掉到 0.25）

        # ---- 批评者 ----
        if oracle:
            tpr = lam * g * 0.95                        # 能抓到真错
            fpr = 0.35 * lam ** 2                       # 也会误伤对的
        else:
            # ★ 关掉 oracle：批评者的怀疑与【是否真错】无关 → 纯噪声
            tpr = fpr = lam * g * 0.5
        susp = (tpr if not maj_right else fpr)
        if rng.random() < susp:
            ans = 1 - maj                               # 翻案为少数派
        else:
            ans = maj
        correct_final += int(ans == tr)
        correct_final_h[t] = int(ans == tr)
        halluc += int(ans != tr and ans == 1)
        halluc_h[t] = int(ans != tr and ans == 1)

    av = correct_vote / n_task
    af = correct_final / n_task
    hal = halluc / n_task
    # ★ 难题分层：多数派最可能错的地方，才是 Lucas 真正的战场
    hard = diff >= 0.70                       # 最难的三成
    nh = max(int(hard.sum()), 1)
    hv = float(correct_vote_h[hard].sum() / nh)
    hf = float(correct_final_h[hard].sum() / nh)
    hh = float(halluc_h[hard].sum() / nh)
    # 独立性的代价：完全不共享 → 重复踩同样的坑
    waste = 0.20 * max(0.0, rho - 0.74) ** 1.2
    return float(af - cost * n - waste + rng.normal(0, 0.003)), hal, af, av, hh, hf, hv
