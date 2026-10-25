# -*- coding: utf-8 -*-
"""
113c2 · 配对版引擎检验
种子间 sd≈0.0144, 组间差≈0.001 —— 独立组设计分辨不出来。
改用【同种子配对】: 同一 seed 下跑四条流, 取差, 再自助法求 CI。
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
K_SAL = 0.60


def one(seq, seed, steps=240, ratio=0.60, k_sal=K_SAL):
    L = Life5(N=8, seed=seed, ratio=ratio, k_sal=k_sal)
    for t in range(steps):
        L.input_val = float(seq[t % len(seq)])
        L.step()
        if not L.alive:
            return None
    return float(np.std(L.y))


def boot_ci(d, n=4000, seed=7):
    d = np.asarray(d, float)
    if len(d) < 2:
        return (float("nan"), float("nan"))
    r = np.random.default_rng(seed)
    bs = np.array([r.choice(d, len(d), replace=True).mean() for _ in range(n)])
    return (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


def main():
    d = json.load(open(os.path.join(OUT, "result113c.json")))
    # 用 113c 存下的统计量重建不了原始序列, 这里重新取真轨迹
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from run113 import RealEye, RealHand, run_agent, GW
    eye = RealEye(); hand = RealHand(enabled=True)
    sal_map = np.array([1.0 if (i % GW) >= GW // 2 else 0.1 for i in range(GW * 6)])

    def real_traj(kind, **kw):
        seq = []; orig = eye.look
        def rec(cx, cy):
            m = orig(cx, cy); seq.append(m); return m
        eye.look = rec
        try:
            run_agent(kind, "A", 6, 12, eye, hand, **kw)
        finally:
            eye.look = orig
        return np.asarray(seq, float)

    Q = np.zeros((GW * 6, GW * 6)) + 0.01
    eps = 1.0
    for _ in range(800):
        run_agent("learned", "A", 1, 12, eye, hand, Q=Q, eps=eps, train=True)
        eps = max(0.05, eps * 0.995)
    traj = {"preset": real_traj("preset", sal=sal_map),
            "learned": real_traj("learned", Q=Q, train=False),
            "blind": real_traj("blind"),
            "none": np.zeros(72)}
    g = max(float(np.max(v)) for v in traj.values())
    traj = {k: v / g for k, v in traj.items()}
    hand.destroy()

    SEEDS = 48
    vals = {k: [] for k in traj}
    for sd in range(SEEDS):
        for k, v in traj.items():
            vals[k].append(one(v, sd))

    res = {}
    for k in traj:
        arr = np.array([x for x in vals[k] if x is not None], float)
        res[k] = dict(mean=float(arr.mean()), n=len(arr))
    pairs = {}
    for a, b in [("preset", "none"), ("learned", "none"), ("blind", "none"),
                 ("learned", "preset"), ("learned", "blind"), ("preset", "blind")]:
        da = np.array([vals[a][i] for i in range(SEEDS) if vals[a][i] is not None
                       and vals[b][i] is not None], float)
        db = np.array([vals[b][i] for i in range(SEEDS) if vals[a][i] is not None
                       and vals[b][i] is not None], float)
        diff = da - db
        lo, hi = boot_ci(diff)
        pairs[f"{a}-{b}"] = dict(d=float(diff.mean()), lo=lo, hi=hi,
                                 sig=bool(lo > 0 or hi < 0), n=len(diff))
        print(f"  {a:8s} - {b:8s}  Δ={diff.mean():+.5f}  CI[{lo:+.5f},{hi:+.5f}]  "
              f"{'显著' if (lo>0 or hi<0) else '跨0 不显著'}")

    out = dict(res=res, pairs=pairs, seeds=SEEDS, k_sal=K_SAL)
    with open(os.path.join(OUT, "result113c2.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
