import time,statistics as st,json,random,math
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
def dp(A,B):
    ma,mb=st.mean(A),st.mean(B); sa,sb=st.pstdev(A),st.pstdev(B)
    sp=((sa**2+sb**2)/2)**0.5
    return (mb-ma)/sp if sp>0 else 0.0
random.seed(2026)
BASE=300; DELTAS=[20,60,150]; NS=[1,2,4,8,16,32,64]; REPS=150
# 构造全部 trial 并随机打乱 -> 漂移被均摊到所有条件
trials=[(dl,N) for dl in DELTAS for N in NS for _ in range(REPS)]
random.shuffle(trials)
acc={}
for dl,N in trials:
    a=[one(BASE) for _ in range(N)]
    b=[one(BASE+dl) for _ in range(N)]
    k=(dl,N); acc.setdefault(k,{'A':[],'B':[]})
    acc[k]['A'].append(st.mean(a)); acc[k]['B'].append(st.mean(b))
res={}
print('BASE work=%d  全条件随机交织  REPS=%d'%(BASE,REPS))
print('%8s'%('N')+''.join('%12s'%('δ+%d'%d) for d in DELTAS))
for N in NS:
    row=[]
    for dl in DELTAS:
        d=dp(acc[(dl,N)]['A'],acc[(dl,N)]['B']); res['d%d_N%d'%(dl,N)]=d; row.append(d)
    print('%8d'%N+''.join('%12.4f'%v for v in row))
print()
print('=== 相对 N=1 的增益倍数 (白噪理论 = sqrt(N)) ===')
print('%8s %10s'%('N','理论√N')+''.join('%12s'%('δ+%d'%d) for d in DELTAS))
for N in NS:
    th=math.sqrt(N)
    print('%8d %10.2f'%(N,th)+''.join('%12.2f'%(res['d%d_N%d'%(dl,N)]/res['d%d_N1'%(dl,1)]) for dl in DELTAS))
json.dump(res,open('core2.json','w'),indent=1)
