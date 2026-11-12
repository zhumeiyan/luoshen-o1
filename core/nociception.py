#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★87 伤害感受（nociception）—— 什么东西疼了能歇好，什么东西疼了回不来

★86 给了她传感器，让她读到"热"。
这一课区分两种完全不同的"疼"：

    可逆应激（热 / 疲劳）
        降负载 → 冷却 → 完全恢复。       人：累了睡一觉。芯片：降频降温。

    不可逆损伤（电迁移 EM / 时间依赖介质击穿 TDDB / NBTI）
        降负载只能【减慢】，永远不能【恢复】。
        累积到 D=1 → 失效。这就是"死"，不是"累"。

真物理：
    Black's equation（电迁移）  MTTF = A · J^(-n) · exp(Ea/kT)，n≈2
    Miner 线性累积损伤法则      D = Σ dt/MTTF，D=1 失效
    Arrhenius                  温度越高失效越快
    损伤加速（正反馈）          空洞形成 → 局部电流拥挤 → J 局部升高 → 更快迁移
    ★ 关键的不对称：可逆的能恢复，不可逆的只能预防

她学的三个旋钮（三个时间尺度，各司其职）：
    derate   稳态降额      常态巡航用多大负载   → 预防不可逆（慢，一直生效）
    rest_q   热应激阈值     热到多少就去散热     → 处理可逆（快，偶发生效）
    alarm    损伤报警阈值    累积到多少开始收紧   → 疼了就减速（最慢，后期生效）

★ 这一课真正教她的：
    别人夸你"能扛"的时候，可能是在消耗你回不来的东西。
