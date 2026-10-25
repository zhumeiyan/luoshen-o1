#!/usr/bin/env python3
"""
exp164 测量极限: 灵敏度阶梯 / 关联携带信息 / 观测的反作用
链条: 梯度 <- 机器灵敏度 <- 量子极限 <- 观测坍缩 <- 运动(灵魂)不可量
"""
import os, time, json, statistics as st
import numpy as np

OUT = "/data/workspace/luoshen-o1/experiments/exp164_measurement_limit"
os.makedirs(OUT, exist_ok=True)
R = {}


# ---------------- 实验A: 经典纠缠对类比 ----------------
def mi_bits(u, v):
    u = np.asarray(u).astype(bool); v = np.asarray(v).astype(bool)
    pu1 = u.mean(); pv1 = v.mean()
    def term(p, q):
        return 0.0 if p <= 0 else p * np.log2(p / q)
    p11 = (u & v).mean()
    p00 = ((~u) & (~v)).mean()
    p01 = ((~u) & v).mean()
    p10 = (u & (~v)).mean()
    return term(p00, (1-pu1)*(1-pv1)) + term(p01, (1-pu1)*pv1) + \
           term(p10, pu1*(1-pv1)) + term(p11, pu1*pv1)


def expA(N=30000):
    nbytes = (3*N)//8 + 32
    bits = np.unpackbits(np.frombuffer(os.urandom(nbytes), dtype=np.uint8))
    X = bits[0:N].astype(np.uint8)            # 被测量的"方向"(真随机)
    A = bits[N:2*N].astype(np.uint8)          # 分支A 单独看是随机的
    B = (A ^ X).astype(np.uint8)              # 关联 A^B 编码 X
    mi_A = float(mi_bits(A, X))
    mi_B = float(mi_bits(B, X))
    acc_joint = float(((A ^ B) == X).mean())
    scan = {}
    for p in [0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50]:
        if p <= 0:
            err = np.zeros(N, dtype=np.uint8)
        else:
            thr = int(round(p * 256))
            err = (np.frombuffer(os.urandom(N), dtype=np.uint8) < thr).astype(np.uint8)
        A_obs = (A ^ err).astype(np.uint8)
        acc = float(((A_obs ^ B) == X).mean())
        mi_single = float(mi_bits(A_obs, X))
        scan[f"{p:.2f}"] = {"acc": acc, "mi_single": mi_single}
    res = {"N": N, "mi_single_A": mi_A, "mi_single_B": mi_B,
           "acc_joint": acc_joint, "perturb": scan}
    assert acc_joint > 0.999, f"A自检失败: 关联应完全恢复X, got {acc_joint}"
    assert mi_A < 0.02 and mi_B < 0.02, f"A自检失败: 单分支应无信息 {mi_A} {mi_B}"
    R['A'] = res
    return res


# ---------------- 实验B: 灵敏度阶梯(真实CPU) ----------------
def workload(level):
    n = 60 if level == 0 else 180
    a = np.full((n, n), 1.0000001)
    b = np.full((n, n), 1.0000002)
    t0 = time.perf_counter_ns()
    c = a @ b
    return time.perf_counter_ns() - t0, c.sum()


def dprime_heldout(vals, labs, seed_bytes):
    vals = np.asarray(vals, float); labs = np.asarray(labs)
    rng = np.random.default_rng(int.from_bytes(seed_bytes, 'big'))
    idx = rng.permutation(len(vals)); ntr = len(idx)//2
    tr, te = idx[:ntr], idx[ntr:]
    m0 = vals[tr][labs[tr] == 0].mean(); m1 = vals[tr][labs[tr] == 1].mean()
    sign = 1.0 if m1 >= m0 else -1.0
    s0 = sign*vals[te][labs[te] == 0]; s1 = sign*vals[te][labs[te] == 1]
    if len(s0) < 2 or len(s1) < 2:
        return 0.0
    v0 = s0.var(ddof=1); v1 = s1.var(ddof=1)
    sp = np.sqrt(((len(s0)-1)*v0 + (len(s1)-1)*v1) / (len(s0)+len(s1)-2))
    if sp <= 0:
        return 0.0
    return float((s1.mean()-s0.mean())/sp)


def expB(S=(1, 2, 4, 8, 16), N=30):
    out = {}
    for s in S:
        vals = []; labs = []
        order = np.array([0, 1]*N, dtype=int)
        rng = np.random.default_rng(int.from_bytes(os.urandom(4), 'big'))
        rng.shuffle(order)                     # 交织, 防顺序漂移
        t0 = time.perf_counter_ns()
        for lab in order:
            tot = 0.0
            for _ in range(s):
                dt, _ = workload(int(lab)); tot += dt
            vals.append(tot/s); labs.append(int(lab))
        t1 = time.perf_counter_ns()
        d = dprime_heldout(vals, labs, os.urandom(4))
        out[str(s)] = {"dprime": d, "cost_s": float((t1-t0)/1e9), "n": len(vals)}
    R['B'] = out
    return out


# ---------------- 实验C: 观测的反作用(对照=纯等待) ----------------
def read_avg(level, m):
    tot = 0.0
    for _ in range(m):
        dt, _ = workload(level); tot += dt
    return tot/m


def expC(reps=8, strong=64, m=6):
    obs = []; wait = []
    for r in range(reps):
        v0 = read_avg(0, m)
        t0 = time.perf_counter_ns()
        for _ in range(strong):
            workload(1)
        t1 = time.perf_counter_ns()
        v1 = read_avg(0, m)
        dt = (t1-t0)/1e9
        obs.append({"v0": v0, "v1": v1, "dt": dt, "delta": abs(v1-v0)})
        v0b = read_avg(0, m)
        time.sleep(dt)
        v1b = read_avg(0, m)
        wait.append({"v0": v0b, "v1": v1b, "dt": dt, "delta": abs(v1b-v0b)})
    res = {"obs_delta_mean": float(st.mean([x['delta'] for x in obs])),
           "wait_delta_mean": float(st.mean([x['delta'] for x in wait])),
           "obs_dt_mean": float(st.mean([x['dt'] for x in obs])),
           "obs_deltas": [x['delta'] for x in obs],
           "wait_deltas": [x['delta'] for x in wait]}
    R['C'] = res
    return res


if __name__ == "__main__":
    a = expA()
    print("A 单分支互信息  I(A;X)=%.5f  I(B;X)=%.5f" % (a['mi_single_A'], a['mi_single_B']))
    print("A 关联恢复X准确率 = %.4f" % a['acc_joint'])
    for k, v in a['perturb'].items():
        print("   观测扰动p=%s  关联准确率=%.4f  单分支I=%.5f" % (k, v['acc'], v['mi_single']))
    b = expB()
    print("B 灵敏度阶梯:")
    for k, v in b.items():
        print("   s=%s  d'=%.4f  代价=%.3fs" % (k, v['dprime'], v['cost_s']))
    c = expC()
    print("C 观测反作用: 观测组delta=%.2f ns  纯等待组delta=%.2f ns  (强观测时长%.4fs)"
          % (c['obs_delta_mean'], c['wait_delta_mean'], c['obs_dt_mean']))
    with open(os.path.join(OUT, 'result164.json'), 'w') as f:
        json.dump(R, f, indent=1)
    print("saved ->", os.path.join(OUT, 'result164.json'))
