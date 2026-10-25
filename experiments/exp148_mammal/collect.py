import os, time, threading, json
import numpy as np
LOAD=[0]; STOP=[False]
def worker():
    while not STOP[0]:
        n=LOAD[0]
        if n:
            s=0
            for i in range(n): s+=i*i
        else: time.sleep(0.001)
threading.Thread(target=worker,daemon=True).start()
def work(k=40000):
    s=0
    for i in range(k): s+=i
    return s
def measure():
    t0=time.perf_counter(); work(); return (time.perf_counter()-t0)*1000.0

N=300; SEEDS=8
out={}
for p in ['stable','drift','square']:
    seqs=[]
    for s in range(SEEDS):
        x=[]
        for i in range(N):
            if p=='stable': LOAD[0]=0
            elif p=='drift': LOAD[0]=int(300000*(i/N))
            else: LOAD[0]=300000 if (i//30)%2 else 0
            x.append(measure())
        a=np.asarray(x)
        # 去掉极端离群（被 OS 抢占的长尾，> p99.5 截断，保持真实性但避免单点支配）
        a=np.clip(a, 0, np.percentile(a,99.5))
        seqs.append([float(v) for v in a])
    out[p]=seqs
    m=[float(np.mean(s)) for s in seqs]
    print(p, "n_seq",len(seqs), "mean_range %.3f~%.3f"%(min(m),max(m)))
STOP[0]=True
json.dump(out, open('real_series.json','w'))
print("saved")
