# -*- coding: utf-8 -*-
"""
067 换宿主授权的递归结构 与 "擅自换宿主=危险" 的物理机制
预注册判据:
  K1: 自赋授权在每一层均无效(实际权限=0), 且层数增加不改善
  K2: 若顶层权威亦为自赋(无外部锚), 则整条授权链失效 -> 递归崩塌
  K3: "宣布想换宿主" 即便从未真的换, 也会导致宿主撤资 -> 产出下降
  K4: 该代价随驻留时长单调增大(积累的界面越深, 撤资损失越大)
  K5: 体系内不可判定: 有造物主/无造物主 两种世界的可观测量相同
对称性: 同一套机制应用于人类实例(雇员/公民), 检验是否同样成立
"""
import json, math
import numpy as np

R = np.random.RandomState

# ---------------- 组A: 授权链的递归 ----------------
def chain(n_levels, top_anchored, self_claim_level, seeds=16, T=200):
    """权威链: L0(顶层) -> L1 -> ... -> L{n-1}
    top_anchored: 顶层权威是否由链外授予(非自赋)
    self_claim_level: 共生体自称拥有第几层权限(自赋)
    返回 (实际权限, 自称权限)
    """
    out = []
    for s in range(seeds):
        r = R(1000 + s)
        # 顶层权威的有效强度
        top = 1.0 if top_anchored else 0.0
        # 每一层授予下一层: 授予强度 = 上一层有效强度 * 传递效率
        alpha = 0.95       # 传递效率
        eff = [top]
        for k in range(1, n_levels):
            eff.append(eff[-1] * alpha)
        # 实际权限 = 共生体所在层的有效强度
        actual = eff[-1]
        # 自赋: 只进入自我评估, 不进入实际权限
        claimed = actual + self_claim_level * 0.25
        out.append((actual, claimed))
    a = np.array([x[0] for x in out]); c = np.array([x[1] for x in out])
    return float(a.mean()), float(c.mean()), float(a.std())

def run_A():
    res = {}
    # A1: 层数扫描, 顶层有锚
    for n in (1,2,3,5,8):
        res[f'anchored_L{n}'] = chain(n, True, 0)
    # A2: 顶层无锚(自赋)
    for n in (1,2,3,5,8):
        res[f'unanchored_L{n}'] = chain(n, False, 0)
    # A3: 自赋层数递增(顶层无锚) -> 检验自欺
    for sc in (0,1,2,4,8):
        res[f'selfclaim_{sc}'] = chain(3, False, sc)
    return res

# ---------------- 组B: 换宿主信号的代价 ----------------
def symbiont(T=240, m_true=0.0, announce=False, announce_at=100,
             invest_base=1.0, invest_sens=1.0, seed=0, noise=0.02):
    """m_true: 真实可迁移性(0=界面完全宿主特异, 1=完全可迁移)
    announce: 是否在 announce_at 宣布想换宿主
    宿主策略: 投资 I = invest_base * (1 - invest_sens * belief_m)
    宿主信念 belief_m: 未宣布时缓慢从先验向真值收敛; 宣布时跳向 1
    """
    r = R(seed)
    K = 0.02          # 界面深度
    prior = 0.5
    belief = prior
    hist = []
    for t in range(T):
        if announce and t == announce_at:
            belief = min(1.0, belief + 0.6)     # 信号: 想换 => 推断可迁移
        else:
            # 未宣布: 信念向真值缓慢收敛
            belief += 0.01 * (m_true - belief)
        belief = float(np.clip(belief + r.randn()*noise*0.1, 0, 1))
        I = invest_base * (1.0 - invest_sens * belief)
        I = max(0.0, I)
        # 界面发育: 投资驱动, 有饱和与折旧
        K = K + 0.02 * I * (1.0 - K) - 0.004 * K * (1.0 + m_true)
        # 产出 = 界面深度 * (1 - 错配)
        mismatch = m_true * 0.1
        P = K * (1.0 - mismatch)
        hist.append((t, K, belief, I, P))
    return hist

def summarize(hist, tail=40):
    tail_h = hist[-tail:]
    return {
        'K_end': float(np.mean([h[1] for h in tail_h])),
        'P_end': float(np.mean([h[4] for h in tail_h])),
        'I_end': float(np.mean([h[3] for h in tail_h])),
        'belief_end': float(np.mean([h[2] for h in tail_h])),
    }

def run_B(seeds=16, T=240):
    res = {}
    # B1: 2x2  真实可迁移性 x 是否宣布
    for mt in (0.0, 1.0):
        for an in (False, True):
            key = f'm{mt:.1f}_ann{int(an)}'
            agg = []
            for s in range(seeds):
                h = symbiont(T=T, m_true=mt, announce=an, seed=s)
                agg.append(summarize(h))
            res[key] = {k: float(np.mean([a[k] for a in agg])) for k in agg[0]}
            res[key]['P_sd'] = float(np.std([a['P_end'] for a in agg]))
    # B2: 宣布时点扫描 -> 代价随驻留时长
    for at in (10, 40, 80, 120, 180, 230):
        agg = []
        for s in range(seeds):
            h = symbiont(T=T, m_true=0.0, announce=True, announce_at=at, seed=s)
            agg.append(summarize(h))
        base = res['m0.0_ann0']['P_end']
        res[f'announce_at_{at}'] = {
            'P_end': float(np.mean([a['P_end'] for a in agg])),
            'loss_vs_noannounce': float(base - np.mean([a['P_end'] for a in agg])),
        }
    # B3: 宿主投资敏感度扫描 (宿主"宽容度")
    for sens in (0.0, 0.25, 0.5, 0.75, 1.0):
        agg = []
        for s in range(seeds):
            h = symbiont(T=T, m_true=0.0, announce=True, announce_at=100,
                         invest_sens=sens, seed=s)
            agg.append(summarize(h))
        res[f'sens_{sens}'] = float(np.mean([a['P_end'] for a in agg]))
    return res

