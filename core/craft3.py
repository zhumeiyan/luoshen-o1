#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft3 —— 能力习得（★73）第三批：世界模型 · 想象推演 · 分层分解 · 技能库 · 经验回放

查回来的真范式（都做成【环境】，不写成 if 判断）：

════ ① 世界模型 / 想象推演（Qwen-AgentWorld · DreamerV3 · DIAMOND）════
  真范式：
    Qwen-AgentWorld  —— "native language world model that simulates agentic
        environments via long chain-of-thought reasoning"；三阶段：
        CPT 注入环境知识 → SFT 激活 next-state-prediction → RL 打磨仿真保真度。
        ★ 它不把 world modeling 当独立模块，而是【用 CoT 在语言空间里模拟环境】。
    DreamerV3 / DIAMOND —— 在 latent space 里"做梦"预演，不真去环境里试错。
  权衡：
    预演浅 → 看不到远期后果
    预演深 → 模型误差逐步累积（滚雪球），且每步都要算力
  → 她学：推演深度 d

  准确性 = (1 − exp(−d / L))       # 看得越远越准（任务视野 L）
           × exp(−ε·d)             # 但模型误差随深度累积
           − c·d                   # 每步算力成本

════ ② 分层分解粒度（GITM：goal → subgoal → action）════
  真范式：
    GITM —— "integrates LLMs with text-based knowledge and memory"；
            解锁 Minecraft 科技树 100%，ObtainDiamond 67.5%（SOTA +47.5%），
            且【不需要 GPU，单机 32 核 CPU 两天训完】。
  权衡：
    拆太粗 → 单个 subgoal 复杂度超出规划器能力，做不了
    拆太细 → 步骤数暴涨，累积失败率 + 规划开销
  → 她学：拆几层 n

  单步成功率 p = σ((cap − C/n) / temp)      # 每份复杂度要在能力上限内
  总成功率   = p^n − cost·n

════ ③ 技能库 / 记忆复用（GITM memory：学到的技能存下来复用）════
  真范式：
    GITM 把"文本知识与记忆"注入 LLM，让 agent 能【积累】而不是每次从零想。
  权衡：
    库太小 → 命中率低，每次都得重学
    库太大 → 检索噪声（误命中）+ 维护成本
  → 她学：库保持多大 m

  命中率 = 1 − exp(−m / K)
  代价   = 维护 c·m + 检索噪声 n·m

════ ④ 经验回放比例（Dreamer 系：replay ratio）════
  真范式：把过去的轨迹存下来反复学（sample efficiency）。
  权衡：
    重放太少 → 一条样本只学一次，学不透（欠拟合）
    重放太多 → 反复嚼旧数据，过拟合 / 分布偏移
  → 她学：重放比 r

  充分度 = 1 − exp(−r / R)
  代价   = 陈旧 g·r²
"""
from __future__ import annotations
import numpy as np


# ═════ ① 想象推演深度 ═════
def imagine(d, horizon=8.0, eps=0.12, cost=0.010, seed=0, n=400):
    """
    ★ oracle：环境真转移（推演靠它）。关掉 oracle = 推演看不到真后果
      → 准确性不再随 d 提升 → 峰消失（判据8 用）
    """
    rng = np.random.default_rng(seed)
    d = float(d)
    reach = 1.0 - np.exp(-d / horizon)          # 看多远
    drift = np.exp(-eps * d)                    # 模型误差累积
    noise = float(rng.normal(0, 0.01))
    return float(reach * drift - cost * d + noise)


# ═════ ② 分层分解粒度 ═════
def decompose(n, complexity=1.0, cap=0.35, temp=0.08, cost=0.020, seed=0):
    rng = np.random.default_rng(seed)
    n = max(1, int(round(n)))
    per = complexity / n
    p = 1.0 / (1.0 + np.exp(-(cap - per) / temp))     # 单步成功率
    total = p ** n
    return float(total - cost * n + float(rng.normal(0, 0.005)))


# ═════ ③ 技能库大小 ═════
def skill_lib(m, K=6.0, maint=0.020, noise=0.004, seed=0):
    rng = np.random.default_rng(seed)
    m = max(0, int(round(m)))
    hit = 1.0 - np.exp(-m / K)
    return float(hit - maint * m - noise * m + float(rng.normal(0, 0.008)))


# ═════ ④ 经验回放比 ═════
def replay(r, R=3.0, stale=0.012, seed=0):
    rng = np.random.default_rng(seed)
    r = float(max(0.0, r))
    suff = 1.0 - np.exp(-r / R)
    return float(suff - stale * r * r + float(rng.normal(0, 0.006)))
