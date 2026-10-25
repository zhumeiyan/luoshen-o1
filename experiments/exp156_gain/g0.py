import time,os,signal,statistics as st,json,sys
def busy_for(sec):
    t0=time.time(); s=0
    while time.time()-t0<sec: s+=1
    return s
def meas(n=40):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter_ns(); s=0
        for i in range(300): s+=i*i
        ts.append(time.perf_counter_ns()-t0)
    return ts
# 无负载基线
base=[]
for _ in range(30): base+=meas(40)
# 有负载(真实子进程忙)
load=[]
pid=os.fork()
if pid==0:
    busy_for(60); os._exit(0)
for _ in range(30): load+=meas(40)
os.kill(pid,signal.SIGKILL); os.waitpid(pid,0)
b=st.mean(base); l=st.mean(load)
sb=st.pstdev(base); sl=st.pstdev(load)
d=(l-b)/((sb**2+sl**2)/2)**0.5
print('无负载 mean=%.1f sd=%.1f  n=%d'%(b,sb,len(base)))
print('有负载 mean=%.1f sd=%.1f  n=%d'%(l,sl,len(load)))
print('delta=%.1fns  Cohen d=%.4f'%(l-b,d))
print('G0 信号存在 =', abs(d)>0.5)
json.dump({'base_mean':b,'load_mean':l,'base_sd':sb,'load_sd':sl,'d':d},open('g0.json','w'))
