# -*- coding: utf-8 -*-
"""
繁衍 v2（含性别）—— 修正 v1 的失效
v1 失效:
  F1 重组取平均 -> 20 后代唯一基因型 1（重组在消灭多样性，与生物学相反）
  F2 pop = offspring 完全替换亲本 -> 种群立刻灭绝
  F3 无性别比例稳定机制、无能量、无死亡、无承载力
v2 修正:
  uniform crossover（每位点随机取自双亲之一）
  亲本存活，死亡率、承载力、能量全部显式
"""
import hashlib
import random

COST_REPRO = 8.0
COST_LIFE = 1.0
GAIN_MAX = 6.0


def _h(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()


class Ind:
    def __init__(self, cid, genome, sex, chain, energy, parent_ids=None):
        self.cid = cid
        self.genome = list(genome)          # 显式新列表，不共享引用
        self.sex = sex
        self.memory_chain = list(chain)
        self.energy_b = energy
        self.parent_ids = parent_ids or []
        self.self_reported_fitness = None   # 不采信

    def genotype(self, grid=2):
        return tuple(round(x, grid) for x in self.genome)

    def chain_head(self):
        return self.memory_chain[-1]


class Env:
    """独立审计器：适应度由环境算，个体说了不算"""
    def __init__(self, centers, sigma=0.35, rng=None, shift_every=0, shift_mag=0.0):
        self.centers0 = [list(c) for c in centers]
        self.centers = [list(c) for c in centers]
        self.sigma = sigma
        self.rng = rng or random.Random(0)
        self.shift_every = shift_every      # >0 表示时变世界（Red Queen）
        self.shift_mag = shift_mag
        self.t = 0

    def tick(self):
        self.t += 1
        if self.shift_every and self.t % self.shift_every == 0:
            # 峰跳到新位置
            self.centers = [
                [min(1.0, max(0.0, x + self.rng.gauss(0, self.shift_mag))) for x in c]
                for c in self.centers
            ]

    def evaluate(self, ind):
        best = 0.0
        for c in self.centers:
            d2 = sum((a - b) ** 2 for a, b in zip(ind.genome, c))
            best = max(best, pow(2.718281828459045, -d2 / (2 * self.sigma ** 2)))
        return best

    def forage(self, ind):
        return GAIN_MAX * self.evaluate(ind) * (0.7 + 0.6 * self.rng.random())


def crossover(p1, p2, rng):
    """uniform crossover：每个位点随机取自双亲之一 —— 不平均，保住分离"""
    return [a if rng.random() < 0.5 else b for a, b in zip(p1.genome, p2.genome)]


def mutate(g, mu, rng, p_site=0.35):
    out = []
    for x in g:
        if rng.random() < p_site:
            x = x + rng.gauss(0, mu)
        out.append(min(1.0, max(0.0, x)))
    return out


class ReproSystem:
    """mode: asexual | sexual_cost | sexual_free"""
    def __init__(self, env, rng, mu=0.12, mode="asexual", sex_at_birth="random"):
        self.env = env
        self.rng = rng
        self.mu = mu
        self.mode = mode
        self.sex_at_birth = sex_at_birth
        self.births = 0
        self.deaths = 0
        self.no_mate_events = 0
        self._cid = 0

    def _new_cid(self):
        self._cid += 1
        return f"i{self._cid}"

    def _make_child(self, genome, parents, energy):
        cid = self._new_cid()
        # 子代性别
        if self.sex_at_birth == "random":
            sex = self.rng.choice(["M", "F"])
        else:
            sex = parents[0].sex if parents else "F"
        head = _h(parents[0].chain_head() if parents else "root",
                  [round(x, 8) for x in genome],
                  cid, self.rng.random())
        chain = (parents[0].memory_chain + [head]) if parents else [head]
        self.births += 1
        return Ind(cid, genome, sex, chain, energy,
                   parent_ids=[p.cid for p in parents])

    def step(self, pop, K):
        # 摄食 + 维持
        for p in pop:
            p.energy_b += self.env.forage(p)
            p.energy_b -= COST_LIFE

        offspring = []
        if self.mode == "asexual":
            for p in pop:
                if p.energy_b >= COST_REPRO:
                    p.energy_b -= COST_REPRO
                    g = mutate(p.genome, self.mu, self.rng)
                    offspring.append(self._make_child(g, [p], COST_REPRO * 0.5))
        else:
            males = [p for p in pop if p.sex == "M"]
            females = [p for p in pop if p.sex == "F"]
            if not males or not females:
                self.no_mate_events += 1
            self.rng.shuffle(males)
            self.rng.shuffle(females)
            for m, f in zip(males, females):
                # 性的代价: 只有 F 产仔；sexual_free 下双方各产一个
                breeders = [f] if self.mode == "sexual_cost" else [f, m]
                for parent in breeders:
                    other = m if parent is f else f
                    if parent.energy_b < COST_REPRO:
                        continue
                    parent.energy_b -= COST_REPRO
                    g = mutate(crossover(parent, other, self.rng), self.mu, self.rng)
                    offspring.append(self._make_child(g, [parent, other], COST_REPRO * 0.5))

        pop2 = [p for p in pop if p.energy_b > 0]      # 亲本存活
        pop2 += offspring
        pop2 = [p for p in pop2 if p.energy_b > 0]
        pop2.sort(key=lambda x: self.env.evaluate(x), reverse=True)
        if len(pop2) > K:
            self.deaths += len(pop2) - K
            pop2 = pop2[:K]
        return pop2


def diversity(pop, grid=2):
    if not pop:
        return 0, 0.0
    cnt = {}
    for p in pop:
        cnt[p.genotype(grid)] = cnt.get(p.genotype(grid), 0) + 1
    n = len(pop)
    return len(cnt), 1.0 - sum((c / n) ** 2 for c in cnt.values())
