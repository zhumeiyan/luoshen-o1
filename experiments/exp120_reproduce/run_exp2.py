# -*- coding: utf-8 -*-
"""
修正版指标：第一版用 round(g,2) 离散，mu=0.1 的高斯扰动让每个个体都唯一，
唯一基因型恒等于种群大小、Simpson 恒等于 1-1/N —— 指标退化成种群规模的单调函数。
本版改用 (a) 粗粒度表型箱  (b) 生态位占据度。
"""
import random
import json
from v2 import Individual, Environment, ReproductionSystemV2, _h

RES2 = {}

SINGLE = [[0.5, 0.5, 0.5]]
MULTI = [[0.1, 0.1, 0.1], [0.9, 0.1, 0.9], [0.5, 0.9, 0.5], [0.9, 0.9, 0.1]]


def pheno_bin(g, step=0.2):
    """粗粒度表型箱：每维 5 档"""
    return tuple(int(round(x / step)) for x in g)


def niche_of(ind, env):
    best, bi = -1, -1
    for i, c in enumerate(env.centers):
        d2 = sum((a - b) ** 2 for a, b in zip(ind.genome, c))
        if bi == -1 or d2 < best:
            best, bi = d2, i
    return bi


def stats(pop, env, step=0.2):
    if not pop:
        return dict(n=0, bins=0, simpson_bin=0.0, niches=0, simpson_niche=0.0,
                    spread=0.0)
    n = len(pop)
    bc = {}
    for p in pop:
        bc[pheno_bin(p.genome, step)] = bc.get(pheno_bin(p.genome, step), 0) + 1
    nc = {}
    for p in pop:
        k = niche_of(p, env)
        nc[k] = nc.get(k, 0) + 1
    simpson_bin = 1.0 - sum((c / n) ** 2 for c in bc.values())
    simpson_niche = 1.0 - sum((c / n) ** 2 for c in nc.values())
    # 表型离散度：到质心的平均距离
    cx = [sum(p.genome[i] for p in pop) / n for i in range(3)]
    spread = sum(sum((p.genome[i] - cx[i]) ** 2 for i in range(3)) ** 0.5
                 for p in pop) / n
    return dict(n=n, bins=len(bc), simpson_bin=round(simpson_bin, 4),
                niches=len(nc), simpson_niche=round(simpson_niche, 4),
                spread=round(spread, 4))


def evolve(centers, K=20, mu=0.1, gens=25, seed=7):
    rng = random.Random(seed)
    adam = Individual("ADAM", [0.5, 0.5, 0.5], [_h("genesis")], 100.0)
    env = Environment(centers, rng=rng)
    sys = ReproductionSystemV2(env, rng, mu=mu)
    pop = [adam]
    traj = []
    for g in range(gens):
        pop = sys.step(pop, carrying_capacity=K)
        if (g + 1) % 5 == 0:
            s = stats(pop, env)
            traj.append((g + 1, s["bins"], s["simpson_bin"], s["niches"], s["spread"]))
    return pop, env, traj, sys


print("=" * 62)
print("B2. 单峰世界 vs 多峰世界（粗粒度表型箱 + 生态位占据度）")
print("=" * 62)
for name, centers in [("SINGLE", SINGLE), ("MULTI", MULTI)]:
    pop, env, traj, sys = evolve(centers)
    s = stats(pop, env)
    RES2[name] = s
    print(f"{name:7s} n={s['n']:3d}  表型箱={s['bins']:3d}  Simpson_bin={s['simpson_bin']:.4f}  "
          f"占据生态位={s['niches']}  Simpson_niche={s['simpson_niche']:.4f}  离散度={s['spread']:.4f}")
    print(f"        轨迹(代,箱,simpson,位,离散度): {traj}")

print()
print("=" * 62)
print("C2. 变异率剂量扫描（多峰世界，25 代）")
print("=" * 62)
for mu in [0.0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.8]:
    pop, env, traj, _ = evolve(MULTI, mu=mu)
    s = stats(pop, env)
    RES2[f"mu_{mu}"] = s
    print(f"  mu={mu:<5} 箱={s['bins']:3d}  Simpson_bin={s['simpson_bin']:.4f}  "
          f"生态位={s['niches']}  离散度={s['spread']:.4f}")

print()
print("=" * 62)
print("D2. 承载力 K 与遗传漂变（多峰世界，25 代）")
print("=" * 62)
for K in [2, 5, 10, 20, 40]:
    pop, env, traj, _ = evolve(MULTI, K=K)
    s = stats(pop, env)
    RES2[f"K_{K}"] = s
    print(f"  K={K:<3} 箱={s['bins']:3d}  Simpson_bin={s['simpson_bin']:.4f}  "
          f"生态位={s['niches']}  离散度={s['spread']:.4f}")

print()
print("=" * 62)
print("F2. 可证伪自检")
print("=" * 62)
s_single = RES2["SINGLE"]; s_multi = RES2["MULTI"]
diff_box = s_multi["bins"] - s_single["bins"]
print(f"  世界结构主效应? 单峰箱={s_single['bins']} 多峰箱={s_multi['bins']} Δ={diff_box} "
      f"{'不饱和' if diff_box != 0 else '饱和(指标分辨不出)'}")
mu0 = RES2["mu_0.0"]; mu4 = RES2["mu_0.4"]
print(f"  变异有效?      mu=0 箱={mu0['bins']}  mu=0.4 箱={mu4['bins']} "
      f"{'不饱和' if mu0['bins'] != mu4['bins'] else '饱和'}")
print(f"  漂变有效?      K=2 箱={RES2['K_2']['bins']}  K=40 箱={RES2['K_40']['bins']} "
      f"{'不饱和' if RES2['K_2']['bins'] != RES2['K_40']['bins'] else '饱和'}")

with open("results2.json", "w") as f:
    json.dump(RES2, f, ensure_ascii=False, indent=2)
print("\n[saved] results2.json")
