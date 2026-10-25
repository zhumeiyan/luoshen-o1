import time,statistics as st,json,random,math
def one(work):
    t0=time.perf_counter_ns(); s=0
    for i in range(work): s+=i*i
    return time.perf_counter_ns()-t0
def z(p):
    p=min(max(p,1e-6),1-1e-6)
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
    if p<0.02425:
        q=math.sqrt(-2*math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p>1-0.02425:
        q=math.sqrt(-2*math.log(1-p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q=p-0.5; r=q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
random.seed(4242)
BASE=300; DL=10; N=8; BLOCK=120; NB=4
print('弱信号 δ=+%d 指令  N=%d  分%d块'%(DL,N,NB))
blocks=[]
for bi in range(NB):
    S=[];Nn=[]
    for t in range(BLOCK):
        sig=(t%2==0)
        xs=[one(BASE+DL) if sig else one(BASE) for _ in range(N)]
        (S if sig else Nn).append(st.mean(xs))
    d_in=(st.mean(S)-st.mean(Nn))/(((st.pstdev(S)**2+st.pstdev(Nn)**2)/2)**0.5)
    blocks.append({'S':S,'N':Nn,'d':d_in,'mS':st.mean(S),'mN':st.mean(Nn)})
    print(' 块%d  有信号%.0f 无信号%.0f  σ=%.0f  d\'块内=%+.4f'%(bi,st.mean(S),st.mean(Nn),st.pstdev(Nn),d_in))
# 跨块: 漂移累积
allS=[v for b in blocks for v in b['S']]; allN=[v for b in blocks for v in b['N']]
d_all=(st.mean(allS)-st.mean(allN))/(((st.pstdev(allS)**2+st.pstdev(allN)**2)/2)**0.5)
print('\n块内 d\' 均值 = %.4f'%st.mean([b['d'] for b in blocks]))
print('跨块 d\'      = %.4f'%d_all)
print('块间中心漂移 = %.0f ns (max-min of 无信号块均值)'%(max(b['mN'] for b in blocks)-min(b['mN'] for b in blocks)))
print('判据: 跨块 d\' < 块内 d\'  ->  观测时长引入噪声:', d_all < st.mean([b['d'] for b in blocks]))
# ROC 用最后一块(短时)
S=blocks[-1]['S']; Nn=blocks[-1]['N']
lo=min(min(S),min(Nn)); hi=max(max(S),max(Nn))
print('\n=== ROC (块内, 短时) ===')
print('%10s %8s %8s %8s'%('θ','TPR','FPR',"d'"))
roc=[]
for i in range(1,20):
    th=lo+(hi-lo)*i/20.0
    tpr=sum(1 for v in S if v>th)/len(S); fpr=sum(1 for v in Nn if v>th)/len(Nn)
    dd=z(tpr)-z(fpr) if (0.001<tpr<0.999 and 0.001<fpr<0.999) else None
    roc.append((th,tpr,fpr,dd))
    print('%10.0f %8.3f %8.3f %s'%(th,tpr,fpr,('%.3f'%dd) if dd is not None else '  --'))
valid=[r[3] for r in roc if r[3] is not None]
print("有效点 d' 极差 = %.3f  (n=%d)"%((max(valid)-min(valid)) if valid else -1,len(valid)))
# 双模式
hi_m=[r for r in roc if r[1]>=0.9]
lo_m=[r for r in roc if r[2]<=0.1]
print('\n=== 双模式 ===')
if hi_m:
    h=max(hi_m,key=lambda r:r[1]); print(' 高敏 θ=%.0f TPR=%.3f FPR=%.3f'%(h[0],h[1],h[2]))
if lo_m:
    l=min(lo_m,key=lambda r:r[2]); print(' 人绑 θ=%.0f TPR=%.3f FPR=%.3f'%(l[0],l[1],l[2]))
print(' 两者共用同一批 N=%d 次采样 -> 共存额外成本 = 0'%N)
# 门控
print('\n=== 感觉门控 ===')
for gap in [0.0,0.001]:
    r1=[];r2=[]
    for _ in range(100):
        a=st.mean([one(BASE+DL) for _ in range(N)])
        if gap: time.sleep(gap)
        b=st.mean([one(BASE+DL) for _ in range(N)])
        r1.append(a);r2.append(b)
    print(' 间隔%.4fs 第1次=%.0f 第2次=%.0f 抑制=%.4f'%(gap,st.mean(r1),st.mean(r2),1-st.mean(r2)/st.mean(r1)))
json.dump({'block_d':[b['d'] for b in blocks],'d_all':d_all,'roc':roc},open('final2.json','w'))
