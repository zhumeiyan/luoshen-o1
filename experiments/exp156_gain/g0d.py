import time,os,statistics as st,json,socket,multiprocessing as mp
def burn(sec):
    t0=time.time(); s=0
    while time.time()-t0<sec: s+=1
def meas(n=200):
    ts=[]
    for _ in range(n):
        t0=time.perf_counter_ns(); s=0
        for i in range(400): s+=i*i
        ts.append(time.perf_counter_ns()-t0)
    return ts
print('=== 候选A: 真实多进程竞争 ===')
base=meas(200); bm,bs=st.mean(base),st.pstdev(base)
print('0进程 mean=%.1f sd=%.1f'%(bm,bs))
out={}
for np_ in [1,2,4]:
    ps=[mp.Process(target=burn,args=(8,)) for _ in range(np_)]
    for p in ps: p.start()
    time.sleep(0.5)
    x=meas(200)
    for p in ps: p.terminate(); p.join(timeout=1)
    m,s=st.mean(x),st.pstdev(x)
    d=(m-bm)/((s**2+bs**2)/2)**0.5
    out[str(np_)]=(m,s,d); print('%d进程 mean=%.1f sd=%.1f d=%.4f'%(np_,m,s,d))
print('=== 候选B: 真实UDP回环 payload扫描 ===')
srv=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); srv.bind(('127.0.0.1',0)); srv.settimeout(0.5)
port=srv.getsockname()[1]
cli=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); cli.settimeout(0.5)
import threading
def echo():
    while True:
        try: d,a=srv.recvfrom(65535); srv.sendto(d[:8],a)
        except: break
threading.Thread(target=echo,daemon=True).start()
udp={}
for size in [64,1024,16384,65507]:
    ts=[]
    for _ in range(120):
        t0=time.perf_counter_ns()
        cli.sendto(b'x'*size,('127.0.0.1',port))
        try: cli.recvfrom(8)
        except: pass
        ts.append(time.perf_counter_ns()-t0)
    udp[size]=(st.median(ts), sorted(ts)[90]-sorted(ts)[30])
    print('payload %6d  中位=%.0fns  IQR=%.0fns'%(size,udp[size][0],udp[size][1]))
json.dump({'proc':out,'udp':udp,'base':(bm,bs)},open('g0d.json','w'))
