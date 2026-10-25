import time,statistics as st,json,math,random
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
def dp(A,B):
    ma,mb=st.mean(A),st.mean(B); sa,sb=st.pstdev(A),st.pstdev(B)
    sp=((sa**2+sb**2)/2)**0.5
    return (mb-ma)/sp if sp>0 else 0.0
random.seed(11)
BASE=300
DELTAS=[20,60,150]
NS=[1,2,4,8,16,32,64,128]
TRIALS=160
print('BASE work=%d  交织测量  判据: d\' 随积分长度 N 的变化'%BASE)
print('(Allan 预测: N 增大先受益, 越过闪烁floor后不再改善)')
res={}
for dl in DELTAS:
    print('--- 信号强度 δ=+%d 指令 ---'%dl)
    for N in NS:
        A=[];B=[]
        for t in range(TRIALS):
            a=[one(BASE) for _ in range(N)]
            b=[one(BASE+dl) for _ in range(N)]
            A.append(st.mean(a)); B.append(st.mean(b))
        d=dp(A,B)
        res['d%d_N%d'%(dl,N)]=d
        print('   N=%4d   d\'=%+.4f'%(N,d))
json.dump(res,open('core.json','w'),indent=1)
print()
print('=== 汇总: d\' vs N ===')
print('%8s'%('N')+''.join('%10s'%('δ+%d'%d) for d in DELTAS))
for N in NS:
    print('%8d'%N+''.join('%10.4f'%res['d%d_N%d'%(dl,N)] for dl in DELTAS))
