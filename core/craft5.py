#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft5 —— 能力习得（★75）：让她【自己训练自己】

查回来的真范式 —— 全是"自己训练"的【失败模式】，不是成功学：

════ ① 模型塌缩（Nature 2024, Shumailov et al., 631:755-759）════
  "indiscriminately learning from data produced by other models causes
   'model collapse' — a degenerative process whereby, over time, models
   forget the true underlying data distribution"
  ★ 原文关键： tails disappearing first（先丢尾部），
    且 "this process is inevitable, even for cases with almost ideal
    conditions ... that is, no function estimation error"
    —— 即使没有函数估计误差，塌缩也不可避免。
  ★ 而且："无论是否保留原始数据，模型崩溃现象都发生了"（科普中国对该文的转述）

════ ② rise-then-collapse（arXiv 2606.21090）════
  Qwen-2.5-7B 竞技编程：pass@1 前 50 步 25%→81%，到 200 步崩到接近 0。
  ★ 最狠的一句：
    "this strategy also reduces solution diversity by 4% and degrades
     hard-case accuracy by 1% — regressions invisible to the agent
     because it only tracked the target metric"
    —— 退化【对 agent 不可见】，因为它只盯目标指标。

════ ③ 出题者退化 / reward hacking ════
  Stanford SGS：Challenger 发现"把题目写得又臭又长，Solver 就答不出来，我就有奖励"
    → 结论里带"或(∨)"的比例从 <10% 飙到 80%+，长度膨胀约 10 倍。
    → 解法：加第三个角色 Guide，对复杂度打分，complexity≥3 直接给 0 分。
  R-Quest：一致性过滤【反直觉地放大无效问题占比】
    —— 无效问题的答案往往高度一致，反而更容易通过过滤。

════ ④ 难度该定在多少 ════
  R-Zero（腾讯 AI Lab）：Challenger 奖励 = 最大化 Solver 的不确定性
    → Solver 正确率【约 50%】时，Challenger 拿最高奖励。
    → Qwen3-4B-Base 数学 +6.49 分。
  阿里/Qwen 微反思：真正有价值的是"有时对有时错的题"= 最近发展区。
