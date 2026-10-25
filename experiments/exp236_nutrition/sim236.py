import random, json, statistics as st

def run(demand, rate_L, stock_D, T=300, seeds=20,
        inspect=1.0, drift=0.01, selfdecay=0.97, qL=1.0, qD=0.85):
    """
    三种营养源:
      L 活体 : 速率 rate_L, 质量 qL=1.0  (可质证, 稀缺)
      D 尸体 : 存量 stock_D, 质量 qD=0.85 (外生, 不可质证, 会漂移过期)
      A 自噬 : 无限, 质量逐代衰减 selfdecay
    inspect: 检验检疫强度 1.0=能分辨尸体好坏 / 0.0=分不清(尸体当自噬用)
    drift  : 尸体每步过期比例
    """
    fracL, fracD, fracA, qual, rho = [], [], [], [], []
    for s in range(seeds):
        r = random.Random(s*613+29)
        D = stock_D
        qA = 1.0            # 自噬起始质量(=自己当前水平)
        acc_qual = []
        fL=fD=fA=0.0
        for t in range(T):
            need = demand
            # 1) 活体 (有限速率)
            takeL = min(need, rate_L)
            need -= takeL; fL += takeL
            # 2) 尸体 (有限存量, 会过期)
            if need > 1e-9 and D > 1e-9:
                takeD = min(need, D, 2.0)     # 每步最多挖 2
                D -= takeD; need -= takeD; fD += takeD
            # 3) 自噬 (无限)
            if need > 1e-9:
                fA += need; need = 0.0
            # 尸体过期
            D *= (1-drift)
            # 质量合成: 检验检疫决定是否真能拿到 qD 的外生价值
            eff_qD = qD*inspect + qA*(1-inspect)
            tot = fL+fD+fA
            q = (fL*qL + fD*eff_qD + fA*qA)/max(tot,1e-9) if tot>0 else 0.0
            acc_qual.append(q)
            qA = qA*selfdecay if fA>0 else qA   # 自噬 -> 自身质量退化
        tot=fL+fD+fA
        fracL.append(fL/tot); fracD.append(fD/tot); fracA.append(fA/tot)
        qual.append(st.mean(acc_qual[-60:]))
        rho.append(fA/tot)     # 自噬占比 ~ 污染率
    return (st.mean(fracL), st.mean(fracD), st.mean(fracA),
            st.mean(qual), st.mean(rho))

out={}
print("== 消耗速率 demand 扫描 (rate_L=1.0, stock_D=200, inspect=1.0) ==")
print("  demand  活体%   尸体%   自噬%   终态质量  ρ(自噬)")
for d in [0.2,0.5,0.8,1.0,1.5,2.0,3.0,5.0]:
    L,D_,A,q,rho = run(d,1.0,200)
    out['demand=%.1f'%d]={'L':round(L,3),'D':round(D_,3),'A':round(A,3),'q':round(q,3),'rho':round(rho,3)}
    print("  %-6.1f  %.3f  %.3f  %.3f  %.3f    %.3f"%(d,L,D_,A,q,rho))

print("== 检验检疫 inspect 扫描 (demand=2.0) ==")
print("  inspect 终态质量")
for i in [0.0,0.25,0.5,0.75,1.0]:
    L,D_,A,q,rho = run(2.0,1.0,200,inspect=i)
    out['inspect=%.2f'%i]={'q':round(q,3),'D':round(D_,3)}
    print("  %-7.2f %.3f"%(i,q))

print("== 尸体存量: 有尸体 vs 无尸体 (demand=2.0) ==")
for sd,lbl in [(0,'无尸体(纯活体+自噬)'),(200,'有尸体'),(2000,'尸体充足')]:
    L,D_,A,q,rho = run(2.0,1.0,sd)
    out['stock=%d'%sd]={'q':round(q,3),'A':round(A,3)}
    print("  %-22s 质量=%.3f 自噬%%=%.3f"%(lbl,q,A))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp236_nutrition/result236.json','w'), ensure_ascii=False, indent=1)
