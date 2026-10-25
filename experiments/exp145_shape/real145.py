#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""145 真实臂: 真实 CPU jitter 时序, 两种真实模式.

PREREG 判据: 判别器在两种真实模式上必须给出**不同**选率, 否则真实数据上无区分力 -> FAIL.
144 教训: 必须标准化, 否则毫秒量级下梯度/权重尺度失衡, 学习根本不发生.
"""
import json, os, time, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
K, M, EVAL_FROM, LAM = 60, 24, 120, 1e-3


def busy(n=180000):
    t0 = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return time.perf_counter() - t0


def collect(kind, n=420):
    x = []
    for i in range(n):
        if kind == "sustain":
            x.append(busy())
        elif kind == "cycle":           # 约每 30 个采样切换一次负载/空闲
            if (i // 30) % 2 == 0:
                x.append(busy())
            else:
                time.sleep(0.004)
                x.append(busy(20000))
        else:
            raise ValueError(kind)
    return np.asarray(x, dtype=float)


def make_features(z, lag=3):
    n = len(z)
    X = np.ones((n, lag + 1))
    Y = np.zeros(n)
    for t in range(lag, n):
        X[t, :lag] = z[t - lag:t]
        Y[t] = z[t]
    return X[lag:], Y[lag:]


def fit(Xh, Yh, lam=LAM):
    d = Xh.shape[1]
    try:
        return np.linalg.solve(Xh.T @ Xh + lam * np.eye(d), Xh.T @ Yh)
    except np.linalg.LinAlgError:
        return np.zeros(d)


def run(X, Y, policy, jr=None):
    errs, picks, idb, zb = [], [], [], []
    for t in range(EVAL_FROM, len(Y)):
        Xa, Ya = X[:t], Y[:t]
        if policy == "ALL":
            pr = False
        elif policy == "RECENT":
            pr = True
        elif policy in ("V3", "V3_RANDOM"):
            s0 = max(EVAL_FROM, t - M)
            ea = er = 0.0
            for s in range(s0, t):
                Xs, Ys = X[:s], Y[:s]
                wa = fit(Xs, Ys); wr = fit(Xs[-K:], Ys[-K:])
                ea += abs(float(X[s] @ wa) - Y[s]); er += abs(float(X[s] @ wr) - Y[s])
            pr = bool(jr.rand() < 0.5) if policy == "V3_RANDOM" else bool(er < ea)
        else:
            raise ValueError(policy)
        picks.append(bool(pr))
        w = fit(Xa[-K:], Ya[-K:]) if pr else fit(Xa, Ya)
        errs.append(abs(float(X[t] @ w) - Y[t]))
        idb.append(abs(Y[t - 1] - Y[t])); zb.append(abs(Y[t]))
    return dict(err=float(np.mean(errs)), recent_rate=float(np.mean(picks)),
                ident=float(np.mean(idb)), zero=float(np.mean(zb)))


def mean_ci(v, nb=4000, seed=24680):
    v = np.asarray(v, float); n = len(v)
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def main():
    out = {"modes": {}}
    for kind in ["sustain", "cycle"]:
        z = collect(kind)
        mu, sd = z.mean(), z.std()
        zz = (z - mu) / (sd if sd > 1e-12 else 1.0)   # 144 教训: 必须标准化
        X, Y = make_features(zz)
        rows = {p: [] for p in ["ALL", "RECENT", "V3", "V3_RANDOM"]}
        for rep in range(6):
            jr = np.random.RandomState(rep * 104729 + 7)
            for p in rows:
                rows[p].append(run(X, Y, p, jr))
        out["modes"][kind] = {"raw_mean_ms": float(z.mean() * 1e3),
                              "raw_std_ms": float(z.std() * 1e3),
                              "seg_means_z": [float(zz[i * (len(zz) // 6):(i + 1) * (len(zz) // 6)].mean())
                                              for i in range(6)]}
        print("== %s  raw %.4f ms (std %.4f)" % (kind, z.mean() * 1e3, z.std() * 1e3))
        print("   seg z:", " ".join("%+.2f" % v for v in out["modes"][kind]["seg_means_z"]))
        for p in rows:
            m, lo, hi = mean_ci([r["err"] for r in rows[p]])
            rr, _, _ = mean_ci([r["recent_rate"] for r in rows[p]])
            out["modes"][kind][p] = {"err": m, "ci": [lo, hi], "recent_rate": rr}
            print("   %-10s err %.4f [%.4f,%.4f]  pick_RECENT %.3f" % (p, m, lo, hi, rr))
        ib = float(np.mean([r["ident"] for r in rows["ALL"]]))
        zb = float(np.mean([r["zero"] for r in rows["ALL"]]))
        out["modes"][kind]["baselines"] = {"ident": ib, "zero": zb}
        print("   baselines: ident %.4f  zero %.4f" % (ib, zb))

    rs = out["modes"]["sustain"]["V3"]["recent_rate"]
    rc = out["modes"]["cycle"]["V3"]["recent_rate"]
    out["verdict"] = {"sustain_rate": rs, "cycle_rate": rc,
                      "distinct": bool(abs(rs - rc) > 0.10)}
    print("REAL DISCRIMINATION: sustain %.3f vs cycle %.3f -> distinct=%s"
          % (rs, rc, out["verdict"]["distinct"]))
    with open(os.path.join(OUT, "result_145_real.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("WROTE result_145_real.json")


if __name__ == "__main__":
    main()
