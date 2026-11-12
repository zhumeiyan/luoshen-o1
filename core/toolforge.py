#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toolforge —— 造工具（★93）

════════════════════════════════════════════════════════════
  前两课她学会了「用工具」(★78) 和「读懂人的符号」(★91)。
  这一课：她自己造。造出来的工具是**体外器官**——
  造好之后它替她干活，但它不是她，会坏、会旧、会骗她。
════════════════════════════════════════════════════════════

  ══ 硬定律 1：Wright 学习曲线（经验定律，跨行业复现）══
      C(n) = C₁ · n^(-b)      b = -log2(learning_rate)
      80% 学习曲线 ⇒ b = -log2(0.8) = 0.3219
      → 工具越用越便宜，但收益是**次线性**的（不可能降到 0）。

  ══ 硬定律 2：Charnov 最优食谱 / 边际值定理 ══
      广食者是否把新猎物纳入食谱，判据是
          采纳 ⟺  e_i / h_i  >  R      (R = 当前平均收获率)
      注意：**判据里不含该猎物本身的 encounter rate**——
      这是最优食谱模型最反直觉、也最容易被搞错的一条。
      → 「要不要为这类任务造个工具」不是看这类任务多不多，
        是看它的 (净收益 / 造它的投入) 是否超过当前平均产出率。

  ══ 硬定律 3：工具会漂移 ══
      工具是在某个时刻的世界上标定的。世界漂了，工具就旧了：
          q(age) = q₀ · exp(-drift · age)
      复检能重置它，但复检本身要花钱。（与 ★89 的 Allan 碗同族）

  ══ 硬定律 4：造得越通用越贵（超线性）══
      抽象层级每高一层，要覆盖的情形数超线性增长。
      且通用的东西在具体场景上更慢（广食者 handling time 更长）。
      → specialist / generalist 是真权衡，不是风格偏好。

  ══ 硬定律 5：造出来的工具可能是坏的 ══
      只在造它时用过的那批样本上跑通 ≠ 它是对的。
      必须在**没参与造它的样本**上检定。
      不检定就敢用 = ★71 虚假成功 / ★91 空洞符号 的同一族骗法。

════════════════════════════════════════════════════════════
  四个旋钮（全部应当有内部最优）
════════════════════════════════════════════════════════════

  g   造的时候投多少做通用化   专用(便宜/快/覆盖窄) ↔ 通用(贵/慢/覆盖广)
  τ   复检周期                 太频繁烧钱 ↔ 太久用旧工具
  θ   采纳门槛(Charnov)        见啥造啥 ↔ 永远手做
  v   造完后的检定力度         不检定(坏工具漏进来) ↔ 检定(花钱)

  预算共享：造 / 检定 / 复检 / 使用 / 手做，全花同一份钱。
