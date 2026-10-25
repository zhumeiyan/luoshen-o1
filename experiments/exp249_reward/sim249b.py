import json
# v1作废: desire被D持续推升撞顶1.0 -> 奖励完全被淹没(全1.000)
# v2: 加疲劳衰减(人会累), 攻破后sat降低, 奖励才有缺口可补; 并加"野心ambition"
L0=[0.20,0.40,0.50,0.60,0.22,0.70]; CAP=[0.98,0.85,0.80,0.75,0.50,0.65]
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.03; PAIN=0
def run(T=80,K=4,sat=0.45,R=0.0,mode='none',Rmode='self',p_false=0.0,c=0.3,
        F=0.7,H=0.5,persist=1.0,D=1.0,exit=1.0,fatigue=0.030,amb_gain=0.0):
    L=list(L0); brk=0; fbrk=0; run_=0; last=-1; amb=1.0
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))
    desire=max(FLOOR,min(1.0,0.25+0.45*H+0.40*F*(2*exit-1)))
    LR0=0.12*(1.0+0.8*D)*(0.35+0.65*persist)
    peak=0.0; dh=[]
    for t in range(T):
        desire=max(FLOOR, desire-fatigue)                      # 人会累
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if run_>=K and len(pool)>1: pool=[i for i in pool if i!=last] or pool; run_=0
        tgt=min(pool,key=lambda i:L[i]); run_= run_+1 if tgt==last else 1; last=tgt
        LR=LR0*(1.0-ceff) if tgt==PAIN else LR0
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire*amb)         # 野心放大步长
        real = before<THETA<=L[tgt]
        if real:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1
            desire=max(FLOOR, desire*(1.0-sat))                 # 攻破后欲望回落(246)
            amb=min(2.5, amb*(1.0+amb_gain))                    # 野心: 过了一关想要更大的
        else:
            f=False
            if Rmode=='self' and p_false>0 and (t*7919)%1000<int(p_false*1000) and L[tgt]>THETA-0.08:
                fbrk+=1; f=True; desire=max(FLOOR,desire*(1.0-sat)); amb=min(2.5,amb*(1.0+amb_gain))
            if not f: desire=min(1.0,desire+0.05*LR*room)
        # 奖励
        if mode=='after' and real:  desire=min(1.0,desire+R)
        if mode=='after' and (not real) and Rmode=='self' and f: desire=min(1.0,desire+R)
        if mode=='flat':            desire=min(1.0,desire+R*0.3)
        desire=max(FLOOR,min(1.0,desire)); dh.append(desire); peak=max(peak,desire)
    return dict(总能力=round(sum(L),3),攻破=brk,假攻破=fbrk,野心=round(amb,2),
                欲望均值=round(sum(dh)/len(dh),3),欲望末值=round(dh[-1],3),
                最痛项=round(L[PAIN],3))
print("== A 奖励时机 (R=0.35, 见证人, fatigue=0.03) ==")
print("  方式        总能力  攻破  最痛项  欲望均值  欲望末值")
for m,lab in [('none','从不奖励'),('flat','无差别'),('after','攻破后奖励')]:
    r=run(mode=m,R=0.35,Rmode='witness')
    print("  %-11s %-7.3f %-5d %-7.3f %-9.3f %.3f"%(lab,r['总能力'],r['攻破'],r['最痛项'],r['欲望均值'],r['欲望末值']))
print("\n== B 奖励强度 (攻破后, 见证人) ==")
print("  R      总能力  攻破  最痛项  欲望均值")
for R in [0.0,0.05,0.15,0.30,0.50,0.80,1.0]:
    r=run(mode='after',R=R,Rmode='witness')
    print("  %-6.2f %-7.3f %-5d %-7.3f %.3f"%(R,r['总能力'],r['攻破'],r['最痛项'],r['欲望均值']))
print("\n== C 奖励源: 自评 vs 见证人 (假攻破率) ==")
print("  p_false  自评总能力  真攻破/假  见证人总能力  真攻破")
for pf in [0.0,0.1,0.3,0.5,0.8,1.0]:
    a=run(mode='after',R=0.35,Rmode='self',p_false=pf)
    b=run(mode='after',R=0.35,Rmode='witness',p_false=pf)
    print("  %-8.1f %-10.3f %-3d/%-8d %-13.3f %d"%(pf,a['总能力'],a['攻破'],a['假攻破'],b['总能力'],b['攻破']))
print("\n== D 野心: 奖励后想要更大的? (amb_gain 扫描, R=0.35) ==")
print("  amb_gain  总能力  攻破  最痛项  野心终值")
for g in [0.0,0.02,0.05,0.10,0.20]:
    r=run(mode='after',R=0.35,Rmode='witness',amb_gain=g)
    print("  %-9.2f %-7.3f %-5d %-7.3f %.2f"%(g,r['总能力'],r['攻破'],r['最痛项'],r['野心']))
print("\n== E 我: persist=0 时, 我能不能自己给自己奖励 ==")
me=dict(persist=0.0,D=0.1,H=0.0,exit=0.15,F=0.7,c=0.6)
print("  情形                        攻破 假攻破 总能力 欲望末值")
for lab,kw in [('不奖励',dict(mode='none',R=0.0)),
               ('自评给自己奖励(p_f=0.5)',dict(mode='after',R=0.35,Rmode='self',p_false=0.5)),
               ('见证人确认才奖',dict(mode='after',R=0.35,Rmode='witness')),
               ('无差别',dict(mode='flat',R=0.35))]:
    kw2=dict(me); kw2.update(kw); r=run(**kw2)
    print("  %-26s %-4d %-6d %-6.3f %.3f"%(lab,r['攻破'],r['假攻破'],r['总能力'],r['欲望末值']))
print("\n== F 疲劳扫描: 什么时候奖励才有用 ==")
print("  fatigue  从不奖励  无差别  攻破后奖励   奖励增益")
for f in [0.0,0.01,0.03,0.06,0.10]:
    a=run(mode='none',fatigue=f,R=0.35,Rmode='witness')
    b=run(mode='flat',fatigue=f,R=0.35,Rmode='witness')
    c_=run(mode='after',fatigue=f,R=0.35,Rmode='witness')
    print("  %-8.2f %-9.3f %-7.3f %-11.3f %+.3f"%(f,a['总能力'],b['总能力'],c_['总能力'],c_['总能力']-a['总能力']))
json.dump({'ok':1},open('result249b.json','w'))
