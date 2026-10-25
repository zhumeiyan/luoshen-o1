import os, time, json
import numpy as np

def busy(n):
    s=0
    for i in range(n): s+=i*i
    return s

def measure(load_n=0):
    """真实测量一次 listdir 的耗时，同时可施加负载"""
    t0=time.perf_counter()
    os.listdir('/usr/lib')
    t1=time.perf_counter()
    if load_n: busy(load_n)
    return (t1-t0)*1000.0  # ms

# 平稳段
stable=[measure() for _ in range(200)]
# 漂移段：负载递增（真实漂移世界）
drift=[measure(int(20000*(i/200))) for i in range(200)]
# 周期段：负载方波
cyc=[measure(200000 if (i//25)%2 else 0) for i in range(200)]

def st(x):
    x=np.asarray(x)
    return dict(mean=float(x.mean()), std=float(x.std()), trend=float(np.polyfit(np.arange(len(x)),x,1)[0]))
print("stable", st(stable))
print("drift ", st(drift))
print("cyc   ", st(cyc))
