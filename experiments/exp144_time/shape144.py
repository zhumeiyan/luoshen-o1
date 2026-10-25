#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
144 v4: 世界时间结构的"形状"决定顺序是资产还是负债
真实臂(周期方波负载切换)给出 d_order = -0.0467 (打乱更优), 与单调漂移世界相反。
假设: 不是真实 vs 模拟的矛盾, 而是我漏了变量 —— 漂移的"形状"。
- 单调漂移(monotone): 保序应优  (已在 v3 验证 +0.0731, 单调剂量响应)
- 方波周期(square):   打乱应优  (复现真实臂的负号)
- 正弦周期(sine):     中间态
"""
import numpy as np, json

D, T, ETA, U_SCALE = 4, 400, 0.01, 0.40
SEEDS = range(32)
GRAD_CLIP = 5.0


def _nr(M, rho):
    m = np.abs(np.linalg.eigvals(M)).max()
    return M * (rho / m) if m > 1e-9 else M


def run(shape, seed):
    rng = np.random.RandomState(seed * 7919 + 13)
    A0 = _nr(rng.normal(0, 1, (D, D)), 0.60)
    Delta = _nr(rng.normal(0, 1, (D, D)), 0.60) * 0.8
    Aseq = []
    for t in range(T):
        if shape == "monotone":
            A = A0 + (t / (T - 1)) * Delta
        elif shape == "square":
            A = A0 + (1.0 if (t // (T // 6)) % 2 == 1 else 0.0) * Delta
        elif shape == "sine":
            A = A0 + np.sin(2 * np.pi * t / (T / 3.0)) * Delta
        elif shape == "stationary":
            A = A0
        Aseq.append(_nr(A, 0.85))
    Aseq = np.array(Aseq)
    A_final = Aseq[-1]

    def sgd(Ah, s, sn):
        g = np.outer(Ah @ s - sn, s)
        gn = np.linalg.norm(g)
        return Ah - ETA * (g * (GRAD_CLIP / gn) if gn > GRAD_CLIP else g)

    ev = np.random.RandomState(99991)
    Stest = ev.normal(0, 1, (400, D))
    def err(Ah):
        return float(np.mean(np.linalg.norm(Stest @ (Ah - A_final).T, axis=1)))

    traj, s = [], rng.normal(0, 1, D)
    for t in range(T):
        sn = Aseq[t] @ s + U_SCALE * rng.normal(0, 1, D)
        traj.append((s.copy(), sn.copy())); s = sn
    S = np.array([p[0] for p in traj]); S2 = np.array([p[1] for p in traj])

    Ah = np.zeros((D, D))
    for i in range(T):
        Ah = sgd(Ah, S[i], S2[i])
    lived = err(Ah)

    o = list(range(T))
    np.random.RandomState(seed * 104729 + 5).shuffle(o)
    Ah2 = np.zeros((D, D))
    for i in o:
        Ah2 = sgd(Ah2, S[i], S2[i])
    shuffled = err(Ah2)

    Xb, *_ = np.linalg.lstsq(S, S2, rcond=None)
    batch = err(Xb.T)

    return {"lived": lived, "shuffled": shuffled, "batch": batch,
            "d_order": shuffled - lived,      # >0 保序优
            "d_batch": batch - lived}


def mean_ci(v, nb=4000, seed=12345):
    v = np.asarray(v, float); n = len(v)
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def main():
    out = {"shapes": {}}
    print(f"{'shape':11s} {'lived':>7s} {'shuffled':>8s} {'batch':>7s} "
          f"{'d_order':>9s}  CI           sign")
    for sh in ["stationary", "monotone", "sine", "square"]:
        rows = [run(sh, sd) for sd in SEEDS]
        rec = {}
        for k in ["lived", "shuffled", "batch", "d_order", "d_batch"]:
            m, lo, hi = mean_ci([r[k] for r in rows])
            rec[k] = {"mean": m, "ci": [lo, hi]}
        rec["sign"] = ("order_is_asset" if rec["d_order"]["ci"][0] > 0
                       else "order_is_liability" if rec["d_order"]["ci"][1] < 0
                       else "null")
        out["shapes"][sh] = rec
        m, lo, hi = rec["d_order"]["mean"], *rec["d_order"]["ci"]
        print(f"{sh:11s} {rec['lived']['mean']:7.4f} {rec['shuffled']['mean']:8.4f} "
              f"{rec['batch']['mean']:7.4f} {m:+9.4f}  [{lo:+.4f},{hi:+.4f}]  {rec['sign']}")

    out["real_cross_check"] = {
        "real_square_d_order": -0.046721,
        "sim_square_sign": out["shapes"]["square"]["sign"],
        "reproduced": out["shapes"]["square"]["sign"] == "order_is_liability",
    }
    with open("result_144_shape.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\n真实(周期方波) d_order = -0.046721 ;",
          "模拟 square 复现:" , out["real_cross_check"]["reproduced"])


if __name__ == "__main__":
    main()
