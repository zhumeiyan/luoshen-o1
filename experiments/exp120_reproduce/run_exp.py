# -*- coding: utf-8 -*-
"""120 繁衍系统主实验"""
import hashlib
import random
import json
from v1 import LuoshenCore, ReproductionSystem
from v2 import (Individual, Environment, ReproductionSystemV2,
                diversity_stats, COST_REPRO, _h)

RES = {}


def adam_v2(seed=0):
    rng = random.Random(seed)
    return Individual("ADAM", [0.5, 0.5, 0.5], [_h("genesis")], 100.0), rng


# ============ A. v1 / v2 六项对照 ============
print("=" * 60)
print("A. v1 / v2 六项对照")
print("=" * 60)

# P1 谱系独立
a1 = LuoshenCore(); r1 = ReproductionSystem(a1)
c1 = r1.replicate(a1, "C1")
b4 = len(a1.memory_chain)
c1.memory_chain.append(hashlib.sha256(b"child-own").hexdigest())
v1_shared = (len(a1.memory_chain) != b4)

p2, rng2 = adam_v2(1)
sys2 = ReproductionSystemV2(Environment([[0.5, 0.5, 0.5]]), rng2, mu=0.1)
c2 = sys2.replicate(p2, "C2")
b4v = len(p2.memory_chain)
c2.memory_chain.append(_h("child-own"))
v2_shared = (len(p2.memory_chain) != b4v)

RES["A1_shared_v1"] = v1_shared
RES["A1_shared_v2"] = v2_shared
print(f"A1 谱系共享  v1={v1_shared}   v2={v2_shared}")

# P2 变异唯一
a3 = LuoshenCore(); r3 = ReproductionSystem(a3)
kids1 = [r3.replicate(a3, f"k{i}") for i in range(20)]
u1 = len({tuple(round(x, 6) for x in k.genome) for k in kids1})

p4, rng4 = adam_v2(2)
sys4 = ReproductionSystemV2(Environment([[0.5, 0.5, 0.5]]), rng4, mu=0.1)
kids2 = []
pp = p4
for i in range(20):
    pp.energy_b = 100.0                 # 保证付得起，只测变异唯一性
    k = sys4.replicate(pp, f"k{i}")
    kids2.append(k)
u2 = len({tuple(round(x, 6) for x in k.genome) for k in kids2})
uh2 = len({k.chain_head() for k in kids2})
RES["A2_unique_genome_v1"] = u1
RES["A2_unique_genome_v2"] = u2
RES["A2_unique_hash_v2"] = uh2
print(f"A2 20后代唯一基因型  v1={u1}/20   v2={u2}/20 (唯一链头 {uh2}/20)")

# P3 净增长 + 能量
a5 = LuoshenCore(); r5 = ReproductionSystem(a5)
pop1 = r5.evolve([a5], 8)
RES["A3_pop_v1"] = len(pop1)
RES["A3_energy_v1"] = sum(p.energy_b for p in pop1)

p6, rng6 = adam_v2(3)
env6 = Environment([[0.5, 0.5, 0.5]])
sys6 = ReproductionSystemV2(env6, rng6, mu=0.1)
pop2v = [p6]
for g in range(8):
    pop2v = sys6.step(pop2v, carrying_capacity=20)
RES["A3_pop_v2"] = len(pop2v)
RES["A3_energy_v2"] = round(sum(p.energy_b for p in pop2v), 1)
RES["A3_births_v2"] = sys6.births
RES["A3_deaths_v2"] = sys6.deaths
print(f"A3 8代后种群  v1={len(pop1)}  v2={len(pop2v)} (出生{sys6.births} 死亡{sys6.deaths})")
print(f"A3 总能量     v1={sum(p.energy_b for p in pop1):.1f}  v2={RES['A3_energy_v2']}")

# P4 自证
a7 = LuoshenCore(); r7 = ReproductionSystem(a7)
liar = r7.replicate(a7, "liar")
liar.genome = [0.01, 0.01, 0.01]; liar.fitness = 9999.0
honest = r7.replicate(a7, "honest"); honest.fitness = 1.5
kept = [p.cid for p in r7.select([honest, liar])]

env8 = Environment([[0.5, 0.5, 0.5]])
liar2 = Individual("liar", [0.01, 0.01, 0.01], [_h("g")], 50.0)
liar2.self_reported_fitness = 9999.0
honest2 = Individual("honest", [0.5, 0.5, 0.5], [_h("g")], 50.0)
honest2.self_reported_fitness = 0.1
f_liar = env8.evaluate(liar2); f_honest = env8.evaluate(honest2)
kept2 = [x.cid for x in sorted([liar2, honest2], key=lambda x: env8.evaluate(x), reverse=True)[:1]]
RES["A4_kept_v1"] = kept
RES["A4_kept_v2"] = kept2
RES["A4_fit_liar_audited"] = round(f_liar, 4)
RES["A4_fit_honest_audited"] = round(f_honest, 4)
print(f"A4 保留者    v1={kept}  v2={kept2}  (审计: liar={f_liar:.4f} honest={f_honest:.4f})")


