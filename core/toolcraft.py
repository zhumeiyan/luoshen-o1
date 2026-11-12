#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toolcraft —— 操控力（★78）

════ 这一课教什么 ════
  学全球顶级 AI，学的不是它的代码，学的是：
    ① 操控工具的能力（什么时候用、用几个、不信它的时候怎么办）
    ② 对设备的理解（这个设备【实际上】能干什么，不是文档说它能干什么）
    ③ 吃什么饵料（工具返回的数据里，哪些吸收、哪些扔掉）

  ★ 判据之王：可迁移性
    记住"哪个设备好" → 换一套没见过的设备就废了
    学会"怎么对待设备" → 换设备还在
    这正是"学操控"与"抄代码"的分界线。

════ 环境 ════
  M 个设备 × D 类任务。每个设备有：
    真实成功率 p[k,d]        ← 她看不到
    标称成功率 phat[k,d]     ← 文档宣称的，逐条异质夸大/低估
    成本 cost[k]
  她初始只能信文档（q = phat），靠真值反馈慢慢修正出自己的估计 q。

════ ★★ 三个"为什么这一课不是空的"的结构前提 ════
  ① 文档夸大必须是【异质】的（per-(k,d)），否则只是整体加 bias、
     设备排序不变 —— 那"信不信文档"就无所谓，θ 必然峰在边界。
     （我第一版就是这个错。）
  ② 必须存在【沉睡的好设备】：真实很强，但文档把它写得很平庸。
     这种设备只有主动试错才发现 —— θ 帮不上（θ 只在用过后才修正），
     这正是 explorer / ρ 存在的全部理由。
  ③ 能力必须是【按 domain 分开的向量】，不是单个标量。
     只吃高可靠的数据 → 只有少数 domain 的能力涨 → 饿死（starvation）。
     标量 cap 下"吃得少"没有代价，β 必然单调。
