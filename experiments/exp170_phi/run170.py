import os, json, time, random, math, sys

N_PER = 250
LIGHT = 60000
HEAVY = 84000
REPS  = 3

def workload(n):
    s = 0.0
    for i in range(n):
        s += (i * 1.000001) % 7.0
    return s

def cm_sleep(kind, i, n):
    if kind == 'none':   return
    if kind == 'dc':     time.sleep(0.001)
    elif kind == 'linear': time.sleep(0.00001 * i)
    elif kind == 'quad':   time.sleep(0.00001 * (i * i) / n)

def measure_cond(kind, seed=1):
    rnd = random.Random(seed)
    xs, ys = [], []
    order = [0]*N_PER + [1]*N_PER
    rnd.shuffle(order)
    t_start = time.perf_counter()
    k = 0
    for lab in order:
        n = LIGHT if lab == 0 else HEAVY
        t0 = time.perf_counter()
        cm_sleep(kind, k, 2*N_PER)
        workload(n)
        t1 = time.perf_counter()
        v = (t1 - t0) * 1e9
        (xs if lab == 0 else ys).append(v)
        k += 1
    return xs, ys

def dprime(a, b):
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    va = sum((x-ma)**2 for x in a)/max(1,len(a)-1)
    vb = sum((x-mb)**2 for x in b)/max(1,len(b)-1)
    s = math.sqrt((va+vb)/2.0)
    if s == 0: return 0.0
    return abs(ma-mb)/s

def holdout_dprime(xs, ys, bucket_fn, seed=7):
    """随机切分 train/test，用分桶后的类别做似然比判别"""
    rnd = random.Random(seed)
    tot = 0.0
    for r in range(REPS):
        rnd.shuffle(xs); rnd.shuffle(ys)
        hx, hy = len(xs)//2, len(ys)//2
        tr = [(bucket_fn(v),0) for v in xs[:hx]] + [(bucket_fn(v),1) for v in ys[:hy]]
        te = [(bucket_fn(v),0) for v in xs[hx:]] + [(bucket_fn(v),1) for v in ys[hy:]]
        # 估计 P(bucket|class)
        cnt = {0:{},1:{}}
        for bk,c in tr: cnt[c][bk] = cnt[c].get(bk,0)+1
        n0 = sum(cnt[0].values()); n1 = sum(cnt[1].values())
        V = set(list(cnt[0])+list(cnt[1]))
        correct = 0
        for bk,c in te:
            p0 = (cnt[0].get(bk,0)+0.5)/(n0+0.5*len(V))
            p1 = (cnt[1].get(bk,0)+0.5)/(n1+0.5*len(V))
            pred = 0 if p0>p1 else 1
            if pred==c: correct+=1
        tot += correct/len(te)
    return tot/REPS   # accuracy

def make_bucket(xs_all, c, mode):
    lo = min(xs_all); hi = max(xs_all)
    if hi<=lo: hi = lo+1.0
    if mode=='linear':
        B = 8
        w = (hi-lo)/B
        return lambda v: min(B-1, int((v-lo)/w))
    elif mode=='uniform_count':
        pass
    # geometric: edges lo * c^i
    edges=[]; v=lo
    while v < hi and len(edges)<2000:
        edges.append(v); v = v*c if v>0 else v+1.0
        if v<=0: v=lo*1.0001
    edges = sorted(set(edges))
    if len(edges)<2: edges=[lo,hi]
    import bisect
    def f(val):
        i = bisect.bisect_right(edges, val)-1
        return max(0,min(len(edges)-1,i))
    return f

PHI = (1+math.sqrt(5))/2
# 三波那契常数
def trib_r():
    x=1.8
    for _ in range(200):
        x = x - (x**4-2*x**3+1)/(4*x**3-6*x**2)
    return x
TRIB = trib_r()

CANDS = [
    ('linear', None),
    ('geom_1.10', 1.10),
    ('geom_phi_%.3f'%PHI, PHI),
    ('geom_trib_%.3f'%TRIB, TRIB),
    ('geom_2_octave', 2.0),
    ('geom_3', 3.0),
    ('geom_5', 5.0),
    ('geom_10', 10.0),
]

out = {'phi':PHI, 'trib':TRIB, 'conds':{}}
for kind in ['none','dc','linear','quad']:
    xs, ys = measure_cond(kind, seed=hash(kind)%1000)
    raw_d = dprime(xs, ys)
    allv = xs+ys
    res=[]
    for name,c in CANDS:
        bf = make_bucket(allv, c, 'linear' if c is None else 'geom')
        acc = holdout_dprime(list(xs), list(ys), bf)
        # 桶数
        bs=set(bf(v) for v in allv)
        res.append({'name':name,'c':c,'acc':acc,'nbucket':len(bs)})
    sv = sorted(allv)
    p1 = sv[int(0.01*len(sv))]; p99 = sv[int(0.99*len(sv))]
    sd = (sum((v-sum(allv)/len(allv))**2 for v in allv)/len(allv))**0.5
    print('  cond done', kind, flush=True)
    out['conds'][kind] = {
        'raw_dprime': raw_d, 'buckets': res,
        'p1':p1,'p99':p99,'sd':sd,
        'range_ratio': (p99-p1)/sd if sd>0 else None,
    }
    print(kind, 'raw_d=%.3f'%raw_d, 'R=%.1f'%((p99-p1)/sd) if sd>0 else '', flush=True)

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp170_phi/result170.json','w'), indent=1)
print('DONE', json.dumps({k:v['raw_dprime'] for k,v in out['conds'].items()}))
