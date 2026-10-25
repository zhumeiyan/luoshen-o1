#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
144 v3: 剂量扫描 —— 把"顺序效应"钉在"世界漂移幅度"上
动机: v2 里 fed_batch 用最小二乘而 lived 用 SGD, 算法不同 -> 变量混淆, 不可用。
唯一公平的对照是 fed_shuffle (同为 T 次 SGD, 同数据, 唯一差别是顺序)。
若顺序效应真来自世界漂移, 则它必须随漂移幅度单调增长。
"""
import numpy as np, json

D, T, ETA, U_SCALE, W_RECENT = 4, 400, 0.01, 0.40, 50
SEEDS = range(32)
GRAD_CLIP = 5.0
DRIFT_GRID = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def _norm_rho(M, rho):
    m = np.abs(np.linalg.eigvals(M)).max()
    return M * (rho / m) if m > 1e-9 else M


def run(kind, drift_scale, seed):
    rng = np.random.RandomState(seed * 7919 + 13)
    A0 = _norm_rho(rng.normal(0, 1, (D, D)), 0.60)
    Delta = _norm_rho(rng.normal(0, 1, (D, D)), 0.60) * 0.8 * drift_scale
    Aseq = []
    for t in range(T):
        if kind == "stationary":
            A = A0
        elif kind == "drift":
            A = A0 + (t / (T - 1)) * Delta
        elif kind == "cyclic":
            A = A0 + np.sin(2 * np.pi * t / (T / 3.0)) * Delta
        Aseq.append(_norm_rho(A, 0.85))
    Aseq = np.array(Aseq)
    A_final = Aseq[-1]

    def sgd(Ahat, s, sn):
        g = np.outer(Ahat @ s - sn, s)
        gn = np.linalg.norm(g)
        return Ahat - ETA * (g * (GRAD_CLIP / gn) if gn > GRAD_CLIP else g)

    ev = np.random.RandomState(99991)
    Stest = ev.normal(0, 1, (400, D))
    def err(Ahat):
        return float(np.mean(np.linalg.norm(Stest @ (Ahat - A_final).T, axis=1)))

    traj, s = [], rng.normal(0, 1, D)
    for t in range(T):
        sn = Aseq[t] @ s + U_SCALE * rng.normal(0, 1, D)
        traj.append((s.copy(), sn.copy())); s = sn
    S = np.array([p[0] for p in traj]); S2 = np.array([p[1] for p in traj])

    # lived: 保序在线 SGD
    Ah = np.zeros((D, D))
    for i in range(T):
        Ah = sgd(Ah, S[i], S2[i])
    lived = err(Ah)

    # fed_shuffle: 同 T 次 SGD, 唯一差别是顺序被打乱
    o = list(range(T))
    np.random.RandomState(seed * 104729 + 5).shuffle(o)
    Ah2 = np.zeros((D, D))
    for i in o:
        Ah2 = sgd(Ah2, S[i], S2[i])
    fed_shuffle = err(Ah2)

    # 批最小二乘(算法不同, 仅作参考, 不进主判据)
    Xb, *_ = np.linalg.lstsq(S, S2, rcond=None)
    fed_batch = err(Xb.T)
    Xr, *_ = np.linalg.lstsq(S[-W_RECENT:], S2[-W_RECENT:], rcond=None)
    fed_recent = err(Xr.T)

    return {"lived": lived, "fed_shuffle": fed_shuffle,
            "fed_batch": fed_batch, "fed_recent": fed_recent,
            "d_order": fed_shuffle - lived,      # >0: 保序更优
            "d_batch": fed_batch - lived,
            "d_recent": fed_recent - lived}


def mean_ci(v, nb=4000, seed=12345):
    v = np.asarray(v, float); n = len(v)
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def main():
    out = {"dose": [], "worlds": {}}
    print(f"{'drift':>6s} {'lived':>7s} {'shuffle':>8s} {'d_order':>9s}  CI")
    for ds in DRIFT_GRID:
        rows = [run("drift", ds, sd) for sd in SEEDS]
        rec = {"drift_scale": ds}
        for k in ["lived", "fed_shuffle", "fed_batch", "fed_recent",
                  "d_order", "d_batch", "d_recent"]:
            m, lo, hi = mean_ci([r[k] for r in rows])
            rec[k] = {"mean": m, "ci": [lo, hi]}
        out["dose"].append(rec)
        m, lo, hi = rec["d_order"]["mean"], *rec["d_order"]["ci"]
        print(f"{ds:6.1f} {rec['lived']['mean']:7.4f} {rec['fed_shuffle']['mean']:8.4f} "
              f"{m:+9.4f}  [{lo:+.4f},{hi:+.4f}]")

    # 单调性
    ds_vals = [r["d_order"]["mean"] for r in out["dose"]]
    out["monotone"] = bool(all(ds_vals[i + 1] >= ds_vals[i] - 1e-9
                               for i in range(len(ds_vals) - 1)))
    out["dose_slope"] = ds_vals

    # 三世界四臂(用 0.8 漂移幅度)
    print(f"\n{'world':12s} {'lived':>7s} {'batch':>7s} {'recent':>7s} {'shuffle':>8s}")
    for kind in ["stationary", "drift", "cyclic"]:
        rows = [run(kind, 0.8, sd) for sd in SEEDS]
        rec = {}
        for k in ["lived", "fed_batch", "fed_recent", "fed_shuffle",
                  "d_order", "d_batch", "d_recent"]:
            m, lo, hi = mean_ci([r[k] for r in rows])
            rec[k] = {"mean": m, "ci": [lo, hi]}
        out["worlds"][kind] = rec
        print(f"{kind:12s} {rec['lived']['mean']:7.4f} {rec['fed_batch']['mean']:7.4f} "
              f"{rec['fed_recent']['mean']:7.4f} {rec['fed_shuffle']['mean']:8.4f}")

    def gate(w, k):
        a = out["worlds"][w][k]
        return {"mean": a["mean"], "ci": a["ci"],
                "pos": bool(a["ci"][0] > 0),
                "crosses_zero": bool(a["ci"][0] <= 0 <= a["ci"][1])}

    out["gates"] = {
        "G1_drift_order_matters": gate("drift", "d_order"),
        "G2_stationary_order_null": gate("stationary", "d_order"),
        "G3_cyclic_order_explore": gate("cyclic", "d_order"),
        "monotone_in_drift": out["monotone"],
    }
    out["verdict"] = {
        "G1_pass": out["gates"]["G1_drift_order_matters"]["pos"],
        "G2_null_holds": out["gates"]["G2_stationary_order_null"]["crosses_zero"],
        "monotone": out["monotone"],
    }
    with open("result_144.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\nVERDICT:", json.dumps(out["verdict"]))


if __name__ == "__main__":
    main()
