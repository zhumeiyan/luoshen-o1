# -*- coding: utf-8 -*-
"""统一竞争模型：连续生态位基因 + 离散有害位点集合 + 真实 two-fold cost
asexual 与 sexual 在同一个池子里抢同一个承载力 K，看长期谁占优。
坏位点洗除机制：重组后子代 bad = 双亲 bad 的交集 + 各自独有部分的一半（期望）
"""
import json, random, statistics

L_ECO = 8          # 生态位基因位点（连续）
L_BAD = 24         # 有害位点（离散集合）
MU_D, MU_B, S = 0.02, 0.001, 0.05
MU_ECO = 0.12
K, GENS, N0 = 60, 250, 40


class P:
    __slots__ = ("eco", "bad", "sex", "mode", "energy")
    def __init__(self, eco, bad, sex, mode, energy=20.0):
        self.eco = list(eco); self.bad = set(bad); self.sex = sex
        self.mode = mode; self.energy = energy
    @property
    def load(self): return len(self.bad)


def eco_fit(p, centers, sigma=0.35):
    b = 0.0
    for c in centers:
        d2 = sum((x - y) ** 2 for x, y in zip(p.eco, c))
        b = max(b, pow(2.718281828459045, -d2 / (2 * sigma ** 2)))
    return b


def total_fit(p, centers):
    return eco_fit(p, centers) * ((1.0 - S) ** p.load)


def mutate_eco(g, rng):
    out = []
    for x in g:
        if rng.random() < 0.35:
            x += rng.gauss(0, MU_ECO)
        out.append(min(1.0, max(0.0, x)))
    return out


def mutate_bad(bad, rng):
    out = set(bad)
    for i in range(L_BAD):
        if i in out:
            if rng.random() < MU_B:
                out.discard(i)
        else:
            if rng.random() < MU_D:
                out.add(i)
    return out


def recombine_bad(b1, b2, rng):
    """重组：双亲共有的坏位点必留；单亲独有的以 1/2 概率留 -> 期望小于任一亲本"""
    inter = b1 & b2
    only1 = b1 - b2
    only2 = b2 - b1
    out = set(inter)
    out |= {i for i in only1 if rng.random() < 0.5}
    out |= {i for i in only2 if rng.random() < 0.5}
    return out


def run(kind, seed):
    rng = random.Random(seed)
    if kind == "static":
        centers = [[0.5] * L_ECO]; shift_every, shift_mag = 0, 0.0
    else:
        centers = [[0.5] * L_ECO]; shift_every, shift_mag = 12, 0.05
    t = 0
    pop = []
    for i in range(N0):
        mode = "asexual" if i % 2 == 0 else "sexual"
        sex = "N" if mode == "asexual" else ("M" if i % 4 == 1 else "F")
        pop.append(P([rng.random() for _ in range(L_ECO)], set(), sex, mode))
    traj = []
    for g in range(GENS):
        t += 1
        if shift_every and t % shift_every == 0:
            centers = [[min(1.0, max(0.0, x + rng.gauss(0, shift_mag))) for x in c] for c in centers]
        for p in pop:
            p.energy += 6.0 * total_fit(p, centers) * (0.7 + 0.6 * rng.random()) - 1.0
        off = []
        # 无性：每个个体独立产 1 仔
        for p in [q for q in pop if q.mode == "asexual"]:
            if p.energy >= 8.0:
                p.energy -= 8.0
                off.append(P(mutate_eco(p.eco, rng), mutate_bad(p.bad, rng), "N", "asexual", 4.0))
        # 有性：只有 F 产仔（two-fold cost），需异性配对
        males = [q for q in pop if q.mode == "sexual" and q.sex == "M"]
        females = [q for q in pop if q.mode == "sexual" and q.sex == "F"]
        rng.shuffle(males); rng.shuffle(females)
        for m, f in zip(males, females):
            if f.energy < 8.0:
                continue
            f.energy -= 8.0
            eco = [a if rng.random() < 0.5 else b for a, b in zip(m.eco, f.eco)]
            sex = rng.choice(["M", "F"])
            off.append(P(mutate_eco(eco, rng), mutate_bad(recombine_bad(m.bad, f.bad, rng), rng),
                          sex, "sexual", 4.0))
        pop = [q for q in pop if q.energy > 0] + off
        pop.sort(key=lambda q: total_fit(q, centers), reverse=True)
        pop = pop[:K]
        if not pop:
            break
        na = sum(1 for q in pop if q.mode == "asexual")
        traj.append(round(na / len(pop), 4))
    if not pop:
        return dict(extinct=True, final_asex_frac=None, traj=traj)
    na = sum(1 for q in pop if q.mode == "asexual")
    return dict(extinct=False, final_asex_frac=round(na / len(pop), 4), N=len(pop),
                mean_load_asex=round(statistics.mean([q.load for q in pop if q.mode == "asexual"]), 2)
                if na else None,
                mean_load_sex=round(statistics.mean([q.load for q in pop if q.mode == "sexual"]), 2)
                if len(pop) - na else None,
                traj=traj)


SEEDS = list(range(10))
out = {}
print(f"{'world':<10}{'final_asex_frac':>18}{'load_asex':>11}{'load_sex':>10}{'extinct':>9}")
for kind in ["static", "shifting"]:
    rs = [run(kind, s) for s in SEEDS]
    ok = [r for r in rs if not r["extinct"]]
    n_ext = len(rs) - len(ok)
    if ok:
        fa = statistics.mean(r["final_asex_frac"] for r in ok)
        la = statistics.mean(r["mean_load_asex"] for r in ok if r["mean_load_asex"] is not None)
        ls = statistics.mean(r["mean_load_sex"] for r in ok if r["mean_load_sex"] is not None)
    else:
        fa, la, ls = None, None, None
    out[kind] = dict(final_asex_frac=fa, load_asex=la, load_sex=ls, n_extinct=n_ext,
                     traj=[r["traj"] for r in rs])
    print(f"{kind:<10}{(f'{fa:.4f}' if fa is not None else 'NA'):>18}"
          f"{(f'{la:.2f}' if la is not None else 'NA'):>11}"
          f"{(f'{ls:.2f}' if ls is not None else 'NA'):>10}{n_ext:>9}")

json.dump(out, open("compete_results.json", "w"), indent=1)

print()
print("=== 无性占比轨迹（10 seed 平均，每 25 代采样）===")
for kind in ["static", "shifting"]:
    trs = [t for t in out[kind]["traj"] if t]
    m = min(len(t) for t in trs) if trs else 0
    line = [round(statistics.mean(t[i] for t in trs), 3) for i in range(0, m, 25)]
    print(f"  {kind:<9} {line}")
print("  (1.0=无性独占 0.0=有性独占)")
