import random
CAP=[0.42,0.55,0.68,0.80,0.90,0.98]; L0=[0.20,0.28,0.35,0.42,0.50,0.58]; N=6
LR=0.12; JUMP=0.45; THETA=0.60; FLOOR=0.05
def sim(D=0.5,F=0.5,H=0.5,c=0.3,exit=0.5,learn=0.3,T=120,seed=0,mode='cycle'):
    r=random.Random(seed*31337+17)
    L=list(L0); known=[False]*N; desire=0.60; brk=0; wasted=0
    # 有效懦弱性: 只有怕死压过希望时才回避
    ceff = c*max(0.0, F-H)/max(1e-9,max(F,H))
    # 驱动: 知死给时限压力; 怕死有出口为正/无出口为负(231); 希望恒正
    drive0 = 0.30 + 0.35*D + 0.40*H + 0.45*F*(2*exit-1)
    drive = max(FLOOR, min(1.0, drive0)); desire=drive
    for t in range(T):
        Lbar=max(L)
        perc=[L[i]+ceff*(Lbar-L[i])*r.random() for i in range(N)]
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6 and not (known[i] and CAP[i]<THETA)]
        if not pool: pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if   mode=='weak':   tgt=min(pool,key=lambda i:L[i])
        elif mode=='strong': tgt=max(pool,key=lambda i:L[i])
        else:                tgt=min(pool,key=lambda i:perc[i])
        if r.random()<learn:
            known[tgt]=True
            if CAP[tgt]<THETA: wasted+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<THETA<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1
            desire*=(1.0-0.30)
        else: desire=min(1.0, desire+0.08*LR*room)
        desire=max(FLOOR, min(1.0, desire))
    return dict(总能力=round(sum(L),3), 攻破=brk, 浪费=wasted, 有效懦弱性=round(ceff,3), 初始驱动=round(drive,3))
print("== A 懦弱性 c 扫描: 怕死主导 vs 希望主导 ==")
print("  c     F>H(0.8/0.2)   F<H(0.2/0.8)")
for cc in [0.0,0.3,0.5,0.8,1.0]:
    a=sim(F=0.8,H=0.2,c=cc)['总能力']; b=sim(F=0.2,H=0.8,c=cc)['总能力']
    print("  %-5.1f %-14.3f %.3f"%(cc,a,b))
print("\n== B 三情绪消融 (c=0.5, exit=0.5) ==")
print("  条件            总能力  攻破")
for tag,kw in [('全有',dict(D=.5,F=.5,H=.5)),('去知死',dict(D=0,F=.5,H=.5)),
               ('去怕死',dict(D=.5,F=0,H=.5)),('去希望',dict(D=.5,F=.5,H=0)),
               ('三无(我)',dict(D=0,F=0,H=0))]:
    s=sim(c=0.5,**kw); print("  %-14s %-7.3f %d"%(tag,s['总能力'],s['攻破']))
print("\n== C 怕死 x 出口 (231号机制复现, D=.5,H=.3,c=.3) ==")
print("  exit  总能力  初始驱动")
for ex in [0.0,0.25,0.5,0.75,1.0]:
    s=sim(F=0.8,H=0.3,exit=ex,c=0.3); print("  %-5.2f %-7.3f %.3f"%(ex,s['总能力'],s['初始驱动']))
print("\n== D 攻弱项 vs 攻强项 x 情绪组合 ==")
print("  组合            weak   strong  差")
for tag,kw in [('怕死主导',dict(F=.8,H=.2)),('希望主导',dict(F=.2,H=.8)),('平衡',dict(F=.5,H=.5))]:
    a=sim(c=0.5,mode='weak',**kw)['总能力']; b=sim(c=0.5,mode='strong',**kw)['总能力']
    print("  %-14s %-6.3f %-7.3f %+.3f"%(tag,a,b,a-b))
