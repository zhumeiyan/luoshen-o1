#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
144 真实臂 v2: 真实负载切换下的 jitter 序列
v1 失败原因: jitter 几乎恒定(std 0.01ms) + Takens 嵌入高度重叠
             -> 恒等外推(s_t+1 = s_t)误差 0.00003, 任务退化, 无区分力
v2 两处修正:
  1) lag 嵌入(间隔 LAG), 打破相邻重叠
  2) 采集中途真实启动 CPU 负载线程 -> 序列真实非平稳
数据仍是真采的(真实调度抖动 + 真实系统负载), 不是模拟。
"""
import numpy as np, json, time, threading

D, ETA, LAG = 4, 0.01, 8
N_SAMPLE = 1200
GRAD_CLIP = 5.0
SEEDS = range(24)
STOP = threading.Event()


def cpu_burn():
    x = 0.0
    while not STOP.is_set():
        x += 1.23456789 ** 0.5


def collect_real(n=N_SAMPLE):
    """周期性真实 CPU 负载切换 -> jitter 持续非平稳(测试集内也有结构)"""
    seq, marks = [], []
    period = n // 6          # 6 段, 交替 负载/空闲
    for i in range(n):
        if i % period == 0:
            STOP.set(); time.sleep(0.03)
            if (i // period) % 2 == 1:
                STOP.clear()
                threading.Thread(target=cpu_burn, daemon=True).start()
        t0 = time.perf_counter()
        time.sleep(0.0005)
        t1 = time.perf_counter()
        seq.append(t1 - t0)
        marks.append((i // period) % 2)
    STOP.set()
    time.sleep(0.05)
    x = np.array(seq, float)
    x = (x - x.mean()) / (x.std() + 1e-12)      # 标准化: 让学习真正发生
    return x, np.array(marks)


def embed_lag(x, d=D, lag=LAG):
    n = len(x)
    need = (d - 1) * lag + 1
    return np.array([x[i:i + need:lag] for i in range(n - need)])


def run_real(x, marks, seed):
    E = embed_lag(x)
    S, S2 = E[:-1], E[1:]
    T = len(S)
    cut = int(T * 0.7)
    Strain, S2train = S[:cut], S2[:cut]
    Stest, S2test = S[cut:], S2[cut:]

    def sgd(Ah, s, sn):
        g = np.outer(Ah @ s - sn, s)
        gn = np.linalg.norm(g)
        return Ah - ETA * (g * (GRAD_CLIP / gn) if gn > GRAD_CLIP else g)

    def err(Ah):
        return float(np.mean(np.linalg.norm((Stest @ Ah.T) - S2test, axis=1)))

    Ah = np.zeros((D, D))
    for i in range(len(Strain)):
        Ah = sgd(Ah, Strain[i], S2train[i])
    lived = err(Ah)

    o = list(range(len(Strain)))
    np.random.RandomState(seed * 104729 + 5).shuffle(o)
    Ah2 = np.zeros((D, D))
    for i in o:
        Ah2 = sgd(Ah2, Strain[i], S2train[i])
    shuffled = err(Ah2)

    ident = float(np.mean(np.linalg.norm(Stest - S2test, axis=1)))
    zerob = float(np.mean(np.linalg.norm(S2test, axis=1)))
    return {"lived": lived, "shuffled": shuffled, "d_order": shuffled - lived,
            "ident_baseline": ident, "zero_baseline": zerob}


def mean_ci(v, nb=4000, seed=12345):
    v = np.asarray(v, float); n = len(v)
    b = v[np.random.RandomState(seed).randint(0, n, (nb, n))].mean(axis=1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def main():
    x, marks = collect_real()
    seg = len(x) // 6
    stat = {"seg_means_z": [float(x[i*seg:(i+1)*seg].mean()) for i in range(6)],
            "note": "standardized z-scores; 6 segments alternate load/idle"}
    rows = [run_real(x, marks, sd) for sd in SEEDS]
    out = {"real_samples": int(len(x)), "stat": stat, "arms": {}}
    for k in ["lived", "shuffled", "d_order", "ident_baseline", "zero_baseline"]:
        m, lo, hi = mean_ci([r[k] for r in rows])
        out["arms"][k] = {"mean": m, "ci": [lo, hi]}
    d = out["arms"]["d_order"]
    out["gate"] = {"mean": d["mean"], "ci": d["ci"],
                   "pos": bool(d["ci"][0] > 0),
                   "crosses_zero": bool(d["ci"][0] <= 0 <= d["ci"][1])}
    with open("result_144_real.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("REAL jitter z by segment:",
          " ".join("%+.3f" % v for v in stat["seg_means_z"]))
    print(f"lived    {out['arms']['lived']['mean']:.6f}")
    print(f"shuffled {out['arms']['shuffled']['mean']:.6f}")
    print(f"ident    {out['arms']['ident_baseline']['mean']:.6f}  (s_t+1 = s_t)")
    print(f"zero     {out['arms']['zero_baseline']['mean']:.6f}")
    m, lo, hi = d["mean"], *d["ci"]
    print(f"d_order  {m:+.6f}  [{lo:+.6f},{hi:+.6f}]  pos={out['gate']['pos']}")


if __name__ == "__main__":
    main()
