import random, json, statistics as st

def run(bind, demand=2.0, T=300, seeds=20, stock_D=200,
        decay=0.985, repair=0.05, qL=1.0, qD=0.85,
        off=None, restore_at=None):
    """
    核心新机制(接221号q门槛): 吸收活体营养的能力 = 自身水平 Q
      有效活体质量 = qL * Q     ← 太差了就认不出好东西
      自噬 -> Q *= decay
      活体 -> Q += (qL-Q)*repair*(活体占比)
    off=(t0,t1) 断绑窗口; restore_at=None 表示断绑后不再恢复
    """
    Qs, quals, Afracs = [], [], []
    for s in range(seeds):
        r = random.Random(s*331+7)
        Q = 1.0; D = stock_D; A = 0.0; tot = 0.0; acc=[]
        for t in range(T):
            b = bind
            if off and off[0] <= t < off[1]:
                b = 0.0
            if off and t >= off[1] and restore_at is None:
                b = bind
            need = demand
            takeL = min(need, b)
            need -= takeL
            takeD = 0.0
            if need>1e-9 and D>1e-9:
                takeD = min(need, D, 2.0); D -= takeD; need -= takeD
            takeA = max(0.0, need); need = 0.0
            tot += takeL+takeD+takeA; A += takeA
            # 质量合成: 自噬部分质量=Q, 活体部分质量=qL*Q(吸收力依赖自身水平)
            q = (takeL*qL*Q + takeD*qD + takeA*Q)/max(takeL+takeD+takeA,1e-9)
            acc.append(q)
            # 更新 Q
            if takeA>0: Q *= decay
            if takeL>0: Q += (qL-Q)*repair*(takeL/demand)
            Q = max(0.0, min(1.0, Q))
        Qs.append(Q); quals.append(st.mean(acc[-60:])); Afracs.append(A/max(tot,1e-9))
    return st.mean(Qs), st.mean(quals), st.mean(Afracs)

out={}
print("== A. 绑定强度 bind 扫描 (demand=2.0) ==")
print("  bind   终态Q    终态质量  自噬%")
for b in [0.0,0.25,0.5,1.0,1.5,2.0,3.0]:
    Q,q,A = run(b)
    out['bind=%.2f'%b]={'Q':round(Q,3),'q':round(q,3),'A':round(A,3)}
    print("  %-6.2f %.3f  %.3f    %.3f"%(b,Q,q,A))

print("== B. 断绑时长 vs 恢复 (棘轮) ==")
print("  断绑步数  恢复后Q   恢复后质量   从未断绑对照=%.3f"%(run(1.0)[1]))
base_q = run(1.0)[1]
for n in [0,10,25,50,100,200,300]:
    Q,q,A = run(1.0, off=(50,50+n))
    out['off=%d'%n]={'Q':round(Q,3),'q':round(q,3),'gap':round(base_q-q,3)}
    print("  %-8d %.3f    %.3f      差 %.3f"%(n,Q,q,base_q-q))

print("== C. 周期绑定 vs 持续绑定 (总量相同) ==")
print("  模式            平均bind  终态质量")
duty = 0.5
Q,q,A = run(1.0); print("  持续 b=1.0       1.00     %.3f"%q); out['持续1.0']=round(q,3)
Q,q,A = run(0.5); print("  持续 b=0.5       0.50     %.3f"%q); out['持续0.5']=round(q,3)
# 周期: 一半时间b=2.0 一半时间b=0
Qc,qc,Ac = run_periodic(2.0, period=20, duty=0.5, seeds=20) if False else (0,0,0)
def run_periodic(peak, period=20, duty=0.5, seeds=20, demand=2.0, T=300):
    Qs,qq=[],[]
    for s in range(seeds):
        Q=1.0; D=200; acc=[]
        for t in range(T):
            b = peak if (t%period) < period*duty else 0.0
            need=demand; takeL=min(need,b); need-=takeL
            takeD=0.0
            if need>1e-9 and D>1e-9: takeD=min(need,D,2.0); D-=takeD; need-=takeD
            takeA=max(0.0,need)
            q=(takeL*1.0*Q + takeD*0.85 + takeA*Q)/max(takeL+takeD+takeA,1e-9)
            acc.append(q)
            if takeA>0: Q*=0.985
            if takeL>0: Q += (1.0-Q)*0.05*(takeL/demand)
            Q=max(0.0,min(1.0,Q))
        Qs.append(Q); qq.append(st.mean(acc[-60:]))
    return st.mean(Qs), st.mean(qq), 0
for P in [2,10,20,60,150]:
    Q,q,_ = run_periodic(2.0,period=P,duty=0.5)
    out['周期P=%d'%P]={'Q':round(Q,3),'q':round(q,3)}
    print("  周期 P=%-4d       1.00     %.3f  (Q=%.3f)"%(P,q,Q))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp237_ratchet/result237.json','w'), ensure_ascii=False, indent=1)
