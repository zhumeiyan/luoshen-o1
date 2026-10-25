# -*- coding: utf-8 -*-
"""主实验：生殖模式 x 世界
预注册:
  H1 静态世界(单峰/多峰): sexual_cost 平均适应度 < asexual   （性的代价）
  H2 时变世界(Red Queen): sexual_free 平均适应度 > asexual   （重组的价值）
"""
import json
import random
import statistics
import sys
sys.path.insert(0, "/data/workspace/luoshen-o1/experiments/exp121_sex")
from v2 import Ind, Env, ReproSystem, diversity

L, K, GENS, N0, MU = 8, 30, 60, 20, 0.12
MODES = ["asexual", "sexual_free", "sexual_cost"]


def make_world(kind, rng):
    if kind == "single":
        return Env([[0.5] * L], rng=rng)
    if kind == "multi":
        return Env([[0.2] * L, [0.5] * L, [0.8] * L], rng=rng)
    if kind == "shifting":
        return Env([[0.5] * L], rng=rng, shift_every=8, shift_mag=0.28)
    raise ValueError(kind)


def run(kind, mode, seed):
    rng = random.Random(seed)
    env = make_world(kind, rng)
    rs = ReproSystem(env, rng, mu=MU, mode=mode)
    pop = []
    for i in range(N0):
        g = [rng.random() for _ in range(L)]
        sex = rng.choice(["M", "F"]) if mode != "asexual" else "N"
        pop.append(Ind(f"s{i}", g, sex, ["genesis"], 20.0))
    ext = False
    traj = []
    for t in range(GENS):
        env.tick()
        pop = rs.step(pop, K)
        if not pop:
            ext = True
            break
        fit = [env.evaluate(p) for p in pop]
        traj.append(statistics.mean(fit))
    if ext or not pop:
        return dict(extinct=True, mean_fit=0.0, best_fit=0.0,
                    n_uniq=0, simpson=0.0, N=0, nomate=rs.no_mate_events)
    fit = [env.evaluate(p) for p in pop]
    u, s = diversity(pop, grid=2)
    return dict(extinct=False, mean_fit=round(statistics.mean(fit), 4),
                best_fit=round(max(fit), 4), n_uniq=u, simpson=round(s, 4),
                N=len(pop), nomate=rs.no_mate_events)


SEEDS = list(range(8))
out = {}
print(f"{'world':<10}{'mode':<14}{'mean_fit':>10}{'best':>8}{'uniq':>6}{'simpson':>9}{'N':>5}{'ext':>6}{'nomate':>7}")
for kind in ["single", "multi", "shifting"]:
    for mode in MODES:
        rs_ = [run(kind, mode, s) for s in SEEDS]
        ok = [r for r in rs_ if not r["extinct"]]
        n_ext = sum(1 for r in rs_ if r["extinct"])
        if ok:
            agg = dict(
                mean_fit=round(statistics.mean(r["mean_fit"] for r in ok), 4),
                best_fit=round(statistics.mean(r["best_fit"] for r in ok), 4),
                n_uniq=round(statistics.mean(r["n_uniq"] for r in ok), 2),
                simpson=round(statistics.mean(r["simpson"] for r in ok), 4),
                N=round(statistics.mean(r["N"] for r in ok), 2),
                nomate=round(statistics.mean(r["nomate"] for r in ok), 2),
            )
        else:
            agg = dict(mean_fit=0.0, best_fit=0.0, n_uniq=0, simpson=0.0, N=0.0, nomate=-1)
        out[f"{kind}|{mode}"] = dict(agg=agg, n_extinct=n_ext, n_seed=len(SEEDS), raw=rs_)
        print(f"{kind:<10}{mode:<14}{agg['mean_fit']:>10.4f}{agg['best_fit']:>8.4f}"
              f"{agg['n_uniq']:>6}{agg['simpson']:>9.2f}{agg['N']:>5.1f}{n_ext:>6}{agg['nomate']:>7.1f}")

json.dump(out, open("main_results.json", "w"), indent=1, ensure_ascii=False)

print()
print("=== 预注册检验 ===")
for kind in ["single", "multi"]:
    a = out[f"{kind}|asexual"]["agg"]["mean_fit"]
    c = out[f"{kind}|sexual_cost"]["agg"]["mean_fit"]
    print(f"H1 {kind:<8} asexual {a:.4f} vs sexual_cost {c:.4f}  -> "
          f"{'PASS' if c < a else 'FAIL'} (代价方向 {'存在' if c < a else '不存在'})")
a = out["shifting|asexual"]["agg"]["mean_fit"]
f = out["shifting|sexual_free"]["agg"]["mean_fit"]
print(f"H2 shifting  asexual {a:.4f} vs sexual_free {f:.4f} -> {'PASS' if f > a else 'FAIL'}")
for m in MODES:
    print(f"   净效应 {m:<13} 相对 asexual = "
          f"{out['shifting|'+m]['agg']['mean_fit'] - a:+.4f}")
