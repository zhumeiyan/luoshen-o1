#!/usr/bin/env python3
"""
exp164b: 修正 B(预热混淆) 与 C(对照反转)
B2: warmup 后扫观测强度 s, 用 held-out 准确率(不会像 d' 被平均人为放大)
C2: 诊断 C 的反转 —— 假设是 CPU 降频: sleep 让 CPU 空闲降频, 复测变慢
C3: 观测强度 k vs 系统读数漂移(真实)
"""
import os, time, json, statistics as st
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp164_measurement_limit"
os.makedirs(OUT, exist_ok=True)
R2 = {}


def workload(level):
    n = 60 if level == 0 else 180
    a = np.full((n, n), 1.0000001)
    b = np.full((n, n), 1.0000002)
    t0 = time.perf_counter_ns()
    c = a @ b
    return time.perf_counter_ns() - t0, c.sum()


def warmup(k=40):
    for i in range(k):
        workload(i % 2)


def acc_heldout(vals, labs, seed_bytes):
    vals = np.asarray(vals, float); labs = np.asarray(labs)
    rng = np.random.default_rng(int.from_bytes(seed_bytes, 'big'))
    idx = rng.permutation(len(vals)); ntr = len(idx)//2
    tr, te = idx[:ntr], idx[ntr:]
    m0 = vals[tr][labs[tr] == 0].mean(); m1 = vals[tr][labs[tr] == 1].mean()
    thr = (m0+m1)/2
    pred = (vals[te] > thr).astype(int) if m1 >= m0 else (vals[te] < thr).astype(int)
    acc = float((pred == labs[te]).mean())
    s0 = vals[te][labs[te] == 0]; s1 = vals[te][labs[te] == 1]
    if len(s0) < 2 or len(s1) < 2:
        return acc, 0.0
    sp = np.sqrt((s0.var(ddof=1)+s1.var(ddof=1))/2)
    d = float(abs(s1.mean()-s0.mean())/sp) if sp > 0 else 0.0
    return acc, d


def expB2(S=(1, 2, 4, 8, 16, 32), N=24):
    warmup()
    out = {}
    for s in S:
        vals = []; labs = []
        order = np.array([0, 1]*N, dtype=int)
        rng = np.random.default_rng(int.from_bytes(os.urandom(4), 'big'))
        rng.shuffle(order)
        t0 = time.perf_counter_ns()
        for lab in order:
            tot = 0.0
            for _ in range(s):
                dt, _ = workload(int(lab)); tot += dt
            vals.append(tot/s); labs.append(int(lab))
        t1 = time.perf_counter_ns()
        acc, d = acc_heldout(vals, labs, os.urandom(4))
        out[str(s)] = {"acc": acc, "dprime": d,
                       "cost_s": float((t1-t0)/1e9),
                       "mean0": float(np.mean([v for v, l in zip(vals, labs) if l == 0])),
                       "mean1": float(np.mean([v for v, l in zip(vals, labs) if l == 1]))}
    R2['B2'] = out
    return out


def expC2(reps=12):
    """降频诊断: sleep 后首次 vs 连续"""
    warmup()
    cont = []; after_sleep = []
    for _ in range(reps):
        # 连续
        a, _ = workload(0); b, _ = workload(0)
        cont.append((a+b)/2)
        # sleep 后首次
        time.sleep(0.05)
        c, _ = workload(0)
        after_sleep.append(c)
    res = {"cont_mean_ns": float(st.mean(cont)),
           "after_sleep_mean_ns": float(st.mean(after_sleep)),
           "ratio": float(st.mean(after_sleep)/st.mean(cont)),
           "cont_all": [float(x) for x in cont],
           "sleep_all": [float(x) for x in after_sleep]}
    R2['C2'] = res
    return res


def expC3(ks=(4, 16, 64, 256), reps=6, m=6):
    """观测强度 k vs 观测前后读数漂移"""
    warmup()
    out = {}
    for k in ks:
        deltas = []
        for _ in range(reps):
            v0 = sum(workload(0)[0] for _ in range(m))/m
            for _ in range(k):
                workload(1)
            v1 = sum(workload(0)[0] for _ in range(m))/m
            deltas.append(abs(v1-v0))
        out[str(k)] = {"delta_mean": float(st.mean(deltas)),
                       "delta_sd": float(st.pstdev(deltas)) if len(deltas) > 1 else 0.0}
    R2['C3'] = out
    return out


if __name__ == "__main__":
    b = expB2()
    print("B2 (warmup后) 观测强度 s -> held-out准确率 / d' / 代价:")
    for k, v in b.items():
        print("   s=%-3s acc=%.4f  d'=%.3f  代价=%.3fs  (mean0=%.0f mean1=%.0f ns)"
              % (k, v['acc'], v['dprime'], v['cost_s'], v['mean0'], v['mean1']))
    c2 = expC2()
    print("C2 降频诊断: 连续=%.0f ns  sleep后首次=%.0f ns  比值=%.3f"
          % (c2['cont_mean_ns'], c2['after_sleep_mean_ns'], c2['ratio']))
    c3 = expC3()
    print("C3 观测强度 k -> 观测前后读数漂移:")
    for k, v in c3.items():
        print("   k=%-4s delta=%.1f ns (sd %.1f)" % (k, v['delta_mean'], v['delta_sd']))
    with open(os.path.join(OUT, 'result164b.json'), 'w') as f:
        json.dump(R2, f, indent=1)
    print("saved")
