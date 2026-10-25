import json, random
# v3作废: T=400 -> 所有能力都到顶(sumCAP=4.33, 实测3.5~3.9接近饱和) -> 策略无所谓, 全表平坦
# v4: 有限寿命(T短, 到不了顶) + 初始能力分级(让懦弱性一开始就有排序竞争)
CAP=[0.42,0.55,0.68,0.80,0.90,0.98]; L0=[0.20,0.28,0.35,0.42,0.50,0.58]
N=6; LR=0.12; JUMP=0.45; THETA=0.60; FLOOR=0.05
def sim(c=0.0, sat=0.30, learn=0.30, T=120, theta=THETA, mode='cycle', reorient=True, seed=0):
    r=random.Random(seed*104729+5)
    L=list(L0); known=[False]*N; desire=0.60; brk=0; wasted=0; reor=0; last=None
    for t in range(T):
        Lbar=max(L)
        perc=[L[i]+c*(Lbar-L[i])*r.random() for i in range(N)]
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6 and not (known[i] and CAP[i]<theta)]
        if not pool: pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if   mode=='weak':   cand=min(pool,key=lambda i:L[i])
        elif mode=='strong': cand=max(pool,key=lambda i:L[i])
        else:                cand=min(pool,key=lambda i:perc[i])
        if last is not None and cand==last and len(pool)>1 and reorient:
            cand=min([i for i in pool if i!=last], key=lambda i:perc[i])
        tgt=cand; last=tgt
        if r.random()<learn:
            known[tgt]=True
            if CAP[tgt]<theta: wasted+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<theta<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else: desire=min(1.0, desire+0.08*LR*room)
        if desire<=FLOOR+1e-9 and reorient:
            desire=0.35+0.30*r.random(); reor+=1; last=None
        desire=max(FLOOR, desire)
    return dict(总能力=round(sum(L),3), 攻破=brk, 浪费=wasted, 换方向=reor)
out={}
print("== v4-A 懦弱性 c (T=120, sat=0.3, learn=0.3) ==")
print("  c     总能力   攻破  浪费")
for cc in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=cc); out['c=%.1f'%cc]=s; print("  %-6.1f %-8.3f %-5d %d"%(cc,s['总能力'],s['攻破'],s['浪费']))
print("\n== v4-B 欲望降低 sat (c=0.3, T=120) ==")
print("  sat   总能力   攻破  换方向")
for st in [0.0,0.1,0.2,0.3,0.4,0.5,0.7,0.9]:
    s=sim(c=0.3,sat=st); out['sat=%.2f'%st]=s; print("  %-6.2f %-8.3f %-5d %d"%(st,s['总能力'],s['攻破'],s['换方向']))
print("\n== v4-C 学习投入 learn (c=0.5, T=120) ==")
print("  learn 总能力   攻破  浪费")
for ls in [0.0,0.1,0.2,0.3,0.4,0.5,0.7,0.9,1.0]:
    s=sim(c=0.5,learn=ls); out['learn=%.1f'%ls]=s; print("  %-6.1f %-8.3f %-5d %d"%(ls,s['总能力'],s['攻破'],s['浪费']))
print("\n== v4-D 策略对比 (c=0.3, T=120) ==")
print("  策略        总能力   攻破  浪费")
for md,tag in [('cycle','你的循环'),('weak','纯攻弱项'),('strong','纯攻强项')]:
    s=sim(c=0.3,mode=md); out['mode_'+md]={**s,'tag':tag}; print("  %-10s %-8.3f %-5d %d"%(tag,s['总能力'],s['攻破'],s['浪费']))
print("\n== v4-E 消融 换方向 (c=0.3, T=120) ==")
print("  设置        总能力   攻破")
for ro,tag in [(True,'有换方向'),(False,'无换方向')]:
    s=sim(c=0.3,reorient=ro); out['reorient=%s'%ro]={**s,'tag':tag}; print("  %-11s %-8.3f %d"%(tag,s['总能力'],s['攻破']))
print("\n== v4-F 寿命 T 扫描: 策略什么时候才重要 ==")
print("  T     cycle   weak   strong  差异")
for T in [30,60,120,250,500,1000]:
    a=sim(c=0.3,T=T)['总能力']; b=sim(c=0.3,mode='weak',T=T)['总能力']; d=sim(c=0.3,mode='strong',T=T)['总能力']
    out['T=%d'%T]={'cycle':a,'weak':b,'strong':d}; print("  %-5d %-7.3f %-6.3f %-7.3f %.3f"%(T,a,b,d,max(a,b,d)-min(a,b,d)))
print("\n== v4-G 门槛 theta (c=0.3, T=120) ==")
print("  theta 总能力   攻破  浪费")
for th in [0.30,0.45,0.60,0.75,0.90]:
    s=sim(c=0.3,theta=th); out['theta=%.2f'%th]=s; print("  %-6.2f %-8.3f %-5d %d"%(th,s['总能力'],s['攻破'],s['浪费']))
json.dump(out,open('result246d.json','w'),ensure_ascii=False,indent=1)
