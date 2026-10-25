"""157C 工作区宽度 vs 信噪比: 什么时候"小心"才真正必要
外敌强度三档 -> 三档 d' ; 每档扫 tau 找 (TPR>0.8 且 FPR<0.1) 的区间宽度
"""
import time, statistics, json, math, random
random.seed(53)
def load(k):
    x=0
    for i in range(k): x+=i*i
    return x
def samp(n, lvl, mode, every, k):
    s=[]; t=time.perf_counter_ns()
    for i in range(n):
        if lvl: load(lvl*200)
        if mode and (i % every)==0: load(k)   # 外敌: 每隔every点一次, 强度k
        a=time.perf_counter_ns(); s.append(a-t); t=a
    return statistics.mean(s)
def d_prime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    sp=math.sqrt((sa*sa+sb*sb)/2) or 1e-9
    return (ma-mb)/sp

GEARS=[("强",1,200),("中",8,60),("弱",40,25)]
N=300
print("=== 157C 信噪比三档 ===")
res={}
for name,every,k in GEARS:
    noi=[samp(N,0,False,every,k) for _ in range(24)]
    sig=[samp(N,0,True, every,k) for _ in range(24)]
    d=d_prime(sig,noi)
    nm_sd=statistics.pstdev(noi); nm_mx=max(noi)
    lo,hi=min(noi+sig),max(noi+sig)
    # 扫 tau 找工作区
    good=[]
    for tau in [lo+(hi-lo)*f/40 for f in range(41)]:
        tpr=statistics.mean([1 if x>tau else 0 for x in sig])
        fpr=statistics.mean([1 if x>tau else 0 for x in noi])
        if tpr>0.8 and fpr<0.1: good.append(tau)
    width=(max(good)-min(good))/(hi-lo) if good else 0.0
    res[name]=dict(d_prime=round(d,3),noise_mean=round(statistics.mean(noi),1),
                   sig_mean=round(statistics.mean(sig),1),
                   work_width_frac=round(width,4), n_good=len(good))
    print("  %s档: d'=%8.3f  噪声mean=%7.1f  信号mean=%7.1f  工作区宽度=%6.2f%% (%d个tau可用)"%(
        name,d,statistics.mean(noi),statistics.mean(sig),width*100,len(good)))
json.dump(res,open("snr.json","w"),ensure_ascii=False,indent=1)
print("\n结论: 工作区宽度随 d' 下降而收窄 -> 看不清时, 阈值怎么调都不安全, 只能靠'不动'")
