# -*- coding: utf-8 -*-
"""217c：最终版。加回误伤、测和平麻痹、算净值(H - 抗体开销)"""
import numpy as np, json

BASE,B,C,K,GENS = 1.0,0.6,0.15,200,400
LAM,FP,NOISE = 0.15,0.02,0.05

def run(scenario,strategy,seed,s=0.3,m=0.01,q=0.01,adaptive=False):
    rng=np.random.default_rng(seed); N=K
    typ=np.zeros(N,dtype=np.int8); mark=np.zeros(N,dtype=np.int8); contrib=np.ones(N)
    if scenario=='external':
        n0=max(1,int(0.02*N)); typ[:n0]=1; mark[:n0]=1; contrib[:n0]=0.0
    n_mis=0; n_killed=0; first_clear=None; Hl=[]; Tl=[]
    thr=0.02
    for g in range(GENS):
        G=contrib.mean()
        fit=BASE+B*G-C*contrib
        if strategy in ('witness','combo'): fit=np.where(typ==0, fit-LAM*s, fit)
        fit=np.clip(fit,1e-6,None)
        idx=rng.choice(N,size=N,replace=True,p=fit/fit.sum())
        typ,mark,contrib=typ[idx].copy(),mark[idx].copy(),contrib[idx].copy()
        if scenario=='external':
            n_in=rng.binomial(N,m)
            if n_in:
                pos=rng.choice(N,size=n_in,replace=False); typ[pos]=1; mark[pos]=1; contrib[pos]=0.0
        else:
            mut=(rng.random(N)<q)&(typ==0)
            if mut.any(): typ[mut]=1; contrib[mut]=0.0
        kill=np.zeros(N,dtype=bool)
        if strategy=='marker':
            kill|=(mark==1); kill|=(rng.random(N)<FP)          # 假阳性：误伤宿主
        elif strategy=='selfreport':
            kill|=(np.where(typ==1,1.0,contrib)<0.5)            # 威胁者谎报 → 不杀
            kill|=(rng.random(N)<FP)
        elif strategy in ('witness','combo'):
            if strategy=='combo': kill|=(mark==1); kill|=(rng.random(N)<FP)
            n_s=max(1,int(round(s*N)))
            samp=rng.choice(N,size=n_s,replace=False)
            kk=np.zeros(N,dtype=bool); kk[samp[contrib[samp]+rng.normal(0,NOISE,n_s)<0.5]]=True
            kill|=kk
        if adaptive and strategy in ('witness','combo','marker'):
            frac=kill.mean()
            thr=thr+0.02*(0.02-frac)      # 清得多 → 放松（自我校准）
            if frac>thr:
                kill &= ~(rng.random(N)<min(0.9,(frac-thr)/max(frac,1e-9)))
        n_mis+=int(((typ==0)&kill).sum()); n_killed+=int(kill.sum())
        alive=~kill
        if alive.sum()==0: alive[:]=True; typ[:]=0; mark[:]=0; contrib[:]=1.0
        if alive.sum()<N:
            rep=rng.choice(np.where(alive)[0],size=N-alive.sum(),replace=True)
            ai=np.concatenate([np.where(alive)[0],rep])
        else: ai=np.where(alive)[0]
        typ,mark,contrib=typ[ai],mark[ai],contrib[ai]
        Hl.append(float(contrib.mean())); Tl.append(float((typ==1).mean()))
        if float((typ==1).mean())==0.0 and first_clear is None and g>5: first_clear=g
    Hf=float(contrib.mean())
    cost = LAM*s if strategy in ('witness','combo') else 0.0
    return {'scenario':scenario,'strategy':strategy,'seed':seed,'s':s,
            'threat_final':float((typ==1).mean()),'H_final':Hf,
            'net':Hf-cost,'cost':cost,
            'H_mean_last50':float(np.mean(Hl[-50:])),
            'mis_per_gen':n_mis/(GENS*N),
            'mis_share':n_mis/max(n_killed,1),
            'clear_gen':first_clear,
            'H_hist':[round(x,4) for x in Hl[::8]],'T_hist':[round(x,4) for x in Tl[::8]]}

if __name__=='__main__':
    SEEDS=[0,1,2,3,4]; out={}
    print('=== 采样率扫描（内生, witness）：净值 = H - 抗体开销 ===')
    print(f"{'s':>6}{'威胁终值':>10}{'H终值':>10}{'净值':>10}{'误杀/代':>10}")
    scan=[]
    for s in [0.05,0.1,0.15,0.2,0.3,0.4,0.5,0.7,0.9,1.0]:
        rs=[run('internal','witness',sd,s=s) for sd in SEEDS]
        tf=np.mean([r['threat_final'] for r in rs]); hf=np.mean([r['H_final'] for r in rs])
        nt=np.mean([r['net'] for r in rs]); mg=np.mean([r['mis_per_gen'] for r in rs])
        scan.append({'s':s,'threat':round(tf,4),'H':round(hf,4),'net':round(nt,4),'mis':round(mg,5)})
        print(f"{s:>6}{tf:>10.3f}{hf:>10.3f}{nt:>10.3f}{mg:>10.4f}")
    out['scan_s']=scan
    best=max(scan,key=lambda d:d['net']); out['best_s']=best
    print(f">>> 最优 s = {best['s']}  净值 {best['net']}\n")
    for sc,key in (('external','A_external'),('internal','B_internal')):
        print(f'=== {"A 外部(带非己标记)" if sc=="external" else "B 内生(marker=self)"} ===')
        print(f"{'策略':<12}{'威胁终值':>10}{'H终值':>10}{'误杀/代':>10}{'误杀占比':>10}{'清零':>7}")
        rows=[]
        for st in ['none','marker','selfreport','witness','combo']:
            rs=[run(sc,st,sd,s=0.3) for sd in SEEDS]
            tf=np.mean([r['threat_final'] for r in rs]); hf=np.mean([r['H_final'] for r in rs])
            mg=np.mean([r['mis_per_gen'] for r in rs]); ms=np.mean([r['mis_share'] for r in rs])
            cg=sum(1 for r in rs if r['clear_gen'] is not None)
            rows.append({'strategy':st,'threat':round(tf,4),'H':round(hf,4),
                         'mis_per_gen':round(mg,5),'mis_share':round(ms,4),'cleared':f"{cg}/5"})
            print(f"{st:<12}{tf:>10.3f}{hf:>10.3f}{mg:>10.4f}{ms:>10.3f}{str(cg)+'/5':>7}")
        out[key]=rows; print()
    print('=== 和平麻痹：外部见证人 vs 自我校准（内生场景）===')
    print(f"{'模式':<14}{'威胁终值':>10}{'H终值':>10}{'末阈值':>10}")
    par=[]
    for mode,ad in (('witness(外部见证人)',False),('witness(自我校准)',True)):
        rs=[run('internal','witness',sd,s=0.3,adaptive=ad) for sd in SEEDS]
        tf=np.mean([r['threat_final'] for r in rs]); hf=np.mean([r['H_final'] for r in rs])
        par.append({'mode':mode,'threat':round(tf,4),'H':round(hf,4),
                    'per_seed_threat':[round(r['threat_final'],3) for r in rs]})
        print(f"{mode:<14}{tf:>10.3f}{hf:>10.3f}")
    out['paralysis']=par
    json.dump(out,open('result217c.json','w'),ensure_ascii=False,indent=1)
    print('\nsaved result217c.json')