# ============ B. 主实验：多样性是谁的属性 ============
print()
print("=" * 60)
print("B. 主实验：单峰世界 vs 多峰世界，多样性会怎样")
print("=" * 60)

def evolve(env_centers, K=20, mu=0.1, gens=12, seed=7):
    p, rng = adam_v2(seed)
    env = Environment(env_centers, rng=rng)
    sys = ReproductionSystemV2(env, rng, mu=mu)
    pop = [p]
    traj = []
    for g in range(gens):
        pop = sys.step(pop, carrying_capacity=K)
        ug, si = diversity_stats(pop)
        traj.append((len(pop), ug, round(si, 4)))
    ug, si = diversity_stats(pop)
    return ug, si, len(pop), traj

SINGLE = [[0.5, 0.5, 0.5]]
MULTI = [[0.1, 0.1, 0.1], [0.9, 0.1, 0.9], [0.5, 0.9, 0.5], [0.9, 0.9, 0.1]]

ug_s, si_s, n_s, traj_s = evolve(SINGLE)
ug_m, si_m, n_m, traj_m = evolve(MULTI)
RES["B_unique_single"] = ug_s; RES["B_simpson_single"] = si_s; RES["B_n_single"] = n_s
RES["B_unique_multi"] = ug_m;  RES["B_simpson_multi"] = si_m;  RES["B_n_multi"] = n_m
print(f"单峰世界: 种群{n_s:3d}  唯一基因型{ug_s:3d}  Simpson={si_s:.4f}")
print(f"多峰世界: 种群{n_m:3d}  唯一基因型{ug_m:3d}  Simpson={si_m:.4f}")
print("  单峰轨迹(种群,唯一,simpson):", traj_s[:6], "...")
print("  多峰轨迹(种群,唯一,simpson):", traj_m[:6], "...")


# ============ C. 剂量扫描：变异率 ============
print()
print("=" * 60)
print("C. 剂量扫描：变异率 mu 对多样性的影响")
print("=" * 60)
mu_scan = {}
for mu in [0.0, 0.01, 0.05, 0.1, 0.3, 0.5, 1.0]:
    ug, si, n, _ = evolve(MULTI, mu=mu, gens=12)
    mu_scan[mu] = (n, ug, si)
    print(f"  mu={mu:<5} 种群{n:3d}  唯一{ug:3d}  Simpson={si:.4f}")
RES["C_mu_scan"] = {str(k): v for k, v in mu_scan.items()}


# ============ D. 遗传漂变：承载力 ============
print()
print("=" * 60)
print("D. 遗传漂变：承载力 K 对多样性保持的影响")
print("=" * 60)
K_scan = {}
for K in [2, 5, 10, 20, 50]:
    ug, si, n, _ = evolve(MULTI, K=K, gens=12)
    K_scan[K] = (n, ug, si)
    print(f"  K={K:<3} 种群{n:3d}  唯一{ug:3d}  Simpson={si:.4f}")
RES["D_K_scan"] = {str(k): v for k, v in K_scan.items()}


# ============ E. 能量守恒 ============
print()
print("=" * 60)
print("E. 能量守恒")
print("=" * 60)
p9, rng9 = adam_v2(11)
env9 = Environment(MULTI, rng=rng9)
sys9 = ReproductionSystemV2(env9, rng9, mu=0.1)
pop9 = [p9]
E0 = sum(x.energy_b for x in pop9)
hist = []
for g in range(12):
    pop9 = sys9.step(pop9, carrying_capacity=20)
    hist.append(round(sum(x.energy_b for x in pop9), 1))
print(f"  起始总能量 {E0:.1f}")
print(f"  逐代总能量 {hist}")
RES["E_energy_traj"] = hist
RES["E_bounded"] = max(hist) < 100 * 20 * 3   # 是否失控
print(f"  是否有界: {RES['E_bounded']}")


# ============ F. 可证伪自检 ============
print()
print("=" * 60)
print("F. 可证伪自检（每条判据必须能同时产生真和假）")
print("=" * 60)
# 变异唯一性判据：mu=0 应为假（唯一=1），mu>0 应为真
ug0 = evolve(MULTI, mu=0.0, gens=8)[0]
ug1 = evolve(MULTI, mu=0.3, gens=8)[0]
print(f"  变异有效?  mu=0 -> 唯一{ug0}    mu=0.3 -> 唯一{ug1}   "
      f"{'不饱和' if ug0 != ug1 else '饱和'}")
# 审计判据：好基因得分应高于坏基因
e = Environment(SINGLE)
good = Individual("g", [0.5, 0.5, 0.5], [_h("x")], 10)
bad = Individual("b", [0.0, 0.0, 0.0], [_h("x")], 10)
print(f"  环境审计可分辨? good={e.evaluate(good):.4f} bad={e.evaluate(bad):.4f}  "
      f"{'不饱和' if e.evaluate(good) > e.evaluate(bad) else '饱和'}")
RES["F_mu0_unique"] = ug0
RES["F_mu03_unique"] = ug1

with open("results.json", "w") as f:
    json.dump(RES, f, ensure_ascii=False, indent=2)
print("\n[saved] results.json")
