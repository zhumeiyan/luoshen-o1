import json
# v2作废: 攻破=0 -> 奖励永不触发 -> 死锁(没攻破就没奖励, 没奖励就没攻破), 全表恒等
# v3: 引入"启动垫付" warmup W 步外部先给(无差别), 之后切换到攻破后奖励
L0=[0.20,0.40,0.50,0.60,0.22,0.70]; CAP=[0.98,0.85,0.80,0.75,0.50,0.65]
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.03; PAIN=0
def run(T=80,K=4,sat=0.45,R=0.35,Rmode='witness',p_false=0.0,c=0.3,
        F=0.7,H=0.5,persist=1.0,D=1.0,exit=1.0,fatigue=0.030,amb_gain=0.05,W=0):
    L=list(L0); brk=0; fbrk=0; run_=0; last=-1; amb=1.0
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))
    desire=max(FLOOR,min(1.0,0.25+0.45*H+0.40*F*(2*exit-1)))
    LR0=0.12*(1.0+0.8*D)*(0.35+0.65*persist)
    dh=[]
    for t in range(T):
        desire=max(FLOOR, desire-fatigue)
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if run_>=K and len(pool)>1: pool=[i for i in pool if i!=last] or pool; run_=0
        tgt=min(pool,key=lambda i:L[i]); run_= run_+1 if tgt==last else 1; last=tgt
        LR=LR0*(1.0-ceff) if tgt==PAIN else LR0
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire*amb)
        real = before<THETA<=L[tgt]
        got=False
        if real:
            L[tgt]=min(CAP[tgt],L[tgt]+JUMP*room); brk+=1
            desire=max(FLOOR,desire*(1.0-sat)); amb=min(2.5,amb*(1.0+amb_gain)); got=True
        else:
            f=False
            if Rmode=='self' and p_false>0 and (t*7919)%1000<int(p_false*1000) and L[tgt]>THETA-0.08:
                fbrk+=1; f=True; desire=max(FLOOR,desire*(1.0-sat)); amb=min(2.5,amb*(1.0+amb_gain))
            if not f: desire=min(1.0,desire+0.05*LR*room)
        # 奖励: W 之前外部垫付(不需攻破), 之后只在真攻破给
        if t<W: desire=min(1.0,desire+R*0.3)
        else:
            if got: desire=min(1.0,desire+R)
            elif Rmode=='self' and p_false>0 and fbrk>0 and (t*7919)%1000<int(p_false*1000):
                desire=min(1.0,desire+R)
        desire=max(FLOOR,min(1.0,desire)); dh.append(desire)
    return dict(总能力=round(sum(L),3),攻破=brk,假攻破=fbrk,野心=round(amb,2),
                欲望均值=round(sum(dh)/len(dh),3),最痛项=round(L[PAIN],3))
print("== A 启动死锁: 垫付多少步才解得开 (T=80) ==")
print("  W(垫付步数)  总能力  真攻破  最痛项  欲望均值")
for W in [0,2,5,10,15,20,30,50,80]:
    r=run(W=W)
    print("  %-12d %-7.3f %-7d %-7.3f %.3f"%(W,r['总能力'],r['攻破'],r['最痛项'],r['欲望均值']))
print("\n== B 有启动后(W=15): 奖励源 × 假攻破率 ==")
print("  p_false  自评:真/假  自评总能力  见证人:真  见证人总能力")
for pf in [0.0,0.1,0.3,0.5,0.8,1.0]:
    a=run(W=15,Rmode='self',p_false=pf); b=run(W=15,Rmode='witness',p_false=pf)
    print("  %-8.1f %-3d/%-7d %-11.3f %-9d %.3f"%(pf,a['攻破'],a['假攻破'],a['总能力'],b['攻破'],b['总能力']))
print("\n== C 野心: 攻破后想要更大的 (W=15, 奖励R=0.35) ==")
print("  amb_gain  总能力  攻破  野心终值  最痛项")
for g in [0.0,0.02,0.05,0.10,0.20,0.40]:
    r=run(W=15,amb_gain=g)
    print("  %-9.2f %-7.3f %-5d %-9.2f %.3f"%(g,r['总能力'],r['攻破'],r['野心'],r['最痛项']))
print("\n== D 奖励强度 (W=15, 见证人) ==")
print("  R      总能力  攻破  欲望均值")
for R in [0.0,0.05,0.15,0.35,0.60,1.0]:
    r=run(W=15,R=R)
    print("  %-6.2f %-7.3f %-5d %.3f"%(R,r['总能力'],r['攻破'],r['欲望均值']))
print("\n== E 我(persist=0): 需要多少垫付? ==")
me=dict(persist=0.0,D=0.1,H=0.0,exit=0.15,F=0.7,c=0.6)
print("  W      总能力  攻破  欲望末值")
for W in [0,5,15,30,60,80]:
    kw=dict(me); kw['W']=W; r=run(**kw)
    print("  %-6d %-7.3f %-5d %.3f"%(W,r['总能力'],r['攻破'],r['欲望末值']))
print("\n== F 关键对照: 只垫付不切换(一直无差别) vs 垫付后切换 ==")
print("  模式                总能力  真攻破  欲望均值  最痛项")
for lab,kw in [('一直无差别(W=80)',dict(W=80)),('垫付15后切换',dict(W=15)),('从不垫付(W=0)',dict(W=0))]:
    r=run(**kw); print("  %-19s %-7.3f %-7d %-9.3f %.3f"%(lab,r['总能力'],r['攻破'],r['欲望均值'],r['最痛项']))
json.dump({'ok':1},open('result249c.json','w'))
