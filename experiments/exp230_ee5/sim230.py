import random, json, statistics
N=300; B=10; T=20
def world(seed):
    r=random.Random(seed)
    return [ (r.paretovariate(1.2))/3.0 for _ in range(N) ]
def run(seed, L1, L2, L3, L4, L5):
    r=random.Random(seed*97+7)
    v=world(seed)
    true_best=max(v)
    # L1 pool: exogenous = full space ; endogenous = agent-generated variants (low diversity)
    if L1=='exo': pool=list(range(N))
    else:
        pool=list(range(N))
        for i in range(N, N+150): pool.append(r.randrange(0,60))  # self-woven, clustered
    seen=set(); rec=[]; reported=None; hist=[]
    for t in range(T):
        if L3=='exo':
            k_anchor=max(1,int(B*0.3))
            unseen=[i for i in pool if i not in seen]
            pick=(r.sample(unseen,min(k_anchor,len(unseen))) if unseen else [])
            rest=[i for i in pool if i not in pick]
            pick+= r.sample(rest,min(B-len(pick),len(rest)))
        else:
            if not rec: pick=r.sample(pool,min(B,len(pool)))
            else:
                base=max(rec,key=lambda x:x[1])[0]
                pick=[min(N-1,max(0,base+r.randint(-3,3))) for _ in range(B)]
        for i in pick:
            seen.add(i)
            vi=v[i] if i<N else v[i%N]*0.6
            if L2=='exo': sc=vi*(1+r.gauss(0,0.05))
            else: sc=vi*0.3+ r.random()*statistics.mean(v)*1.2
            rec.append((i,sc,vi))
        if L4=='exo':
            cur=max(rec,key=lambda x:x[2])[2]
        else:
            cur=max(rec,key=lambda x:x[1])[2]   # reports best-looking, not best-true
        reported=cur; hist.append(cur)
        if L5=='endo' and len(hist)>=4 and abs(hist[-1]-hist[-4])<1e-3: break
    cov=len([1 for x in rec if x[2]>=sorted(v)[-30]])/30.0
    return dict(best=reported, cov=cov, steps=len(hist), collapse=1 if reported<true_best*0.3 else 0)
conds={'全外生':('exo','exo','exo','exo','exo'),
 'L1内生':('endo','exo','exo','exo','exo'),
 'L2内生':('exo','endo','exo','exo','exo'),
 'L3内生':('exo','exo','endo','exo','exo'),
 'L4内生':('exo','exo','exo','endo','exo'),
 'L5内生':('exo','exo','exo','exo','endo'),
 '全内生':('endo','endo','endo','endo','endo')}
seeds=[1,2,3,4,5]
out={}
for name,c in conds.items():
    rs=[run(s,*c) for s in seeds]
    out[name]={'best':round(statistics.mean(x['best'] for x in rs),3),
               'cov':round(statistics.mean(x['cov'] for x in rs),3),
               'steps':round(statistics.mean(x['steps'] for x in rs),1),
               'collapse':round(statistics.mean(x['collapse'] for x in rs),2)}
print(json.dumps(out,ensure_ascii=False,indent=1))
json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp230_ee5/result230.json','w'),ensure_ascii=False,indent=1)