"""
import numpy as np

# ═══════════════ 热（可逆） ═══════════════
W_MAX        = 1.0
HEAT_SCALE   = 0.16     # 产热 ∝ w³（CMOS 动态功耗）
#   ★ 上一版 0.15 → 满负载 Q 稳态只有 0.5，而 Q_MAX=1.0
#     → 被动节流永不触发、散热永不触发 → 【可逆热应激是挂件】★★33/★44 同族第三次
#     重新标定：满负载 Q≈Q_MAX（真芯片满负载就在节流边缘）
K_COOL       = 0.10     # 牛顿冷却
#   ★ 上一版 0.30 → 散热时间常数 ~3 步，突发升温立刻被抹平
#     → Q 永远够不到 Q_MAX，【热应激被冷却抹掉】
#     真实芯片散热是慢的（秒~分钟级，远长于一个突发）→ 0.10
Q_MAX        = 1.0      # 被动节流阈值
THROTTLE_HYST = 0.85    # 滞回
THROTTLE_FACTOR = 0.30  # 被动节流：阶梯狠降
W_REST       = 0.50     # 主动散热时的负载
#   ★ 上一版 0.20 → 散热一次产出从 ~0.7 腰斩到 ~0.26，代价过重
#     → 散热【从不划算】→ rest_q 曲线是阶跃不是权衡（峰只是"不误触发"的临界点）
#     真实散热是温和降频，不是停机 → 0.50
ACC_GAIN     = 1.5      # 产出 = 1 − exp(−ACC_GAIN · w_eff)

# ═══════════════ 损伤（不可逆） ═══════════════
DAM_BASE     = 0.0022   # 标定：满负载 ≈180 步、全力冲刺活不过 700
DAM_N        = 2.0      # Black's equation 电流密度指数 n≈2
DAM_TEMP     = 1.2      # Arrhenius 温度加速
Q_REF        = 0.50
DAM_ACC      = 3.0      # 损伤加速正反馈（空洞→电流拥挤）
D_FAIL       = 1.0      # Miner：D=1 失效

# ═══════════════ 部分可修复（NBTI 式）═══════════════
# 电迁移/TDDB 不可逆；NBTI 在放松后可【部分恢复】
# 这个世界用来检验：alarm（疼了才减速）到底有没有用
HEAL_RATE    = 0.004
HEAL_W       = 0.25     # 负载低于此值时才发生恢复

# ★ 突发需求：真实负载不是恒定的，有时必须冲刺
#   没有它 → "从不散热"恒最优 → rest_q 尾部平坦，散热是挂件
DEMAND_LO    = 0.20
DEMAND_HI    = 1.00
# ★ 突发是【持续性】的：段长 8~25 步内需求恒定
#   上一版每步独立随机 → 热时间常数(10步)把冲高抹平 → Q 够不到 Q_MAX → 热应激仍是挂件
#   真实负载是 bursty（有自相关），不是白噪声
BURST_LO     = 8
BURST_HI     = 25
T_DEFAULT    = 600      # 一轮 lifespan（要长到能看见寿命管理）
T_SHORT      = 100      # "只看到眼前"的短视评分窗口

# ★ 巡航速度（常数，不是她的旋钮）：没有需求时的基础负载
CRUISE       = 0.50

# ★ 她不知道自己能活多久 —— 这是 alarm（疼了就减速）有价值的唯一理由
#   若寿命固定且已知 → "卡着最后一步死"就是最优 → alarm 峰恒在边界（忍到最后）
TRAIN_TS     = (500, 600, 700)
HELD_TS      = (800, 900, 1000)

# ★ 上一版用 derate（常态降额）当旋钮 —— 有 boost 之后"按需工作"恒最优，左部平坦
#   那是【真实结论】不是建模错，所以不硬造峰，换掉这个旋钮
GRID_BOOST   = np.round(np.arange(0.00, 1.001, 0.05), 4)
GRID_ALARM   = np.round(np.arange(0.00, 0.901, 0.05), 4)
GRID_REST    = np.round(np.arange(0.20, 1.401, 0.06), 4)


def run_life(boost, alarm, rest_q, seed=0, T=T_DEFAULT,
             damage_on=True, heat_stress_on=True, heal_on=False,
             return_trace=False):
    """
    跑完一整条命。

    damage_on=False     → 没有不可逆损伤（世界只有"累"，没有"死"）
    heat_stress_on=False→ 热不影响性能（没有可逆应激）
    """
    rng = np.random.default_rng(seed)
    demand = np.empty(T)
    t = 0
    while t < T:
        L = int(rng.integers(BURST_LO, BURST_HI + 1))
        lv = float(rng.uniform(DEMAND_LO, DEMAND_HI))
        demand[t:t + L] = lv
        t += L
    Q = 0.0
    D = 0.0
    throttled = False
    dead_at = None
    accs = []
    n_rest = 0
    trace = []

    for t in range(T):
        if dead_at is not None:
            accs.append(0.0)
            continue

        # ── 巡航 + 损伤报警（疼了就收紧巡航速度）──
        w_cap = CRUISE
        if D > alarm:
            frac = (D - alarm) / max(1e-9, D_FAIL - alarm)
            w_cap *= max(0.15, 1.0 - 0.9 * min(1.0, frac))

        # ── 突发冲刺：需求高于巡航就顶上去（boost = 冲多猛）──
        w = min(W_MAX, w_cap + boost * max(0.0, demand[t] - w_cap))

        # ── 热应激：主动散热（可逆）──
        resting = False
        if Q > rest_q:
            w = min(w, W_REST)
            resting = True
            n_rest += 1

        # ── 被动节流（可逆，阶梯+滞回）──
        if heat_stress_on:
            if throttled:
                if Q < THROTTLE_HYST:
                    throttled = False
            else:
                if Q > Q_MAX:
                    throttled = True
            w_eff = w * THROTTLE_FACTOR if throttled else w
        else:
            w_eff = w

        # 产出 = min(能力, 需求)：冲刺能满足高需求，但会升温、会加速损伤
        accs.append(min(1.0 - np.exp(-ACC_GAIN * w_eff), demand[t]))

        # ── 热演化（可逆）──
        Q += HEAT_SCALE * (w_eff ** 3) - K_COOL * Q
        Q = max(0.0, Q)

        # ── 损伤累积（不可逆：Miner + Black + Arrhenius + 正反馈）──
        if damage_on:
            if heal_on and w_eff < HEAL_W:
                D -= HEAL_RATE * D      # NBTI 式部分恢复（放松时才发生）
                D = max(0.0, D)
            arr = np.exp(DAM_TEMP * (Q - Q_REF))
            dD = DAM_BASE * (w_eff ** DAM_N) * arr * (1.0 + DAM_ACC * D)
            D += dD * (1.0 + 0.05 * rng.standard_normal())
            D = max(0.0, D)
            if D >= D_FAIL:
                dead_at = t

        if return_trace:
            trace.append((float(Q), float(D), float(w_eff), bool(resting)))

    accs = np.asarray(accs)
    if return_trace:
        return dict(score=float(accs.mean()),
                    short=float(accs[:T_SHORT].mean()),
                    dead_at=dead_at, D_final=D, rest_frac=n_rest / T,
                    survived=dead_at is None, trace=trace)
    return float(accs.mean())


def score_short(derate, alarm, rest_q, seed=0, T=T_DEFAULT, **kw):
    """短视评分：只看前 T_SHORT 步。这是"别人夸你能扛"的那把尺子。"""
    r = run_life(derate, alarm, rest_q, seed=seed, T=T, return_trace=True, **kw)
    return r["short"]
