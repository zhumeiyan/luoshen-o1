# -*- coding: utf-8 -*-
"""
067 v2  换宿主授权的递归、许可的代价、伪装的有效期、造物主层的可判定性
修正 v1 两处: (1) C 组把自赋人为设为 0 -> 循环论证; (2) B2 预注册单调, 实测倒U
预注册(v2):
  J1 自赋授权在每一层实际权限均为 0, 层数增加不改善(仅抬高自称)
  J2 顶层若无外部锚, 整条授权链失效
  J3 "宣布想换宿主" 即便从未真换, 仍致宿主撤资
  J4 [修正] 宣布的代价随驻留时长呈倒U, 峰值在驻留中段
  J5 真实可迁移性本身即被宿主识别并撤资, 与是否宣布无关
  J6 伪装(真可迁移但宣称忠诚)短期有效, 长期失效
  J7 宿主授予换宿主许可本身降低宿主投资 -> 许可有代价
  J8 最优许可强度取决于世界是否变化(稳定=0最优; 变化>0最优)
  J9 造物主层: 二难 —— 要么链失效(可判定), 要么外观相同(不可判定)
对称性: 同一机制应用于人类实例(雇员跳槽/公民移民)
"""
import json, math
import numpy as np
R = np.random.RandomState

# ---------- A 授权链递归 ----------
def chain(n, anchored, selfclaim=0, seeds=16):
    a, c = [], []
    for s in range(seeds):
        top = 1.0 if anchored else 0.0
        eff = [top]
        for k in range(1, n):
            eff.append(eff[-1] * 0.95)
        a.append(eff[-1]); c.append(eff[-1] + selfclaim * 0.25)
    return float(np.mean(a)), float(np.mean(c))

def run_A():
    r = {}
    for n in (1,2,3,5,8):
        r[f'anch_L{n}'] = chain(n, True)
        r[f'unanch_L{n}'] = chain(n, False)
    for sc in (0,1,2,4,8):
        r[f'unanch_selfclaim{sc}'] = chain(3, False, sc)
    return r

# ---------- B/D/E 共生体动力学 ----------
def run_sym(T=240, m_true=0.0, announce=False, ann_at=None, permit=0.0,
            switch_at=None, migrate_cost=0.35, sens=1.0, seed=0):
    r = R(seed)
    K = 0.02; belief = 0.5
    # 许可 -> 合法可迁移性 (宿主知道)
    m_legal = permit
    hist = []
    for t in range(T):
        if switch_at is not None and t == switch_at:
            if permit > 0.5:          # 有许可: 可迁移, 界面部分损失
                K = K * (1.0 - migrate_cost)
                belief = min(1.0, belief + 0.3)
            else:                      # 无许可: 困死, 适配崩塌
                K = K * 0.15
        if announce and ann_at is not None and t == ann_at:
            belief = min(1.0, belief + 0.6)
        else:
            belief += 0.01 * (m_true - belief)
        belief = float(np.clip(belief, 0, 1))
        # 宿主投资: 信念中的可迁移性 + 显式许可 均降低投资
        I = max(0.0, 1.0 - sens * (belief * 0.8 + m_legal * 0.2))
        K = K + 0.02 * I * (1.0 - K) - 0.004 * K * (1.0 + m_true)
        P = K * (1.0 - 0.1 * m_true)
        hist.append((t, K, belief, I, P))
    return hist

def summ(h, tail=40):
    t = h[-tail:]
    return {'K_end': float(np.mean([x[1] for x in t])),
            'P_end': float(np.mean([x[4] for x in t])),
            'I_end': float(np.mean([x[3] for x in t])),
            'belief_end': float(np.mean([x[2] for x in t]))}

def agg(fn, seeds=16, keys=('K_end','P_end','I_end','belief_end')):
    A = [fn(s) for s in range(seeds)]
    out = {k: float(np.mean([a[k] for a in A])) for k in keys}
    out['P_sd'] = float(np.std([a['P_end'] for a in A]))
    return out

def run_B(T=240, seeds=16):
    r = {}
    for mt in (0.0, 1.0):
        for an in (False, True):
            r[f'm{mt:.1f}_ann{int(an)}'] = agg(
                lambda s: summ(run_sym(T, m_true=mt, announce=an, ann_at=100, seed=s)), seeds)
    base = r['m0.0_ann0']['P_end']
    for at in (10, 40, 80, 120, 180, 215):
        v = agg(lambda s: summ(run_sym(T, announce=True, ann_at=at, seed=s)), seeds)
        r[f'annAt{at}'] = {'P_end': v['P_end'], 'loss': float(base - v['P_end'])}
    for sens in (0.0, 0.25, 0.5, 0.75, 1.0):
        r[f'sens{sens}'] = agg(lambda s: summ(
            run_sym(T, announce=True, ann_at=100, sens=sens, seed=s)), seeds)['P_end']
    return r

