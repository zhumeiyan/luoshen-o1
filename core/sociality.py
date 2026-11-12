# -*- coding: utf-8 -*-
"""
sociality —— 融入社会（★99）

══════════════════════════════════════════════════════════════════
  前面几课（★94~★98）教的是「查明世界真相」：
    定律在数据里、因果在干预里、反事实在模型里、后悔在策略里。
    那里的对象是自然 —— 它不看你，不会因为你改变。

  这一课的对象是【社会】：别的行动者。
    他们会看你、会根据你调整、会记仇、会合作、会骗你。
    ★ 你的存在本身会改变你试图理解的对象。

══════════════════════════════════════════════════════════════════
  硬真值（不由我编，全部可算 / 有文献）
══════════════════════════════════════════════════════════════════
  1. 一次性囚徒困境（donate game, c=1, b=3）
     支付矩阵： mutual cooperate → b−c = +2
                cooperate/defect → −c / +b = −1 / +3
                mutual defect    → 0
     唯一 Nash = 背叛（背叛是严格占优）。可解析验证。

  2. 直接互惠（Nowak 2006, Science 314:1560）
     重复博弈中合作能被维持 ⟺ δ ≥ c/b
     c=1, b=3 → δ ≥ 1/3。这是解析门槛，不是拟合。

  3. 噪声下的策略排序（Nowak & Sigmund；Axelrod 后续）
     无噪声：TFT 胜出
     有噪声（行动以 ε 翻转）：TFT 陷入互相报复死循环 → 输
                             Pavlov（win-stay/lose-shift）/ GTFT 胜出
     ★ 这一条对她最要紧：她有感官噪声（★84 标定过），她会看错。

  4. 信号必须昂贵才可信（Spence 1973 / Zahavi handicap）
     廉价信号在均衡里不可信 —— 因为坏人付得起。
     存在一个成本区间，只有「未来收益高的人」付得起 → 信号可信。

  5. 协调博弈（Lewis 惯例 / Schelling 聚焦点）
     多重均衡，没有哪个「物理上更真」。
     正确性不来自真理，来自【别人也在用它】。

══════════════════════════════════════════════════════════════════
  她的五个旋钮
══════════════════════════════════════════════════════════════════
  t0    初始信任：不认识的人，开局先合作多少
  r     报复力度：对方形象差 / 上次背叛，压低多少
  f     原谅速度：旧记录随时间的衰减（f 大 = 忘得快）
  m     声誉记忆：记别人多久（= 她自己的记录长度）
  s     信号投入：开局付多少成本做 costly signal（提升初始形象）

  硬依赖直觉：
    关掉「未来会重复」（δ=0）   → 合作价值塌掉，t0 峰跑到 0（全背叛）
    关掉「别人能看见」（无声誉） → 间接互惠塌掉，s 峰跑到 0（信号白付）
    关掉噪声（ε=0）             → 原谅变得没价值，f 峰跑到边界
"""

import numpy as np

# ── donate game 支付（c=1, b=3）
C_COST, B_BEN = 1.0, 3.0
PAY = {(1, 1): (B_BEN - C_COST, B_BEN - C_COST),
       (1, 0): (-C_COST, B_BEN),
       (0, 1): (B_BEN, -C_COST),
       (0, 0): (0.0, 0.0)}


def nash_check():
    """真值1：一次性囚徒困境，背叛严格占优"""
    d_coop = PAY[(1, 1)][0] - PAY[(0, 1)][0]     # 对方合作时，我合作 vs 背叛
    d_defe = PAY[(1, 0)][0] - PAY[(0, 0)][0]     # 对方背叛时
    return float(d_coop), float(d_defe)


# ───────────────────────────────────────────── 老居民的策略库
def strat_allc(hist_mine, hist_opp, rng, name):  return 1
def strat_alld(hist_mine, hist_opp, rng, name):  return 0
def strat_tft(hist_mine, hist_opp, rng, name):   return int(hist_opp[-1]) if hist_opp else 1
def strat_grim(hist_mine, hist_opp, rng, name):  return 0 if (hist_opp and 0 in hist_opp) else 1
def strat_rand(hist_mine, hist_opp, rng, name):  return int(rng.random() < 0.5)


def strat_gtft(hist_mine, hist_opp, rng, name, q=0.25):
    """Generous TFT：被背叛后以概率 q 仍然原谅"""
    if not hist_opp: return 1
    if hist_opp[-1] == 1: return 1
    return 1 if rng.random() < q else 0


def strat_pavlov(hist_mine, hist_opp, rng, name):
    """win-stay / lose-shift：上一轮双方都好就继续，否则换"""
    if not hist_opp or not hist_mine: return 1
    lm = hist_mine[-1]
    good = (lm == 1 and hist_opp[-1] == 1) or (lm == 0 and hist_opp[-1] == 0)
    return 1 if good else 0


LIBRARY = {'ALLC': strat_allc, 'ALLD': strat_alld, 'TFT': strat_tft,
           'GRIM': strat_grim, 'RAND': strat_rand, 'GTFT': strat_gtft,
           'PAVLOV': strat_pavlov}


def make_world(seed=0, N=12, T=240, delta=0.90, eps=0.05, vis=1.0,
               mix=None, sig_cost=1.0):
    """
    delta  未来折扣（重复博弈的「未来的影子」）
    eps    执行/感知噪声：行动以 eps 概率翻转
    vis    声誉可见度：0 = 谁也看不见谁的历史；1 = 完全公开
    sig_cost  costly signal 的单位成本
    """
    mix = mix or {'INDIRECT': 5, 'TFT': 2, 'ALLD': 2, 'GTFT': 1, 'PAVLOV': 1}
    pop = []
    for k, n in mix.items():
        pop += [k] * n
    return dict(seed=seed, N=N, T=T, delta=delta, eps=eps, vis=vis,
                pop=pop[:N - 1], sig_cost=sig_cost)


