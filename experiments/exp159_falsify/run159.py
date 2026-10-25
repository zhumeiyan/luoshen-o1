#!/usr/bin/env python3
# exp159 — 三条规律的可证伪性检验
# 对方判词：三条都是"把定义当发现、把误用当规律"，不可证伪。
# 本轮不辩，直接构造能翻掉它们的实验。
#
# T1 存在全域占优策略吗？   —— 若有，"没有更好策略"被证伪
# T2 周期世界里给正确世界模型，时间顺序是否由负债转资产？ —— 若是，判词成立
# T3 无结构地形上，好奇心在大预算下是否反超？ —— 若是，"好奇有害"是预算假象

import numpy as np, json, os, itertools

OUT = "/data/workspace/luoshen-o1/experiments/exp159_falsify"
os.makedirs(OUT, exist_ok=True)
R = {}

# ================= 世界生成器 =================
def gen_world(kind, T, rng):
    t = np.arange(T)
    if kind == "monotone":
        return 0.02 * t + rng.normal(0, 0.3, T)
    if kind == "stationary":
        return rng.normal(0, 1.0, T)
    if kind == "sine":
        return 3 * np.sin(2 * np.pi * t / 40) + rng.normal(0, 0.2, T)
    if kind == "square":
        return 3 * np.sign(np.sin(2 * np.pi * t / 40)) + rng.normal(0, 0.2, T)
    if kind == "burst":
        x = rng.normal(0, 0.3, T)
        for s in range(0, T, 50):
            x[s:s + 10] += rng.normal(3, 0.5)
        return x
    if kind == "rw":
        return np.cumsum(rng.normal(0, 0.3, T))
    if kind == "chaotic":
        x = np.zeros(T); x[0] = 0.4
        for i in range(1, T):
            x[i] = 3.9 * x[i - 1] * (1 - x[i - 1])
        return x + rng.normal(0, 0.05, T)
    raise ValueError(kind)

WORLDS = ["monotone", "stationary", "sine", "square", "burst", "rw", "chaotic"]

# ================= 策略（全部在线、因果，只用过去） =================
def strat_const_zero(h):  return 0.0
def strat_last(h):        return h[-1] if len(h) else 0.0
def strat_mean_all(h):    return float(np.mean(h)) if len(h) else 0.0
def strat_mean_recent(h, k=8):
    return float(np.mean(h[-k:])) if len(h) else 0.0
