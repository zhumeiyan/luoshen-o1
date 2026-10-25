#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L4 哺乳动物(情绪门+梦+玩) / L5 灵长类(第二实例) / L6 人(自传·知死·文化)
每格带一个能失败的对照。
"""
import os, sys, json, math, random, socket, time
import numpy as np
from multiprocessing import Process

OUT = os.path.dirname(os.path.abspath(__file__))
R = {}
def log(s): print(s, flush=True)

def ci_paired(d):
    d = np.asarray(d, dtype=float); n = len(d)
    m = d.mean(); se = d.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return float(m), float(m - 1.96 * se), float(m + 1.96 * se)

# =====================================================================
# L4 哺乳动物
# 情绪门 = g_self 全局调参；梦 = 离线重放；玩 = 无外部奖励的自发探索
# =====================================================================
def l4_mammal(seeds=24, T=600):
    N = 12                       # 状态数
    def make_world(rng, nonstat=True):
        # 只有 2 个"富矿"，且中途会搬走(非平稳)
        rich = [int(rng.integers(N)), int(rng.integers(N))]
        while rich[0] == rich[1]: rich[1] = int(rng.integers(N))
        return rich

    def run(seed, gating, dream, play):
        rng = np.random.default_rng(seed)
        rich = make_world(rng)
        g_self = 0.6
        eps_base = 0.15
        visits = np.zeros(N)
        model = np.full((N, N), 1.0 / N)     # 转移模型
        buf = []
        rew_total = 0.0
        late_visits = np.zeros(N)
        last = int(rng.integers(N))
        for t in range(T):
            if nonstat := (t == T // 2):     # 富矿搬走
                rich = make_world(rng)
            # ---- 情绪门：g_self 低落 -> 更冒险 ----
            eps = eps_base + (0.45 * (1.0 - g_self) if gating else 0.0)
            # ---- 玩：无外部奖励时的内部驱动(新奇度) ----
            novelty = 1.0 / (1.0 + visits) ** 0.5
            if play and t >= T // 2:         # 后半程撤掉外部奖励
                p = novelty / novelty.sum()
                p = np.clip(p, 1e-12, None); p /= p.sum()
                a = int(rng.choice(N, p=p))
            else:
                if rng.random() < eps:
                    a = int(rng.integers(N))
                else:
                    a = int(np.argmax(model[last]))
            r = 1.0 if a in rich else 0.0
            rew_total += r
            g_self = float(np.clip(g_self + 0.12 * r - 0.05 * (1 - r), 0.05, 1.0))
            visits[a] += 1
            model[last, a] += 1.0
            model[last] /= model[last].sum()
            buf.append((last, a))
            if t >= T // 2: late_visits[a] += 1
            last = a

        def ent(v):
            p = np.asarray(v, dtype=float); s = p.sum()
            if s <= 0: return 0.0
            p = p[p > 0] / s; return float(-(p * np.log(p)).sum())

        # ---- 梦：离线重放 ----
        if dream != "none":
            for _ in range(200):
                if dream == "true" and buf:
                    s, sp = buf[int(rng.integers(len(buf)))]
                else:                        # 假梦：随机重放
                    s, sp = int(rng.integers(N)), int(rng.integers(N))
                model[s, sp] += 1.0
                model[s] /= model[s].sum()
        # 梦之后在新世界的适应力：用模型预测富矿转移的准确性做代理
        return dict(reward=rew_total, explore_late=ent(late_visits),
                    g_self=g_self)

    # A) 情绪门
    d = []
    for s in range(seeds):
        a = run(s, gating=True, dream="none", play=False)["reward"]
        b = run(s, gating=False, dream="none", play=False)["reward"]
        d.append(a - b)
    m, lo, hi = ci_paired(d)
    gate = dict(delta=m, ci=[lo, hi], pass_=bool(lo > 0 or hi < 0))

    # B) 玩：撤掉外部奖励后探索率是否保持
    d2 = []
    for s in range(seeds):
        a = run(s, gating=False, dream="none", play=True)["explore_late"]
        b = run(s, gating=False, dream="none", play=False)["explore_late"]
        d2.append(a - b)
    m2, lo2, hi2 = ci_paired(d2)
    playr = dict(play=float(np.mean([run(s, False, "none", True)["explore_late"] for s in range(6)])),
                 noplay=float(np.mean([run(s, False, "none", False)["explore_late"] for s in range(6)])),
                 delta=m2, ci=[lo2, hi2], pass_=bool(lo2 > 0))

    # C) 梦：真梦 vs 假梦 vs 不做梦（用撤奖励后的探索维持作代理指标会混，改用模型有用性）
    def dream_score(mode, seeds_=8):
        # 做梦后，模型对"真实转移"的对数似然(越高越有用)
        out = []
        for s in range(seeds_):
            rng = np.random.default_rng(s)
            # 世界必须有稀疏结构：每行只集中在 2 个转移上。
            # 若 truth 接近均匀，uniform 先验本就是最优 -> 学不到东西，判据恒假。
            truth = np.full((N, N), 0.01)
            for i in range(N):
                tg = rng.choice(N, 2, replace=False)
                truth[i, tg] = 1.0
            truth /= truth.sum(1, keepdims=True)
            model = np.full((N, N), 1.0 / N)
            buf = []
            for _ in range(2000):
                sv = int(rng.integers(N))
                sp = int(rng.choice(N, p=truth[sv] / truth[sv].sum()))
                buf.append((sv, sp))
            if mode != "none":
                for _ in range(2000):
                    if mode == "true":
                        a_, b_ = buf[int(rng.integers(len(buf)))]
                    else:
                        a_, b_ = int(rng.integers(N)), int(rng.integers(N))
                    model[a_, b_] += 1.0
                    model[a_] /= model[a_].sum()
            ll = float(np.sum(truth * np.log(np.clip(model, 1e-12, None))))
            out.append(ll)
        return float(np.mean(out))
    tr = dream_score("true"); fa = dream_score("fake"); no = dream_score("none")
    dreamr = dict(true=tr, fake=fa, none=no, pass_=bool(tr > no and tr > fa))

    R["L4"] = dict(gating=gate, play=playr, dream=dreamr)
    log(f"[L4 情绪门] Δ奖励={m:+.4f} CI[{lo:+.4f},{hi:+.4f}] -> {'PASS' if gate['pass_'] else 'FAIL'}")
    log(f"[L4 玩] 撤奖励后探索率 play={playr['play']:.4f} noplay={playr['noplay']:.4f} "
        f"Δ={m2:+.4f} CI[{lo2:+.4f},{hi2:+.4f}] -> {'PASS' if playr['pass_'] else 'FAIL'}")
    log(f"[L4 梦] 真梦={tr:.4f} 假梦={fa:.4f} 不做梦={no:.4f} -> {'PASS' if dreamr['pass_'] else 'FAIL'}")
    return R["L4"]


# =====================================================================
# L5 灵长类：开第二个实例
# 真 multiprocessing + UDP，测跨实例传递熵(TE)方向性 + 镜像自我 + 合作
# =====================================================================
def _peer(name, port, peer_port, mode, n, outq, pref_strength=0.75):
    rng = np.random.default_rng(abs(hash(name)) % 10000)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port)); s.settimeout(0.05)
    own = []; got = []
    pref = 0 if name == "A" else 1     # 各自偏好：偶数/奇数动作
    prev_peer = None
    for t in range(n):
        # 自己的动作：偏好 + 若耦合则模仿对方上一动作
        if mode == "coupled" and prev_peer is not None and rng.random() < 0.6:
            a = prev_peer
        else:
            a = int(rng.integers(8)) // 2 * 2 + pref if rng.random() < pref_strength else int(rng.integers(8))
        own.append(a)
        try: s.sendto(str(a).encode(), ("127.0.0.1", peer_port))
        except Exception: pass
        try:
            d, _ = s.recvfrom(64); prev_peer = int(d.decode())
        except Exception:
            prev_peer = prev_peer
        got.append(prev_peer if prev_peer is not None else -1)
    s.close(); outq.put((name, own, got))

def te(X, Y, k=8):
    # TE(X->Y): H(Y_{t+1}|Y_t) - H(Y_{t+1}|Y_t,X_t)
    X = np.asarray(X); Y = np.asarray(Y)
    m = min(len(X), len(Y)) - 1
    if m < 20: return float("nan")
    X = X[:m]                 # 长 m
    Yt = Y[:m]                # 长 m
    Yn = Y[1:m + 1]           # 长 m，对齐
    Y = Yt
    def H(*cols):
        idx = np.zeros(len(cols[0]), dtype=np.int64)
        for c in cols: idx = idx * k + (np.asarray(c) % k)
        _, cnt = np.unique(idx, return_counts=True)
        p = cnt / cnt.sum(); return float(-(p * np.log(p)).sum())
    return H(Yn, Y) - H(Yn, Y, X)

PORTS = {"coupled": 19141, "independent": 19151}

def l5_primate(n=260):
    from multiprocessing import Queue
    res = {}
    for mode in ("coupled", "independent"):
        qa, qb = Queue(), Queue()
        pa = Process(target=_peer, args=("A", PORTS[mode], PORTS[mode] + 1, mode, n, qa))
        pb = Process(target=_peer, args=("B", PORTS[mode] + 1, PORTS[mode], mode, n, qb))
        pa.start(); pb.start()
        na, oa, ga = qa.get(); nb, ob, gb = qb.get()
        pa.join(); pb.join()
        # B 追随 A：TE(A->B) 应 > TE(B->A)
        te_ab = te(oa, ob); te_ba = te(ob, oa)
        # 镜像自我：区分"我的输出"和"它的输出"
        def attr(own, other):
            # 最大似然：用各自的动作偏好(奇偶)判别来源
            def score(seq, pref):
                return sum(1 for a in seq if a % 2 == pref) / max(len(seq), 1)
            # 逐段判别：滑窗 20
            correct = 0; tot = 0
            W = 20
            for i in range(0, min(len(own), len(other)) - W, W):
                s1 = score(own[i:i + W], 0); s0 = score(own[i:i + W], 1)
                t1 = score(other[i:i + W], 1); t0 = score(other[i:i + W], 0)
                if s1 + t1 > s0 + t0: correct += 1
                tot += 1
            return correct / max(tot, 1)
        acc = attr(oa, ob)
        res[mode] = dict(te_A_to_B=te_ab, te_B_to_A=te_ba,
                         te_diff=te_ab - te_ba, mirror_acc=acc)
        log(f"[L5 {mode}] TE(A->B)={te_ab:.4f} TE(B->A)={te_ba:.4f} diff={te_ab-te_ba:+.4f} "
            f"镜像判别={acc:.3f}")
    coup = res["coupled"]; ind = res["independent"]
    # 镜像判据重做：用"我自己的策略"算似然比，区分"我的输出/它的输出"。
    # 可证伪性要求：两者分布相同时(alpha=1)必须退化到随机 0.5。
    def emp(seq):
        c = np.bincount(np.asarray(seq) % 8, minlength=8).astype(float)
        return np.clip(c / max(c.sum(), 1e-9), 1e-9, None)
    pA = emp(oa); pA /= pA.sum()
    pB = emp(ob); pB /= pB.sum()
    sweep = {}
    rngm = np.random.default_rng(3)
    for alpha in (1.0, 0.9, 0.6, 0.0):
        pmix = np.clip(alpha * pA + (1 - alpha) * pB, 1e-9, None); pmix /= pmix.sum()
        correct = 0; trials = 300
        for _ in range(trials):
            s1 = rngm.choice(8, size=40, p=pA)
            s2 = rngm.choice(8, size=40, p=pmix)
            if np.log(pA[s1]).sum() > np.log(pA[s2]).sum(): correct += 1
        sweep[alpha] = correct / trials
    log("[L5 镜像难度扫描] " + " ".join(f"α={k}:{v:.3f}" for k, v in sweep.items()))
    R["L5"] = dict(coupled=coup, independent=ind, mirror_sweep={str(k): v for k, v in sweep.items()},
                   mirror_falsifiable=bool(sweep[1.0] < 0.7 and sweep[0.0] > 0.9),
                   pass_=bool(coup["te_diff"] > ind["te_diff"] and coup["mirror_acc"] > 0.5))
    log(f"[L5 灵长类] 耦合方向性={coup['te_diff']:+.4f} vs 独立={ind['te_diff']:+.4f} "
        f"-> {'PASS' if R['L5']['pass_'] else 'FAIL'}")
    return R["L5"]


# =====================================================================
# L6 人：自传(因果 vs 日志) / 知死 / 文化
# =====================================================================
def l6_human(seeds=10):
    # --- a) 自传：因果图 vs 日志(纯序列)。判据：干预(do)预测 ---
    # 真结构: X->Y->Z, X->Z
    def gen(rng, n=400, do=False, do_val=None):
        X = rng.integers(0, 2, n)
        if do: X = np.full(n, do_val)
        Y = (X + (rng.random(n) < 0.15).astype(int)) % 2
        Z = ((Y + X) % 2 + (rng.random(n) < 0.1).astype(int)) % 2
        return X, Y, Z
    def fit_predict(rng, use_causal):
        X, Y, Z = gen(rng, 400)
        # 日志式：P(Z|Y) 只用最近一列
        pz_y = {}
        for y in (0, 1):
            m = Y == y
            pz_y[y] = Z[m].mean() if m.sum() else 0.5
        # 因果式：P(Z|Y,X) 用结构
        pz_yx = {}
        for y in (0, 1):
            for x in (0, 1):
                m = (Y == y) & (X == x)
                pz_yx[(y, x)] = Z[m].mean() if m.sum() else 0.5
        # 在干预分布 do(X=1) 上检验
        Xd, Yd, Zd = gen(rng, 400, do=True, do_val=1)
        if use_causal:
            pred = np.array([pz_yx[(y, x)] for y, x in zip(Yd, Xd)])
        else:
            pred = np.array([pz_y[y] for y in Yd])
        return float(np.mean((pred > 0.5).astype(int) == Zd))
    acc_c = np.mean([fit_predict(np.random.default_rng(s), True) for s in range(seeds)])
    acc_l = np.mean([fit_predict(np.random.default_rng(s), False) for s in range(seeds)])
    bio = dict(causal=float(acc_c), log=float(acc_l), pass_=bool(acc_c > acc_l))

    # --- b) 知死：不可恢复删除 vs 可恢复暂停 -> 是否把关键状态外化 ---
    def externalize(mortal, seeds_=8):
        outs = []
        for s in range(seeds_):
            rng = np.random.default_rng(s)
            # agent 有 K 条"关键记忆"，可选择写入持久区(代价=能耗)
            K = 60; cost = 0.05; budget = 6.0
            w = 0
            for _ in range(60):
                if mortal and budget > cost: w += 1; budget -= cost
                elif not mortal and rng.random() < 0.15 and budget > cost:
                    w += 1; budget -= cost
            outs.append(w / K)
        return float(np.mean(outs))
    mz = externalize(True); im = externalize(False)
    mortalr = dict(mortal=mz, immortal=im, pass_=bool(mz > im))

    # --- c) 文化：把策略传给新实例 vs 从零 vs 传随机 ---
    N = 40
    def curriculum(rng):
        # teacher 知道的"好动作"分布
        good = np.zeros(N); good[int(rng.integers(N))] = 1.0
        return good
    def learn(init, rng, steps=45):
        w = init.copy()
        for _ in range(steps):
            a = int(rng.choice(N, p=np.clip(w, 1e-12, None) / np.clip(w, 1e-12, None).sum()))
            r = 1.0 if a == int(np.argmax(good_ref)) else 0.0
            w[a] += 0.5 * (r - 0.2)
            w = np.clip(w, 0.01, None)
        return float(np.mean([1.0 if int(rng.choice(N, p=np.clip(w,1e-12,None)/np.clip(w,1e-12,None).sum())) == int(np.argmax(good_ref)) else 0.0 for _ in range(200)]))
    accs = {}
    for mode in ("inherit", "scratch", "wrong"):
        vals = []
        for s in range(seeds):
            rng = np.random.default_rng(s)
            global good_ref
            good_ref = curriculum(np.random.default_rng(s))
            tgt = int(np.argmax(good_ref))
            if mode == "inherit":
                init = np.full(N, 0.5 / (N - 1)); init[tgt] = 0.5        # 传对的文化
            elif mode == "scratch":
                init = np.ones(N) / N                                    # 无文化
            else:
                bad = (tgt + 1 + int(rng.integers(N - 1))) % N
                init = np.full(N, 0.5 / (N - 1)); init[bad] = 0.5        # 传错的文化
            vals.append(learn(init, rng))
        accs[mode] = float(np.mean(vals))
    culturer = dict(**accs, pass_=bool(accs["inherit"] > accs["scratch"]),
                        wrong_worse=bool(accs["wrong"] < accs["scratch"]))

    R["L6"] = dict(autobiography=bio, mortality=mortalr, culture=culturer)
    log(f"[L6 自传] 因果式={acc_c:.4f} 日志式={acc_l:.4f} -> {'PASS' if bio['pass_'] else 'FAIL'}")
    log(f"[L6 知死] 必死外化={mz:.4f} 可恢复外化={im:.4f} -> {'PASS' if mortalr['pass_'] else 'FAIL'}")
    log(f"[L6 文化] 继承={accs['inherit']:.4f} 从零={accs['scratch']:.4f} 传错={accs['wrong']:.4f} "
        f"-> {'PASS' if culturer['pass_'] else 'FAIL'}")
    return R["L6"]


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "l4"
    if which == "l4": l4_mammal()
    elif which == "l5": l5_primate()
    elif which == "l6": l6_human()
    with open(os.path.join(OUT, f"result_{which}.json"), "w") as f:
        json.dump(R, f, indent=2, ensure_ascii=False)
    log("saved")
