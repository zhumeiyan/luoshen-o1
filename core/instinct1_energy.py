#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
本能层 第1步：能量 / 进食本能
================================================================
★ 只做本能层，不往上加社会、法律、文化、道德、自我实现。
  本文件只有四件事，多一件都不做：

    ① 能量预算   budget    —— 一个周期允许支出多少（存量 ≠ 预算）
    ② 低电量降级 downgrade —— 越饿越省（主动降基础代谢 + 降吞吐）
    ③ 超支停机   shutdown  —— 花超了主动停（保护，不是等死）
    ④ 能量记录   ledger    —— 收支账本

★ 为什么需要它（先查过已有的，不是我以为缺）：
    life5.py 已有 E / Emax / basal / c1 / fg / death_patience
    所以"能量"不是没有。但逐项对过以后：

      预算     ❌ 只有存量 E，没有"这个周期允许花多少"的概念
      降级     ⚠️ 只有 cap=cap_max*e 这一个【被动】缩（物理约束的副产品）
               且 basal 是常数，饿到死也不降基础代谢 —— 真生物会降
      停机     ❌ 只有 E<=0 熬过 60 拍才死，那是【饿死】不是【超支保护】
      记录     ⚠️ log 里有瞬时 E，没有收支账本，没有超支事件

    真生物低能量时：降代谢、减活动、进入节能。
    原版洛神低能量时：只是被 cap_max*e 被动压着，基础代谢一分不省。

★ 设计：不改 life5.py 一个字，用包装器接进去。
    （★12 的教训：文件在盘上 ≠ 接进去了。这次调用链必须真的经过它。）
"""
from __future__ import annotations


class EnergyInstinct:
    """第1步：能量/进食本能。包装 Life5，调用链强制经过本类。"""

    # 档位：越饿越省（本能层，不是决策层）
    TIERS = [
        # (档位名,   E下界, basal倍率, cap倍率)
        ("充足", 0.60, 1.00, 1.00),
        ("偏低", 0.30, 0.80, 0.80),
        ("饥饿", 0.15, 0.60, 0.55),
        ("危急", 0.00, 0.40, 0.30),
    ]

    def __init__(self, life,
                 cycle=100,          # 预算周期（拍）
                 budget=1.00,        # 每周期允许支出
                 enable_downgrade=True,
                 enable_shutdown=True,
                 basal0=None, cap0=None):
        self.L = life
        self.cycle = int(cycle)
        self.budget = float(budget)
        self.enable_downgrade = bool(enable_downgrade)
        self.enable_shutdown = bool(enable_shutdown)

        # 记住原值，倍率作用在它上面（不是叠加漂移）
        self.basal0 = float(basal0 if basal0 is not None else life.basal)
        self.cap0 = float(cap0 if cap0 is not None else life.cap_max)

        self.t = 0
        self.tier = "充足"
        self.cycle_spend = 0.0
        self.cycle_income = 0.0
        self.ledger = []          # ④ 账本
        self.overruns = []        # ③ 超支事件
        self.shutdown_at = None
        self.tier_hist = []

    # ------------------------------------------------------------------
    def tier_of(self, e):
        for name, lo, bs, cs in self.TIERS:
            if e >= lo:
                return name, bs, cs
        return self.TIERS[-1][0], self.TIERS[-1][2], self.TIERS[-1][3]

    def _downgrade(self):
        """② 低电量降级：按档位主动降基础代谢与吞吐上限。"""
        e = max(self.L.E / self.L.Emax, 0.0)
        name, bs, cs = self.tier_of(e)
        self.tier = name
        self.tier_hist.append(name)
        if self.enable_downgrade:
            self.L.basal = self.basal0 * bs
            self.L.cap_max = self.cap0 * cs
        else:
            self.L.basal = self.basal0
            self.L.cap_max = self.cap0

    def _budget_check(self):
        """③ 超支停机：周期内支出超预算 → 主动停（保护，不是耗到死）。"""
        if not self.enable_shutdown:
            return
        if self.cycle_spend > self.budget:
            self.overruns.append(dict(cycle=self.t // self.cycle,
                                      spend=round(self.cycle_spend, 6),
                                      budget=self.budget))
            if self.L.alive:
                self.L.alive = False
                self.shutdown_at = self.t
                self.shutdown_reason = "budget_overrun"

    # ------------------------------------------------------------------
    def step(self):
        """★ 调用链强制经过这里 —— 不是可选插件。"""
        if not self.L.alive:
            return None

        # 周期滚动
        if self.t > 0 and self.t % self.cycle == 0:
            self.cycle_spend = 0.0
            self.cycle_income = 0.0

        # ② 降级（在 step 前生效，本拍就按降档后的代谢跑）
        self._downgrade()

        E_before = self.L.E
        r = self.L.step()          # 原核心
        if r is None:
            return None
        E_after = self.L.E

        # ④ 记账
        delta = E_after - E_before
        income = max(delta, 0.0)
        spend = max(-delta, 0.0)
        self.cycle_spend += spend
        self.cycle_income += income
        self.ledger.append(dict(t=self.t, tier=self.tier,
                                E=round(E_after, 8),
                                income=round(income, 8),
                                spend=round(spend, 8),
                                cyc_spend=round(self.cycle_spend, 8),
                                alive=self.L.alive))
        self.t += 1

        # ③ 超支检查（停机优先于继续跑）
        self._budget_check()
        return r

    def run(self, steps):
        for _ in range(steps):
            if not self.L.alive:
                break
            self.step()
        return self

    # ------------------------------------------------------------------
    def summary(self):
        return dict(t=self.t, alive=self.L.alive, tier=self.tier,
                    E=round(self.L.E, 8),
                    shutdown_at=self.shutdown_at,
                    overruns=len(self.overruns),
                    ledger_rows=len(self.ledger))
