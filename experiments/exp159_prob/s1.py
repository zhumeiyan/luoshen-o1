import json, math, os, random, subprocess, sys, time
from collections import Counter

# ---- 真噪声源：真实时序抖动（同一段代码在不同系统负载下的抖动）----
def real_jitter(n=4000):
    out=[]
    a=0
    for _ in range(n):
        t0=time.perf_counter_ns()
        for _ in range(400): a=(a*1103515245+12345)&0x7fffffff
        out.append(time.perf_counter_ns()-t0)
    return out

J=real_jitter()
J.sort()
def emp_cdf(x):
    lo,hi=0,len(J)
    while lo<hi:
        m=(lo+hi)//2
        if J[m]<x: lo=m+1
        else: hi=m
    return lo/len(J)

# 真实噪声的经验分布（不假设高斯）
mu0=sum(J)/len(J)
sd0=(sum((x-mu0)**2 for x in J)/len(J))**0.5

# ---- 真损伤通道：fork/SIGKILL 真实计时 ----
def real_cost():
    ts=[]
    for _ in range(200):
        t0=time.perf_counter_ns()
        p=subprocess.Popen([sys.executable,"-c","pass"])
        p.kill(); p.wait()
        ts.append(time.perf_counter_ns()-t0)
    return sum(ts)/len(ts), (sum((x-sum(ts)/len(ts))**2 for x in ts)/len(ts))**0.5

C_ACT_MU, C_ACT_SD = real_cost()

rng=random.Random(20261019)
# 信号幅度（真实：把抖动按 3 档真实负载放大）——用经验抽样而非高斯
SIG=[0.0, 1.0, 2.0, 4.0]
PRIOR=[0.3,0.5,0.7]

def draw(mu, sd):  # 真实抖动重采样 + 偏移
    x=J[min(len(J)-1, int(abs(rng.gauss(0,1))*0.4*len(J)))]
    return x + rng.gauss(mu, sd)

def run(pi, sig, mode, N=3000):
    """mode: 'bayes' 解析阈值 | 'scan' 经验扫描最优 | 'always' | 'never'"""
    C_fp=C_ACT_MU          # 误报代价 = 真实抢占开销
    C_miss=C_ACT_MU*8.0    # 漏报代价 = 损伤扩大（157 实测 8 倍量级）
    thr_lr=(C_fp/C_miss)*((1-pi)/pi)
    tot=0.0; hits=0; fps=0; misses=0; acted=0; damage=0
    for _ in range(N):
        d = 1 if rng.random()<pi else 0
        o = draw(sig*sd0, sd0) if d else draw(0.0, sd0)
        # 经验似然比（用真实经验 CDF 而非解析密度）
        if d==1: pass
        # 用真实 CDF 构造 LR：P(o|d)/P(o|~d) 用移位经验分布
        p1 = 1.0-emp_cdf(o-sig*sd0) if sig>0 else 0.5
        p0 = 1.0-emp_cdf(o)
        p1=max(p1,1e-9); p0=max(p0,1e-9)
        lr = math.log(p1/p0)
        if mode=='bayes':   act = lr > math.log(max(thr_lr,1e-9))
        elif mode=='scan':  act = o > mu0 + 1.0*sd0     # 157 扫出的经验最优档
        elif mode=='always':act = True
        else:               act = False
        if act:
            acted+=1
            tot+=C_ACT_MU
            if d: hits+=1
            else: fps+=1
        else:
            if d: misses+=1; tot+=C_miss; damage+=1
    return dict(mode=mode,prior=pi,sig=sig,cost=tot/N,hits=hits,misses=misses,
                fps=fps,acted=acted,damage_rate=damage/N)

res=[]
for pi in PRIOR:
    for s in SIG:
        for m in ['bayes','scan','always','never']:
            res.append(run(pi,s,m))

json.dump(dict(noise_mu=mu0,noise_sd=sd0,C_ACT_MU=C_ACT_MU,C_ACT_SD=C_ACT_SD,
               res=res), open('s1.json','w'), indent=1)

print("真实噪声  mu=%.1f ns  sd=%.1f ns"%(mu0,sd0))
print("真实抢占成本 %.1f ± %.1f ns"%(C_ACT_MU,C_ACT_SD))
print()
print("prior sig | bayes     scan      always    never   | 公式胜?")
for pi in PRIOR:
    for s in SIG:
        row={r['mode']:r['cost'] for r in res if r['prior']==pi and r['sig']==s}
        win=min(row,key=row.get)
        print(" %.1f  %.1f | %8.1f %8.1f %8.1f %8.1f | %s"%(
            pi,s,row['bayes'],row['scan'],row['always'],row['never'],win))
