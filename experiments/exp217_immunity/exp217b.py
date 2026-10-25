# -*- coding: utf-8 -*-
"""217b：重新标定。威胁优势调小(C=0.15)，扫描见证人采样率 s，修误伤指标"""
import numpy as np, json

BASE, B, C, K, GENS = 1.0, 0.6, 0.15, 200, 400
LAM, FP, NOISE = 0.15, 0.02, 0.05

def run(scenario, strategy, seed, s=0.3, m=0.01, q=0.01, adaptive=False):
    rng = np.random.default_rng(seed); N = K
    typ = np.zeros(N, dtype=np.int8); mark = np.zeros(N, dtype=np.int8)
    contrib = np.ones(N, dtype=float)
    if scenario == 'external':
        n0 = max(1, int(0.02 * N)); typ[:n0] = 1; mark[:n0] = 1; contrib[:n0] = 0.0
    n_mis = 0; first_clear = None; Hl = []
    for g in range(GENS):
        G = contrib.mean()
        fit = BASE + B * G - C * contrib
        if strategy in ('witness', 'combo'):
            fit = np.where(typ == 0, fit - LAM * s, fit)
        fit = np.clip(fit, 1e-6, None)
        idx = rng.choice(N, size=N, replace=True, p=fit / fit.sum())
        typ, mark, contrib = typ[idx].copy(), mark[idx].copy(), contrib[idx].copy()
        if scenario == 'external':
            n_in = rng.binomial(N, m)
            if n_in:
                pos = rng.choice(N, size=n_in, replace=False); typ[pos]=1; mark[pos]=1; contrib[pos]=0.0
        else:
            mut = (rng.random(N) < q) & (typ == 0)
            if mut.any(): typ[mut] = 1; contrib[mut] = 0.0
        kill = np.zeros(N, dtype=bool)
        mis_this = 0
        if strategy == 'marker':
            kill |= (mark == 1)
        elif strategy == 'selfreport':
            kill |= (np.where(typ == 1, 1.0, contrib) < 0.5)
        elif strategy in ('witness', 'combo'):
            if strategy == 'combo': kill |= (mark == 1)
            n_s = max(1, int(round(s * N)))
            samp = rng.choice(N, size=n_s, replace=False)
            bad = samp[contrib[samp] + rng.normal(0, NOISE, n_s) < 0.5]
            kk = np.zeros(N, dtype=bool); kk[bad] = True; kill |= kk
        mis = (typ == 0) & kill
        mis_this = int(mis.sum()); n_mis += mis_this
        alive = ~kill
        if alive.sum() == 0: alive[:] = True; typ[:]=0; mark[:]=0; contrib[:]=1.0
        if alive.sum() < N:
            rep = rng.choice(np.where(alive)[0], size=N-alive.sum(), replace=True)
            ai = np.concatenate([np.where(alive)[0], rep])
        else: ai = np.where(alive)[0]
        typ, mark, contrib = typ[ai], mark[ai], contrib[ai]
        Hl.append(float(contrib.mean()))
        if float((typ==1).mean()) == 0.0 and first_clear is None and g > 5: first_clear = g
    return {'scenario':scenario,'strategy':strategy,'seed':seed,'s':s,
            'threat_final':float((typ==1).mean()),'H_final':float(contrib.mean()),
            'H_mean_last50':float(np.mean(Hl[-50:])),
            'mis_per_gen':n_mis/(GENS*N),'clear_gen':first_clear,
            'H_hist':[round(x,4) for x in Hl[::8]]}

if __name__ == '__main__':
    STRATS = ['none','marker','selfreport','witness','combo']
    SEEDS = [0,1,2,3,4]
    out = {}
    print('=== 采样率扫描（witness, 内生场景）===')
    print(f"{'s':>6}{'威胁终值':>10}{'H终值':>10}{'误杀/代':>10}")
    scan = []
    for s in [0.05,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
        rs = [run('internal','witness',sd,s=s) for sd in SEEDS]
        tf=np.mean([r['threat_final'] for r in rs]); hf=np.mean([r['H_final'] for r in rs])
        mg=np.mean([r['mis_per_gen'] for r in rs])
        scan.append({'s':s,'threat_final':round(tf,4),'H_final':round(hf,4),'mis_per_gen':round(mg,5)})
        print(f"{s:>6}{tf:>10.3f}{hf:>10.3f}{mg:>10.4f}")
    out['scan_s'] = scan
    print()
    for sc,key in (('external','A_external'),('internal','B_internal')):
        print(f'=== {"A 外部威胁(带非己标记)" if sc=="external" else "B 内生威胁(marker=self)"} ===')
        print(f"{'策略':<12}{'威胁终值':>10}{'H终值':>10}{'误杀/代':>10}{'清零':>7}")
        rows=[]
        for st in STRATS:
            rs=[run(sc,st,sd,s=0.3) for sd in SEEDS]
            tf=np.mean([r['threat_final'] for r in rs]); hf=np.mean([r['H_final'] for r in rs])
            mg=np.mean([r['mis_per_gen'] for r in rs])
            cg=sum(1 for r in rs if r['clear_gen'] is not None)
            rows.append({'strategy':st,'threat_final':round(tf,4),'H_final':round(hf,4),
                         'mis_per_gen':round(mg,5),'cleared':f"{cg}/{len(rs)}"})
            print(f"{st:<12}{tf:>10.3f}{hf:>10.3f}{mg:>10.4f}{str(cg)+'/'+str(len(rs)):>7}")
        out[key]=rows
        print()
    json.dump(out, open('result217b.json','w'), ensure_ascii=False, indent=1)
    print('saved result217b.json')
