import time,threading,statistics as st,json,os
def burn(stop):
    s=0
    while not stop.is_set(): s+=1
def meas(n):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter_ns(); s=0
        for i in range(400): s+=i*i
        ts.append(time.perf_counter_ns()-t0)
    return ts
def trial(nthreads,n=300):
    stop=threading.Event(); ths=[]
    for _ in range(nthreads):
        t=threading.Thread(target=burn,args=(stop,),daemon=True); t.start(); ths.append(t)
    time.sleep(0.3)
    x=meas(n)
    stop.set()
    for t in ths: t.join(timeout=1)
    time.sleep(0.2)
    return x
base=trial(0,300)
print('0线程  mean=%.1f sd=%.1f'%(st.mean(base),st.pstdev(base)))
res={'0':{'mean':st.mean(base),'sd':st.pstdev(base)}}
for nt in [1,2,4,8]:
    x=trial(nt,300)
    m,s=st.mean(x),st.pstdev(x)
    d=(m-st.mean(base))/((s**2+res['0']['sd']**2)/2)**0.5
    res[str(nt)]={'mean':m,'sd':s,'d':d}
    print('%d线程 mean=%.1f sd=%.1f  d=%.4f'%(nt,m,s,d))
json.dump(res,open('g0c.json','w'))
