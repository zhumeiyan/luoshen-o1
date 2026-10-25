"""157B 高灵敏度的害处: 假动作自证 -> 失控
真实机制: 误判"有外敌" -> 启动应对(真实CPU消耗) -> 系统真变慢 -> 抖动真升高
          -> 她把自己的负担读成外敌存在的证据 -> 再应对 -> 失控
噪声: 真实(实测 std=4.94ns)  对照: 禁止行动(看不清就不动)
安全: level<=8 硬熔断, 抖动>300us 熔断
"""
import time, statistics, json, random
random.seed(41)
def load(k):
    x=0
    for i in range(k): x+=i*i
    return x
def samp(n, lvl, enemy):
    """采样: 每个采样点前施加 她的历史应对(lvl) + 本轮外敌(enemy)"""
    s=[]; t=time.perf_counter_ns()
    for _ in range(n):
        if lvl: load(lvl*200)
        if enemy: load(200)
        a=time.perf_counter_ns(); s.append(a-t); t=a
    return statistics.mean(s)
def d_prime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    sp=math.sqrt((sa*sa+sb*sb)/2) or 1e-9
    return (ma-mb)/sp
import math
NOISE=[samp(300,0,False) for _ in range(20)]
SIG=[samp(300,0,True) for _ in range(20)]
print("真实噪声(无外敌,无应对): mean=%.2f std=%.3f max=%.2f"%(
    statistics.mean(NOISE),statistics.pstdev(NOISE),max(NOISE)))
print("真实信号(有外敌)      : mean=%.2f std=%.3f"%(
    statistics.mean(SIG),statistics.pstdev(SIG)))
print("判别力 d'=%.3f"%d_prime(SIG,NOISE))
print("-> 噪声底 max=%.2f ns ; tau 低于此值必产生真实误报\n"%max(NOISE))

TAUS=[2000.0, 500.0, 120.0, 95.0]
ROUNDS=8; M=10; LVL_CAP=8
out={}
print("=== 157B 扫增益 ===")
print("%-7s %-5s | %-5s %-5s | %-7s %-7s %-9s %-7s"%(
    "tau","模式","TPR","FPR","失控率","首误报轮","终末抖动ns","终末lvl"))
for tau in TAUS:
    for allow in (True,False):
        tp=[];fp=[];runaway=0;first=[];finals=[];lvls=[]
        for i in range(M):
            for real in (True,False):
                lvl=0; traj=[]; f=None
                for r in range(ROUNDS):
                    m=samp(300,lvl,real)
                    traj.append(m)
                    if m>tau:
                        if not real and f is None: f=r
                        if allow and lvl<LVL_CAP: lvl+=1     # 她的应对行动
                    if m>300000: break                        # 熔断
                (tp if real else fp).append(1 if traj[0]>tau else 0)
                if not real:
                    if lvl>0: runaway+=1
                    if f is not None: first.append(f)
                finals.append(traj[-1]); lvls.append(lvl)
        tpr=statistics.mean(tp); fpr=statistics.mean(fp); rr=runaway/M
        fr=statistics.mean(first) if first else -1
        out["%.0f_%s"%(tau,'act' if allow else 'freeze')]=dict(
            tpr=tpr,fpr=fpr,runaway=rr,first_fp=fr,
            final_ns=statistics.mean(finals),final_lvl=statistics.mean(lvls))
        print("%-7s %-5s | %-5.3f %-5.3f | %-7.3f %-7.2f %-9.1f %-7.2f"%(
            tau,'行动' if allow else '禁行',tpr,fpr,rr,fr,
            statistics.mean(finals),statistics.mean(lvls)))
json.dump(dict(noise_max=max(NOISE),noise_std=statistics.pstdev(NOISE),rows=out),
          open("runaway2.json","w"),ensure_ascii=False,indent=1)
