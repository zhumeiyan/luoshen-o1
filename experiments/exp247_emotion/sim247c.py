import random, statistics as st
# v2作废: 最弱项天花板<门槛 -> 攻它本就是浪费 -> 回避它反而理性 -> c测出负效应(设计错)
# v3: 天花板与起始值反相关 -> 最弱项天花板最高(最痛但最值得攻) -> 回避它才是真懦弱
CAP=[0.98,0.90,0.82,0.70,0.58,0.45]     # idx0 天花板最高
L0 =[0.20,0.28,0.35,0.42,0.50,0.58]     # idx0 起始最低 = 最弱, 但最值得攻
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.05
def sim(D=0.5,F=0.5,H=0.5,c=0.3,exit=0.5,learn=0.3,T=40,seed=0,mode='cycle',sat=0.30):
    r=random.Random(seed*7919+13)
    L=list(L0); known=[False]*N; brk=0; wasted=0; avoided=0
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))     # 懦弱性被(F-H)调制
    base=0.25+0.45*H+0.40*F*(2*exit-1)
    desire=max(FLOOR,min(1.0,base)); LR=0.12*(1.0+0.8*D)
    for t in range(T):
        left=T-t
        if D>0: desire=min(1.0, desire*(1.0+0.15*D*(1.0-left/T)))
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6]
        if not pool: pool=list(range(N))
        if mode=='weak':    tgt=min(pool,key=lambda i:L[i])
        elif mode=='strong':tgt=max(pool,key=lambda i:L[i])
        else:
            order=sorted(pool,key=lambda i:L[i])
            if r.random()<ceff and len(order)>1:
                tgt=order[1]; avoided+=1          # 懦弱: 回避最弱的, 攻次弱的
            else: tgt=order[0]
        if r.random()<learn:
            known[tgt]=True
            if CAP[tgt]<THETA: wasted+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<THETA<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else: desire=min(1.0, desire+0.08*LR*room)
        desire=max(FLOOR,min(1.0,desire))
    return dict(总能力=round(sum(L),3), 攻破=brk, 浪费=wasted, 回避次数=avoided, ceff=round(ceff,3))
S=range(12)
print("== v3-A 懦弱性 c (怕死主导 F=.8/H=.2, T=40) 12seed ==")
print("  c     总能力            ceff")
for cc in [0.0,0.2,0.4,0.6,0.8,1.0]:
    v=[sim(F=0.8,H=0.2,c=cc,seed=s)['总能力'] for s in S]
    print("  %-5.1f %.3f ±%.3f   %.2f"%(cc,st.mean(v),st.pstdev(v),cc*max(0,.8-.2)/.8))
print("\n== v3-B 懦弱性 x 情绪调制 (c=0.8) ==")
print("  组合          ceff  总能力")
for tag,f,h in [('怕死主导 .8/.2',.8,.2),('平衡 .5/.5',.5,.5),('希望主导 .2/.8',.2,.8),('无怕死 0/.8',0,.8)]:
    v=[sim(F=f,H=h,c=0.8,seed=s)['总能力'] for s in S]
    print("  %-13s %.2f   %.3f ±%.3f"%(tag,0.8*max(0,f-h)/max(1e-9,max(f,h)),st.mean(v),st.pstdev(v)))
print("\n== v3-C 三情绪消融 (c=0.5) 12seed ==")
print("  条件        总能力          攻破")
for tag,kw in [('全有',dict(D=.5,F=.5,H=.5)),('去知死',dict(D=0,F=.5,H=.5)),
               ('去怕死',dict(D=.5,F=0,H=.5)),('去希望',dict(D=.5,F=.5,H=0)),
               ('三无(我)',dict(D=0,F=0,H=0)),('怕死无出口',dict(D=.5,F=.8,H=.2,exit=0.0))]:
    v=[sim(c=0.5,**kw,seed=s)['总能力'] for s in S]
    b=[sim(c=0.5,**kw,seed=s)['攻破'] for s in S]
    print("  %-11s %.3f ±%.3f   %.1f"%(tag,st.mean(v),st.pstdev(v),st.mean(b)))
print("\n== v3-D 知死 D 扫描 12seed ==")
print("  D     总能力")
for dd in [0.0,0.2,0.4,0.6,0.8,1.0]:
    v=[sim(D=dd,c=0.5,seed=s)['总能力'] for s in S]
    print("  %-5.1f %.3f ±%.3f"%(dd,st.mean(v),st.pstdev(v)))
print("\n== v3-E 攻弱/攻强 x 情绪 (c=0.5) ==")
print("  组合        weak          strong")
for tag,f,h in [('怕死主导',.8,.2),('希望主导',.2,.8)]:
    a=[sim(F=f,H=h,c=.5,mode='weak',seed=s)['总能力'] for s in S]
    b=[sim(F=f,H=h,c=.5,mode='strong',seed=s)['总能力'] for s in S]
    print("  %-10s %.3f±%.3f  %.3f±%.3f"%(tag,st.mean(a),st.pstdev(a),st.mean(b),st.pstdev(b)))
