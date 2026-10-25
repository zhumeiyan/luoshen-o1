import json, math, os, random
import numpy as np
exec(open('run148c.py').read().split("D=json.load")[0])
D=json.load(open('real_series.json'))
def ci(d):
    d=np.asarray(d,float); m=d.mean(); se=d.std(ddof=1)/math.sqrt(len(d))
    return float(m), float(m-1.96*se), float(m+1.96*se)
def sig(lo,hi): return bool(lo>0 or hi<0)
R={}

# ---------- 梦 ----------
dream={}
for p in ['stable','drift','square']:
    base=[run3(D[p][s],'none',False,s) for s in range(8)]
    dream[p]={'none':float(np.mean(base))}
    for c in ['real','rev','shuf','cross','noise']:
        v=[run3(D[p][s],c,False,s,other=D[p][(s+4)%8]) for s in range(8)]
        m,lo,hi=ci([b-a for b,a in zip(base,v)])
        dream[p][c]=dict(mae=float(np.mean(v)),gain=m,lo=lo,hi=hi,sig=sig(lo,hi))
    # mismatch: square 的个体用 stable 的真实经历
    if p=='square':
        v=[run3(D['square'][s],'cross',False,s,other=D['stable'][s]) for s in range(8)]
        m,lo,hi=ci([b-a for b,a in zip(base,v)])
        dream[p]['mismatch']=dict(mae=float(np.mean(v)),gain=m,lo=lo,hi=hi,sig=sig(lo,hi))
R['dream']=dream

# ---------- 梦剂量扫描 ----------
dose={}
for r in [1,2,4,8]:
    b=[run3(D['stable'][s],'none',False,s) for s in range(8)]
    row={}
    for c in ['real','shuf']:
        v=[run3(D['stable'][s],c,False,s,rounds=r) for s in range(8)]
        m,lo,hi=ci([x-y for x,y in zip(b,v)])
        row[c]=dict(gain=m,lo=lo,hi=hi,mae=float(np.mean(v)))
    row['real_minus_shuf']=float(row['real']['mae']*0+ (np.mean([run3(D['stable'][s],'shuf',False,s,rounds=r) for s in range(8)])-np.mean([run3(D['stable'][s],'real',False,s,rounds=r) for s in range(8)])))
    dose[r]=row
R['dose']=dose

# ---------- 情绪门 ----------
gate={}
for p in ['stable','drift','square']:
    a=[run3(D[p][s],'none',True,s) for s in range(8)]
    b=[run3(D[p][s],'none',False,s) for s in range(8)]
    m,lo,hi=ci([y-x for x,y in zip(a,b)])
    gate[p]=dict(gate=float(np.mean(a)),fixed=float(np.mean(b)),gain=m,lo=lo,hi=hi,sig=sig(lo,hi))
R['gate']=gate

# ---------- 玩 ----------
def scand(p):
    try:
        e=list(os.scandir(p)); return [x.path for x in e if x.is_dir()], sum(1 for x in e if x.is_file())
    except Exception: return [],0
TREE={}; ROOT='/usr/lib/python3.10'
def rec(p,d,maxd=3):
    if d>maxd: return
    dirs,nf=scand(p); TREE[p]=dict(nfile=nf,depth=d)
    for q in dirs[:12]: rec(q,d+1)
rec(ROOT,0)
truth=float(np.mean([v['nfile'] for v in TREE.values()])); nodes=list(TREE.keys())
def phase(mode,seed,budget=30):
    rng=random.Random(seed); seen=set(); obs=[]; dirs_seen=[]
    for _ in range(budget):
        if mode=='play':
            cand=[n for n in nodes if n not in seen] or nodes
            cand.sort(key=lambda p:TREE[p]['depth']+rng.random()*2); p=cand[0]
        elif mode=='rand_norep':
            cand=[n for n in nodes if n not in seen] or nodes; p=rng.choice(cand)
        else: p=rng.choice(nodes)
        seen.add(p); dirs_seen.append(p); obs.append(TREE[p]['nfile'])
    return obs, len(set(dirs_seen))
def task(obs,seed,extra=10):
    rng=random.Random(seed*7919+13)
    return float(np.mean(list(obs)+[TREE[rng.choice(nodes)]['nfile'] for _ in range(extra)]))
play={}
for mode in ['play','rand_norep','rand']:
    errs=[];u=[]
    for s in range(24):
        o,uq=phase(mode,s); errs.append(abs(task(o,s)-truth)/truth); u.append(uq)
    play[mode]=dict(err=float(np.mean(errs)), uniq_dirs=float(np.mean(u)))
a=[abs(task(phase('play',s)[0],s)-truth)/truth for s in range(24)]
b=[abs(task(phase('rand',s)[0],s)-truth)/truth for s in range(24)]
c=[abs(task(phase('rand_norep',s)[0],s)-truth)/truth for s in range(24)]
m,lo,hi=ci([y-x for x,y in zip(a,b)]); play['play_vs_rand']=dict(gain=m,lo=lo,hi=hi,sig=sig(lo,hi))
m2,lo2,hi2=ci([y-x for x,y in zip(a,c)]); play['play_vs_rand_norep']=dict(gain=m2,lo=lo2,hi=hi2,sig=sig(lo2,hi2))
play['truth']=truth; play['spontaneous_acts']=30
R['play']=play
json.dump(R, open('result148.json','w'), indent=1, ensure_ascii=False)
print(json.dumps(R, indent=1, ensure_ascii=False)[:2600])
