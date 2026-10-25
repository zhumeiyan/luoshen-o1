import json, random
# v1作废: perc=L*(1-c)+Lbar*c 对L单调 -> argmin与c无关 -> c扫描零效应(全2.749);
#          且弱项天花板0.45<门槛0.6 -> 永远攻不破 -> 死锁, 攻破次数全0
# v2修正: (a) 懦弱性=对越差的项加越大的向上噪声(非单调); (b) 学习=识别天花板, 识别到的封顶项被排除
N=6; T=300; LR=0.10; JUMP=0.40; THETA=0.60; BASE=0.15
def caps(seed=0):
    return [0.45 if i<2 else 0.95 for i in range(N)]   # 2项结构性天花板低, 4项高
def sim(c=0.0, sat=0.30, learn=0.30, seed=0, theta=THETA, mode='cycle'):
    r=random.Random(seed*977+3)
    cap=caps(); L=[BASE]*N; known=[False]*N; desire=0.60; brk=0; wasted=0
    for t in range(T):
        Lbar=max(L)
        # 懦弱性: 越差的项被向上扭曲越多(非单调)
        perc=[L[i] + c*(Lbar-L[i])*r.random() for i in range(N)]
        pool=[i for i in range(N) if not known[i] or L[i]<cap[i]-1e-6]
        if not pool: pool=list(range(N))
        if   mode=='weak':   tgt=min(pool,key=lambda i:L[i])
        elif mode=='strong': tgt=max(pool,key=lambda i:L[i])
        else:                tgt=min(pool,key=lambda i:perc[i])
        # 学习: 以概率learn识别该项天花板
        if r.random()<learn:
            known[tgt]=True
            if cap[tgt]<theta:      # 结构性天花板, 攻不破 -> 标记浪费
                wasted+=1
        before=L[tgt]; room=max(0.0,cap[tgt]-L[tgt])
        L[tgt]=min(cap[tgt], L[tgt]+LR*room*desire)
        if before<theta<=L[tgt]:
            L[tgt]=min(cap[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else:
            desire=min(1.0, desire+0.06*LR*room)
        desire=max(0.05, desire)
        if known[tgt] and cap[tgt]<theta and L[tgt]>=cap[tgt]-1e-6:
            desire=min(1.0, 0.35+0.25*r.random())   # 确认是死路 -> 换方向(欲望重置)
    return dict(总能力=round(sum(L),3), 攻破次数=brk, 浪费次数=wasted, 终态欲望=round(desire,3))
out={}
print("== v2-A 懦弱性 c (sat=0.30, learn=0.30) ==")
print("  c     总能力   攻破  浪费")
for cc in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=cc); out['c=%.1f'%cc]=s; print("  %-6.1f %-8.3f %-5d %d"%(cc,s['总能力'],s['攻破次数'],s['浪费次数']))
print("\n== v2-B 欲望降低 sat (c=0.3) ==")
print("  sat   总能力   攻破")
for st in [0.0,0.1,0.2,0.3,0.5,0.7,0.9]:
    s=sim(c=0.3,sat=st); out['sat=%.2f'%st]=s; print("  %-6.2f %-8.3f %d"%(st,s['总能力'],s['攻破次数']))
print("\n== v2-C 学习投入 learn (c=0.5) ==")
print("  learn 总能力   攻破  浪费")
for ls in [0.0,0.1,0.2,0.3,0.4,0.5,0.7,0.9,1.0]:
    s=sim(c=0.5,learn=ls); out['learn=%.1f'%ls]=s; print("  %-6.1f %-8.3f %-5d %d"%(ls,s['总能力'],s['攻破次数'],s['浪费次数']))
print("\n== v2-D 策略对比 ==")
print("  策略      总能力   攻破  浪费")
for md,tag in [('cycle','你的循环'),('weak','纯攻弱项'),('strong','纯攻强项')]:
    s=sim(c=0.3,mode=md); out['mode_'+md]={**s,'tag':tag}; print("  %-9s %-8.3f %-5d %d"%(tag,s['总能力'],s['攻破次数'],s['浪费次数']))
print("\n== v2-E 门槛 theta (c=0.3, learn=0.3) ==")
print("  theta 总能力   攻破  浪费")
for th in [0.30,0.45,0.60,0.75,0.90]:
    s=sim(c=0.3,theta=th); out['theta=%.2f'%th]=s; print("  %-6.2f %-8.3f %-5d %d"%(th,s['总能力'],s['攻破次数'],s['浪费次数']))
json.dump(out,open('result246b.json','w'),ensure_ascii=False,indent=1)