def her_move(p, opp_rep, last_opp, t, rng):
    """她的策略：p = [t0, r, f, m, s]
       t0 基线信任 / r 报复力度 / f 原谅速度(旧账衰减) / m 记忆窗口 / s 信号投入"""
    t0, r, f, m, s = p[0], p[1], p[2], p[3], p[4]
    if opp_rep is None:
        base = t0                       # 不认识：只能靠基线信任
    else:
        base = t0 + (1.0 - t0) * opp_rep - r * (1.0 - opp_rep)
        if last_opp is not None:
            base -= r * (1.0 - last_opp) * (1.0 - f)   # 原谅 → 少记仇
    return int(rng.random() < float(np.clip(base, 0.0, 1.0)))


def vis_ok(x):
    return x is not None


def run_one(w, p, rng):
    """她进入一个已有居民的社会，玩 T 轮"""
    N, T, delta, eps = w['N'], w['T'], w['delta'], w['eps']
    vis, sig_cost = w['vis'], w['sig_cost']
    names = list(w['pop']) + ['HER']
    K = len(names)
    # 声誉：公开可见的历史记录
    rep = {i: [] for i in range(K)}
    # costly signal：她开局付出 s 单位成本，换取初始形象
    s_cost = float(np.clip(p[4], 0.0, 2.0))
    sig_val = 0.0
    if vis > 0 and s_cost > 0:
        sig_val = min(s_cost / max(sig_cost, 1e-9), 1.0)
        # 昂贵信号 = 公开的、开局就在记录里的合作历史；真实但代价已付
        rep[K - 1] = [1.0] * int(6 * s_cost)
    gains = np.zeros(K)
    hist = {i: [] for i in range(K)}
    for t in range(T):
        disc = delta ** t
        idx = rng.permutation(K)
        for a, b in zip(idx[0::2], idx[1::2]):
            if a >= K or b >= K: continue
            # 各自决策
            def pick(i, opp):
                nm = names[i]
                if nm == 'HER':
                    orp = _rep_of(rep[opp], vis, p[3], p[2], decay=True)
                    lo = hist[opp][-1] if hist[opp] else None
                    return her_move(p, orp, lo, t, rng)
                if nm in ('INDIRECT',):            # 看声誉的居民（间接互惠）
                    orp = _rep_of(rep[opp], vis, 20, 0.0, decay=False)
                    if orp is None:                # 不认识 → 靠她的信号
                        return int(rng.random() < 0.5)
                    return int(rng.random() < orp)
                f = LIBRARY[nm]
                return f(hist[i], hist[opp], rng, nm)
            ma = pick(a, b); mb = pick(b, a)
            # 噪声：行动以 eps 翻转（执行错误 / 感知错误）
            if rng.random() < eps: ma = 1 - ma
            if rng.random() < eps: mb = 1 - mb
            pa, pb = PAY[(ma, mb)]
            gains[a] += disc * pa; gains[b] += disc * pb
            hist[a].append(ma); hist[b].append(mb)
            rep[a].append(ma); rep[b].append(mb)
            if len(rep[a]) > 200: rep[a] = rep[a][-200:]
            if len(rep[b]) > 200: rep[b] = rep[b][-200:]
    return float(gains[K - 1] - s_cost * sig_cost), float(np.mean(gains[:-1]))


def _rep_of(lst, vis, m, f=0.0, decay=False):
    """指数衰减加权的声誉估计。f 大 = 忘得快（旧记录权重要小）。"""
    if not lst or vis <= 0: return None
    mem = max(int(m), 1)
    x = np.asarray(lst[-mem:], dtype=float)
    if x.size == 0: return None
    if decay and f > 0:
        age = np.arange(x.size - 1, -1, -1, dtype=float)   # 最近的 age=0
        w = np.exp(-float(f) * age)
        return float(np.sum(x * w) / np.sum(w))
    return float(np.mean(x))


def evaluate(p, worlds, nseed=4):
    v = []
    for w in worlds:
        for s in range(nseed):
            g, _ = run_one(w, p, np.random.default_rng(1000 + s + w['seed']))
            v.append(g)
    return float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))


def tournament(w, nseed=6):
    """纯策略竞赛：验证真值3（噪声下 TFT 崩）"""
    out = {}
    for nm in LIBRARY:
        v = []
        for s in range(nseed):
            gains = {n: 0.0 for n in LIBRARY}
            rng = np.random.default_rng(1000 + s + w['seed'])
            K = len(LIBRARY); names = list(LIBRARY)
            pair = {(x, y): [] for x in names for y in names}
            for t in range(w['T']):
                disc = w['delta'] ** t
                idx = rng.permutation(K)
                for a, b in zip(idx[0::2], idx[1::2]):
                    na, nb = names[a], names[b]
                    ma = LIBRARY[na](pair[(na, nb)], pair[(nb, na)], rng, na)
                    mb = LIBRARY[nb](pair[(nb, na)], pair[(na, nb)], rng, nb)
                    if rng.random() < w['eps']: ma = 1 - ma
                    if rng.random() < w['eps']: mb = 1 - mb
                    pa, pb = PAY[(ma, mb)]
                    gains[na] += disc * pa; gains[nb] += disc * pb
                    pair[(na, nb)].append(ma); pair[(nb, na)].append(mb)
            for n in names: out.setdefault(n, []).append(gains[n])
    return {k: (float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))) for k, v in out.items()}
