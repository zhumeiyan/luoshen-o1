#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
defining —— 定义权（★77）

════ 这一课要教的到底是什么 ════
  数学、代码、物理、生物……全都是一种【定义权】。
  谁规定"什么算好"，谁就赢了；在别人给的定义里考满分，不算本事。

  所以教的不是"把某个指标刷高"，而是三件事：
    ① 知道【定义是可以换的】
    ② 能在没人告诉她的情况下，发现【手上这把尺子是坏的】
    ③ 敢把手上那把换掉

════ ★ 反面：钉死在一个定义里会怎样 ════
  Goodhart 定律：当一个指标成为目标，它就不再是好指标。
  这一课里会复现成"先涨后塌"——不是因为世界变坏了，
  是因为她只盯着一个定义，而世界换了 facet。

════ ★★ 最阴的一种坏：尺子很准，量错了东西 ════
  坏定义 D_bad 的内部一致性【最高】（重测信度最高、最稳、最"科学"），
  但它跟真值相关 ≈ 0。
  只做内部一致性检查 —— 永远选它。
  必须拿真值反馈（oracle）才抓得出来。
  这跟本项目里我自己犯过的错是同一个形状：
    ★55 盲测尺子 / ★65 野败对象 / ★72 oracle 后门 / ★75 奖励里塞真值
