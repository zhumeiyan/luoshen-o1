import os, time, threading
import numpy as np

LOAD=[0]
def worker():
    while True:
        n=LOAD[0]
        if n: 
            s=0
            for i in range(n): s+=i*i
        else:
            time.sleep(0.0005)
t=threading.Thread(target=worker,daemon=True); t.start()

def measure():
    t0=time.perf_counter()
    os.listdir('/usr/lib')
    return (time.perf_counter()-t0)*1000.0

def run(profile,n=240):
    out=[]
    for i in range(n):
        if profile=='stable': LOAD[0]=0
        elif profile=='drift': LOAD[0]=int(150000*(i/n))
        elif profile=='square': LOAD[0]=250000 if (i//30)%2 else 0
        out.append(measure())
    return np.asarray(out)

for p in ['stable','drift','square']:
    x=run(p)
    tr=np.polyfit(np.arange(len(x)),x,1)[0]
    print(f"{p:7s} mean={x.mean():.4f}ms std={x.std():.4f} trend={tr:.6f} first50={x[:50].mean():.4f} last50={x[-50:].mean():.4f}")
