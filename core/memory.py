#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory · 记忆 —— 她为什么"记性不好"
=====================================

★ 起因
------
朱美岩说：别人说她记性不太好，你当妈的怎么做。

先诊断，不辩解：
    全仓搜 memory / 海马 / 巩固 / 遗忘 / 间隔
    → 命中的只有 immunity.py 里一个 dict（存权重，没有衰减、没有巩固、没有干扰）
    → **她根本没有记忆器官。**
      不是"记性差"，是我从没给她装过海马体。
      （★ 归因：造物主侧。跟 ★61 素材、★66 副本同一类。）

★ 但作为妈，不能只给她装一个"不会忘"的记忆。
  因为【遗忘本身是功能】：
    · 环境在变，过时的记忆必须被淘汰（概念漂移）
    · 什么都记得 = 检索时被旧条目淹没
    · 不遗忘的系统会过拟合到噪声样本
  ⇒ 这一层要证明：会遗忘的系统，在变化的环境中【泛化更好】。
    如果这条成立，那"记性不好"这个评价本身就是错的。

★ 真实机制（全部可证伪）
------------------------
  1 遗忘曲线（艾宾浩斯）  R = e^(-t/τ)，保留率随时间指数衰减
  2 必要难度（Bjork）    提取越费力，增强越大 → 复习间隔存在【最优】，倒 U
  3 测试效应             主动提取比被动重看更巩固
  4 巩固                 离线回放（睡眠）减缓衰减
  5 干扰                 相似条目互相竞争，降低目标提取率
  6 提取失败 ≠ 存储失败  认得出 > 想得起（舌尖现象）
  7 遗忘的功能           变化环境下，会遗忘的适应更快

