import time,statistics as st,json,random,math
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
def dp_from(tpr,fpr):
    from math import sqrt
    # d' = z(TPR) - z(FPR)
    def z(p):
        p=min(max(p,1e-6),1-1e-6)
        # Acklam 近似
        a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
        b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
        c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
        d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
        pl=0.02425
        if p<pl:
            q=sqrt(-2*math.log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p>1-pl:
            q=sqrt(-2*math.log(1-p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q=p-0.5; r=q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    return z(tpr)-z(fpr)
random.seed(99)
BASE=300; DL=60; N=8; TRIALS=600
# 采集: 交织, 一半有信号一半无
data=[]
for t in range(TRIALS):
    sig = (t%2==0)
    xs=[one(BASE+DL) if sig else one(BASE) for _ in range(N)]
    data.append((sig, st.mean(xs)))
S=[v for s,v in data if s]; Nn=[v for s,v in data if not s]
print('有信号 n=%d mean=%.0f sd=%.0f'%(len(S),st.mean(S),st.pstdev(S)))
print('无信号 n=%d mean=%.0f sd=%.0f'%(len(Nn),st.mean(Nn),st.pstdev(Nn)))
lo=min(min(S),min(Nn)); hi=max(max(S),max(Nn))
print('\n=== ROC: 扫阈值(增益) ===')
print('%12s %8s %8s %8s'%('阈值θ','TPR','FPR',"d'"))
roc=[]
for i in range(1,20):
    th=lo+(hi-lo)*i/20.0
    tpr=sum(1 for v in S if v>th)/len(S)
    fpr=sum(1 for v in Nn if v>th)/len(Nn)
    d=dp_from(tpr,fpr)
    roc.append((th,tpr,fpr,d))
    print('%12.0f %8.3f %8.3f %8.3f'%(th,tpr,fpr,d))
ds=[r[3] for r in roc if 0.02<r[1]<0.98 and 0.02<r[2]<0.98]
print("\nd' 在有效区间内: min=%.3f max=%.3f 极差=%.3f"%(min(ds),max(ds),max(ds)-min(ds)))
print("判据: 增益改变阈值但 d' 应恒定 -> 极差<1.0 视为成立:", (max(ds)-min(ds))<1.0)
# 双模式: 同一次测量, 两个阈值
print('\n=== 双模式（共用同一次测量）===')
mode_hi=[r for r in roc if r[1]>=0.80]  # 高敏: TPR>=0.8
mode_lo=[r for r in roc if r[2]<=0.20]  # 人绑: FPR<=0.2
if mode_hi and mode_lo:
    hi_m=max(mode_hi,key=lambda r:r[1]); lo_m=min(mode_lo,key=lambda r:r[2])
    print('高敏模式  θ=%.0f  TPR=%.3f FPR=%.3f'%(hi_m[0],hi_m[1],hi_m[2]))
    print('人绑模式  θ=%.0f  TPR=%.3f FPR=%.3f'%(lo_m[0],lo_m[1],lo_m[2]))
    print('两套读数来自同一批测量 -> 共存成本 = 0 次额外采样')
# 门控: 连续重复刺激
print('\n=== 感觉门控（重复刺激抑制）===')
def gate_test(gap):
    r1=[];r2=[]
    for _ in range(120):
        a=st.mean([one(BASE+DL) for _ in range(N)])
        if gap>0: time.sleep(gap)
        b=st.mean([one(BASE+DL) for _ in range(N)])
        r1.append(a); r2.append(b)
    return st.mean(r1),st.mean(r2)
for gap in [0,0.0005]:
    a,b=gate_test(gap)
    print('间隔=%.4fs  第1次=%.0f 第2次=%.0f  抑制率=%.4f'%(gap,a,b,1-b/a))
json.dump({'roc':roc,'base':st.mean(Nn),'sig':st.mean(S)},open('final.json','w'),indent=1)