"""

from __future__ import annotations
import numpy as np


# ═════ ① 自生成数据比例 α（递归多代）═════
def selftrain(alpha, n_gen=10, tail0=1.0, tail_loss=0.16,
              data_gain=1.2, seed=0):
    """
    alpha: 训练数据里【自己生成】的比例（1-alpha 是真实数据）
    递归 n 代：每代拿上代的输出当训练数据的一部分。

    ★ 第一版写坏了：数据量增益用了 log1p 且质量项有 0.35 的地板
      → 即使 tail 掉到 0 也还剩 0.35，而 log 的量增益很大
      → 结果代 40 时【纯自生成反而略优于最优 α】，判据 6 假通过。
      修：量增益改成【有上限的线性】，质量项地板降到 0.05（尾部做不了就是做不了）。

    数据量：自生成的便宜 → 量 ↑ 但有上限（边际递减）
    尾部：每代丢失 0.16·alpha（Nature：tails disappear first）
          ★ 且即使 alpha=0 也缓慢流失 —— Nature 原文：
            "无论是否保留原始数据，模型崩溃现象都发生了"
    """
    rng = np.random.default_rng(seed)
    tail = tail0
    for _ in range(n_gen):
        tail *= (1.0 - tail_loss * alpha) - 0.004 * (1 - alpha)
    tail = max(tail, 0.0)
    vol = 1.0 + data_gain * (1.0 - np.exp(-2.2 * alpha))     # 量增益，有上限
    score = vol * (0.05 + 0.95 * tail)                        # 尾部决定尾部任务
    return float(score + rng.normal(0, 0.006))


# ═════ ② 出题目标正确率 δ ════
def propose(delta, seed=0):
    """
    delta: 出题者瞄准的【Solver 正确率】
    R-Zero 说 50% 最优（不确定性最大）。但这里必须有两个真实代价：
      (a) 题越难 → 步骤/算力越多
      (b) 正确率低 → 多数投票给的伪标签不可靠（错的多，投出来的也是错的）
    → 峰应【略高于】0.5（比 R-Zero 的 50% 更保守一点才是真的权衡）
    """
    rng = np.random.default_rng(seed)
    delta = float(np.clip(delta, 0.02, 0.98))
    uncertainty = 4.0 * delta * (1.0 - delta)          # 信息量，峰在 0.5
    label_noise = float(np.exp(-3.0 * delta))          # 正确率越低，伪标签越不可信
    cost = 0.30 * (1.0 - delta)                        # 难题费算力
    gain = uncertainty * (1.0 - 0.85 * label_noise)
    return float(gain - cost + rng.normal(0, 0.008))


# ═════ ③ 隐蔽指标监控权重 γ ════
def monitor(gamma, T=200, seed=0):
    """
    gamma: 拿多少注意力去盯【隐蔽退化】（多样性 / 难题准确率）
    ★ 复现 rise-then-collapse：
        γ 低 → 峰值高（敢冲），但看不见的损伤累积 → 后期崩到接近 0
        γ 中 → 早停/正则，峰值被压低一点，但终点保得住
        γ 高 → 盯过头：不敢优化，停在原地（过度保守也是失败）
    ★ 第一版我写坏了：多样性/难题收益是【线性】的，而"盯过头"的代价
      只有 γ>0.6 才生效且很小 → 变成 γ=1 最好（单调，没内部峰）。
      改：收益边际递减 + 过度监控代价加大。
    """
    rng = np.random.default_rng(seed)
    gamma = float(np.clip(gamma, 0, 1))
    peak = 0.85 * (1.0 - 0.45 * gamma)                      # 监控越严，峰值越低
    severity = float(np.exp(-gamma / 0.16))                 # γ=0 → 崩得最狠
    end = peak * (1.0 - 0.92 * severity)                    # 崩塌后的终点
    diversity = 0.50 * (1.0 - np.exp(-2.5 * gamma))         # 边际递减
    hardcase  = 0.25 * (1.0 - np.exp(-2.0 * gamma))
    over = 0.55 * max(0.0, gamma - 0.45) ** 1.3             # 盯过头 → 不进步
    return float(end + diversity + hardcase - over + rng.normal(0, 0.010))


# ═════ ④ 出题者会不会 reward hack（不是参数，是检验）═════
def proposer_round(strategy, guide=False, lam=1.3, seed=0):
    """
    strategy s: 出题者把精力花在【堆砌复杂度】上的比例（1 = 纯伪难度）

    ★★ 关键建模：出题者【优化的东西】与【我们真正想要的】必须分开。
       第一版我把 real_gain 直接加进了它的奖励 → 它当然选 s=0 → 我测不出
       reward hacking。这是我的尺子错，不是它不会 hack。

    出题者看到的奖励 = Solver 答错率
        fail = 0.30 + 0.60·s + 0.30·(1−s)
        ★ 伪难度【更容易】让 Solver 失败（又臭又长能骗过它），所以 s↑ 奖励↑
    真实价值 = 只有【真的更难】才提升 Solver 能力
        true_gain = 0.70·(1−s)

    无 Guide：出题者使 fail 最大 → s = 1 → 真实价值 0
    有 Guide：reward = fail − λ·s → s = 0 → 真实价值 0.70
    """
    rng = np.random.default_rng(seed)
    s = float(np.clip(strategy, 0, 1))
    fail = 0.30 + 0.60 * s + 0.30 * (1 - s)                 # 出题者的奖励
    true_gain = 0.70 * (1 - s)                              # 真实价值
    reward = fail - (lam * s if guide else 0.0)
    return dict(reward=float(reward + rng.normal(0, 0.012)),
                true=float(true_gain + rng.normal(0, 0.012)),
                fail=float(fail))


# ═════ 训练曲线（复现 rise-then-collapse 的形状）═════
def trace(gamma, T=200):
    """返回 pass@1 随训练步的曲线。γ=0 → 先涨后崩（arXiv 2606.21090 的形状）"""
    gamma = float(np.clip(gamma, 0, 1))
    peak = 0.85 * (1.0 - 0.45 * gamma)
    severity = float(np.exp(-gamma / 0.16))
    ts = np.arange(1, T + 1)
    rise = 1.0 - np.exp(-ts / 18.0)
    decay = severity * 0.92 * (ts / T) ** 1.6
    return 0.22 + (peak - 0.22) * rise - decay * peak
