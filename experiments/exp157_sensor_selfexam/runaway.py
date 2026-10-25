"""157B 高灵敏度的害处: 假动作自证 + 失控
传感器=时序抖动(真实噪声:156号实测闪烁floor+块间漂移5544ns)
她误判"有外敌" -> 真行动(分配30MB且不释放) -> 系统真变慢 -> 抖动真升高 -> 确认错误信念
对照: 禁止行动(看不清就不动) 能否挡住失控
安全: 硬熔断 累积>600MB 或 抖动>50us 立即停
"""
import time, statistics, json, math, random
random.seed(31)

def load(k):
    x=0
    for i in range(k): x+=i*i
    return x

def sample(n=500):
    s=[]; t=time.perf_counter_ns()
    for _ in range(n):
        a=time.perf_counter_ns(); s.append(a-t); t=a
    return statistics.median(s), sorted(s)[int(.95*len(s))]

def d_prime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    sp=math.sqrt((sa*sa+sb*sb)/2) or 1e-9
    return (ma-mb)/sp

# 1) 先量真实噪声底与真实信号
base=[]; sig=[]
for _ in range(20):
    m,_=sample(); base.append(m)
    load(3000); m2,_=sample(); sig.append(m2)
print("真实噪声底(无扰动) 抖动中位: 中位=%.1f  max=%.1f  std=%.1f"%(
    statistics.median(base), max(base), statistics.pstdev(base)))
print("真实信号(有扰动)   抖动中位: 中位=%.1f  max=%.1f"%(
    statistics.median(sig), max(sig)))
NOISE_MAX=max(base); NOISE_MED=statistics.median(base)
print("-> 噪声底最大值 %.1f ns, 任何 tau < 此值 都会产生真实误报"%NOISE_MAX)

# 2) 扫增益 tau, 对照 允许行动/禁止行动
HARD_MB=600; HARD_US=50.0
TAUS=[300.0, 150.0, 110.0, 100.0]     # 逐档逼近噪声底
ROUNDS=10; M=8
out={}
print("\n=== 157B 扫增益 (tau越低=越敏感) ===")
print("%-8s %-6s | %-6s %-6s | %-8s %-10s %-8s"%(
    "tau","模式","TPR","FPR","失控率","终末抖动ns","累积MB"))
for tau in TAUS:
    for allow in (True, False):
        tp=[];fp=[];runaway=0; finals=[]; allocs=[]
        for i in range(M):
            for real in (True, False):
                heap=[]; traj=[]; alloc_mb=0
                for r in range(ROUNDS):
                    if real: load(3000)          # 真实外敌
                    med,p95 = sample()
                    traj.append(med)
                    if med > tau:                # 判定"有外敌"
                        if allow:
                            heap.append(bytearray(30*1024*1024))  # 她的应对行动
                            alloc_mb += 30
                    if alloc_mb>HARD_MB or med>HARD_US*1000:
                        break                    # 熔断
                (tp if real else fp).append(1 if traj[0]>tau else 0)
                # 失控: 无外敌时抖动仍单调上升(自证闭环)
                if not real and len(traj)>2 and traj[-1]>traj[0]*1.5: runaway+=1
                finals.append(traj[-1]); allocs.append(alloc_mb)
                del heap; heap=[]
        tpr=statistics.mean(tp); fpr=statistics.mean(fp)
        rr=runaway/M
        out["%.0f_%s"%(tau,'act' if allow else 'freeze')]=dict(
            tpr=tpr,fpr=fpr,runaway=rr,final_ns=statistics.mean(finals),
            alloc_mb=statistics.mean(allocs))
        print("%-8s %-6s | %-6.3f %-6.3f | %-8.3f %-10.1f %-8.1f"%(
            tau,'行动' if allow else '禁行',tpr,fpr,rr,
            statistics.mean(finals),statistics.mean(allocs)))
json.dump(dict(noise_max=NOISE_MAX,noise_med=NOISE_MED,rows=out),
          open("runaway.json","w"),ensure_ascii=False,indent=1)
