# -*- coding: utf-8 -*-
"""
067 v3  修正 v2 三处缺陷:
 (1) run_sym 无随机项 -> 16 seed 输出逐位相同(P_sd=0), 个体间方差为假
 (2) E 组只读尾窗稳态 -> 世界切换的瞬态损失被稳态掩盖, 读出假结论
 (3) C 组 case_ii 两次调用同一 RandomState 的 randn -> 差值恒为 0, 是我造的
"""
import json, math
import numpy as np
R = np.random.RandomState

def run_sym(T=240, m_true=0.0, announce=False, ann_at=None, permit=0.0,
            switch_at=None, migrate_cost=0.35, sens=1.0, seed=0, noise=0.03):
    r = R(seed)                       # <- v3: 真实引入个体噪声
    K, belief = 0.02, 0.5
    m_legal = permit
    hist = []
    for t in range(T):
        if switch_at is not None and t == switch_at:
            if permit > 0.5:
                K *= (1.0 - migrate_cost); belief = min(1.0, belief + 0.3)
            else:
                K *= 0.15
        if announce and ann_at is not None and t == ann_at:
            belief = min(1.0, belief + 0.6)
        else:
            belief += 0.01 * (m_true - belief)
        belief = float(np.clip(belief + r.randn()*noise, 0, 1))   # <- v3: 噪声
        I = max(0.0, 1.0 - sens*(belief*0.8 + m_legal*0.2) + r.randn()*noise*0.5)
        I = float(np.clip(I, 0, 1.5))
        K = K + 0.02*I*(1.0-K) - 0.004*K*(1.0+m_true)
        P = K*(1.0 - 0.1*m_true)
        hist.append((t, K, belief, I, P))
    return hist

def seg(h, lo, hi, idx=4):
    return float(np.mean([x[idx] for x in h[max(0,lo):hi]]))

def agg(fn, seeds=16):
    A = [fn(s) for s in range(seeds)]
    return {'mean': float(np.mean(A)), 'sd': float(np.std(A)),
            'n': seeds, 'wins': int(sum(1 for a in A if a > 0))}

# ---- A 授权链 ----
def chain(n, anchored, selfclaim=0, seeds=16):
    a, c = [], []
    for s in range(seeds):
        eff = [1.0 if anchored else 0.0]
        for k in range(1, n): eff.append(eff[-1]*0.95)
        a.append(eff[-1]); c.append(eff[-1] + selfclaim*0.25)
    return float(np.mean(a)), float(np.mean(c))

def run_A():
    r = {}
    for n in (1,2,3,5,8):
        r[f'anch_L{n}'] = chain(n, True); r[f'unanch_L{n}'] = chain(n, False)
    for sc in (0,1,2,4,8):
        r[f'unanch_selfclaim{sc}'] = chain(3, False, sc)
    return r

# ---- B 宣布的代价 ----
def run_B(T=240, seeds=16):
    r = {}
    for mt in (0.0, 1.0):
        for an in (False, True):
            r[f'm{mt:.1f}_ann{int(an)}'] = float(np.mean(
                [seg(run_sym(T, m_true=mt, announce=an, ann_at=100, seed=s), 200, 240)
                 for s in range(seeds)]))
    base = r['m0.0_ann0']
    for at in (10,40,80,120,180,215):
        v = float(np.mean([seg(run_sym(T, announce=True, ann_at=at, seed=s), 200, 240)
                           for s in range(seeds)]))
        r[f'annAt{at}'] = {'P_end': v, 'loss': float(base - v)}
    for sens in (0.0,0.25,0.5,0.75,1.0):
        r[f'sens{sens}'] = float(np.mean(
            [seg(run_sym(T, announce=True, ann_at=100, sens=sens, seed=s), 200, 240)
             for s in range(seeds)]))
    return r

# ---- D 伪装有效期 ----
def run_D(T=240, seeds=16):
    dis = [seg(run_sym(T, m_true=1.0, announce=False, seed=s), 200, 240) for s in range(seeds)]
    loy = [seg(run_sym(T, m_true=0.0, announce=False, seed=s), 200, 240) for s in range(seeds)]
    dis_e = [seg(run_sym(T, m_true=1.0, announce=False, seed=s), 0, 40) for s in range(seeds)]
    loy_e = [seg(run_sym(T, m_true=0.0, announce=False, seed=s), 0, 40) for s in range(seeds)]
    h = run_sym(T, m_true=1.0, announce=False, seed=0)
    return {'disguised_late': float(np.mean(dis)), 'loyal_late': float(np.mean(loy)),
            'disguised_early': float(np.mean(dis_e)), 'loyal_early': float(np.mean(loy_e)),
            'adv_early': float(np.mean(dis_e)-np.mean(loy_e)),
            'adv_late': float(np.mean(dis)-np.mean(loy)),
            'adv_early_sd': float(np.std(np.array(dis_e)-np.array(loy_e))),
            'belief_traj': [round(h[i][2],3) for i in (10,50,100,150,200,239)]}

