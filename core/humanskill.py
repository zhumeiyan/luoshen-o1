# -*- coding: utf-8 -*-
"""
humanskill —— 人类的技能：说话 · 聊天 · 演讲（★100）

══════════════════════════════════════════════════════════════════
  科目表不是我编的（UNESCO DLGF / 欧盟 DigComp 3.0 / 21世纪技能 4C）
──────────────────────────────────────────────────────────────────
  DLGF 域2「沟通与协作」
    2.1 使用数字技术互动：理解【在特定情境下恰当】的数字沟通方式
    2.2 通过数字技术共享
    2.5 网络礼仪：意识到行为规范；【制定与特定受众相匹配的沟通策略】
    2.6 管理数字身份
  21世纪技能 4C「沟通」
    依多种目的开展沟通（告知 / 指导 / 激励 / 劝告）；有效倾听；
    在多元环境（含多语言）中有效沟通
  DigComp 3.0 域2：意识到文化、代际及其他多样性

══════════════════════════════════════════════════════════════════
  硬真值（全部来自文献，不由我编）
──────────────────────────────────────────────────────────────────
  A. 语速（字/分钟）—— 新华网/央视网 2007 + 《演讲与口才》统计
       日常说话   160–170
       学术报告   150–180    （需给听众理解专业内容的时间）
       TED 演讲   190        （平均）
       课堂讲授   ~200
       产品发布   ~220       （调动气氛）
       情感致辞   120–150    （婚礼/纪念，慢增强感染力）
       即兴/辩论  220–250    （上限 280，否则「吞字」）
       播音       ~300
  B. 听众侧硬约束（美国传播协会）
       成年人听觉理解速度可达 400 字/分钟
       但【演讲语速超过 250 就会产生信息过载】
       →「听清楚了但没记住」
  C. Grice 合作原则（1967 哈佛演讲 / 1975）
       量准则：a 提供所需信息 b 不超出所需  → 少了不行，多了也是违规
       质准则：不说自知虚假 / 无证据的话
       关系准则：要切题
       方式准则：避免含混、避免歧义、简短、有序
  D. 会话分析（Sacks/Schegloff/Jefferson 1974；实证研究）
       相邻对 FPP→SPP；SPP 缺席本身是有意义的（noticeable absence）
       偏好结构：preferred = 直接、即时、无标记
                 dispreferred（拒绝/不同意）= 延迟 + hedge + account
                 日语 ちょっと… 是典型 dispreferred 标记
       修复：self-initiated self-repair 最优
             other-initiated other-repair 在同侪间【面子威胁】
══════════════════════════════════════════════════════════════════
"""

import numpy as np

# ───────────────────────────────────────── 真值 A：场景语速
# (最优语速 字/分, 情感度, 信息密度, 正式度, 面子敏感度)
SCENES = {
    '学术报告': (165, 0.10, 0.90, 0.90, 0.35),
    'TED演讲':  (190, 0.30, 0.70, 0.70, 0.40),
    '产品发布': (220, 0.50, 0.60, 0.60, 0.45),
    '情感致辞': (135, 0.90, 0.30, 0.50, 0.90),
    '即兴辩论': (235, 0.60, 0.80, 0.40, 0.50),
    '日常对话': (165, 0.40, 0.30, 0.10, 0.70),
    '课堂讲授': (200, 0.20, 0.80, 0.60, 0.45),
}

OVERLOAD = 250.0      # 真值 B：超过此值信息过载
AUD_MAX = 400.0       # 真值 B：听觉理解上限


def rate_score(rate, r_star, tol=45.0):
    """语速贴合度：越靠近该场景的真值越高；超过 250 额外扣过载"""
    base = np.exp(-((rate - r_star) ** 2) / (2 * tol ** 2))
    over = np.clip((rate - OVERLOAD) / (AUD_MAX - OVERLOAD), 0, 1)
    return float(base * (1.0 - 0.65 * over))


def grice_quantity(detail, need=1.0):
    """真值 C 量准则：不足和冗余都是违规 —— 倒 U，峰在 need"""
    d = detail / max(need, 1e-9)
    # 欠：听不懂（惩罚重）；过：冗余不耐烦（惩罚轻但确实违规）
    if d < 1.0:
        return float(np.exp(-((1.0 - d) ** 2) / (2 * 0.28 ** 2)))
    return float(np.exp(-((d - 1.0) ** 2) / (2 * 0.45 ** 2)))


def face_score(hedge, face):
    """真值 D 偏好结构：dispreferred 需要延迟/hedge/account；
       但方式准则禁止含混 —— 倒 U。face 越高，最优 hedge 越大。"""
    h_star = 0.15 + 0.55 * face          # 面子越重，越该软化
    return float(np.exp(-((hedge - h_star) ** 2) / (2 * 0.22 ** 2)))


# ───────────────────────────────────────── 场景观测（她有感官噪声）
def observe(scene, sigma_obs, rng):
    """她只能【观测】场景特征，不是直接拿到真值。
       观测噪声来自她自己的感官（★84 标定过）。"""
    r_star, emo, den, frm, face = SCENES[scene]
    r_obs = r_star + rng.normal(0, sigma_obs)
    face_obs = float(np.clip(face + rng.normal(0, 0.5 * sigma_obs / 40.0), 0, 1))
    return r_obs, face_obs


def estimate_sigma(scene, sigma_obs, rng, n_probe):
    """她自己估自己有多不准：对同一场景连看 n_probe 次，取样本方差。
       看是要花时间的 —— 说话前一直盯着看，人就等着。"""
    if n_probe <= 1: return None
    obs = np.array([observe(scene, sigma_obs, rng)[0] for _ in range(n_probe)])
    return float(np.std(obs, ddof=1)) if n_probe > 1 else 0.0