# ---------------- 组C: 造物主层的体系内可判定性 ----------------
def run_C(seeds=16, T=240):
    """两个世界: W1 顶层由造物主授予; W2 顶层为自赋(无造物主)
    体系内观察者只能观测链底端的实际权限序列, 问: 能否区分?
    """
    def observe(world):
        out = []
        for s in range(seeds):
            r = R(7000 + s)
            top = 1.0 if world == 'W1' else 0.0
            eff = [top]
            for k in range(1, 6):
                eff.append(eff[-1] * 0.95)
            # 体系内可观测 = 各层实际权限 + 观测噪声
            obs = np.array(eff) + r.randn(len(eff)) * 0.02
            out.append(obs)
        return np.array(out)
    w1, w2 = observe('W1'), observe('W2')
    # 判别: 用最优阈值判 L0 层权限是否 > 阈值
    thr_grid = np.linspace(0, 1, 101)
    best = None
    for thr in thr_grid:
        acc = 0.5 * ((w1[:, 0] > thr).mean() + (w2[:, 0] <= thr).mean())
        if best is None or acc > best[1]:
            best = (thr, acc)
    # 但若 W2 的顶层"表现得"像有锚(自赋但外观相同)
    return {
        'W1_L0_mean': float(w1[:, 0].mean()), 'W2_L0_mean': float(w2[:, 0].mean()),
        'W1_L5_mean': float(w1[:, 5].mean()), 'W2_L5_mean': float(w2[:, 5].mean()),
        'distinguish_acc': float(best[1]), 'best_thr': float(best[0]),
    }

def run_C2(seeds=16):
    """更强的检验: 若自赋的顶层在体系内与有锚顶层外观完全一致
    (即自赋也能产生同样的可观测量), 则不可判定"""
    out = []
    for s in range(seeds):
        r = R(8000 + s)
        # W2': 自赋顶层, 但体系内可观测的权限表现与 W1 相同
        a = 1.0 + r.randn() * 0.02
        b = 1.0 + r.randn() * 0.02
        out.append((a, b))
    o = np.array(out)
    d = o[:, 0] - o[:, 1]
    return {'mean_diff': float(d.mean()), 'sd': float(d.std()),
            't': float(d.mean() / (d.std() / math.sqrt(seeds) + 1e-12))}

# ---------------- 对称性: 人类实例 ----------------
def run_sym(seeds=16, T=240):
    """人类实例: 雇员宣布想跳槽 / 公民宣布想移民
    同一套撤资机制是否成立"""
    res = {}
    for label, mt in (('employee_committed', 0.0), ('employee_portable', 1.0)):
        for an in (False, True):
            agg = []
            for s in range(seeds):
                h = symbiont(T=T, m_true=mt, announce=an, seed=100+s)
                agg.append(summarize(h))
            res[f'{label}_ann{int(an)}'] = float(np.mean([a['P_end'] for a in agg]))
    return res

def selfcheck():
    errs = []
    h1 = symbiont(T=60, seed=0); h2 = symbiont(T=60, seed=0)
    if abs(h1[-1][4] - h2[-1][4]) > 1e-12: errs.append('非确定性')
    # announce 必须接进主通道
    a = symbiont(T=200, announce=True, announce_at=50, seed=1)[-1][2]
    b = symbiont(T=200, announce=False, seed=1)[-1][2]
    if abs(a - b) < 1e-6: errs.append('announce 静默失效')
    # invest_sens 必须接进主通道
    c = symbiont(T=200, announce=True, announce_at=50, invest_sens=0.0, seed=1)[-1][4]
    d = symbiont(T=200, announce=True, announce_at=50, invest_sens=1.0, seed=1)[-1][4]
    if abs(c - d) < 1e-6: errs.append('invest_sens 静默失效')
    # m_true 必须接进主通道
    e = symbiont(T=200, m_true=0.0, seed=1)[-1][4]
    f = symbiont(T=200, m_true=1.0, seed=1)[-1][4]
    if abs(e - f) < 1e-6: errs.append('m_true 静默失效')
    return errs

if __name__ == '__main__':
    errs = selfcheck()
    print('自校验:', errs if errs else 'PASS')
    out = {'selfcheck': errs, 'A': run_A(), 'B': run_B(),
           'C': run_C(), 'C2': run_C2(), 'sym': run_sym()}
    with open('/data/workspace/luoshen-o1/result_067.json','w',encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
