# -*- coding: utf-8 -*-
"""Muller's ratchet：无性种群不可逆地积累有害突变；有性能通过重组逆转
离散位点模型：位点 0=好 1=坏(有害)
负载 load = 坏位点个数；best_load = 种群中最干净个体的负载
棘轮咔哒 = best_load 上升且再也回不去
预注册 H3: 无性棘轮咔哒次数 > 有性；无性 best_load 单调不降
"""
import json, random, statistics, sys

L = 20            # 位点数
MU_D = 0.02       # 好->坏
MU_B = 0.001      # 坏->好（回突变，罕见）
S = 0.05          # 每个坏位点的选择系数
N = 100           # 种群大小
GENS = 200


def fitness(load):
    return (1.0 - S) ** load


class P:
    __slots__ = ("g", "sex")
    def __init__(self, g, sex):
        self.g = list(g)
        self.sex = sex
    @property
    def load(self):
        return sum(self.g)


def mutate_bits(g, rng):
    return [0 if (b == 1 and rng.random() < MU_B) else (1 if (b == 0 and rng.random() < MU_D) else b)
            for b in g]


def run(mode, seed):
    rng = random.Random(seed)
    pop = [P([0] * L, rng.choice(["M", "F"]) if mode != "asexual" else "N") for _ in range(N)]

    best_traj, mean_traj = [], []
    clicks = 0
    prev_best = 0
    ever_reversed = 0        # best_load 下降的次数

    for t in range(GENS):
        w = [fitness(p.load) for p in pop]
        tot = sum(w)
        if tot <= 0:
            break
        # 按适应度加权抽亲本
        def pick():
            r = rng.random() * tot
            acc = 0.0
            for i, x in enumerate(w):
                acc += x
                if r <= acc:
                    return pop[i]
            return pop[-1]

        newpop = []
        if mode == "asexual":
            while len(newpop) < N:
                par = pick()
                newpop.append(P(mutate_bits(par.g, rng), "N"))
        else:
            while len(newpop) < N:
                p1 = pick()
                p2 = pick()
                if mode == "sexual_cost":
                    # 需要异性别配对才成功；同性配对失败 -> 重试（有限次）
                    tries = 0
                    while p1.sex == p2.sex and tries < 20:
                        p2 = pick(); tries += 1
                    if p1.sex == p2.sex:
                        continue
                g = [a if rng.random() < 0.5 else b for a, b in zip(p1.g, p2.g)]
                newpop.append(P(mutate_bits(g, rng), rng.choice(["M", "F"])))
        pop = newpop

        bl = min(p.load for p in pop)
        ml = statistics.mean(p.load for p in pop)
        best_traj.append(bl)
        mean_traj.append(ml)
        if bl > prev_best:
            clicks += 1
        if bl < prev_best:
            ever_reversed += 1
        prev_best = bl

    return dict(final_best_load=best_traj[-1], final_mean_load=round(mean_traj[-1], 3),
                clicks=clicks, reversals=ever_reversed,
                best_traj=best_traj, mean_traj=[round(x, 3) for x in mean_traj],
                final_fit=round(fitness(best_traj[-1]), 4))


SEEDS = list(range(10))
res = {}
print(f"{'mode':<14}{'final_best_load':>17}{'mean_load':>11}{'clicks':>8}{'reversals':>11}{'fit':>8}")
for mode in ["asexual", "sexual_free", "sexual_cost"]:
    rs = [run(mode, s) for s in SEEDS]
    agg = {k: round(statistics.mean(r[k] for r in rs), 3)
           for k in ["final_best_load", "final_mean_load", "clicks", "reversals", "final_fit"]}
    res[mode] = dict(agg=agg, raw=[{k: r[k] for k in
                    ["final_best_load","final_mean_load","clicks","reversals","final_fit"]} for r in rs])
    print(f"{mode:<14}{agg['final_best_load']:>17}{agg['final_mean_load']:>11}"
          f"{agg['clicks']:>8}{agg['reversals']:>11}{agg['final_fit']:>8}")

json.dump(res, open("ratchet_results.json", "w"), indent=1)

print()
print("=== 单种子 best_load 轨迹（看棘轮是不是真的咔哒） ===")
for mode in ["asexual", "sexual_free"]:
    r = run(mode, 3)
    t = r["best_traj"]
    print(f"{mode:<13} best_load: t0={t[0]} t25={t[25]} t50={t[50]} t100={t[100]} t199={t[199]}")
    print(f"{'':<13} mean_load: t0={r['mean_traj'][0]} t50={r['mean_traj'][50]} t199={r['mean_traj'][199]}")

print()
print("=== H3 检验 ===")
a, sf = res["asexual"]["agg"], res["sexual_free"]["agg"]
print(f"  无性 clicks {a['clicks']}  vs 有性(无代价) clicks {sf['clicks']}  -> "
      f"{'PASS' if a['clicks'] > sf['clicks'] else 'FAIL'}")
print(f"  无性 reversals {a['reversals']} vs 有性 reversals {sf['reversals']}")
print(f"  终态 best_load   无性 {a['final_best_load']} vs 有性 {sf['final_best_load']}")
