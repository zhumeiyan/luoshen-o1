import os, time, threading
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

def run(profile,n=240):
    out=[]
    for i in range(n):
        if profile=='stable': LOAD[0]=0
        elif profile=='drift': LOAD[0]=int(300000*(i/n))
        elif profile=='square': LOAD[0]=300000 if (i//30)%2 else 0
        out.append(measure())
    return np.asarray(out)
for p in ['stable','drift','square']:
    x=run(p); tr=np.polyfit(np.arange(len(x)),x,1)[0]
    print(f"{p:7s} first50={x[:50].mean():.4f}ms last50={x[-50:].mean():.4f}ms std={x.std():.4f} trend={tr:.6f}")
    if p=='square': print("   phase means:", [round(float(x[i:i+30].mean()),3) for i in range(0,240,30)])
STOP[0]=True
