import time,statistics as st,json,math
def acquire(n,work=300):
    xs=[]
    for _ in range(n):
        t0=time.perf_counter_ns(); s=0
        for i in range(work): s+=i*i
        xs.append(time.perf_counter_ns()-t0)
    return xs
def allan(xs,taus):
    out={}
    for m in taus:
        if m*2>len(xs): continue
        # 连续窗口平均的相邻差
        means=[st.mean(xs[i*m:(i+1)*m]) for i in range(len(xs)//m)]
        diffs=[means[i+1]-means[i] for i in range(len(means)-1)]
        out[m]=math.sqrt(st.mean([d*d for d in diffs])/2.0)
    return out
print('采集真实CPU时序抖动 20000 次...')
xs=acquire(20000)
print('n=%d mean=%.1fns sd=%.1fns cv=%.4f'%(len(xs),st.mean(xs),st.pstdev(xs),st.pstdev(xs)/st.mean(xs)))
taus=[1,2,4,8,16,32,64,128,256,512,1024]
A=allan(xs,taus)
print('\nAllan deviation (窗口m -> sigma_A):')
print('%8s %12s %12s %10s'%('窗口m','sigma_A(ns)','理论白噪','效率'))
s1=A[1]
slopes={}
prev=None
for m in sorted(A):
    white=s1/math.sqrt(m)
    eff=white/A[m] if A[m]>0 else 0
    print('%8d %12.1f %12.1f %10.3f'%(m,A[m],white,eff))
# 局部斜率 d log sigma / d log m
ks=sorted(A)
print('\n局部斜率 (白噪=-0.5, 闪烁=0, 随机游走=+0.5):')
for i in range(len(ks)-1):
    m1,m2=ks[i],ks[i+1]
    sl=(math.log(A[m2])-math.log(A[m1]))/(math.log(m2)-math.log(m1))
    print('  m %4d->%4d  斜率=%+.3f'%(m1,m2,sl))
    slopes['%d_%d'%(m1,m2)]=sl
json.dump({'allan':{str(k):v for k,v in A.items()},'slopes':slopes,'sd1':st.pstdev(xs),'mean':st.mean(xs)},open('allan.json','w'),indent=1)
