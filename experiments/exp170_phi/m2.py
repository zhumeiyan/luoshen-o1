import json, time, random, math, bisect
N=200
WORK=20000
def workload(n):
    s=0.0
    for i in range(n): s+=(i*1.000001)%7.0
    return s
def meas(slp):
    t0=time.perf_counter()
    if slp>0: time.sleep(slp)
    workload(WORK)
    return (time.perf_counter()-t0)*1e9
DELTAS=[0.0002,0.0005,0.001,0.002,0.004,0.008]
def cond(delta,seed):
    rnd=random.Random(seed)
    A=[];B=[]
    order=[0]*N+[1]*N
    rnd.shuffle(order)
    for lab in order:
        v=meas(0.0 if lab==0 else delta)
        (A if lab==0 else B).append(v)
    return A,B
def acc_at(A,B,nb):
    """held-out acc using equal-width bins over pooled range, nb bins"""
    allv=A+B
    lo=min(allv);hi=max(allv)
    if hi<=lo: return 0.5
    w=(hi-lo)/nb
    f=lambda v: min(nb-1,int((v-lo)/w))
    tot=0.0
    for r in range(4):
        rnd=random.Random(100+r)
        AA=A[:];BB=B[:]
        rnd.shuffle(AA);rnd.shuffle(BB)
        h=len(AA)//2
        tr=[(f(v),0) for v in AA[:h]]+[(f(v),1) for v in BB[:h]]
        te=[(f(v),0) for v in AA[h:]]+[(f(v),1) for v in BB[h:]]
        cnt={0:{},1:{}}
        for bk,c in tr: cnt[c][bk]=cnt[c].get(bk,0)+1
        n0=sum(cnt[0].values());n1=sum(cnt[1].values())
        V=set(list(cnt[0])+list(cnt[1]))
        ok=0
        for bk,c in te:
            p0=(cnt[0].get(bk,0)+0.5)/(n0+0.5*len(V))
            p1=(cnt[1].get(bk,0)+0.5)/(n1+0.5*len(V))
            if (0 if p0>p1 else 1)==c: ok+=1
        tot+=ok/len(te)
    return tot/4
def dprime(a,b):
    ma=sum(a)/len(a);mb=sum(b)/len(b)
    va=sum((x-ma)**2 for x in a)/(len(a)-1);vb=sum((x-mb)**2 for x in b)/(len(b)-1)
    s=math.sqrt((va+vb)/2)
    return abs(ma-mb)/s if s>0 else 0.0
out={'deltas':DELTAS,'res':[]}
BS=[2,3,4,6,8,12,16,24,32,48]
for d in DELTAS:
    A,B=cond(d,seed=int(d*1e6)%9999)
    sv=sorted(A+B)
    p1=sv[int(.01*len(sv))];p99=sv[int(.99*len(sv))]
    sa=(sum((v-sum(A)/len(A))**2 for v in A)/(len(A)-1))**.5
    sb=(sum((v-sum(B)/len(B))**2 for v in B)/(len(B)-1))**.5
    sig=math.sqrt((sa*sa+sb*sb)/2)
    R=(p99-p1)/sig if sig>0 else 0
    accs=[acc_at(A,B,nb) for nb in BS]
    # B* = smallest nb reaching 98% of max acc
    mx=max(accs)
    thr=0.5+(mx-0.5)*0.98
    bstar=None
    for nb,a in zip(BS,accs):
        if a>=thr: bstar=nb;break
    if bstar is None: bstar=BS[-1]
    cstar=R**(1.0/bstar) if R>1 and bstar>0 else None
    out['res'].append({'delta':d,'dprime':dprime(A,B),'R':R,'sigma':sig,
                       'accs':dict(zip(BS,accs)),'Bstar':bstar,'cstar':cstar,
                       'phi':(1+math.sqrt(5))/2})
    print(d,'d=%.2f'%dprime(A,B),'R=%.1f'%R,'B*=%s'%bstar,'c*=%s'%(round(cstar,3) if cstar else None),flush=True)
json.dump(out,open('m2.json','w'),indent=1)
print('DONE')
