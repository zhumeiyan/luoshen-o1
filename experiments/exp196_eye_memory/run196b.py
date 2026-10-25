#!/usr/bin/env python3
# 196b: 坍缩扫描 —— 记忆增益到底由什么决定？
# 假设：增益只依赖 r/tau（采样间隔 / 世界相关时间），与 tau、r 各自无关
import numpy as np, json, os
from collections import defaultdict

OUT = "/data/workspace/luoshen-o1/experiments/exp196_eye_memory"
rng_master = 196


def quantize(x, V=10):
    qs = np.quantile(x, np.linspace(0, 1, V + 1)[1:-1])
    return np.digitize(x, qs)


def make_ou(n, tau, rng, sigma=1.0):
    a = np.exp(-1.0 / tau)
    x = np.zeros(n)
    s = sigma * np.sqrt(1 - a * a)
    noise = rng.standard_normal(n)
    for i in range(1, n):
        x[i] = a * x[i - 1] + s * noise[i]
    return x


def eval_k(seq, k, ntest=4000):
    n = len(seq)
    split = int(n * 0.8)
    tr, te = seq[:split], seq[split:split + ntest]
    if len(te) <= k + 1:
        return None
    counts = defaultdict(lambda: defaultdict(float))
    ctx = defaultdict(float)
    marg = defaultdict(float)
    tot = 0.0
    for i in range(k, len(tr)):
        c = tuple(tr[i - k:i])
        counts[c][tr[i]] += 1
        ctx[c] += 1
        marg[tr[i]] += 1
        tot += 1
    base = max(marg.values()) / tot if tot > 0 else 0.0
    top_m = max(marg.items(), key=lambda kv: kv[1])[0] if marg else 0
    corr = 0.0
    n2 = 0
    for i in range(k, len(te)):
        c = tuple(te[i - k:i])
        pred = max(counts[c].items(), key=lambda kv: kv[1])[0] if ctx[c] > 0 else top_m
        corr += (pred == te[i])
        n2 += 1
    return corr / n2, base


def best_gain(seq, kmax=6, ntest=4000):
    best = -9
    bk = None
    for k in range(1, kmax + 1):
        r = eval_k(seq, k, ntest)
        if r is None:
            continue
        acc, base = r
        if acc - base > best:
            best = acc - base
            bk = k
    return best, bk


# ---- 坍缩扫描：固定总时长 N，改变采样率 r ----
N = 40000
xs = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
taus = [5, 10, 20, 40, 80]
seeds = [1, 2, 3]

collapse = {}
for x in xs:
    collapse[str(x)] = {}
    for tau in taus:
        r = max(1, int(round(x * tau)))
        gains = []
        ks = []
        for sd in seeds:
            rng = np.random.default_rng(rng_master + sd)
            full = make_ou(N, tau, rng)
            q = quantize(full[::r])
            g, k = best_gain(q)
            gains.append(g)
            ks.append(k)
        collapse[str(x)][str(tau)] = {
            "r": r, "r_over_tau": r / tau,
            "gain_mean": float(np.mean(gains)),
            "gain_std": float(np.std(gains)),
            "kstar": [int(t) for t in ks],
            "n_samples": int(N / r),
        }

# 坍缩质量：组间方差 / 组内方差
rows = []
for x in xs:
    for tau in taus:
        d = collapse[str(x)][str(tau)]
        rows.append((x, tau, d["gain_mean"], d["gain_std"]))

group_means = {}
for x in xs:
    vals = [v for (xx, tt, v, s) in rows if xx == x]
    group_means[x] = np.mean(vals)
within = np.mean([s for (xx, tt, v, s) in rows]) ** 2
between = np.var([group_means[x] for x in xs])
# 每个 tau 内部的离散度（同 x 下不同 tau 的差）
spread = {str(x): float(np.std([v for (xx, tt, v, s) in rows if xx == x])) for x in xs}
level = float(np.std([group_means[x] for x in xs]))

summary = {
    "collapse_grid": collapse,
    "group_mean_by_x": {str(k): float(v) for k, v in group_means.items()},
    "spread_within_x": spread,
    "spread_across_x": level,
    "collapse_ratio": float(np.mean(list(spread.values())) / level) if level > 0 else None,
    "seed_std_mean": float(np.mean([s for (xx, tt, v, s) in rows])),
}
json.dump(summary, open(OUT + "/collapse196.json", "w"), ensure_ascii=False, indent=1)

print("=== 坍缩扫描：gain 只依赖 r/tau ? ===")
print(f"{'r/tau':>6} | " + " | ".join(f"tau={t:<3}" for t in taus) + " | 组内std | 组均值")
for x in xs:
    line = f"{x:>6} | "
    for tau in taus:
        line += f"{collapse[str(x)][str(tau)]['gain_mean']:.4f} | "
    line += f" {spread[str(x)]:.4f} | {group_means[x]:.4f}"
    print(line)
print()
print(f"组内(同 r/tau, 不同 tau)平均离散 = {np.mean(list(spread.values())):.5f}")
print(f"组间(不同 r/tau)离散           = {level:.5f}")
print(f"坍缩比 = 组内/组间 = {summary['collapse_ratio']:.4f}   (越小越坍缩)")
print(f"种子间 std 均值 = {summary['seed_std_mean']:.5f}")