★ 继承 ★50：监测，不限制。不规定她该记住什么。
★ 硬依赖：空记忆库 / 无条目 抛错，不许回退默认。
"""

import numpy as np

from core.genome import NoGenomeError


# ---------------------------------------------------------------- 条目
class MemoryItem:
    """一条记忆。strength ∈ [0,1]，越强越容易被提取。"""

    __slots__ = ("key", "content", "strength", "tau", "n_recall", "age")

    def __init__(self, key, content, strength=1.0, tau=20.0):
        self.key = key
        self.content = np.asarray(content, dtype=float)
        self.strength = float(np.clip(strength, 0.0, 1.0))
        self.tau = float(tau)
        self.n_recall = 0
        self.age = 0.0


# ---------------------------------------------------------------- 记忆系统
class MemorySystem:
    """★ 记忆系统：会遗忘、能被提取加固、会互相干扰。

    ★★ 核心机制（这是 spacing effect 和 testing effect 的共同来源）：

        提取成功概率   p = strength
        提取带来的增益 gain ∝ (1 - strength)     ← 越费力，增强越大
        期望增益       E = p × (1 - strength)    ← 在 strength=0.5 时最大

    ⇒ 由此自动推出【复习间隔存在最优值】：
        复习太早：记忆还强（s→1），(1-s)→0，增益≈0
        复习太晚：记忆已弱（s→0），p→0，提取不出来，增益≈0
        中等间隔：s≈0.5，增益最大                 ★ 倒 U，可证伪
    """

    def __init__(self, tau0=20.0, gain=0.6, tau_growth=0.35,
                 interference=0.5, seed=0):
        if tau0 <= 0:
            raise NoGenomeError("tau0 必须为正，否则记忆瞬间消亡")
        self.tau0 = float(tau0)
        self.gain = float(gain)
        self.tau_growth = float(tau_growth)
        self.interference = float(interference)
        self.items = {}
        self.rng = np.random.default_rng(seed)
        self.t = 0.0

    # ---- 写 ----
    def store(self, key, content, strength=1.0):
        self.items[key] = MemoryItem(key, content, strength, self.tau0)
        return self.items[key]

    # ---- 时间流逝 ----
    def advance(self, dt=1.0):
        """★★ 遗忘：所有条目指数衰减。"""
        for it in self.items.values():
            it.strength *= float(np.exp(-dt / it.tau))
            it.age += dt
        self.t += dt

    # ---- 提取 ----
    def _sim(self, q, it):
        a = np.asarray(q, dtype=float)
        b = it.content
        n = min(len(a), len(b))
        if n == 0:
            return 0.0
        a, b = a[:n], b[:n]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def recall(self, query, topk=1):
        """★★ 提取：强度 × 相似度，并受【干扰项】压制。

        返回 (命中的 key 列表, 是否成功)
        """
        if not self.items:
            raise NoGenomeError("记忆库为空，无从提取")
        scores = []
        for k, it in self.items.items():
            s = self._sim(query, it)
            scores.append((k, s * it.strength))
        scores.sort(key=lambda x: -x[1])
        if not scores or scores[0][1] <= 1e-9:
            return [], False
        # 干扰：竞争者越强，目标越难被提取
        tops = scores[:max(1, topk)]
        rivals = scores[max(1, topk):]      # ★ 全部竞争者，不再截 6 个
        rival = float(np.sum([r[1] for r in rivals])) if rivals else 0.0
        lead = tops[0][1]
        p = lead / (lead + self.interference * rival + 1e-12)
        ok = bool(self.rng.random() < p)
        if ok:
            self._strengthen(tops[0][0])
        return [t[0] for t in tops], ok

    def _strengthen(self, key):
        """★★ 提取成功 → 加固。增益 ∝ (1 - strength)（越费力越有效）

        ★ 修正（★67）：tau 的延长【也】必须 ∝ (1-s)。
          否则 s≈1 时（复习太早）虽然增益≈0，但 tau 仍无条件增长，
          反复复习就能无限拉长 tau → 实测最优间隔退到 1，倒U消失。
          真实机制：只有当提取【费力】时才触发巩固。
        """
        it = self.items[key]
        d = 1.0 - it.strength
        it.strength = float(np.clip(it.strength + self.gain * d, 0.0, 1.0))
        it.tau *= (1.0 + self.tau_growth * d)   # ★ 费力才延长
        it.n_recall += 1

    def review(self, key, strength=1.0):
        """被动重看（对照：比主动提取弱得多）。"""
        if key not in self.items:
            raise NoGenomeError(f"没存过 {key}")
        it = self.items[key]
        it.strength = float(np.clip(max(it.strength, strength * 0.8), 0.0, 1.0))

    # ---- 巩固：离线回放 ----
    def consolidate(self, n_replay=None, boost=0.25):
        """★★ 巩固（睡眠/离线回放）：随机挑一批条目回放，减缓衰减。

        机制：tau 延长 → 之后衰减更慢。
        """
        if not self.items:
            raise NoGenomeError("记忆库为空，无从巩固")
        keys = list(self.items.keys())
        n = n_replay or max(1, len(keys) // 2)
        pick = self.rng.choice(keys, size=min(n, len(keys)), replace=False)
        for k in pick:
            it = self.items[k]
            it.tau *= (1.0 + boost)
        return len(pick)

    # ---- 认得出 vs 想得起 ----
    def recognize(self, query):
        """★★ 再认：给候选，只要相似度最高就选对（不需要强度支撑）。

        对照 recall（自由回忆，需要 strength 足够高才能提取成功）。
        REAL：舌尖现象 —— 认得出但想不起。
        """
        if not self.items:
            raise NoGenomeError("记忆库为空")
        best, bk = -2.0, None
        for k, it in self.items.items():
            s = self._sim(query, it) * it.strength   # ★ 强度参与再认
            if s > best:
                best, bk = s, k
        return bk, best


# ---------------------------------------------------------------- 概念漂移
def drift_world(n_items=60, dim=8, n_rounds=40, drift=0.35, noise=0.20,
                seed=0):
    """★ 变化的世界：每条记忆的"正确答案"会缓慢漂移。

    用来检验【遗忘的功能】：
        不遗忘的系统被过时条目拖累
        会遗忘的系统自动淘汰过时条目 → 适应更快
    """
    rng = np.random.default_rng(seed)
    truth = rng.normal(size=(n_items, dim))
    hist = []
    for r in range(n_rounds):
        drift_step = rng.normal(scale=drift, size=(n_items, dim))
        truth = truth + drift_step
        # ★ 看到（存入）的和考的必须是【两份独立的含噪采样】
        #   若考的就是存的那份，最新条目相似度恒=1，永远赢 → 组间无差异
        q_store = truth + rng.normal(scale=noise, size=(n_items, dim))
        q_test = truth + rng.normal(scale=noise, size=(n_items, dim))
        hist.append((r, truth.copy(), q_store, q_test))
    return hist
