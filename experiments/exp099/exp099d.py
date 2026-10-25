# -*- coding: utf-8 -*-
"""099d: 修正版 —— 先做保活阳性对照，再注入可读性梯度"""
import os, sys, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1/core')
from life5 import Life5
OUT=os.path.dirname(os.path.abspath(__file__))
BASE=dict(N=8, ratio=0.6, k_seek=0.6, k_sal=0.6, sigma_in=0.15)
STEPS=600; SEEDS=list(range(16))

def skew(s):
    c=np.asarray(s.capacity,float)
    if c.std()<1e-12: return 0.0
    z=(c-c.mean())/c.std(); return float((z**3).mean())

def run(readability, seed, mode='sense'):
    """readability r in [0,1]: 世界可读度。sal 每拍 = r 稳定 + (1-r) 抖动"""
    r=float(readability)
    rng=np.random.default_rng(seed*977+13)
    if mode=='none':
        lf=Life5(seed=seed, **{**BASE,'k_seek':0.0,'k_sal':0.0})
    else:
        lf=Life5(seed=seed, **BASE)
    for t in range(STEPS):
        if mode!='none':
            base=0.3+0.5*r
            lf.sal=np.full(lf.N, max(0.0, base+(1-r)*rng.normal(0,0.25)))
        lf.step()
        if not lf.alive: break
    return lf

READ={'原文':0.863,'换1词':0.771,'换3词':0.721,'换全部':0.683}
print("=== 阳性对照（保活检查）===")
for mode in ['none','sense']:
    a=sum(1 for sd in SEEDS if run(READ['原文'],sd,mode).alive)
    print(f"  {mode:<6} 存活 {a}/16")

print("\n=== 可读性梯度 ===")
res={}; SK={}
for name,r in READ.items():
    sk=[];al=0
    for sd in SEEDS:
        lf=run(r,sd)
        if lf.alive: al+=1; sk.append(skew(lf))
    sk=np.array(sk); SK[name]=sk
    print(f"  {name:<8} r={r:.3f} 存活={al}/16 偏度={sk.mean():.6f}±{sk.std():.6f} (n={len(sk)})")
    res[name]={'r':r,'alive':al,'skew_mean':float(sk.mean()) if len(sk) else None,
               'skew_sd':float(sk.std()) if len(sk)>1 else 0.0,'n':len(sk)}

def paired(a,b):
    A=np.array(SK[a]);B=np.array(SK[b]); n=min(len(A),len(B))
    D=B[:n]-A[:n]
    boot=np.array([np.random.default_rng(k).choice(D,n,replace=True).mean() for k in range(4000)])
    return {'n':int(n),'diff':float(D.mean()),'ci':[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))]}
pc=paired('原文','换全部'); res['paired_orig_vs_all']=pc
print("\n配对 原文->换全部:", json.dumps(pc,ensure_ascii=False))
# 无感官基线配对
base=[]; orig=[]
for sd in SEEDS:
    a=run(0,sd,'none'); b=run(READ['原文'],sd)
    if a.alive and b.alive: base.append(skew(a)); orig.append(skew(b))
base=np.array(base);orig=np.array(orig)
if len(base):
    D=orig-base; boot=np.array([np.random.default_rng(k).choice(D,len(D),replace=True).mean() for k in range(4000)])
    P={'n':int(len(D)),'diff':float(D.mean()),'ci':[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))]}
    res['paired_none_vs_orig']=P
    print("配对 无感官->原文:", json.dumps(P,ensure_ascii=False))
json.dump(res,open(os.path.join(OUT,'result_099d.json'),'w'),ensure_ascii=False,indent=1)
