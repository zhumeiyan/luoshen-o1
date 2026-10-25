#!/usr/bin/env python3
# 196: 眼睛、采样率与记忆深度 —— 鱼为什么"记忆少"
import numpy as np, json, os
from collections import defaultdict

OUT = "/data/workspace/luoshen-o1/experiments/exp196_eye_memory"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)
N = 40000


def quantize(x, V=10):
    qs = np.quantile(x, np.linspace(0, 1, V + 1)[1:-1])
    return np.digitize(x, qs)


def make_ar(n, coefs, sigma=1.0):
    m = len(coefs)
    x = np.zeros(n)
    for i in range(m, n):
        x[i] = sum(c * x[i - j - 1] for j, c in enumerate(coefs)) + sigma * rng.standard_normal()
    return x[m:]


def make_ou(n, tau, sigma=1.0):
    a = np.exp(-1.0 / tau)
    return make_ar(n, [a], sigma * np.sqrt(1 - a * a))


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


def scan_k(seq, kmax=6, ntest=4000):
    res = []
    for k in range(1, kmax + 1):
        r = eval_k(seq, k, ntest)
        if r is None:
            continue
        acc, base = r
        res.append({"k": k, "acc": acc, "base": base, "gain": acc - base})
    if not res:
        return None, []
    best = max(res, key=lambda d: d["gain"])
    return best["k"], res


results = {}

# ---------- A: 动力学阶数 vs 最优记忆深度 ----------
partA = {}
specs = {"AR1(梯度)": [0.8], "AR2(带惯性)": [0.6, 0.25],
         "AR3": [0.5, 0.25, 0.15], "AR4": [0.4, 0.2, 0.15, 0.1]}
for name, co in specs.items():
    x = make_ar(N, co)
    q = quantize(x)
    ks, res = scan_k(q)
    partA[name] = {"coefs": co, "kstar": ks, "curve": res}
results["A_order"] = partA

# ---------- B: 采样率 vs 记忆（世界相关时间 tau） ----------
partB = {}
for tau in [2, 5, 10, 20, 50]:
    x = make_ou(N, tau)
    row = {}
    for r in [1, 2, 4, 8, 16]:
        xs = x[::r]
        q = quantize(xs)
        ks, res = scan_k(q)
        best = max(res, key=lambda d: d["gain"])
        # 理论保持率: a^r = exp(-r/tau)
        row[str(r)] = {"kstar": ks, "gain": best["gain"], "acc": best["acc"],
                       "span_phys": (ks * r if ks else None),
                       "theory_retain": float(np.exp(-r / tau)), "n": len(q)}
    partB[str(tau)] = row
results["B_sampling"] = partB

# ---------- C: 两类agent ----------
# C1 化学趋向(无眼): 沿路径的平滑浓度场
pos = np.cumsum(rng.standard_normal(N)) * 1.0
field = np.sin(pos * 0.05) + 0.5 * np.sin(pos * 0.013)
q = quantize(field)
k1, res1 = scan_k(q)
# C2 追捕(有眼): 猎物带惯性 AR2 振荡
prey = make_ar(N, [1.5, -0.6], 0.3)
q2 = quantize(prey)
k2, res2 = scan_k(q2)
# C3 追捕: 猎物近似匀速(位置=速度积分) -> 需两个采样才能得速度
vel = make_ou(N, 20, 0.5)
p = np.cumsum(vel)
q3 = quantize(p)
k3, res3 = scan_k(q3)
results["C_agent"] = {
    "C1_化学趋向_平滑场": {"kstar": k1, "curve": res1},
    "C2_追捕_猎物带惯性": {"kstar": k2, "curve": res2},
    "C3_追捕_猎物匀速": {"kstar": k3, "curve": res3},
}

json.dump(results, open(OUT + "/result196.json", "w"), ensure_ascii=False, indent=1)

# 打印摘要
print("=== A 动力学阶数 -> k* ===")
for k, v in partA.items():
    print(f"  {k:14s} k*={v['kstar']}  gain={max(d['gain'] for d in v['curve']):.4f}")
print("=== B 采样率 vs 记忆 (tau) ===")
for tau, row in partB.items():
    s = "  tau=%3s : " % tau
    for r, d in row.items():
        s += f"r{r}:k*={d['kstar']},g={d['gain']:.4f},ret={d['theory_retain']:.3f}  "
    print(s)
print("=== C agent ===")
for k, v in results["C_agent"].items():
    print(f"  {k:20s} k*={v['kstar']}")
print("saved")
