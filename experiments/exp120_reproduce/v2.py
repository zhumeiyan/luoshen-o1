# -*- coding: utf-8 -*-
"""
繁衍系统 v2 —— 修正版
针对 v1 六个静默失效：共享引用 / 常量变异 / 零成本 / 适应度自证 / 无死亡 / 无谱系
"""
import copy
import hashlib
import random


COST_REPRO = 8.0        # 复制一次父代支付
COST_LIFE = 1.0         # 每代维持消耗
GAIN_MAX = 6.0          # 每代从环境摄取上限


def _h(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


class Individual:
    def __init__(self, cid, genome, chain, energy, parent_id=None):
        self.cid = cid
        self.genome = list(genome)
        self.memory_chain = list(chain)      # 显式建新列表，不共享
        self.energy_b = energy
        self.parent_id = parent_id
        self.alive = True
        self.self_reported_fitness = None    # 不采信，只记录

    def chain_head(self):
        return self.memory_chain[-1]

    def genotype(self, grid=2):
        return tuple(round(x, grid) for x in self.genome)


class Environment:
    """独立审计器：适应度由环境算，个体说了不算。
    niche_centers 决定世界有几个山峰。"""

    def __init__(self, niche_centers, sigma=0.35, rng=None):
        self.centers = [list(c) for c in niche_centers]
        self.sigma = sigma
        self.rng = rng or random.Random(0)

    def evaluate(self, ind):
        best = 0.0
        for c in self.centers:
            d2 = sum((a - b) ** 2 for a, b in zip(ind.genome, c))
            v = pow(2.718281828459045, -d2 / (2 * self.sigma ** 2))
            best = max(best, v)
        return best                      # 0..1

    def forage(self, ind):
        """摄食：按适应度分配，带随机波动"""
        f = self.evaluate(ind)
        return GAIN_MAX * f * (0.7 + 0.6 * self.rng.random())


class ReproductionSystemV2:
    def __init__(self, env, rng, mu=0.1):
        self.env = env
        self.rng = rng
        self.mu = mu
        self.deaths = 0
        self.births = 0

    def replicate(self, parent, cid):
        # 父代必须付得起，否则不产生后代
        if parent.energy_b < COST_REPRO:
            return None
        parent.energy_b -= COST_REPRO

        g = [x + self.rng.gauss(0, self.mu) for x in parent.genome]
        g = [max(0.0, min(1.0, x)) for x in g]

        # 谱系：子的链头 = hash(父链头, 自身基因型, 随机数) —— 每次不同
        head = _h(parent.chain_head(), [round(x, 8) for x in g], self.rng.random())
        chain = parent.memory_chain + [head]     # 新列表，父不受影响

        child = Individual(cid, g, chain, COST_REPRO * 0.5, parent_id=parent.cid)
        self.births += 1
        # 独立的出生事件也刻进父链（父自己的历史），但对象是父自己的
        parent.memory_chain = parent.memory_chain + [_h("spawned", cid)]
        return child

    def step(self, pop, carrying_capacity):
        """一代：摄食 -> 维持 -> 繁衍 -> 死亡 -> 承载裁剪"""
        # 摄食与维持
        for p in pop:
            p.energy_b += self.env.forage(p)
            p.energy_b -= COST_LIFE
        # 繁衍
        offspring = []
        for i, p in enumerate(pop):
            if p.energy_b >= COST_REPRO:
                c = self.replicate(p, f"{p.cid}->{i}")
                if c is not None:
                    offspring.append(c)
        pop2 = pop + offspring
        # 死亡：能量耗尽
        pop2 = [p for p in pop2 if p.energy_b > 0]
        # 环境审计排序（不看自报）
        pop2.sort(key=lambda x: self.env.evaluate(x), reverse=True)
        # 承载力裁剪 —— 超额即死
        if len(pop2) > carrying_capacity:
            self.deaths += len(pop2) - carrying_capacity
            pop2 = pop2[:carrying_capacity]
        return pop2


def diversity_stats(pop, grid=2):
    """Simpson 多样性 + 唯一基因型数"""
    if not pop:
        return 0, 0.0
    counts = {}
    for p in pop:
        counts[p.genotype(grid)] = counts.get(p.genotype(grid), 0) + 1
    n = len(pop)
    simpson = 1.0 - sum((c / n) ** 2 for c in counts.values())
    return len(counts), simpson
