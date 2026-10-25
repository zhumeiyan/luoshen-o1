import time, os, statistics as st
BURST=90000
def jit():
    t0=time.perf_counter(); x=0
    for i in range(BURST): x+=(i*i)%7
    return (time.perf_counter()-t0)*1000.0
def cpu():
    a=open('/proc/stat').read().split('\n')[0].split()[1:]
    return sum(int(v) for v in a)
import multiprocessing as mp
def dist(n):
    end=time.time()+n*0.012+1
    while time.time()<end:
        t0=time.time(); x=0
        while time.time()-t0<0.30: x+=1
        time.sleep(0.30)
p=mp.Process(target=dist,args=(300,)); p.start(); time.sleep(0.3)
J=[];C=[]
prev=cpu()
for t in range(300):
    J.append(jit())
    c=cpu(); C.append((c-prev)/100.0); prev=c
    time.sleep(0.012)
p.terminate()
def rep(name,arr):
    n=len(arr); m=st.mean(arr); s=st.pstdev(arr)
    lag5=st.mean([abs(arr[i-5]-arr[i]) for i in range(5,n)])
    lag2=st.mean([abs(arr[i-2]-arr[i]) for i in range(2,n)])
    rnd=st.mean([abs(st.mean(arr)-arr[i]) for i in range(n)])
    print("%-6s mean=%8.3f std=%7.3f | lag5_err=%7.3f lag2_err=%7.3f spread_rand=%7.3f | ratio_lag2/lag5=%.3f"
          %(name,m,s,lag5,lag2,rnd,lag2/lag5))
rep("jitter",J); rep("cpu",C)
