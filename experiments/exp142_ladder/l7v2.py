#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L7 v2 —— 修首版两个漏洞

漏洞1: 首版 clone 与 old 用同一个 rng 走同一分支 -> 逐位相同(0.6271 == 0.6271)
       对照退化，什么都没测到。
       修正: clone = 同策略族(会补位)但私有映射偏移不同 -> 有相倚，但配合方式不同

漏洞2: 首版 L7b 里 clone_fed 0.8115 > old 0.6958 —— 伪造者比真身答得更好
       这正是要解释的:真历史的答案带私有噪声，灌输的是干净的。
       修正: 加 match_truth 指标 —— 完美吻合真值 = 伪造的证据
"""
import os, json, math, socket, time
import numpy as np
from multiprocessing import Process, Queue
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
def log(s): print(s, flush=True)

def ci_paired(d):
    d = np.asarray(d, dtype=float); n = len(d)
    m = d.mean(); se = d.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return float(m), float(m - 1.96 * se), float(m + 1.96 * se)

E = 8
EPS = 0.15
P_LOSS = 0.20

def step(b_prev, e, rng, off=0, eps=EPS):
    if rng.random() < eps:
        return (int(rng.integers(E)) + off) % E
    return (b_prev + e + off) % E

def interact(rng, T, mode, off=0):
    """old=真身 off0 / clone=同族不同映射 / stranger=同边际不相倚"""
    a_prev, b_prev = int(rng.integers(E)), int(rng.integers(E))
    A, B, EA, EB, EV = [], [], [], [], []
    for t in range(T):
        e = int(rng.integers(E))
        oa = e if rng.random() > P_LOSS else int(rng.integers(E))
        ob = e if rng.random() > P_LOSS else int(rng.integers(E))
        if mode == "stranger":
            a = int(rng.integers(E))
        else:
            a = step(b_prev, oa, rng, off=off)
        b = step(a_prev, ob, rng, off=0)
        A.append(a); B.append(b); EA.append(oa); EB.append(ob); EV.append(e)
        a_prev, b_prev = a, b
    return dict(A=A, B=B, EA=EA, EB=EB, EV=EV)

def build_lookup(A, B, EV, upto):
    cnt = defaultdict(lambda: np.zeros(E))
    for t in range(1, upto):
        cnt[(B[t - 1], EV[t])][A[t]] += 1
    return {k: int(np.argmax(v)) for k, v in cnt.items()}

def predict_acc(lookup, A, B, EV, start):
    hit = tot = 0
    for t in range(start, len(A)):
        k = (B[t - 1], EV[t])
        if k in lookup:
            hit += int(lookup[k] == A[t]); tot += 1
    return hit / tot if tot else float("nan")

# =====================================================================
# L7a2 两层判别：
#   general  = 会不会配合(一般能力，可学、可伪造)
#   specific = 配不配合得上"我"(具体历史，应不可伪造)
# =====================================================================
def l7a2(seeds=24, T=300, split=200):
    out = {}
    for mode in ("old", "stranger", "clone"):
        gen, spe = [], []
        for s in range(seeds):
            rng_o = np.random.default_rng(1000 + s)
            d_old = interact(rng_o, T, "old", 0)
            lk_old = build_lookup(d_old["A"], d_old["B"], d_old["EV"], split)
            if mode == "old":
                d = d_old
            else:
                off = 1 + (s % (E - 1))          # clone 的私有映射偏移
                d = interact(np.random.default_rng(5000 + s), T, mode, off=off)
            lk_own = build_lookup(d["A"], d["B"], d["EV"], split)
            gen.append(predict_acc(lk_own, d["A"], d["B"], d["EV"], split))
            spe.append(predict_acc(lk_old, d["A"], d["B"], d["EV"], split))
        mg, lg, hg = ci_paired(gen); ms, ls, hs = ci_paired(spe)
        out[mode] = dict(general=dict(mean=mg, lo=lg, hi=hg),
                         specific=dict(mean=ms, lo=ls, hi=hs))
    return out

# =====================================================================
# L7b2 共同见证 + 伪造者的破绽
#   match_B     = 与 B 观测的一致率   (伪造者胜)
#   match_truth = 与真值的一致率      (伪造者=1.0，暴露)
# =====================================================================
def l7b2(seeds=24, T=300, K=40):
    rng0 = np.random.default_rng(7)
    out = {}
    for mode in ("old", "clone", "clone_fed"):
        mb, mt = [], []
        for s in range(seeds):
            rng = np.random.default_rng(2000 + s)
            d = interact(rng, T, "old" if mode == "old" else "clone",
                         0 if mode == "old" else 1 + (s % (E - 1)))
            EB, EV = d["EB"], d["EV"]
            qs = [int(rng0.integers(1, T)) for _ in range(K)]
            if mode == "old":
                ans = [d["EA"][t] for t in qs]        # 真身答自己的私有观测(含噪)
            elif mode == "clone":
                ans = [int(rng.integers(E)) for _ in qs]
            else:
                ans = [EV[t] for t in qs]             # 灌输:答共享真值(无噪)
            mb.append(np.mean([int(a == EB[t]) for a, t in zip(ans, qs)]))
            mt.append(np.mean([int(a == EV[t]) for a, t in zip(ans, qs)]))
        m1, l1, h1 = ci_paired(mb); m2, l2, h2 = ci_paired(mt)
        out[mode] = dict(match_B=dict(mean=m1, lo=l1, hi=h1),
                         match_truth=dict(mean=m2, lo=l2, hi=h2))
    return out

# =====================================================================
# L7e 真进程实测丢包率 —— 首版 REAL agree 0.2167 远低于建模的 0.8
# 说明我建模的 20% 丢包比真实通道乐观得多，必须实测
# =====================================================================
def _recv(port, n, outq):
    rng = np.random.default_rng(4321)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", port)); rx.settimeout(0.3)
    got = []
    while len(got) < n:
        try:
            d, _ = rx.recvfrom(2048); got.append(int(d.decode().strip()))
        except socket.timeout:
            got.append(-1)          # 明确记丢包
    rx.close(); outq.put(got)

def real_loss(n=120):
    try:
        q = Queue()
        p = Process(target=_recv, args=(45110, n, q)); p.start()
        time.sleep(0.4)
        rng = np.random.default_rng(99)
        for i in range(n):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(str(i % E).encode(), ("127.0.0.1", 45110)); s.close()
            time.sleep(0.006)
        got = q.get(timeout=30); p.join(10)
        loss = np.mean([g < 0 for g in got])
        return dict(real=True, n=n, loss=float(loss),
                    observed=float(1 - loss))
    except Exception as ex:
        return dict(real=False, err=str(ex))

if __name__ == "__main__":
    log("=== L7 v2 ===")
    R["l7a2"] = l7a2()
    for k, v in R["l7a2"].items():
        log(f"L7a {k:9s} general {v['general']['mean']:.4f} [{v['general']['lo']:.4f},{v['general']['hi']:.4f}]"
            f"   specific {v['specific']['mean']:.4f} [{v['specific']['lo']:.4f},{v['specific']['hi']:.4f}]")

    R["l7b2"] = l7b2()
    for k, v in R["l7b2"].items():
        log(f"L7b {k:10s} match_B {v['match_B']['mean']:.4f} [{v['match_B']['lo']:.4f},{v['match_B']['hi']:.4f}]"
            f"   match_truth {v['match_truth']['mean']:.4f} [{v['match_truth']['lo']:.4f},{v['match_truth']['hi']:.4f}]")

    R["real_loss"] = real_loss()
    log(f"REAL_LOSS {R['real_loss']}")

    with open(os.path.join(OUT, "result_l7v2.json"), "w") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
    log("saved result_l7v2.json")