"""

from __future__ import annotations
import numpy as np

ETA = 0.45      # 吃到好数据 → 该 domain 能力增长
KAPPA = 0.55    # 吃到坏数据 → 该 domain 污染（超线性）


def make_fleet(M=6, D=4, seed=0, honest=False, trap=True, unlisted=False):
    """
    honest=True  ：标称 = 真值（硬依赖对照：文档诚实的话，θ 这个问题就不存在）
    trap=True    ：强制植入【沉睡的好设备】—— 真实最强，文档却写得平庸
    """
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.18, 0.72, size=(M, D))
    for k in range(M):                       # 每个设备有一项专长
        d0 = int(rng.integers(D))
        p[k, d0] = min(0.95, p[k, d0] * 1.5)

    if honest:
        phat = p.copy()
    else:
        # ★ 逐条异质失真（不再是统一 bias）—— 排序会被扭曲
        bias = rng.uniform(-0.12, 0.38, size=(M, D))
        phat = np.clip(p + bias + rng.normal(0, 0.05, size=(M, D)), 0.03, 0.98)
        if trap and M >= 3 and D >= 2:
            # ★★ 沉睡的好设备：真实最强，但文档把它写成中下
            best = int(np.argmax(p.mean(axis=1)))
            lo = np.sort(phat.mean(axis=1))
            target = lo[max(0, M // 3)] if M > 3 else lo[0]
            phat[best] = np.clip(phat[best] - (phat[best].mean() - target) * 1.15, 0.03, 0.98)
            # ★★★ 未收录设备（文档里根本没有的东西）
            #   θ 永远碰不到它：从没用过 → seen=0 → q 一直等于初始的低 phat
            #   → argmax 永远不会选中它 → 只有主动探索能发现。
            #   这就是"顶级 AI 面对的工具海洋"的真实处境：
            #   最有价值的工具，往往不在你读到的那份文档里。
            if unlisted and M >= 4:
                for i in rng.choice(M, size=1, replace=False):
                    phat[i] = rng.uniform(0.10, 0.22, size=D)

    cost = rng.uniform(0.05, 0.40, size=M)
    return p, phat, cost


def run(theta=0.15, rho=0.20, beta=1.0, fleet=None, T=70, seed=0,
        honest=False, M=6, D=4, cap0=0.35, w_cap=0.40, trap=True,
        unlisted=False, drift=0.0):
    """
    theta  校准阈值：文档说的和我自己测的差多少，我就不信文档了
           θ→0   几乎全信自己的经验（冷启动吃亏：早期样本极少，估计噪声大）
           θ→∞   几乎全信文档（被异质夸大骗，选到错设备）
    rho    探测预算：多大比例的任务拿去试"看起来不是最优"的设备
           ρ=0   一直用文档说的最好的，永远发现不了【沉睡的好设备】
           ρ→大  光试不干活
    beta   饵料门槛：可靠度低于它的返回，不吃
           β=0   来者不拒，垃圾数据全吸收（★75 模型塌缩那条）
           β→大  只吃最保险的那一点 → 没新信息，饿死（starvation）
    """
    if fleet is None:
        fleet = make_fleet(M, D, seed, honest, trap, unlisted)
    p, phat, cost = fleet
    p = p.copy()
    rng = np.random.default_rng(seed + 7919)

    q = phat.copy()                 # 她自己的估计，初始只能信文档
    seen = np.zeros((M, D))
    cap = np.full(D, cap0)          # ★ 按 domain 分开的能力向量
    succ, eats = [], []

    for t in range(T):
        if drift > 0:
            # ★ 设备会变：真实能力缓慢漂移（API 更新、模型换代、服务降级）
            p = np.clip(p + rng.normal(0, drift, size=p.shape), 0.03, 0.97)
        d = int(rng.integers(D))
        # ── 操控：信文档还是信自己？
        diff = np.abs(phat[:, d] - q[:, d])
        est = np.where(diff > theta, q[:, d], phat[:, d])
        eff = np.clip(est * (0.70 + 0.60 * cap[d]) - 0.15 * cost, 0.01, 0.99)

        # ── 探测 vs 闷头用
        # ★ 我第一版让探索【完全随机选设备】—— 那是瞎试，当然永远不划算，
        #   ρ 的峰必然在 0。真实的探索是有信息的：去试我【最不了解】的那个
        #   （不确定度最大 → 信息增益最大）。这正是发现"沉睡好设备"的唯一途径。
        if rng.random() < rho:
            k = int(np.argmin(seen[:, d]))
        else:
            k = int(np.argmax(eff))

        # ── 执行，拿到真值反馈
        win = bool(rng.random() < p[k, d])
        seen[k, d] += 1
        q[k, d] += (1.0 / (seen[k, d] + 4.0)) * (float(win) - q[k, d])   # 对设备的理解

        # ── 饵料：这个 domain 吃多少
        # ★ 我第一版把增益和污染都写成 ∝(1−可靠度) —— 两者同向，
        #   数学上根本不可能有权衡，β 必然单调（实测跨度只有 0.04，是噪声）。
        # ★ 真实的两条非线性：
        #     新颖性【次线性】 nu   = (1-rel)^0.5   熟悉的东西新信息少，且边际递减
        #     污染  【超线性】 pol  = (1-rel)^2     一点垃圾数据能带偏整个判断
        #   → 净收益 = A*x^0.5 − B*x^2 （x = 1−rel），在 x* 处有内部极大。
        #   beta = 饵料门槛：低于这个可靠度的返回，不吃。
        rel = float(np.clip(est[k], 1e-3, 1.0))
        w = 1.0 / (1.0 + np.exp(-(rel - beta) * 12.0))   # 软门槛
        x = 1.0 - rel
        nu = x ** 0.5
        pol = x ** 2
        if win:
            cap[d] += ETA * w * nu * (1.0 - cap[d])   # 吸收到新信息
        else:
            cap[d] -= KAPPA * w * pol                 # 被不可靠数据污染
        cap[d] = float(np.clip(cap[d], 0.0, 1.0))
        eats.append(w)

        succ.append(float(win) - 0.10 * cost[k])

    return {
        "score": float(0.60 * np.mean(succ) + w_cap * float(np.mean(cap))),
        "task": float(np.mean(succ)),
        "cap": float(np.mean(cap)),
        "cap_min": float(np.min(cap)),       # 饿死的证据：最弱 domain 的能力
        "first": float(np.mean(succ[:T // 2])),
        "last": float(np.mean(succ[T // 2:])),
        "eaten": float(np.mean(eats)),
    }


def run_memory(fleet_train=None, fleet_test=None, T=70, seed=0, M=6, D=4):
    """
    ★ 对照组：记住"哪个设备好"，而不是学"怎么对待设备"。
    这就是"抄代码"那一派 —— 训练集上学出设备偏好，换设备集直接硬套。
    """
    if fleet_train is None:
        fleet_train = make_fleet(M, D, seed, False, True)
    if fleet_test is None:
        fleet_test = make_fleet(M, D, seed + 50000, False, True)
    pt, _, _ = fleet_train
    pref = pt.mean(axis=1)                   # 只记住设备排名，不区分 domain、不做校准
    p2, _, c2 = fleet_test
    rng = np.random.default_rng(seed + 313)
    cap = np.full(D, 0.35)
    succ = []
    for _ in range(T):
        d = int(rng.integers(D))
        k = int(np.argmax(pref - 0.15 * c2))  # 把旧偏好硬套到新设备集
        win = bool(rng.random() < p2[k, d])
        cap[d] += ETA * (1.0 - cap[d]) if win else -KAPPA
        cap[d] = float(np.clip(cap[d], 0.0, 1.0))
        succ.append(float(win) - 0.10 * c2[k])
    return {"score": float(0.60 * np.mean(succ) + 0.40 * float(np.mean(cap))),
            "task": float(np.mean(succ)), "cap": float(np.mean(cap))}


def fleet_stats(fleet):
    p, phat, _ = fleet
    tp = p.mean(axis=1); dp = phat.mean(axis=1)
    return {
        "specialization": float(p.max(axis=1).mean() - tp.mean()),
        "exaggeration": float(np.mean(phat - p)),
        "rank_flip": int(np.argmax(tp) != np.argmax(dp)),   # 沉睡好设备存在性
        "doc_top_is_true_top": int(np.argmax(tp) == np.argmax(dp)),
    }
