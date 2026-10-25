import time, statistics as st, os
def sweep(name, arr, lags=(1,2,3,5,8,12)):
    n=len(arr)
    row=[]
    for L in lags:
        e=st.mean([abs(arr[i-L]-arr[i]) for i in range(L,n)])
        row.append(e)
    mono=all(row[i]<=row[i+1]+1e-9 for i in range(len(row)-1))
    print("%-10s std=%7.3f err(lag1..12)=%s monotone=%s"%(name,st.pstdev(arr),
        " ".join("%.3f"%v for v in row), mono))
    return mono
# 候选1: 大计算量抖动
def jit(b):
    t0=time.perf_counter(); x=0
    for i in range(b): x+=(i*i)%7
    return (time.perf_counter()-t0)*1000.0
# 候选2: sleep 过冲
def ov():
    t0=time.perf_counter(); time.sleep(0.012); return (time.perf_counter()-t0)*1000.0
# 候选3: /proc/stat 100ms 窗口占用率
def cpufrac(win=0.10):
    def rd():
        a=open('/proc/stat').read().split('\n')[0].split()[1:]
        tot=sum(int(v) for v in a); idle=int(a[3])+int(a[4])
        return tot,idle
    t0,i0=rd(); time.sleep(win); t1,i1=rd()
    return 100.0*(1-(i1-i0)/max(1,(t1-t0)))
import multiprocessing as mp
def dist(n):
    end=time.time()+n*0.02+1
    while time.time()<end:
        t0=time.time()
        while time.time()-t0<0.30: pass
        time.sleep(0.30)
p=mp.Process(target=dist,args=(260,)); p.start(); time.sleep(0.4)
A=[];B=[];C=[]
for t in range(260):
    A.append(jit(90000)); B.append(ov()); C.append(cpufrac())
    time.sleep(0.008)
p.terminate()
sweep("jitter90k",A); sweep("sleep_ov",B); sweep("cpu_frac",C)
