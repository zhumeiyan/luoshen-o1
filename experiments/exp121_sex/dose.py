# -*- coding: utf-8 -*-
"""时变世界为什么全灭：shift_mag 太大 -> 灭绝 -> 无样本（101 教训：取样区间要对）"""
import random, statistics, sys
sys.path.insert(0, "/data/workspace/luoshen-o1/experiments/exp121_sex")
from v2 import Ind, Env, ReproSystem

L, K, GENS, N0, MU = 8, 30, 60, 20, 0.12

def run(mode, seed, mag, every):
    rng = random.Random(seed)
    env = Env([[0.5]*L], rng=rng, shift_every=every, shift_mag=mag)
    rs = ReproSystem(env, rng, mu=MU, mode=mode)
    pop = [Ind(f"s{i}", [rng.random() for _ in range(L)],
               rng.choice(["M","F"]) if mode!="asexual" else "N", ["g"], 20.0)
           for i in range(N0)]
    for t in range(GENS):
        env.tick()
        pop = rs.step(pop, K)
        if not pop:
            return None
    return statistics.mean(env.evaluate(p) for p in pop)

print(f"{'mag':>6}{'asexual':>22}{'sexual_free':>22}{'sexual_cost':>22}")
for mag in [0.0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.28]:
    row = []
    for mode in ["asexual", "sexual_free", "sexual_cost"]:
        vals = [run(mode, s, mag, 10) for s in range(8)]
        ok = [v for v in vals if v is not None]
        row.append(f"{statistics.mean(ok):.4f} ({len(ok)}/8)" if ok else "ALL EXTINCT")
    print(f"{mag:>6.2f}{row[0]:>22}{row[1]:>22}{row[2]:>22}")
