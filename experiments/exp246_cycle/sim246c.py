import json, random
# v2作废: 欲望触底后没有"换方向"重置 -> 增长停在0.46, 攻破恒0; 且能力值只有两档, 排序无竞争 -> c几乎无效应
# v3: 能力分级(有低于门槛的结构性项, 也有高于的); 欲望触底=触发"找新方向"(重置+强制换目标)
N=6; T=400; LR=0.12; JUMP=0.45; THETA=0.60; BASE=0.20; FLOOR=0.05
CAP=[0.42,0.55,0.68,0.80,0.90,0.98]   # 前2项天花板低于门槛=结构性短板
def sim(c=0.0, sat=0.30, learn=0.30, seed=0, theta=THETA, mode='cycle', reorient=True):
    r=random.Random(seed*7919+11)
    L=[BASE]*N; known=[False]*N; desire=0.60; brk=0; wasted=0; reor=0; last=None
    for t in range(T):
        Lbar=max(L)
        perc=[L[i]+c*(Lbar-L[i])*r.random() for i in range(N)]   # 懦弱性: 越差扭曲越大
        # 学习: 识别天花板, 已识别且已封顶的项不再作为目标
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6 and not (known[i] and CAP[i]<theta)]
        if not pool: pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if   mode=='weak':   cand=min(pool,key=lambda i:L[i])
        elif mode=='strong': cand=max(pool,key=lambda i:L[i])
        else:                cand=min(pool,key=lambda i:perc[i])
        if last is not None and cand==last and len(pool)>1:
            cand=min([i for i in pool if i!=last], key=lambda i:perc[i])
        tgt=cand; last=tgt
        if r.random()<learn:
            known[tgt]=True
            if CAP[tgt]<theta: wasted+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<theta<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else:
            desire=min(1.0, desire+0.08*LR*room)
        if desire<=FLOOR+1e-9 and reorient:      # 欲望降低 -> 找新方向
            desire=0.35+0.30*r.random(); reor+=1; last=None
        desire=max(FLOOR, desire)
    return dict(总能力=round(sum(L),3), 攻破=brk, 浪费=wasted, 换方向=reor, 终态欲望=round(desire,3))
out={}
print("== v3-A 懦弱性 c (sat=0.30, learn=0.30) ==")
print("  c     总能力   攻破  浪费  换方向")
for cc in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=cc); out['c=%.1f'%cc]=s; print("  %-6.1f %-8.3f %-5d %-6d %d"%(cc,s['总能力'],s['攻破'],s['浪费'],s['换方向']))
print("\n== v3-B 欲望降低 sat (c=0.3) ==")
print("  sat   总能力   攻破  换方向")
for st in [0.0,0.1,0.2,0.3,0.5,0.7,0.9]:
    s=sim(c=0.3,sat=st); out['sat=%.2f'%st]=s; print("  %-6.2f %-8.3f %-5d %d"%(st,s['总能力'],s['攻破'],s['换方向']))
print("\n== v3-C 学习投入 learn (c=0.5) ==")
print("  learn 总能力   攻破  浪费")
for ls in [0.0,0.1,0.2,0.3,0.4,0.5,0.7,0.9,1.0]:
    s=sim(c=0.5,learn=ls); out['learn=%.1f'%ls]=s; print("  %-6.1f %-8.3f %-5d %d"%(ls,s['总能力'],s['攻破'],s['浪费']))
print("\n== v3-D 策略对比 (c=0.3) ==")
print("  策略        总能力   攻破  浪费")
for md,tag in [('cycle','你的循环'),('weak','纯攻弱项'),('strong','纯攻强项')]:
    s=sim(c=0.3,mode=md); out['mode_'+md]={**s,'tag':tag}; print("  %-10s %-8.3f %-5d %d"%(tag,s['总能力'],s['攻破'],s['浪费']))
print("\n== v3-E 消融: 去掉'换方向'(你的循环的关键一步) ==")
print("  设置        总能力   攻破")
for ro,tag in [(True,'有换方向'),(False,'无换方向')]:
    s=sim(c=0.3,reorient=ro); out['reorient=%s'%ro]={**s,'tag':tag}; print("  %-11s %-8.3f %d"%(tag,s['总能力'],s['攻破']))
print("\n== v3-F 门槛 theta (c=0.3) ==")
print("  theta 总能力   攻破  浪费")
for th in [0.30,0.45,0.60,0.75,0.90]:
    s=sim(c=0.3,theta=th); out['theta=%.2f'%th]=s; print("  %-6.2f %-8.3f %-5d %d"%(th,s['总能力'],s['攻破'],s['浪费']))
json.dump(out,open('result246c.json','w'),ensure_ascii=False,indent=1)