def strat_trend(h, k=8):
    # 线性外推：用最近 k 点的顺序信息
    if len(h) < 3: return float(h[-1]) if len(h) else 0.0
    y = np.asarray(h[-k:]); x = np.arange(len(y))
    A = np.vstack([x, np.ones(len(x))]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(a * len(y) + b)
def strat_sgd(h, k=8, eta=0.05):
    # 在线 SGD，顺序敏感（逐点更新）
    w, b = 0.0, 0.0
    for i in range(1, len(h)):
        p = w * h[i - 1] + b
        e = h[i] - p
        w += eta * e * h[i - 1]
        b += eta * e
    return float(w * h[-1] + b) if len(h) else 0.0
def strat_phase(h, P=40, recency=None):
    # 相位条件均值：需要"世界模型"（知道周期 P）
    if len(h) < 2: return float(h[-1]) if len(h) else 0.0
    idx = np.arange(len(h))
    ph = (idx % P)
    cur = (len(h)) % P
    m = (ph == cur)
    if recency is not None:
        m = m & (idx >= len(h) - recency * P)
    return float(np.mean(np.asarray(h)[m])) if m.any() else float(np.mean(h))

STRATS = {
    "const_zero": strat_const_zero,
    "last":       strat_last,
    "mean_all":   strat_mean_all,
    "mean_recent8": strat_mean_recent,
    "trend":      strat_trend,
    "sgd":        strat_sgd,
    "phase_uniform": lambda h: strat_phase(h, recency=None),
    "phase_recent2": lambda h: strat_phase(h, recency=2),
}

# ================= T1：全域占优检验 =================
def run_t1(T=600, nseeds=8):
    res = {w: {s: [] for s in STRATS} for w in WORLDS}
    for seed in range(nseeds):
        rng = np.random.default_rng(1000 + seed)
        for w in WORLDS:
            x = gen_world(w, T, rng)
            burn = int(T * 0.4)
            for name, f in STRATS.items():
                errs = []
                for i in range(burn, T):
                    h = x[:i]
                    p = f(h)
                    if not np.isfinite(p): p = 0.0
                    errs.append(abs(x[i] - p))
                res[w][name].append(float(np.mean(errs)))
    out = {w: {s: {"mean": float(np.mean(v)),
                   "lo": float(np.percentile(v, 2.5)),
                   "hi": float(np.percentile(v, 97.5))}
               for s, v in d.items()} for w, d in res.items()}
    # 占优判定
    best_per_world = {}
    for w in WORLDS:
        m = min(out[w][s]["mean"] for s in STRATS)
        best_per_world[w] = sorted([s for s in STRATS
                                    if out[w][s]["mean"] <= m * 1.02])
    # 有没有一个策略在所有世界里都进 best
    ever_best = {s: sum(1 for w in WORLDS if s in best_per_world[w]) for s in STRATS}
    dominator = [s for s in STRATS if ever_best[s] == len(WORLDS)]
    # NFL 检验：跨世界平均后，策略间差异大小
    avg = {s: float(np.mean([out[w][s]["mean"] for w in WORLDS])) for s in STRATS}
    return {"per_world": out, "best_per_world": best_per_world,
            "ever_best": ever_best, "dominator": dominator,
            "avg_over_worlds": avg}

# ================= T2：周期世界里"时间顺序"的符号能否被世界模型翻转 =================
def run_t2(T=1200, nseeds=8, P=40):
    # 周期 + 缓慢漂移的振幅，使"相位 + 近期"可能优于"相位 + 全部"
    def gen(rng):
        t = np.arange(T)
        amp = 3.0 + 0.5 * np.sin(2 * np.pi * t / (T / 1.5))  # 慢变振幅
        return amp * np.sin(2 * np.pi * t / P) + rng.normal(0, 0.2, T)
    arms = {
        "no_model_recent": lambda h: strat_mean_recent(h, 8),      # 用顺序，无世界模型
        "no_model_all":    strat_mean_all,                          # 不用顺序，无世界模型
        "model_uniform":   lambda h: strat_phase(h, P=P, recency=None),  # 有模型，不用近期
        "model_recent":    lambda h: strat_phase(h, P=P, recency=2),     # 有模型 + 近期
    }
    acc = {k: [] for k in arms}
    for seed in range(nseeds):
        rng = np.random.default_rng(2000 + seed)
        x = gen(rng)
        burn = int(T * 0.5)
        for name, f in arms.items():
            errs = [abs(x[i] - f(x[:i])) for i in range(burn, T)]
            acc[name].append(float(np.mean(errs)))
    summ = {k: {"mean": float(np.mean(v)),
                "lo": float(np.percentile(v, 2.5)),
                "hi": float(np.percentile(v, 97.5))} for k, v in acc.items()}
    # 关键对比：无模型时 顺序-无顺序（正=顺序是负债）
    d_nomodel = np.array(acc["no_model_recent"]) - np.array(acc["no_model_all"])
    # 有模型时 顺序-无顺序
    d_model = np.array(acc["model_recent"]) - np.array(acc["model_uniform"])
    # 有模型 vs 无模型最好者
    best_nomodel = np.minimum(np.array(acc["no_model_recent"]), np.array(acc["no_model_all"]))
    d_modelgain = best_nomodel - np.array(acc["model_recent"])
    def ci(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {"arms": summ,
            "no_model_order_minus_noorder": {"mean": float(d_nomodel.mean()), "ci": ci(d_nomodel)},
            "model_order_minus_noorder":    {"mean": float(d_model.mean()), "ci": ci(d_model)},
            "best_nomodel_minus_model_recent": {"mean": float(d_modelgain.mean()), "ci": ci(d_modelgain)}}

# ================= T3：好奇心在无结构地形上，是"有害"还是"预算不足" =================
def run_t3(budgets=(50, 200, 800, 3200), nseeds=10, n_nodes=60, n_feat=6):
    out = {}
    for B in budgets:
        rows = {}
        for arm in ["curiosity", "random", "uniform_norepeat"]:
            errs = []
            for seed in range(nseeds):
                rng = np.random.default_rng(3000 + seed)
                X = rng.normal(0, 1, (n_nodes, n_feat))       # 无结构：目标与特征无关
                y = rng.normal(0, 1, n_nodes)
                visited = np.zeros(n_nodes, dtype=int)
                w = np.zeros(n_feat)
                eta = 0.05
                for step in range(B):
                    if arm == "curiosity":
                        # 偏好"最远/最少访问"：以访问次数倒排 + 特征新奇度
                        nov = 1.0 / (1.0 + visited)
                        dist = np.abs(X - w).sum(1)
                        score = nov + 0.3 * dist / (dist.max() + 1e-9)
                        i = int(np.argmax(score))
                    elif arm == "random":
                        i = int(rng.integers(0, n_nodes))
                    else:  # uniform_norepeat：随机但不重复
                        cand = np.where(visited == 0)[0]
                        i = int(rng.choice(cand)) if len(cand) else int(rng.integers(0, n_nodes))
                    visited[i] += 1
                    p = float(w @ X[i])
                    w += eta * (y[i] - p) * X[i]
                errs.append(float(np.mean((X @ w - y) ** 2)))
            rows[arm] = {"mean": float(np.mean(errs)),
                         "lo": float(np.percentile(errs, 2.5)),
                         "hi": float(np.percentile(errs, 97.5))}
        d = np.array([0])  # placeholder
        out[str(B)] = rows
    return out

if __name__ == "__main__":
    R["T1"] = run_t1()
    R["T2"] = run_t2()
    R["T3"] = run_t3()
    with open(os.path.join(OUT, "result159.json"), "w") as f:
        json.dump(R, f, indent=2, ensure_ascii=False)
    print("=== T1 全域占优检验 ===")
    print("每个世界的最优策略：")
    for w in WORLDS:
        b = R["T1"]["best_per_world"][w]
        m = min(R["T1"]["per_world"][w][s]["mean"] for s in STRATS)
        print(f"  {w:11s} best={b}  minMAE={m:.4f}")
    print("各策略进最优的次数 /7:", R["T1"]["ever_best"])
    print("全域占优策略:", R["T1"]["dominator"] or "无")
    print("跨世界平均 MAE:", {k: round(v, 4) for k, v in R["T1"]["avg_over_worlds"].items()})
    print()
    print("=== T2 周期世界：世界模型能否翻转时间顺序的符号 ===")
    for k, v in R["T2"]["arms"].items():
        print(f"  {k:18s} {v['mean']:.4f}  CI[{v['lo']:.4f},{v['hi']:.4f}]")
    print("  无模型: 顺序-无顺序 =", round(R["T2"]["no_model_order_minus_noorder"]["mean"], 4),
          R["T2"]["no_model_order_minus_noorder"]["ci"])
    print("  有模型: 顺序-无顺序 =", round(R["T2"]["model_order_minus_noorder"]["mean"], 4),
          R["T2"]["model_order_minus_noorder"]["ci"])
    print("  无模型最优 - 有模型+近期 =", round(R["T2"]["best_nomodel_minus_model_recent"]["mean"], 4),
          R["T2"]["best_nomodel_minus_model_recent"]["ci"])
    print()
    print("=== T3 无结构地形：好奇心 vs 预算 ===")
    for B, rows in R["T3"].items():
        print(f"  budget={B}")
        for a, v in rows.items():
            print(f"    {a:18s} {v['mean']:.4f}  CI[{v['lo']:.4f},{v['hi']:.4f}]")
