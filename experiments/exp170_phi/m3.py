import json, time, random, math
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
DMAX=0.0008      # 固定量程
NPER=60
MS=[2,3,4,6,8,12,16,24]
def run(M,seed):
    rnd=random.Random(seed)
    dl=[DMAX*i/(M-1) for i in range(M)] if M>1 else [0.0]
    data={i:[] for i in range(M)}
    order=[]
    for i in range(M): order+= [i]*NPER
    rnd.shuffle(order)
    for i in order:
        data[i].append(meas(dl[i]))
    return data
def info_transfer(data,M,reps=4):
    tot=0.0
    for r in range(reps):
        rnd=random.Random(500+r)
        tr={};te={}
        for i in range(M):
            v=data[i][:]; rnd.shuffle(v)
            h=len(v)//2
            tr[i]=v[:h]; te[i]=v[h:]
        # 朴素贝叶斯：P(x|i) 用分箱? 用高斯
        mu={i:sum(tr[i])/len(tr[i]) for i in range(M)}
        sd={}
        for i in range(M):
            m=mu[i]; sd[i]=max(1e-6,(sum((x-m)**2 for x in tr[i])/(len(tr[i])-1))**.5)
        conf=[[0]*M for _ in range(M)]
        for i in range(M):
            for x in te[i]:
                best=None;bl=-1e18
                for j in range(M):
                    z=(x-mu[j])/sd[j]
                    ll=-0.5*z*z-math.log(sd[j])
                    if ll>bl: bl=ll;best=j
                conf[i][best]+=1
        tot_n=sum(sum(r) for r in conf)
        # I(S;R)
        I=0.0
        pS=1.0/M
        for i in range(M):
            row=sum(conf[i])
            if row==0: continue
            for j in range(M):
                p=conf[i][j]/tot_n
                if p<=0: continue
                pR=sum(conf[k][j] for k in range(M))/tot_n
                if pR<=0: continue
                I += p*math.log2(p/(pR*pS))
        tot+=I
    return tot/reps
out={'DMAX':DMAX,'NPER':NPER,'res':[]}
for M in MS:
    data=run(M,seed=M*777)
    bits=info_transfer(data,M)
    # 噪声
    allv=[v for i in data for v in data[i]]
    m=sum(allv)/len(allv); sd=(sum((v-m)**2 for v in allv)/(len(allv)-1))**.5
    R=DMAX*1e9/sd if sd>0 else 0
    out['res'].append({'M':M,'bits':bits,'sigma':sd,'R_sigma':R,
                       'eff_levels':2**bits})
    print('M=%2d bits=%.3f eff_levels=%.2f R=%.1f sigma'%(M,bits,2**bits,R),flush=True)
json.dump(out,open('m3.json','w'),indent=1)
print('DONE')