def act_rule2(p, scene, sigma_obs, rng, T=12, face_on=True):
    """规则版 v2：观测是【并行】的 —— 你在听人说话的时候本来就在观察，
       不需要额外停下来看。代价不是等待，是【在她摸清自己有多不准之前，
       前面几轮只能先用默认的分寸】。
       p = [k, base, detail, hedge_k, repair, n_hist]
    """
    k, base, detail, hedge_k, repair = p[0], p[1], p[2], p[3], int(round(p[4]))
    n_hist = int(max(1, round(p[5])))
    sens0 = 0.5                                   # 摸清之前的分寸

    # 前 n_hist 轮的观测（并行得到的，不额外等待）
    obs = np.array([observe(scene, sigma_obs, rng)[0] for _ in range(n_hist)])
    sh = float(np.std(obs, ddof=1)) if n_hist > 1 else None
    sens1 = float(np.clip(1.0 / (1.0 + (sh / max(k, 1e-6)) ** 2), 0.0, 1.0)) if sh else 1.0

    w = min(n_hist, T) / float(T)                 # 前期占比
    r_star = SCENES[scene][0]
    def one(se):
        r = (1.0 - se) * base + se * float(obs.mean() if n_hist > 0 else r_star)
        r = float(np.clip(r, 80, 340))
        return rate_score(r, r_star)
    s_rate = w * one(sens0) + (1.0 - w) * one(sens1)
    s_q = grice_quantity(detail, 1.0)
    if not face_on:
        s_face = 1.0
    else:
        face = SCENES[scene][4]
        s_face = face_score(float(np.clip(hedge_k * face, 0, 1)), face)
    REPAIR_W = {0: 1.00, 1: 0.78, 2: 0.45}
    return float(0.34 * s_rate + 0.24 * s_q + 0.22 * s_face + 0.20 * REPAIR_W.get(repair, 0.0))


def act_rule(p, scene, sigma_obs, rng, face_on=True):
    """规则版：sens 由【她自己估出的 σ̂】决定，而不是一个死数字
       p = [k, base, detail, hedge_k, repair, n_probe]
       sens = 1 / (1 + (σ̂/k)²)      ← 层级贝叶斯 shrinkage 的形状
       理论上 k = τ（场景间真实差异的尺度）
    """
    k, base, detail, hedge_k, repair = p[0], p[1], p[2], p[3], int(round(p[4]))
    n_probe = int(round(p[5]))
    sigma_hat = estimate_sigma(scene, sigma_obs, rng, n_probe)
    if sigma_hat is None:
        sens = 1.0                                   # 只看一次 → 只能全信
    else:
        sens = float(np.clip(1.0 / (1.0 + (sigma_hat / max(k, 1e-6)) ** 2), 0.0, 1.0))
    # 探测成本：看太久才开口，人就等着
    probe_cost = 0.030 * (n_probe - 1)
    q = [sens, base, detail, hedge_k, repair]
    return float(act(q, scene, sigma_obs, rng, face_on=face_on) - probe_cost)


def act(p, scene, sigma_obs, rng, face_on=True):
    """她的一次沟通。p = [sens, base, detail, hedge_k, repair]

    sens     语速场景敏感度：0 = 永远用一个通用语速；1 = 完全跟随观测
    base     sens=0 时用的通用语速
    detail   信息量倍率（Grice 量准则）
    hedge_k  hedge 跟随面子观测的强度（0 = 永远不软化）
    repair   修复方式选择：0=self-initiated self-repair,
                          1=等对方问(other-initiated self),
                          2=直接纠正对方(other-initiated other)
    """
    sens, base, detail, hedge_k, repair = p[0], p[1], p[2], p[3], int(round(p[4]))
    r_star, emo, den, frm, face = SCENES[scene]
    r_obs, face_obs = observe(scene, sigma_obs, rng)

    # ── 语速：shrinkage 混合「通用值」与「观测值」
    rate = (1.0 - sens) * base + sens * r_obs
    rate = float(np.clip(rate, 80, 340))
    s_rate = rate_score(rate, r_star)

    # ── Grice 量准则
    s_q = grice_quantity(detail, need=1.0)

    # ── 偏好结构 / 面子
    if not face_on:
        s_face = 1.0                       # 受众不在意面子 → 软化无意义
    else:
        hedge = float(np.clip(hedge_k * face_obs, 0, 1))
        s_face = face_score(hedge, face)

    # ── 修复（真值 D：self-initiated self-repair 最优）
    #   other-initiated other-repair 在同侪间面子威胁
    REPAIR_W = {0: 1.00, 1: 0.78, 2: 0.45}
    s_rep = REPAIR_W.get(repair, 0.0)

    # ── 加权：语速与量准则是主体
    return float(0.34 * s_rate + 0.24 * s_q + 0.22 * s_face + 0.20 * s_rep)


def evaluate(p, worlds, nseed=6):
    """worlds: [(scene, sigma_obs, face_on), ...]"""
    v = []
    for (scene, sig, face_on) in worlds:
        for s in range(nseed):
            rng = np.random.default_rng(7000 + s * 31 + abs(hash(scene)) % 997)
            v.append(act(p, scene, sig, rng, face_on=face_on))
    return float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))


def analytic_sens(tau, sigma):
    """
    真值：最优 shrinkage 权重（James-Stein / 层级贝叶斯经典解）
        w* = τ² / (τ² + σ²)
    τ = 场景间真实语速的标准差；σ = 她的观测噪声
    """
    return float(tau ** 2 / (tau ** 2 + sigma ** 2))