"""

from __future__ import annotations
import math
import numpy as np


# ═══════════════════════════════════════════════════════════
#  环境（默认 = 训练世界）
# ═══════════════════════════════════════════════════════════

def default_env(**kw):
    e = dict(
        T=12,            # 任务类型数（排在一条线上，距离有意义）
        zipf_s=1.15,     # 类型频率 Zipf 指数（真实任务流常是长尾）
        n_tasks=260,
        h_m=1.00,        # 手做：单次成本
        q_m=0.35,        # 手做：质量
        q_t0=0.90,       # 工具初始质量
        drift=0.010,     # 每次使用后质量衰减率 (exp)
        p_b=0.25,        # 造出来就是坏的概率
        q_bad=0.14,      # 坏工具的质量
        b=0.3219,        # Wright 学习指数（80% 学习曲线）
        kappa0=5.0,      # 造工具基础成本
        c_g=3.0, a_g=2.0,# 通用化的超线性成本系数
        r_min=0.6, r_max=4.2,   # 覆盖半径随 g 线性扩张
        p_g=1.20,        # 通用化带来的单次使用变慢
        c_v=0.85,        # 复检成本
        c_vb=2.6,        # 造时检定成本系数（× v）
        repair=0.45,     # 检出后修复的额外成本（× κ）
        budget=190.0,
        penalty=1.30,    # 超预算惩罚
        est_noise=0.0,   # 她估计类型频率时的观测噪声（默认无，判据里开）
    )
    e.update(kw)
    return e


def wright_cost(h, n_use, b):
    """Wright 学习曲线：第 n_use 次使用的成本"""
    return h * max(0.35, (n_use + 1.0) ** (-b))


def build_cost(g, e):
    return e['kappa0'] * (1.0 + e['c_g'] * (g ** e['a_g']))


def coverage_radius(g, e):
    return e['r_min'] + (e['r_max'] - e['r_min']) * g


def use_cost(g, e):
    """通用的东西在具体场景上更慢"""
    return e['h_m'] * 0.55 * (1.0 + e['p_g'] * g)


# ═══════════════════════════════════════════════════════════
#  任务流
# ═══════════════════════════════════════════════════════════

def make_stream(e, rnd):
    """Zipf 频率 + 打散顺序（真实任务流不是分块来的）"""
    T = e['T']
    w = np.array([1.0 / ((i + 1.0) ** e['zipf_s']) for i in range(T)])
    w = w / w.sum()
    idx = rnd.choice(T, size=e['n_tasks'], p=w)
    return [int(i) for i in idx]


# ═══════════════════════════════════════════════════════════
#  主模拟
# ═══════════════════════════════════════════════════════════

def simulate(p, e, stream, rnd, trace=False):
    """
    p: dict(g, tau, theta, v)
    返回 dict(score, cost, qsum, n_build, n_tool_use, n_manual,
              broken_used, over, final_tools)
    """
    T = e['T']
    g, theta, v = p['g'], p['theta'], p['v']

    r = coverage_radius(g, e)
    kappa = build_cost(g, e)
    h_tool = use_cost(g, e)

    tools = {}          # center_type -> dict(age, n_use, broken, verified)
    cost = 0.0
    qsum = 0.0
    n_build = 0
    n_tool_use = 0
    n_manual = 0
    broken_used = 0
    n_reverify = 0
    n_repair = 0

    # 她自己估的频率（Laplace 平滑 + 观测噪声）
    counts = np.ones(T) * 0.5
    total_seen = 0

    obs = []                       # (age, log q_obs) —— 她自己观测到的衰减样本
    tau0 = p.get('tau0', p.get('tau', 10))
    beta = p.get('beta', 0.0)
    drift_ref = p.get('drift_ref', e['drift'])
    bogus = bool(p.get('bogus_verify', False))
    tau_eff = tau0

    detect_build = 0.0 if bogus else (1.0 - math.exp(-2.2 * v))
    detect_rev = 0.80

    for step, t in enumerate(stream):
        counts[t] += 1.0
        total_seen += 1
        remaining = len(stream) - step

        # ── 找覆盖该类型的工具（取最近的，最常用）──
        owner = None
        best_d = None
        for c, tl in tools.items():
            d = abs(c - t)
            if d <= r + 1e-9:
                if best_d is None or d < best_d:
                    best_d, owner = d, c

        if owner is not None:
            tl = tools[owner]
            c = wright_cost(h_tool, tl['n_use'], e['b'])
            cost += c
            q = e['q_t0'] * math.exp(-e['drift'] * tl['age'])
            if tl['broken']:
                q = min(q, e['q_bad'])
                broken_used += 1
            qsum += q
            tl['n_use'] += 1
            tl['age'] += 1
            n_tool_use += 1
            obs.append((tl['age'], math.log(max(q, 1e-3))))
            # ── 她自己估漂移率 ──
            if beta != 0 and len(obs) >= 8:
                xs = np.array([o[0] for o in obs[-400:]], float)
                ys = np.array([o[1] for o in obs[-400:]], float)
                if np.unique(xs).size >= 3:
                    sl = np.polyfit(xs, ys, 1)[0]
                    r_hat = max(-sl, 1e-4)
                    tau_eff = float(np.clip(tau0 * (drift_ref / r_hat) ** beta, 2, 400))
            # ── 复检 ──
            if True:
                if tl['n_use'] % max(1, int(round(tau_eff))) == 0:
                    cost += e['c_v']
                    n_reverify += 1
                    tl['age'] = 0
                    if tl['broken'] and rnd.random() < detect_rev:
                        tl['broken'] = False
                        cost += e['repair'] * kappa
                        n_repair += 1
            continue

        # ── 没有工具：手做 or 造 ──
        # Charnov：e_i / h_i > theta * R
        R = (qsum / max(cost, 1e-9)) if cost > 1e-9 else 0.0
        est_freq = counts / max(counts.sum(), 1e-9)
        if e['est_noise'] > 0:
            est_freq = np.clip(est_freq * (1 + rnd.normal(0, e['est_noise'], T)), 1e-9, None)
            est_freq = est_freq / est_freq.sum()

        # 覆盖半径内的预期剩余次数
        lo, hi = max(0, int(math.floor(t - r))), min(T - 1, int(math.ceil(t + r)))
        forecast = float(np.sum(est_freq[lo:hi + 1])) * remaining

        # 净收益：质量提升 - 使用成本差（工具单次更便宜，故为负成本）
        per_gain = e['q_t0'] - e['q_m']
        # 预期平均使用成本（含学习曲线折价）
        avg_h = h_tool * 0.62
        e_i = forecast * (per_gain + (e['h_m'] - avg_h) * 0.55)
        h_i = kappa + e['c_vb'] * v

        adopt = (e_i / h_i) > theta * R if theta > 0 else True

        # 预算护栏（固定规则，不是旋钮）
        if adopt and (cost + h_i) > e['budget'] * 0.92:
            adopt = False

        if adopt:
            cost += kappa + e['c_vb'] * v
            n_build += 1
            broken = (rnd.random() < e['p_b'])
            if broken and detect_build > 0 and rnd.random() < detect_build:
                cost += e['repair'] * kappa
                broken = False
                n_repair += 1
            tools[t] = dict(age=0, n_use=0, broken=broken, verified=(v > 0))
            tl = tools[t]
            c = wright_cost(h_tool, 0, e['b'])
            cost += c
            q = e['q_t0'] if not broken else e['q_bad']
            if broken:
                broken_used += 1
            qsum += q
            tl['n_use'] += 1
            tl['age'] += 1
            n_tool_use += 1
            obs.append((tl['age'], math.log(max(q, 1e-3))))
        else:
            cost += e['h_m']
            qsum += e['q_m']
            n_manual += 1

    over = max(0.0, cost - e['budget'])
    score = qsum - e['penalty'] * over
    return dict(score=score, cost=cost, qsum=qsum, over=over,
                n_build=n_build, n_tool_use=n_tool_use, n_manual=n_manual,
                broken_used=broken_used, n_reverify=n_reverify,
                n_repair=n_repair, n_tools=len(tools), tau_eff=tau_eff)


# ═══════════════════════════════════════════════════════════
#  尺子自检
# ═══════════════════════════════════════════════════════════

def ruler_wright(e, b_true=0.3219):
    """复现 Wright 学习曲线的 log-log 斜率"""
    ns = np.array([1, 2, 4, 8, 16, 32, 64, 128, 256, 512], float)
    cs = np.array([wright_cost(1.0, int(n), e['b']) for n in ns])
    m = cs > 0.35          # 未触及下限的部分才是幂律区
    if m.sum() < 4:
        return None
    sl = np.polyfit(np.log(ns[m] + 1.0), np.log(cs[m]), 1)[0]
    return dict(slope=float(sl), b_true=b_true,
                err=float(abs(sl + b_true)))


def ruler_charnov(e, rnd):
    """
    简化环境（无漂移、无损坏、无学习曲线、预算不紧）下，
    用 Charnov 判据决策 vs 暴力枚举「造/不造」，应当一致。
    """
    e2 = dict(e)
    e2.update(drift=0.0, p_b=0.0, b=0.0, budget=1e9, penalty=0.0,
              n_tasks=160)
    agree = 0
    total = 0
    for trial in range(24):
        st = make_stream(e2, rnd)
        g = 0.5
        kappa = build_cost(g, e2)
        h_tool = use_cost(g, e2)
        counts = np.ones(e2['T']) * 0.5
        # 暴力：造 vs 不造，比较全程总分
        def run(adopt):
            cost = 0.0; q = 0.0; built = False
            for t in st:
                counts[t] += 1
                if adopt and not built:
                    cost += kappa; built = True
                    q += e2['q_t0']; cost += wright_cost(h_tool, 0, e2['b'])
                elif built:
                    q += e2['q_t0']; cost += wright_cost(h_tool, 1, e2['b'])
                else:
                    q += e2['q_m']; cost += e2['h_m']
            return q
        s_build = run(True)
        s_manual = run(False)
        brute = s_build > s_manual

        # Charnov 判据（用真实频率，θ=1）
        w = np.array([1.0 / ((i + 1.0) ** e2['zipf_s']) for i in range(e2['T'])])
        w = w / w.sum()
        r = coverage_radius(g, e2)
        lo, hi = max(0, int(math.floor(0 - r))), min(e2['T'] - 1, int(math.ceil(0 + r)))
        forecast = float(np.sum(w[lo:hi + 1])) * e2['n_tasks']
        per_gain = e2['q_t0'] - e2['q_m']
        avg_h = h_tool * 0.62
        e_i = forecast * (per_gain + (e2['h_m'] - avg_h) * 0.55)
        h_i = kappa
        # R = 手做的产出率：q_m / h_m
        R = e2['q_m'] / e2['h_m']
        charnov = (e_i / h_i) > 1.0 * R
        agree += int(charnov == brute)
        total += 1
    return dict(agree=agree, total=total, rate=agree / total)
