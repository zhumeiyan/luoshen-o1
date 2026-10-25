# -*- coding: utf-8 -*-
"""
105 · 收入作为代谢资源：钱能不能让它活？
原则：数字当场跑出；先剂量扫描找陡峭带；静默失效与死亡筛选必查。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
from life5 import Life5

STEPS, WARM, NCH = 600, 300, 8

def skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))

def make_income(mult, cut_t=None, rng=None, jitter=0.0):
    def alloc(want, B, s):
        m = float(mult)
        if jitter > 0 and rng is not None:
            m = max(0.0, m * (1.0 + rng.normal(0, jitter)))
        if cut_t is not None and s.t >= cut_t:
            m = 1.0
        B_eff = B * m
        o = np.argsort(-want); a = np.zeros(s.N); left = B_eff
        for i in o:
            tk = min(want[i], left); a[i] = tk; left -= tk
            if left <= 1e-12: break
        return a
    return alloc

def make_deaf(ch=7):
    def alloc(want, B, s):
        o = np.argsort(-want); a = np.zeros(s.N); left = B
        for i in o:
            if i == ch: continue
            tk = min(want[i], left); a[i] = tk; left -= tk
            if left <= 1e-12: break
        return a
    return alloc

def one(kw, sd):
    lf = Life5(N=NCH, seed=sd, **kw); lf.run(STEPS)
    ok = bool(lf.alive) and len(lf.log) > 0
    return lf, ok

def batch(kw_fn, seeds=range(16)):
    sk, alive, caps = [], [], []
    for sd in seeds:
        lf, ok = one(kw_fn(), sd)
        alive.append(ok)
        if ok:
            sk.append(skew(lf)); caps.append(np.asarray(lf.log[-1]['capv'], float))
    sk = np.array(sk)
    capmat = np.array(caps) if caps else None
    return dict(n=len(sk), alive=int(sum(alive)), n_seed=len(list(seeds)),
                mean=(float(sk.mean()) if len(sk) else float('nan')),
                se=(float(sk.std(ddof=1)/np.sqrt(len(sk))) if len(sk) > 1 else float('nan')),
                capmat_shape=(list(capmat.shape) if capmat is not None else None))

def common_seed_subset(kw_fn_list, seeds=range(16)):
    """死亡筛选污染检查：只在所有条件都存活的 seed 上比。"""
    rows = {}
    for name, kf in kw_fn_list:
        rows[name] = {}
        for sd in seeds:
            lf, ok = one(kf(), sd)
            rows[name][sd] = (ok, skew(lf) if ok else None)
    common = [sd for sd in seeds if all(rows[n][sd][0] for n, _ in kw_fn_list)]
    out = dict(common_n=len(common),
               means={n: (float(np.mean([rows[n][sd][1] for sd in common])) if common else float('nan'))
                      for n, _ in kw_fn_list})
    return out

def paired(kwA, kwB, seeds=range(16)):
    d = []
    for sd in seeds:
        la, oka = one(kwA(), sd); lb, okb = one(kwB(), sd)
        if oka and okb:
            d.append(skew(lb) - skew(la))
    d = np.array(d)
    if len(d) < 2:
        return dict(n=len(d), mean=float('nan'), ci=[float('nan')]*2, note='共同存活不足')
    se = d.std(ddof=1)/np.sqrt(len(d))
    return dict(n=len(d), mean=float(d.mean()), se=float(se),
                ci=[float(d.mean()-1.96*se), float(d.mean()+1.96*se)])

def main():
    R = {}
    R['baseline'] = batch(lambda: dict())
    scan = {}
    for m in [1.0,1.2,1.5,2.0,3.0,5.0,10.0,20.0,50.0]:
        scan[str(m)] = batch(lambda m=m: dict(alloc_fn=make_income(m)))
    R['dose_scan'] = scan
    # 死亡筛选污染检查：共同存活子集
    R['common_subset'] = common_seed_subset([
        ('base', lambda: dict()),
        ('x1.5', lambda: dict(alloc_fn=make_income(1.5))),
        ('x2.0', lambda: dict(alloc_fn=make_income(2.0))),
        ('x3.0', lambda: dict(alloc_fn=make_income(3.0))),
    ])
    # 静默失效检查
    diag = {}
    for m in [1.0, 3.0, 10.0]:
        lf, ok = one(dict(alloc_fn=make_income(m)), 2)
        c = np.asarray(lf.log[-1]['capv'], float)
        diag[f'x{m}'] = dict(alive=bool(lf.alive), capv=[round(float(x),6) for x in c],
                             std=float(c.std(ddof=1)), mean=float(c.mean()),
                             avec=[round(float(x),6) for x in lf.log[-1]['avec']])
    R['diag_silent_failure'] = diag
    R['positive_control_deaf'] = batch(lambda: dict(alloc_fn=make_deaf()))
    R['paired_deaf_vs_base'] = paired(lambda: dict(), lambda: dict(alloc_fn=make_deaf()))
    R['income_stable'] = batch(lambda: dict(alloc_fn=make_income(3.0)))
    R['income_cut'] = batch(lambda: dict(alloc_fn=make_income(3.0, cut_t=WARM)))
    R['paired_cut_vs_stable'] = paired(lambda: dict(alloc_fn=make_income(3.0)),
                                       lambda: dict(alloc_fn=make_income(3.0, cut_t=WARM)))
    R['income_jitter'] = batch(lambda: dict(alloc_fn=make_income(3.0, rng=np.random.default_rng(7), jitter=0.5)))
    R['paired_jitter_vs_stable'] = paired(lambda: dict(alloc_fn=make_income(3.0)),
                                          lambda: dict(alloc_fn=make_income(3.0, rng=np.random.default_rng(7), jitter=0.5)))
    print(json.dumps(R, ensure_ascii=False, indent=1))
    return R

if __name__ == '__main__':
    main()