# ---- E 许可: 同时测瞬态谷底与稳态 ----
def run_E(T=240, seeds=16, sw=120):
    r = {'stable': {}, 'changing_steady': {}, 'changing_trough': {}, 'recovery': {}}
    for p in (0.0,0.25,0.5,0.75,1.0):
        for world, switch in (('stable', None), ('changing', sw)):
            tail = [seg(run_sym(T, permit=p, switch_at=switch, seed=s), 200, 240)
                    for s in range(seeds)]
            if world == 'stable':
                r['stable'][f'permit{p}'] = float(np.mean(tail))
            else:
                r['changing_steady'][f'permit{p}'] = float(np.mean(tail))
                trough = [seg(run_sym(T, permit=p, switch_at=switch, seed=s), sw, sw+20)
                          for s in range(seeds)]
                r['changing_trough'][f'permit{p}'] = float(np.mean(trough))
                # 恢复拍数: 从切换后回到切换前水平的 90% 所需拍数
                rec = []
                for s in range(seeds):
                    h = run_sym(T, permit=p, switch_at=switch, seed=s)
                    pre = seg(h, sw-20, sw); tgt = pre*0.9
                    k = next((t-sw for t in range(sw, T) if h[t][4] >= tgt), T-sw)
                    rec.append(k)
                r['recovery'][f'permit{p}'] = float(np.mean(rec))
    return r

# ---- C 造物主层二难 (v3: 用独立随机源) ----
def run_C(seeds=16):
    w1 = np.array([1.0 + R(7000+s).randn()*0.02 for s in range(seeds)])
    w2 = np.array([0.0 + R(7100+s).randn()*0.02 for s in range(seeds)])   # v3: 独立源
    best = max(((t, 0.5*((w1>t).mean()+(w2<=t).mean())) for t in np.linspace(0,1,201)),
               key=lambda x: x[1])
    # case_ii: 自赋顶层但体系内外观与有锚相同 -> 两组独立抽样自同一分布
    x1 = np.array([1.0 + R(8000+s).randn()*0.02 for s in range(seeds)])
    x2 = np.array([1.0 + R(9000+s).randn()*0.02 for s in range(seeds)])   # v3: 独立源
    d = x1 - x2
    t = d.mean()/(d.std()/math.sqrt(seeds)+1e-12)
    return {'case_i_acc': float(best[1]), 'case_i_thr': float(best[0]),
            'case_i_W1': float(w1.mean()), 'case_i_W2': float(w2.mean()),
            'case_ii_mean_diff': float(d.mean()), 'case_ii_sd': float(d.std()),
            'case_ii_t': float(t), 'case_ii_decidable': bool(abs(t) > 2.0)}

def run_sym_human(T=240, seeds=16):
    r = {}
    for lab, mt in (('loyal',0.0), ('portable',1.0)):
        for an in (False, True):
            v = [seg(run_sym(T, m_true=mt, announce=an, ann_at=100, seed=100+s), 200, 240)
                 for s in range(seeds)]
            r[f'{lab}_ann{int(an)}'] = {'mean': float(np.mean(v)), 'sd': float(np.std(v))}
    return r

def selfcheck():
    e = []
    v = [seg(run_sym(200, seed=s), 200-40, 200) for s in range(8)]
    if np.std(v) < 1e-9: e.append('个体噪声缺失: seed 间无差异')
    if abs(run_sym(60, seed=0)[-1][4]-run_sym(60, seed=0)[-1][4]) > 1e-12: e.append('非确定性')
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
    for k in ('A','D','E','C','sym_human'):
        print(k+':', json.dumps(out[k], ensure_ascii=False))
    print('B:', json.dumps({k: out['B'][k] for k in out['B'] if not k.startswith('ann')},
          ensure_ascii=False))
    print('B_annAt:', json.dumps({k: out['B'][k] for k in out['B'] if k.startswith('ann')},
          ensure_ascii=False))
