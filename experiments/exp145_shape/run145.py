#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""145: 能否在线判定世界形状，并据此切换记忆策略？

144 结论: 保持时间顺序是资产(drift)还是负债(square周期)，取决于世界形状。
但 144 里形状是实验者给的。本轮: 学习者只看过去观测，自己判形状，自己选策略。

严格约束:
  判别器只能看 Y[0:t] (过去), 不能看未来, 不能看真权重 W。
  策略只影响"用哪些历史样本拟合", 不改学习算法本身。
"""
import json, os, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
N = 420          # 步数
D = 4            # 特征维
K = 60           # 近因窗口
EVAL_FROM = 120  # 前 120 步预热, 之后才计入误差
NOISE = 0.15
CYCLES = 3.0
LAM = 1e-3
THETAS = [1.0, 1.5, 2.0, 3.0, 4.0]
THETA_MAIN = 2.0
SEEDS = list(range(24))


# ---------------- 世界 ----------------
def gen_world(kind, seed, n=N, d=D, drift=1.0):
    rng = np.random.RandomState(seed)
    X = rng.normal(size=(n, d))
    w0 = rng.normal(size=d)
    v = rng.normal(size=d)          # 漂移方向, 一次性采样
    u = np.arange(n) / float(n)
    if kind == "stationary":
        amp = np.zeros(n)
    elif kind == "monotone":
        amp = drift * u
    elif kind == "sine":
        amp = drift * np.sin(2 * np.pi * CYCLES * u)
    elif kind == "square":
        amp = drift * np.sign(np.sin(2 * np.pi * CYCLES * u))
    else:
        raise ValueError(kind)
    W = w0[None, :] + amp[:, None] * v[None, :]
    Y = np.sum(X * W, axis=1) + rng.normal(scale=NOISE, size=n)
    return X, Y, W


# ---------------- 判别器: 只看过去, 判 "是否 drift" ----------------
def judge_drift(Yhist, theta=THETA_MAIN):
    """对 Y[0:t] 做斜率显著性检验。返回 (是否判drift, t统计量)"""
    n = len(Yhist)
    if n < 12:
        return False, 0.0
    t = np.arange(n, dtype=float)
    A = np.vstack([np.ones(n), t]).T
    try:
        coef, *_ = np.linalg.lstsq(A, Yhist, rcond=None)
    except np.linalg.LinAlgError:
        return False, 0.0
    resid = Yhist - A @ coef
    s = resid.std()
    denom = np.sum((t - t.mean()) ** 2)
    if denom <= 0 or s <= 1e-12:
        return False, 0.0
    se = s / np.sqrt(denom)
    tstat = abs(coef[1]) / se
    return bool(tstat > theta), float(tstat)


# ---------------- 策略 ----------------
def fit_ridge(Xh, Yh, lam=LAM):
    d = Xh.shape[1]
    A = Xh.T @ Xh + lam * np.eye(d)
    b = Xh.T @ Yh
    try:
        return np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return np.zeros(d)


def run_arm(kind, seed, policy, theta=THETA_MAIN, jitter_rng=None):
    """policy: ALL / RECENT / ADAPTIVE / ADAPTIVE_RANDOM"""
    X, Y, W = gen_world(kind, seed)
    errs, verdicts, truth = [], [], []
    zero_b, ident_b = [], []
    for t in range(EVAL_FROM, len(Y)):
        Xh_all, Yh_all = X[:t], Y[:t]
        is_drift, _ = judge_drift(Yh_all, theta)
        truth.append(kind == "monotone")
        if policy == "ALL":
            use, v = (Xh_all, Yh_all), False
        elif policy == "RECENT":
            use, v = (Xh_all[-K:], Yh_all[-K:]), True
        elif policy == "ADAPTIVE":
            v = is_drift
        elif policy == "ADAPTIVE_RANDOM":
            # 负面对照: 判定结果随机化, 保率不同但破坏时序针对性
            v = bool(jitter_rng.rand() < 0.5)
        else:
            raise ValueError(policy)
        if policy in ("ADAPTIVE", "ADAPTIVE_RANDOM"):
            use = (Xh_all[-K:], Yh_all[-K:]) if v else (Xh_all, Yh_all)
        verdicts.append(bool(v))
        w = fit_ridge(use[0], use[1])
        pred = float(X[t] @ w)
        errs.append(abs(pred - Y[t]))
        zero_b.append(abs(Y[t]))
        ident_b.append(abs(Y[t - 1] - Y[t]))
    return dict(err=float(np.mean(errs)),
                drift_rate=float(np.mean(verdicts)),
                truth_drift_rate=float(np.mean(truth)),
                zero=float(np.mean(zero_b)), ident=float(np.mean(ident_b)))


# ---------------- 统计 ----------------
def mean_ci(v, nb=4000, seed=987654):
    v = np.asarray(v, float)
    n = len(v)
    if n == 0:
        return 0.0, 0.0, 0.0
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def main():
    worlds = ["stationary", "monotone", "sine", "square"]
    policies = ["ALL", "RECENT", "ADAPTIVE", "ADAPTIVE_RANDOM"]
    res = {w: {p: [] for p in policies} for w in worlds}
    for w in worlds:
        for sd in SEEDS:
            jr = np.random.RandomState(sd * 7919 + 13)
            for p in policies:
                res[w][p].append(run_arm(w, sd, p, THETA_MAIN, jr))

    out = {"worlds": {}, "verdict": {}}
    print("=== MAIN (theta=%.1f) ===" % THETA_MAIN)
    for w in worlds:
        out["worlds"][w] = {}
        print("-- %s" % w)
        for p in policies:
            rs = res[w][p]
            m, lo, hi = mean_ci([r["err"] for r in rs])
            dr, _, _ = mean_ci([r["drift_rate"] for r in rs])
            out["worlds"][w][p] = {"err": m, "ci": [lo, hi], "drift_rate": dr}
            print("   %-16s err %.4f [%.4f,%.4f]  judge_drift %.3f"
                  % (p, m, lo, hi, dr))
        z = np.mean([r["zero"] for r in res[w]["ALL"]])
        ib = np.mean([r["ident"] for r in res[w]["ALL"]])
        out["worlds"][w]["baselines"] = {"zero": float(z), "ident": float(ib)}
        print("   baselines: zero %.4f  ident %.4f" % (z, ib))

    # G1: 判别器能产生真也能产生假
    g1a = out["worlds"]["monotone"]["ADAPTIVE"]["drift_rate"] > 0.5
    g1b = out["worlds"]["stationary"]["ADAPTIVE"]["drift_rate"] < 0.3
    # G2: ADAPTIVE 不劣于较好的固定策略 (+容差)
    g2 = {}
    for w in worlds:
        a = out["worlds"][w]["ADAPTIVE"]["err"]
        best = min(out["worlds"][w]["ALL"]["err"], out["worlds"][w]["RECENT"]["err"])
        g2[w] = bool(a <= best + 0.02)
    # G3: 随机化判定显著更差 (跨世界合计)
    diff = []
    for w in worlds:
        for i in range(len(res[w]["ADAPTIVE"])):
            diff.append(res[w]["ADAPTIVE_RANDOM"][i]["err"] - res[w]["ADAPTIVE"][i]["err"])
    m3, lo3, hi3 = mean_ci(diff)
    g3 = bool(lo3 > 0)
    # 阴性对照: stationary 上切换应无收益
    ds = [res["stationary"]["RECENT"][i]["err"] - res["stationary"]["ADAPTIVE"][i]["err"]
          for i in range(len(res["stationary"]["ADAPTIVE"]))]
    ms, los, his = mean_ci(ds)

    out["verdict"] = {
        "G1_drift_judged": bool(g1a), "G1_stationary_not_judged": bool(g1b),
        "G1": bool(g1a and g1b),
        "G2_per_world": g2, "G2": bool(all(g2.values())),
        "G3_diff_mean": m3, "G3_ci": [lo3, hi3], "G3": g3,
        "negctl_stationary_recent_minus_adaptive": [ms, los, his],
    }
    print("G1", out["verdict"]["G1"], "| G2", g2, "| G3", g3,
          "diff %+.4f [%+.4f,%+.4f]" % (m3, lo3, hi3))
    print("negctl stationary recent-adaptive %+.4f [%+.4f,%+.4f]" % (ms, los, his))

    # theta 敏感性 (不挑好看的, 全报)
    out["theta_scan"] = {}
    for th in THETAS:
        row = {}
        for w in ["monotone", "stationary"]:
            rr = [run_arm(w, sd, "ADAPTIVE", th,
                          np.random.RandomState(sd * 7919 + 13)) for sd in SEEDS[:12]]
            e, _, _ = mean_ci([r["err"] for r in rr])
            d, _, _ = mean_ci([r["drift_rate"] for r in rr])
            row[w] = {"err": e, "drift_rate": d}
        out["theta_scan"][str(th)] = row
        print("theta %.1f  monotone err %.4f dr %.3f | stationary err %.4f dr %.3f"
              % (th, row["monotone"]["err"], row["monotone"]["drift_rate"],
                 row["stationary"]["err"], row["stationary"]["drift_rate"]))

    with open(os.path.join(OUT, "result_145.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("WROTE result_145.json")


if __name__ == "__main__":
    main()