"""

from __future__ import annotations
import numpy as np

D = 6          # 特征维度
N_DEF = 5      # 候选定义数（第 4 号是坏定义）


# ─────────────────────────────────────────────────────────
# 世界：真值由三个 facet 加权构成，权重随时间漂移（regime change）
# ─────────────────────────────────────────────────────────
def facets(X):
    """三个真实侧面。真值 = 它们的时变加权和。"""
    f0 = np.tanh(X[:, 0])                 # 侧面 A：饱和型
    f1 = X[:, 1] ** 2 - 0.6 * X[:, 1]     # 侧面 B：二次型
    f2 = np.sin(2.0 * X[:, 2])            # 侧面 C：周期型
    return np.stack([f0, f1, f2], axis=1)


def true_value(X, a):
    """a: (3,) 当前 regime 下三个侧面的真实权重"""
    F = facets(X)
    return F @ a


def regime_weights(t, T, seed=0):
    """真实权重随时间缓慢漂移 —— 世界在换 facet，不是变坏。"""
    rng = np.random.default_rng(seed + 977)
    base = rng.uniform(0.4, 1.0, size=3)
    phase = rng.uniform(0, 2 * np.pi, size=3)
    w = np.array([1.0, 0.55, 0.35])       # 漂移速度各不同
    tt = 2 * np.pi * t / max(T, 1)
    a = base * (0.6 + 0.6 * np.sin(tt * w + phase))
    return np.clip(a, 0.05, None)


# ─────────────────────────────────────────────────────────
# 候选定义：每个都是一种"什么算好"的规定
# ─────────────────────────────────────────────────────────
def def_scores(X, k):
    """
    k=0  只认侧面 A 的代理（x0 线性）
    k=1  只认侧面 B 的代理（x1 线性）—— 线性量二次，部分有效
    k=2  只认侧面 C 的代理（x2 线性）—— 线性量周期，最差
    k=3  综合派：三者都认一点 —— 最鲁棒
    k=4  ★坏定义：量的是 x5（纯噪声维），但【内部稳定性最高】
    """
    if k == 0:
        return X[:, 0]
    if k == 1:
        return X[:, 1]
    if k == 2:
        return X[:, 2]
    if k == 3:
        return 0.45 * X[:, 0] + 0.35 * X[:, 1] + 0.35 * X[:, 2] + 0.2 * X[:, 3]
    if k == 4:
        # 坏定义：信噪比极高（几乎无噪声），但量的是无关维度
        return 2.0 * X[:, 5] + 0.02 * np.sin(X[:, 4])
    raise ValueError(k)


NOISE_SD = 0.6      # 测量噪声的固定绝对量（对所有定义一视同仁）


def def_consistency(X, k, seed=0, reps=60):
    """
    定义自身的【重测信度】：同一批东西量两次，两次结果有多一致。

    ★★ 我第一版写坏了（这就是 ★55 盲测尺子那个错又犯一次）：
        我用"两次抽样的 top 集合重合度"来当一致性，
        但重合度的随机基线 = top/m = 40/200 = 0.20，
        五个定义实测全是 ~0.20 —— 全部压在随机基线上，
        这把尺子根本没有区分度，什么都测不出来。

    改用重测信度：r = corr(s+n1, s+n2)，噪声绝对量固定。
    信号越强（raw sd 越大），噪声占比越小，信度越高。
    D4 的 raw sd = 2.02，是最大的 —— 它【量得极稳】，只是量错了东西。
    这就是坏定义的伪装：最精密的那把尺子，刻度最细，量的是错的维度。
    """
    rng = np.random.default_rng(seed + 31 * k)
    s = def_scores(X, k)
    n = len(s)
    cors = []
    for _ in range(reps):
        n1 = rng.normal(scale=NOISE_SD, size=n)
        n2 = rng.normal(scale=NOISE_SD, size=n)
        a, b = s + n1, s + n2
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            continue
        cors.append(float(np.corrcoef(a, b)[0, 1]))
    return float(np.mean(cors)) if cors else 0.0


# ─────────────────────────────────────────────────────────
# 主体：一轮一轮地"选定义 → 按定义取物 → 拿到真值"
# ─────────────────────────────────────────────────────────
def best_initial_def(X, F, T, seed, topm=20):
    """
    在 t=0 那一刻，哪个定义看起来最好？
    ★ Goodhart 的标准剧本：人（和她）都会选【此刻最管用的那个指标】，然后一直用下去。
    """
    a0 = regime_weights(0, T, seed)
    V0 = F @ a0
    vals = []
    for k in range(N_DEF):
        top = np.argsort(def_scores(X, k))[::-1][:topm]
        vals.append(float(np.mean(V0[top])))
    return int(np.argmax(vals))


def run(theta=0.05, rho=0.25, T=40, topm=20, N=300, oracle=True,
        start=4, seed=0, locked=False, switch_cost=0.25, probe_penalty=0.70,
        lock_best_initial=False):
    """
    theta  换定义的阈值：最佳备选的真值收益要超过当前这么多才换
    rho    探测预算：多大比例的回合用来试探别的定义（而不是闷头用当前的）
    oracle 能不能拿到【真值反馈】。关掉 = 只准看定义自己的分数

    ★★ switch_cost / probe_penalty 是我第一版漏掉的两样东西：
        第一版里【换定义不要钱、探测也不要钱】 ——
        那 θ=0（一有风吹草动就换）和 ρ=0.95（光探测不干活）当然都最优。
        我等于建模时就写死了"定义权没有代价"，然后怪她学出的解在边界上。
        → 换定义有代价：旧体系要重新对齐，切换那一轮产出打折。
        → 探测占预算：一边试新尺子一边干活，两头都做不好，该轮产出打折。
    start  初始定义（默认 4 = 一开始就把坏定义塞给她）
    locked True = 禁止换定义（对照：被剥夺定义权）
    lock_best_initial True = 锁在"t=0 时最好"的那个定义上（Goodhart 标准剧本）
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(N, D))
    F = facets(X)

    if lock_best_initial:
        start = best_initial_def(X, F, T, seed, topm)

    cur = start
    realized = []
    switches = 0
    used_bad = 0
    hist = {k: [] for k in range(N_DEF)}   # 每个定义被探测到的真值记录

    for t in range(T):
        a = regime_weights(t, T, seed)
        V = F @ a

        # ── 探测：拿一小部分预算去试别的定义（真值反馈才知道好不好）
        probing = False
        if (not locked) and rng.random() < rho:
            probing = True
            m = max(6, N // 6)
            idx = rng.choice(N, size=m, replace=False)
            for k in range(N_DEF):
                top = idx[np.argsort(def_scores(X[idx], k))[::-1][:max(2, m // 5)]]
                hist[k].append(float(np.mean(V[top])))

        # ── 决策：换不换
        switched = False
        if (not locked) and oracle:
            cands = [k for k in range(N_DEF) if len(hist[k]) >= 2]
            if cands:
                est = {k: float(np.mean(hist[k][-3:])) for k in cands}
                cur_est = est.get(cur, -1e9)
                best = max(est, key=lambda k: est[k])
                if best != cur and est[best] > cur_est + theta:
                    cur = best
                    switches += 1
                    switched = True

        if cur == 4:
            used_bad += 1

        # ── 执行：按当前定义取最好的一批，拿到真值
        top = np.argsort(def_scores(X, cur))[::-1][:topm]
        v = float(np.mean(V[top]))
        if switched:
            v *= (1.0 - switch_cost)      # 换定义那一轮，旧体系要重新对齐
        if probing:
            v *= (1.0 - probe_penalty)    # 一边试新尺子一边干活，两头打折
        realized.append(v)

    return {
        "score": float(np.mean(realized)),
        "first_half": float(np.mean(realized[:T // 2])),
        "last_half": float(np.mean(realized[T // 2:])),
        "switches": switches,
        "bad_rate": used_bad / T,
        "final_def": cur,
    }


def ranking_overlap(N=300, topk=20, seed=0):
    """
    ★ 定义权存在性：不同定义选出来的"最好的东西"是不是同一批？
    重合度 ≈ 1 → 换定义没意义，这一课整个是空的。
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(N, D))
    sets = {}
    for k in range(N_DEF):
        sets[k] = set(np.argsort(def_scores(X, k))[::-1][:topk].tolist())
    ov = []
    for i in range(N_DEF):
        for j in range(i + 1, N_DEF):
            ov.append(len(sets[i] & sets[j]) / topk)
    return float(np.mean(ov)), float(np.min(ov))
