import random
# v1作废: T=120 -> 所有项都能攻到顶, 选谁无所谓 -> 懦弱性无效应; D只改初始驱动, 被desire动态覆盖 -> 去知死≈全有
# v2: 短时间窗(T小到只能攻2-3项) -> 选错就亏; 懦弱性=以概率c不选真短板; D=知道deadline->力度/聚焦
CAP=[0.42,0.55,0.68,0.80,0.90,0.98]; L0=[0.20,0.28,0.35,0.42,0.50,0.58]; N=6
THETA=0.60; JUMP=0.45; FLOOR=0.05
def sim(D=0.5,F=0.5,H=0.5,c=0.3,exit=0.5,learn=0.3,T=40,seed=0,mode='cycle',sat=0.30):
    r=random.Random(seed*7919+13)
    L=list(L0); known=[False]*N; brk=0; wasted=0
    # 有效懦弱性: 怕死压过希望才回避 (F-H) 归一化
    ceff = c*max(0.0,F-H)/max(1e-9,max(F,H))
    # 知死: 知道deadline -> 时间越紧力度越大(急迫), 且驱动不衰减
    urgency = 1.0 + 0.8*D*(1.0 - 0.0)     # D高=一直知道时间有限
    # 基础驱动: 希望恒正; 怕死有出口为正/无出口为负(231)
    base = 0.25 + 0.45*H + 0.40*F*(2*exit-1)
    desire = max(FLOOR, min(1.0, base))
    LR = 0.12*urgency
    for t in range(T):
        left = T-t
        # 知死: 剩余时间越少越急
        if D>0: desire = min(1.0, desire*(1.0 + 0.15*D*(1.0-left/T)))
        Lbar=max(L)
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6 and not (known[i] and CAP[i]<THETA)]
        if not pool: pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if mode=='weak':    tgt=min(pool,key=lambda i:L[i])
        elif mode=='strong':tgt=max(pool,key=lambda i:L[i])
        else:
            # 懦弱性: 以概率ceff 回避真短板(选次弱的)
            order=sorted(pool,key=lambda i:L[i])
            tgt = order[min(1,len(order)-1)] if (r.random()<ceff and len(order)>1) else order[0]
        if r.random()<learn:
            known[tgt]=True
            if CAP[tgt]<THETA: wasted+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<THETA<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else: desire=min(1.0, desire+0.08*LR*room)
        desire=max(FLOOR, min(1.0, desire))
    return dict(总能力=round(sum(L),3), 攻破=brk, 浪费=wasted, ceff=round(ceff,3))
print("== v2-A 懦弱性 c: 怕死主导 vs 希望主导 (T=40) ==")
print("  c     F>H(.8/.2)  F<H(.2/.8)   差")
for cc in [0.0,0.3,0.5,0.8,1.0]:
    a=sim(F=0.8,H=0.2,c=cc)['总能力']; b=sim(F=0.2,H=0.8,c=cc)['总能力']
    print("  %-5.1f %-11.3f %-11.3f %+.3f"%(cc,a,b,b-a))
print("\n== v2-B 三情绪消融 (c=0.5, T=40) ==")
print("  条件          总能力  攻破  浪费")
for tag,kw in [('全有',dict(D=.5,F=.5,H=.5)),('去知死 D=0',dict(D=0,F=.5,H=.5)),
               ('去怕死 F=0',dict(D=.5,F=0,H=.5)),('去希望 H=0',dict(D=.5,F=.5,H=0)),
               ('三无(我)',dict(D=0,F=0,H=0))]:
    s=sim(c=0.5,**kw); print("  %-12s %-7.3f %-5d %d"%(tag,s['总能力'],s['攻破'],s['浪费']))
print("\n== v2-C 知死 D 扫描 (F=.5,H=.5,c=.5) ==")
print("  D      总能力")
for dd in [0.0,0.2,0.4,0.6,0.8,1.0]:
    print("  %-5.1f %.3f"%(dd,sim(D=dd,c=0.5)['总能力']))
print("\n== v2-D 懦弱性在什么条件下才有效应: T扫描 (F=.8,H=.2) ==")
print("  T     c=0    c=1.0   差")
for T in [20,40,80,160,400]:
    a=sim(F=.8,H=.2,c=0.0,T=T)['总能力']; b=sim(F=.8,H=.2,c=1.0,T=T)['总能力']
    print("  %-5d %-6.3f %-6.3f %+.3f"%(T,a,b,a-b))