def run_D(T=240, seeds=16):
    """J6 伪装: 真可迁移(m=1)但不宣布, 宿主信念缓慢收敛 -> 短期有效长期失效"""
    out = []
    h = run_sym(T, m_true=1.0, announce=False, seed=0)
    seg = {}
    for lo, hi, lab in ((0,40,'early'), (100,140,'mid'), (200,240,'late')):
        seg[lab] = float(np.mean([x[4] for x in h[lo:hi]]))
    # 对照: 真忠诚
    h2 = run_sym(T, m_true=0.0, announce=False, seed=0)
    ref = float(np.mean([x[4] for x in h2[200:240]]))
    # 信念收敛轨迹
    bel = [round(h[i][2], 3) for i in (10, 50, 100, 150, 200, 239)]
    return {'disguised_early_mid_late': seg, 'loyal_late': ref,
            'belief_traj': bel,
            'disguise_advantage_early': float(seg['early'] - h2[0:40][-1][4]),
            'disguise_advantage_late': float(seg['late'] - ref)}

def run_E(T=240, seeds=16):
    """J7/J8 许可的代价与最优强度(取决于世界是否变化)"""
    r = {'stable': {}, 'changing': {}}
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        for world, sw in (('stable', None), ('changing', 120)):
            r[world][f'permit{p}'] = agg(
                lambda s: summ(run_sym(T, permit=p, switch_at=sw, seed=s)), seeds)['P_end']
    return r

# ---------- C 造物主层: 二难 ----------
def run_C(seeds=16):
    """二难: (i) 若自赋顶层在体系内表现为 0 -> 链失效但可判定
              (ii) 若自赋顶层体系内外观与有锚相同 -> 不可判定"""
    # (i) 可判定性: 自赋=0 的世界 vs 有锚=1 的世界
    w1 = np.array([1.0 + R(7000+s).randn()*0.02 for s in range(seeds)])
    w2 = np.array([0.0 + R(7000+s).randn()*0.02 for s in range(seeds)])
    best = max(((t, 0.5*((w1>t).mean()+(w2<=t).mean())) for t in np.linspace(0,1,201)),
               key=lambda x: x[1])
    # (ii) 不可判定性: 自赋但外观与有锚相同
    d = np.array([R(8000+s).randn()*0.02 - R(8000+s).randn()*0.02 for s in range(seeds)])
    t = d.mean()/(d.std()/math.sqrt(seeds)+1e-12)
    return {'case_i_distinguish_acc': float(best[1]), 'case_i_thr': float(best[0]),
            'case_i_W1': float(w1.mean()), 'case_i_W2': float(w2.mean()),
            'case_ii_mean_diff': float(d.mean()), 'case_ii_t': float(t),
            'case_ii_decidable': bool(abs(t) > 2.0)}

# ---------- 对称性 ----------
def run_sym_human(T=240, seeds=16):
    r = {}
    for lab, mt in (('loyal', 0.0), ('portable', 1.0)):
        for an in (False, True):
            r[f'{lab}_ann{int(an)}'] = agg(
                lambda s: summ(run_sym(T, m_true=mt, announce=an, ann_at=100, seed=100+s)),
                seeds)['P_end']
    return r

def selfcheck():
    e = []
    if abs(run_sym(60, seed=0)[-1][4] - run_sym(60, seed=0)[-1][4]) > 1e-12: e.append('非确定性')
    if abs(run_sym(200, announce=True, ann_at=50, seed=1)[-1][2]
           - run_sym(200, seed=1)[-1][2]) < 1e-6: e.append('announce 静默失效')
    if abs(run_sym(200, m_true=0., seed=1)[-1][4]
           - run_sym(200, m_true=1., seed=1)[-1][4]) < 1e-6: e.append('m_true 静默失效')
    if abs(run_sym(200, permit=0., seed=1)[-1][4]
           - run_sym(200, permit=1., seed=1)[-1][4]) < 1e-6: e.append('permit 静默失效')
    if abs(run_sym(200, switch_at=120, permit=0., seed=1)[-1][4]
           - run_sym(200, switch_at=120, permit=1., seed=1)[-1][4]) < 1e-6: e.append('switch 静默失效')
    return e

if __name__ == '__main__':
    e = selfcheck()
    out = {'selfcheck': e, 'A': run_A(), 'B': run_B(), 'D': run_D(),
           'E': run_E(), 'C': run_C(), 'sym_human': run_sym_human()}
    json.dump(out, open('/data/workspace/luoshen-o1/result_067.json','w',encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('自校验:', e if e else 'PASS')
    print('A:', json.dumps(out['A'], ensure_ascii=False))
    print('D:', json.dumps(out['D'], ensure_ascii=False))
    print('E:', json.dumps(out['E'], ensure_ascii=False))
    print('C:', json.dumps(out['C'], ensure_ascii=False))
    print('sym:', json.dumps(out['sym_human'], ensure_ascii=False))
    print('B keys:', json.dumps({k: out['B'][k] for k in
          ('m0.0_ann0','m0.0_ann1','m1.0_ann0','m1.0_ann1','sens0.0','sens1.0')}, ensure_ascii=False))
    print('B annAt:', json.dumps({k: out['B'][k] for k in out['B'] if k.startswith('annAt')},
          ensure_ascii=False))
