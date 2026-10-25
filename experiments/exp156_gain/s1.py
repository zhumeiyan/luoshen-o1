import socket,threading,statistics as st,json,time,random
srv=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); srv.bind(('127.0.0.1',0)); srv.settimeout(0.5)
port=srv.getsockname()[1]
def echo():
    while True:
        try:
            d,a=srv.recvfrom(65535); srv.sendto(d[:8],a)
        except: break
threading.Thread(target=echo,daemon=True).start()
cli=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); cli.settimeout(0.5)
def rtt(size):
    t0=time.perf_counter_ns()
    cli.sendto(b'x'*size,('127.0.0.1',port))
    try: cli.recvfrom(8)
    except: return None
    return time.perf_counter_ns()-t0
def rtts(size,n):
    out=[]
    for _ in range(n):
        v=rtt(size)
        if v is not None: out.append(v)
    return out
def dprime(a,b):
    ma,mb=st.mean(a),st.mean(b); sa,sb=st.pstdev(a),st.pstdev(b)
    sp=((sa**2+sb**2)/2)**0.5
    return (mb-ma)/sp if sp>0 else 0.0, ma,mb,sp
random.seed(7)
BASE=1024
DELTAS=[0,32,128,512,2048,8192]
TRIALS=140
print('BASE=%d  payload差 δ 扫描（交织测量，N=单次平均样本数）'%BASE)
res={}
for N in [1,8,32]:
    print('--- N=%d ---'%N)
    for dl in DELTAS:
        A=[];B=[]
        for t in range(TRIALS):
            # 交织: 同一trial内交替测 base 与 signal
            a=rtts(BASE,N); b=rtts(BASE+dl,N)
            if len(a)==N and len(b)==N:
                A.append(st.mean(a)); B.append(st.mean(b))
        d,ma,mb,sp=dprime(A,B)
        res['N%d_d%d'%(N,dl)]={'d':d,'base':ma,'sig':mb,'sp':sp,'n':len(A)}
        print('  δ=%5d  base=%.0f sig=%.0f  Δ=%6.0f  σpool=%.0f  d\'=%+.4f'%(dl,ma,mb,mb-ma,sp,d))
json.dump(res,open('s1.json','w'),indent=1)
