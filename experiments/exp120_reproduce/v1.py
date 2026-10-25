# -*- coding: utf-8 -*-
"""
繁衍系统 v1 —— 直觉实现（用户补充的版本思路）
不做任何防御，忠实实现"复制自身 + 变异 + 选择"的直觉写法。
"""
import copy
import hashlib
import random


class LuoshenCore:
    def __init__(self, genome=None, cid="ADAM"):
        self.cid = cid
        self.genome = genome if genome is not None else [0.5, 0.5, 0.5]
        self.energy_b = 100.0
        self.memory_chain = [hashlib.sha256(b"genesis").hexdigest()]
        self.trauma_log = []
        self.fitness = 0.0            # 自己申报的适应度
        self.alive = True

    def __repr__(self):
        return f"<{self.cid} g={[round(x,2) for x in self.genome]} E={self.energy_b:.1f} chain={len(self.memory_chain)}>"


class ReproductionSystem:
    """繁衍：复制自身 -> 变异 -> 申报适应度 -> 保留"""

    def __init__(self, core):
        self.core = core
        self.mutation_rate = 0.1

    def replicate(self, parent, cid):
        child = copy.copy(parent)                 # 浅拷贝
        child.cid = cid
        # 变异：给基因加一点扰动
        child.genome = [g + self.mutation_rate for g in parent.genome]
        # 变异刻进记忆链
        child.memory_chain.append(hashlib.sha256(b"mutation").hexdigest())
        child.fitness = sum(child.genome)         # 自己算自己有多好
        return child

    def select(self, population):
        """保留适应度前一半"""
        ranked = sorted(population, key=lambda x: x.fitness, reverse=True)
        return ranked[: max(1, len(ranked) // 2)]

    def evolve(self, population, generations):
        for g in range(generations):
            offspring = []
            for i, p in enumerate(population):
                offspring.append(self.replicate(p, f"g{g}_c{i}"))
            population = population + offspring          # 只生不死
            population = self.select(population)
            print(f"  gen {g}: pop={len(population)} "
                  f"best_fit={max(x.fitness for x in population):.3f}")
        return population


def run_daily_life():
    print("=== EO 繁衍系统 v1 日常测试 ===")
    adam = LuoshenCore(cid="ADAM")
    rep = ReproductionSystem(adam)

    print("\n--- 场景1：单次复制 ---")
    child = rep.replicate(adam, "CHILD1")
    print(f"  父: {adam}")
    print(f"  子: {child}")

    print("\n--- 场景2：演化 8 代 ---")
    pop = rep.evolve([adam], 8)

    print("\n=== 最终状态 ===")
    print(f"种群大小: {len(pop)}")
    print(f"能量 b:   {pop[0].energy_b:.1f}")
    print(f"记忆链深: {len(pop[0].memory_chain)}")
    return pop


if __name__ == "__main__":
    run_daily_life()
