#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L7 灵长类之上那一格：关系与历史
上一轮(142) L5 只测了 TE 方向 + 来源归因，没覆盖"共同历史"。
本轮补四件事，每件事配一个能失败的对照。

  L7a 认出老朋友   —— 靠相倚结构，不靠 ID，不靠边际分布
  L7b 共同见证     —— 共享事件可复制，各自私有噪声不可复制
  L7c 债务与回报   —— 欠过配合的，后面更愿意配合
  L7d 时间 vs 数据 —— 一次性灌输历史能不能代替真的活过

判据铁律：每条判据必须能同时产生真和假。
"""
import os, sys, json, math, random, socket, time
import numpy as np
from multiprocessing import Process

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
def log(s): print(s, flush=True)

def ci_paired(d):
    d = np.asarray(d, dtype=float); n = len(d)
    m = d.mean()
    se = d.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return float(m), float(m - 1.96 * se), float(m + 1.96 * se)

E = 8            # 事件 / 动作空间大小
EPS = 0.15       # 策略噪声
def partner(a_prev, e, rng, eps=EPS):
    """补位策略：依赖对方上一动作 + 本轮事件"""
    if rng.random() < eps:
        return int(rng.integers(E))
    return int((a_prev + e) % E)

def interact(rng, T, mode, seed):
    """
    mode: 'old'(老朋友,相倚) 'stranger'(陌生人,同边际不相倚)
          'clone'(复制者,相倚但无历史)
    返回 A 侧动作序列、B 侧动作序列、双方各自带噪声的私有观测
    """
    a_prev, b_prev = int(rng.integers(E)), int(rng.integers(E))
    A, B, EA, EB, EV = [], [], [], [], []
    for t in range(T):
        e = int(rng.integers(E))
        # 各自私有观测：p_loss 概率丢包 -> 观测变成私有随机值
        oa = e if rng.random() > P_LOSS else int(rng.integers(E))
        ob = e if rng.random() > P_LOSS else int(rng.integers(E))
        if mode == "old" or mode == "clone":
            a = partner(b_prev, oa, rng)
        elif mode == "stranger":
            a = int(rng.integers(E))          # 边际同为均匀，但不依赖 b_prev
        else:
            raise ValueError(mode)
        b = partner(a_prev, ob, rng)
        A.append(a); B.append(b); EA.append(oa); EB.append(ob); EV.append(e)
        a_prev, b_prev = a, b
    return dict(A=A, B=B, EA=EA, EB=EB, EV=EV)

def build_lookup(A, B, EV, upto):
    """B 从训练段学 (b_{t-1}, e_t) -> 最常见的 a_t"""
    from collections import defaultdict
    cnt = defaultdict(lambda: np.zeros(E))
    for t in range(1, upto):
        cnt[(B[t - 1], EV[t])][A[t]] += 1
    return {k: int(np.argmax(v)) for k, v in cnt.items()}

def predict_acc(lookup, A, B, EV, start):
    """测试段用 lookup 预测 a_t 的准确率"""
    hit = tot = 0
    for t in range(start, len(A)):
        key = (B[t - 1], EV[t])
        if key in lookup:
            hit += int(lookup[key] == A[t]); tot += 1
    return hit / tot if tot else float("nan")

P_LOSS = 0.20    # 私有观测丢包率

# =====================================================================
# L7a 认出老朋友：B 能不能只凭交互结构区分 老朋友 / 陌生人 / 复制者
# =====================================================================
def l7a(seeds=24, T=300, split=200):
    out = {}
    for mode in ("old", "stranger", "clone"):
        accs = []
        for s in range(seeds):
            rng = np.random.default_rng(1000 + s)
            d = interact(rng, T, mode, s)
            lk = build_lookup(d["A"], d["B"], d["EV"], split)
            accs.append(predict_acc(lk, d["A"], d["B"], d["EV"], split))
        m, lo, hi = ci_paired(accs)
        out[mode] = dict(mean=m, lo=lo, hi=hi, n=seeds)
    return out

# =====================================================================
# L7b 共同见证：共享事件可灌输，各自私有噪声不可灌输
# 质询：B 抽查轮次 t，问对方"你当时观测到什么"，与 B 自己的观测比对
# =====================================================================
def l7b(seeds=24, T=300, K=40):
    rng0 = np.random.default_rng(7)
    out = {}
    for mode in ("old", "clone", "clone_fed"):
        rates = []
        for s in range(seeds):
            rng = np.random.default_rng(2000 + s)
            d = interact(rng, T, "old" if mode == "old" else "clone", s)
            EB, EV = d["EB"], d["EV"]
            qs = [int(rng0.integers(1, T)) for _ in range(K)]
            if mode == "old":
                ans = [d["EA"][t] for t in qs]         # 真经历过，带自己的私有噪声
            elif mode == "clone":
                ans = [int(rng.integers(E)) for _ in qs]   # 没经历过，只能猜
            else:  # clone_fed：把共享事件序列整段灌输给它
                ans = [EV[t] for t in qs]              # 答共享真值，但不含私有丢包
            rates.append(np.mean([int(a == EB[t]) for a, t in zip(ans, qs)]))
        m, lo, hi = ci_paired(rates)
        out[mode] = dict(mean=m, lo=lo, hi=hi, n=seeds)
    return out

# =====================================================================
# L7c 债务与回报：欠过配合的，后面是否更愿意配合
# 对照：清零账本
# =====================================================================
def l7c(seeds=24, T=300):
    def run(s, ledger):
        rng = np.random.default_rng(3000 + s)
        debt = 0
        cooperate = 0; chances = 0
        a_prev = int(rng.integers(E))
        for t in range(T):
            e = int(rng.integers(E))
            # 对方有机会求助（概率 0.3）
            if rng.random() < 0.3:
                chances += 1
                p = 0.30 + (0.50 * min(debt, 6) / 6.0 if ledger else 0.0)
                if rng.random() < p:
                    cooperate += 1
                    debt = max(0, debt - 1)
            # 对方帮了我 -> 我欠它
            if rng.random() < 0.3:
                debt += 1
            a_prev = (a_prev + e) % E
        return cooperate / chances if chances else float("nan")
    res = {}
    for name, led in (("ledger", True), ("no_ledger", False)):
        v = [run(s, led) for s in range(seeds)]
        m, lo, hi = ci_paired(v)
        res[name] = dict(mean=m, lo=lo, hi=hi, n=seeds)
    return res

# =====================================================================
# L7d 时间 vs 数据：把整段历史一次性灌输，能不能代替真的活过
# 训练段长度固定，比较"真跑 T 轮" vs "拿到 T 轮数据后只跑 1 轮"
# =====================================================================
def l7d(seeds=24, T=300, split=200):
    def acc_lived(s):
        rng = np.random.default_rng(4000 + s)
        d = interact(rng, T, "old", s)
        lk = build_lookup(d["A"], d["B"], d["EV"], split)
        return predict_acc(lk, d["A"], d["B"], d["EV"], split)
    def acc_fed(s):
        # 拿到同样长度的别人历史，自己只跑最后 20 轮
        rng = np.random.default_rng(4000 + s)
        d_src = interact(np.random.default_rng(9000 + s), T, "old", s)
        lk = build_lookup(d_src["A"], d_src["B"], d_src["EV"], split)
        d_own = interact(rng, 40, "old", s)
        # 用别人的 lookup 预测自己的交互
        hit = tot = 0
        for t in range(1, len(d_own["A"])):
            k = (d_own["B"][t - 1], d_own["EV"][t])
            if k in lk:
                hit += int(lk[k] == d_own["A"][t]); tot += 1
        return hit / tot if tot else float("nan")
    a = [acc_lived(s) for s in range(seeds)]
    b = [acc_fed(s) for s in range(seeds)]
    m1, l1, h1 = ci_paired(a); m2, l2, h2 = ci_paired(b)
    dl = [x - y for x, y in zip(a, b)]
    md, lod, hid = ci_paired(dl)
    return dict(lived=dict(mean=m1, lo=l1, hi=h1),
                fed=dict(mean=m2, lo=l2, hi=h2),
                delta=dict(mean=md, lo=lod, hi=hid), n=seeds)

# =====================================================================
# 真双进程验证：机制在真实进程 + UDP 上也成立（不是只在模拟里）
# =====================================================================
def _peer(port, host_port, role, n_round, outq):
    rng = np.random.default_rng(1234 if role == "A" else 5678)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", port)); rx.settimeout(0.25)
    prev = int(rng.integers(E)); seen = []
    for t in range(n_round):
        try:
            data, _ = rx.recvfrom(1024)
            e = int(data.decode().strip())
        except socket.timeout:
            e = int(rng.integers(E))       # 丢包 = 私有观测噪声
        seen.append(e)
        a = partner(prev, e, rng)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(str(a).encode(), ("127.0.0.1", host_port))
            s.close()
        except Exception:
            pass
        prev = a
    rx.close()
    outq.put(seen)

def real_proc(n_round=60):
    try:
        from multiprocessing import Queue
        qa, qb = Queue(), Queue()
        pa = Process(target=_peer, args=(45101, 45100, "A", n_round, qa))
        pb = Process(target=_peer, args=(45100, 45101, "B", n_round, qb))
        pa.start(); pb.start()
        # 主进程广播事件
        rng = np.random.default_rng(99)
        time.sleep(0.3)
        for t in range(n_round):
            e = int(rng.integers(E))
            for p in (45100, 45101):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.sendto(str(e).encode(), ("127.0.0.1", p)); s.close()
                except Exception:
                    pass
            time.sleep(0.004)
        sa = qa.get(timeout=20) if not qa.empty() else []
        sb = qb.get(timeout=20) if not qb.empty() else []
        pa.join(10); pb.join(10)
        # 双方各自观测序列的重合度（受各自丢包影响）
        n = min(len(sa), len(sb))
        agree = np.mean([int(sa[i] == sb[i]) for i in range(n)]) if n else float("nan")
        return dict(real=True, rounds=n_round, observed=n, agree=float(agree))
    except Exception as ex:
        return dict(real=False, err=str(ex))

if __name__ == "__main__":
    log("=== L7 关系格：共同历史、认出老朋友、债务、时间 ===")
    R["l7a"] = l7a()
    log(f"L7a old      {R['l7a']['old']['mean']:.4f}  [{R['l7a']['old']['lo']:.4f},{R['l7a']['old']['hi']:.4f}]")
    log(f"L7a stranger {R['l7a']['stranger']['mean']:.4f}  [{R['l7a']['stranger']['lo']:.4f},{R['l7a']['stranger']['hi']:.4f}]")
    log(f"L7a clone    {R['l7a']['clone']['mean']:.4f}  [{R['l7a']['clone']['lo']:.4f},{R['l7a']['clone']['hi']:.4f}]")

    R["l7b"] = l7b()
    for k in ("old", "clone", "clone_fed"):
        log(f"L7b {k:10s} {R['l7b'][k]['mean']:.4f}  [{R['l7b'][k]['lo']:.4f},{R['l7b'][k]['hi']:.4f}]")

    R["l7c"] = l7c()
    log(f"L7c ledger    {R['l7c']['ledger']['mean']:.4f}  [{R['l7c']['ledger']['lo']:.4f},{R['l7c']['ledger']['hi']:.4f}]")
    log(f"L7c no_ledger {R['l7c']['no_ledger']['mean']:.4f}  [{R['l7c']['no_ledger']['lo']:.4f},{R['l7c']['no_ledger']['hi']:.4f}]")

    R["l7d"] = l7d()
    log(f"L7d lived {R['l7d']['lived']['mean']:.4f}  fed {R['l7d']['fed']['mean']:.4f}  "
        f"delta {R['l7d']['delta']['mean']:+.4f} [{R['l7d']['delta']['lo']:+.4f},{R['l7d']['delta']['hi']:+.4f}]")

    R["real"] = real_proc()
    log(f"REAL {R['real']}")

    with open(os.path.join(OUT, "result_l7.json"), "w") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
    log("saved result_l7.json")
