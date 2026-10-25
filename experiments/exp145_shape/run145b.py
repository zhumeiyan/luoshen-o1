#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""145 v2: 判别器修正是"换量", 不是调阈值.

v1 判 Y 序列的趋势 -> FAIL (monotone 判出率 0.039).
诊断: Y 的 std 2.24 几乎全部来自随机特征 X, w 的漂移在 Y 的边际分布里不可见
      (趋势 t 统计量仅 0.137, 阈值 2.0). 判错了量, 调任何阈值都救不回来.

v2 判残差: 用全历史拟合 w_all, 看残差 r[s]=Y[s]-X[s]@w_all 是否有系统趋势.
v3 不判形状, 直接让两个专家(ALL/RECENT)在最近 M 步上比预测误差, 选赢家.
   v3 只用过去, 不看未来, 不需要知道世界是什么形状.
"""
import json, os, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
N, D, K = 420, 4, 60
EVAL_FROM = 120
NOISE, CYCLES, LAM = 0.15, 3.0, 1e-3
M = 24                 # v3 回溯评估窗口
SEEDS = list(range(24))
THETA = 2.0


def gen_world(kind, seed, n=N, d=D, drift=1.0):
    rng = np.random.RandomState(seed)
    X = rng.normal(size=(n, d))
    w0 = rng.normal(size=d)
    v = rng.normal(size=d)
    u = np.arange(n) / float(n)
    amp = {"stationary": np.zeros(n),
           "monotone": drift * u,
           "sine": drift * np.sin(2 * np.pi * CYCLES * u),
           "square": drift * np.sign(np.sin(2 * np.pi * CYCLES * u))}[kind]
    W = w0[None, :] + amp[:, None] * v[None, :]
    Y = np.sum(X * W, axis=1) + rng.normal(scale=NOISE, size=n)
    return X, Y, W


def fit(Xh, Yh, lam=LAM):
    d = Xh.shape[1]
    try:
        return np.linalg.solve(Xh.T @ Xh + lam * np.eye(d), Xh.T @ Yh)
    except np.linalg.LinAlgError:
        return np.zeros(d)


def detrend_tstat(z):
    """对序列 z 做斜率显著性检验, 返回 |t|"""
    n = len(z)
    if n < 12:
        return 0.0
    t = np.arange(n, dtype=float)
    A = np.vstack([np.ones(n), t]).T
    coef, *_ = np.linalg.lstsq(A, z, rcond=None)
    resid = z - A @ coef
    s = resid.std()
    den = np.sum((t - t.mean()) ** 2)
    if den <= 0 or s <= 1e-12:
        return 0.0
    return float(abs(coef[1]) / (s / np.sqrt(den)))


def run(X, Y, policy, M=M, jitter_rng=None, theta=THETA):
    """policy: ALL / RECENT / V2_RESID / V3_EXPERT / V3_RANDOM"""
    n = len(Y)
    errs, pick_recent = [], []
    for t in range(EVAL_FROM, n):
        Xa, Ya = X[:t], Y[:t]
        if policy == "ALL":
            pr = False
        elif policy == "RECENT":
            pr = True
        elif policy == "V2_RESID":
            w_all = fit(Xa, Ya)
            r = Ya - Xa @ w_all
            pr = bool(detrend_tstat(r) > theta)
        elif policy in ("V3_EXPERT", "V3_RANDOM"):
            # 最近 M 步回溯: 用截至 s 的历史预测 s+1, 比两个专家
            s0 = max(EVAL_FROM, t - M)
            ea = er = 0.0
            for s in range(s0, t):
                Xs, Ys = X[:s], Y[:s]
                wa = fit(Xs, Ys)
                wr = fit(Xs[-K:], Ys[-K:])
                if s + 1 < n:
                    ea += abs(float(X[s] @ wa) - Y[s])
                    er += abs(float(X[s] @ wr) - Y[s])
            if policy == "V3_RANDOM":
                pr = bool(jitter_rng.rand() < 0.5)
            else:
                pr = bool(er < ea)
        else:
            raise ValueError(policy)
        pick_recent.append(bool(pr))
        w = fit(Xa[-K:], Ya[-K:]) if pr else fit(Xa, Ya)
        errs.append(abs(float(X[t] @ w) - Y[t]))
    return dict(err=float(np.mean(errs)),
                recent_rate=float(np.mean(pick_recent)) if pick_recent else 0.0)


def mean_ci(v, nb=4000, seed=987654):
    v = np.asarray(v, float); n = len(v)
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


POL = ["ALL", "RECENT", "V2_RESID", "V3_EXPERT", "V3_RANDOM"]


def sweep(worlds, nseed=len(SEEDS)):
    res = {w: {p: [] for p in POL} for w in worlds}
    for w in worlds:
        for sd in SEEDS[:nseed]:
            X, Y, _ = gen_world(w, sd)
            jr = np.random.RandomState(sd * 7919 + 13)
            for p in POL:
                res[w][p].append(run(X, Y, p, M, jr))
    return res


def main():
    worlds = ["stationary", "monotone", "sine", "square"]
    res = sweep(worlds)
    out = {"worlds": {}}
    print("=== v2/v3 ===")
    for w in worlds:
        out["worlds"][w] = {}
        print("-- %s" % w)
        for p in POL:
            m, lo, hi = mean_ci([r["err"] for r in res[w][p]])
            rr, _, _ = mean_ci([r["recent_rate"] for r in res[w][p]])
            out["worlds"][w][p] = {"err": m, "ci": [lo, hi], "recent_rate": rr}
            print("   %-10s err %.4f [%.4f,%.4f]  pick_RECENT %.3f" % (p, m, lo, hi, rr))

    # G2: V3 不劣于较好的固定策略
    g2 = {}
    for w in worlds:
        a = out["worlds"][w]["V3_EXPERT"]["err"]
        best = min(out["worlds"][w]["ALL"]["err"], out["worlds"][w]["RECENT"]["err"])
        g2[w] = bool(a <= best + 0.02)
    # G3: 随机选专家显著劣于 V3
    diff = []
    for w in worlds:
        for i in range(len(res[w]["V3_EXPERT"])):
            diff.append(res[w]["V3_RANDOM"][i]["err"] - res[w]["V3_EXPERT"][i]["err"])
    m3, lo3, hi3 = mean_ci(diff)
    g3 = bool(lo3 > 0)
    # G1': V3 的选率必须随世界变化 (能产生真也能产生假)
    r_stat = out["worlds"]["stationary"]["V3_EXPERT"]["recent_rate"]
    r_mono = out["worlds"]["monotone"]["V3_EXPERT"]["recent_rate"]
    g1 = bool(r_mono - r_stat > 0.15)
    out["verdict"] = {"G1_selectivity": g1,
                      "rate_stationary": r_stat, "rate_monotone": r_mono,
                      "G2_per_world": g2, "G2": bool(all(g2.values())),
                      "G3_diff": m3, "G3_ci": [lo3, hi3], "G3": g3}
    print("G1 selectivity %s (stat %.3f -> mono %.3f)" % (g1, r_stat, r_mono))
    print("G2", g2, " G3", g3, "diff %+.4f [%+.4f,%+.4f]" % (m3, lo3, hi3))

    # ---- 形状切换: 前半 monotone, 后半 square ----
    sw = []
    for sd in SEEDS[:12]:
        X1, Y1, _ = gen_world("monotone", sd, n=N // 2)
        X2, Y2, _ = gen_world("square", sd + 1000, n=N // 2)
        X = np.vstack([X1, X2]); Y = np.concatenate([Y1, Y2])
        r = run(X, Y, "V3_EXPERT", M, None)
        # 分段统计选率
        n2 = N // 2
        sw.append(r)
    # 分段: 单独跑一次带分段记录
    segs = {"first_half": [], "second_half": []}
    for sd in SEEDS[:12]:
        X1, Y1, _ = gen_world("monotone", sd, n=N // 2)
        X2, Y2, _ = gen_world("square", sd + 1000, n=N // 2)
        X = np.vstack([X1, X2]); Y = np.concatenate([Y1, Y2])
        n2 = N // 2
        picks = []
        errs = []
        for t in range(EVAL_FROM, len(Y)):
            Xa, Ya = X[:t], Y[:t]
            s0 = max(EVAL_FROM, t - M)
            ea = er = 0.0
            for s in range(s0, t):
                Xs, Ys = X[:s], Y[:s]
                wa = fit(Xs, Ys); wr = fit(Xs[-K:], Ys[-K:])
                ea += abs(float(X[s] @ wa) - Y[s]); er += abs(float(X[s] @ wr) - Y[s])
            pr = er < ea
            picks.append(bool(pr))
            w = fit(Xa[-K:], Ya[-K:]) if pr else fit(Xa, Ya)
            errs.append(abs(float(X[t] @ w) - Y[t]))
        picks = np.array(picks)
        ts = np.arange(EVAL_FROM, len(Y))
        first = picks[ts < n2]; second = picks[ts >= n2]
        segs["first_half"].append(float(first.mean()) if len(first) else float("nan"))
        segs["second_half"].append(float(second.mean()) if len(second) else float("nan"))
    f, flo, fhi = mean_ci(segs["first_half"]); s, slo, shi = mean_ci(segs["second_half"])
    out["switch"] = {"first_half_rate": [f, flo, fhi], "second_half_rate": [s, slo, shi]}
    print("SWITCH: monotone-half pick_RECENT %.3f | square-half %.3f" % (f, s))

    with open(os.path.join(OUT, "result_145b.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("WROTE result_145b.json")


if __name__ == "__main__":
    main()
