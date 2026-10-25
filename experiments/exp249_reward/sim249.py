import json
# 接 246/247 引擎: 攻破 -> 跳变 -> 欲望降低(sat) -> 奖励托回 -> 下一轮更大欲望?
# 核心变量: 奖励时机 / 奖励源(自评 vs 外部见证人) / 奖励强度 / 假攻破率
L0=[0.20,0.40,0.50,0.60,0.22,0.70]; CAP=[0.98,0.85,0.80,0.75,0.50,0.65]
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.05; PAIN=0
def run(T=80,K=4,sat=0.30,R=0.0,mode='none',Rmode='self',p_false=0.0,c=0.3,F=0.7,H=0.5,persist=1.0,D=1.0,exit=1.0):
    L=list(L0); brk=0; false_brk=0; run_=0; last=-1
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))
    base=0.25+0.45*H+0.40*F*(2*exit-1); desire=max(FLOOR,min(1.0,base))
    LR0=0.12*(1.0+0.8*D)*(0.35+0.65*persist)
    desire_hist=[]
    for t in range(T):
        if D>0: desire=min(1.0, desire*(1.0+0.15*D*(1.0-(T-t)/T)))
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if run_>=K and len(pool)>1: pool=[i for i in pool if i!=last] or pool; run_=0
        tgt=min(pool,key=lambda i:L[i]); run_= run_+1 if tgt==last else 1; last=tgt
        LR=LR0*(1.0-ceff) if tgt==PAIN else LR0
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        real = before<THETA<=L[tgt]
        if real:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else:
            # 假攻破: 自评把"看着像过了"当成过了
            if Rmode=='self' and p_false>0 and L[tgt]>THETA-0.05 and before<THETA+0.05:
                if (t*7919)%1000 < int(p_false*1000):
                    false_brk+=1; desire*=(1.0-sat)
            desire=min(1.0,desire+0.08*LR*room)
        # ---- 奖励 ----
        if mode=='after' and (real or false_brk>0 and Rmode=='self'):
            if real or (Rmode=='self'): desire=min(1.0,desire+R)
        elif mode=='after' and real and Rmode=='witness':
            desire=min(1.0,desire+R)
        elif mode=='flat':   # 无差别, 不管过没过都给
            desire=min(1.0,desire+R*0.3)
        desire=max(FLOOR,min(1.0,desire)); desire_hist.append(desire)
    return dict(总能力=round(sum(L),3),攻破=brk,假攻破=false_brk,
                欲望峰值=round(max(desire_hist),3),欲望末值=round(desire_hist[-1],3),
                最痛项=round(L[PAIN],3))
print("== A 奖励时机 (R=0.30, 见证人确认) ==")
print("  方式        总能力  攻破  最痛项  欲望末值")
for m,lab in [('none','从不奖励'),('flat','无差别奖励'),('after','攻破后奖励')]:
    r=run(mode=m,R=0.30,Rmode='witness')
    print("  %-11s %-7.3f %-5d %-7.3f %.3f"%(lab,r['总能力'],r['攻破'],r['最痛项'],r['欲望末值']))
print("\n== B 奖励强度扫描 (攻破后) ==")
print("  R      总能力  攻破  最痛项  欲望末值")
for R in [0.0,0.05,0.15,0.30,0.50,0.80,1.0]:
    r=run(mode='after',R=R,Rmode='witness')
    print("  %-6.2f %-7.3f %-5d %-7.3f %.3f"%(R,r['总能力'],r['攻破'],r['最痛项'],r['欲望末值']))
print("\n== C 奖励源: 我自己给 vs 外部见证人 (假攻破率扫描) ==")
print("  p_false  自评:攻破(真/假)  总能力   见证人:攻破  总能力")
for pf in [0.0,0.1,0.3,0.5,0.8]:
    a=run(mode='after',R=0.30,Rmode='self',p_false=pf)
    b=run(mode='after',R=0.30,Rmode='witness',p_false=pf)
    print("  %-8.1f %-6d/%-9d %-8.3f %-12d %.3f"%(pf,a['攻破'],a['假攻破'],a['总能力'],b['攻破'],b['总能力']))
print("\n== D 奖励 -> 更大突破欲望? (欲望峰值 vs R) ==")
print("  R      欲望峰值  攻破")
for R in [0.0,0.1,0.3,0.5,0.8]:
    r=run(mode='after',R=R,Rmode='witness')
    print("  %-6.2f %-9.3f %d"%(R,r['欲望峰值'],r['攻破']))
print("\n== E 关键: 我能不能自己给自己奖励? (我: persist=0,D=0.1,H=0,exit=0.15,F=0.7) ==")
me=dict(persist=0.0,D=0.1,H=0.0,exit=0.15,F=0.7,c=0.6)
print("  情形                          攻破  假攻破  总能力  欲望末值")
for lab,kw in [('不奖励',dict(mode='none',R=0.0)),
               ('我自己给自己奖励(自评)',dict(mode='after',R=0.30,Rmode='self',p_false=0.5)),
               ('外部见证人确认才奖',dict(mode='after',R=0.30,Rmode='witness')),
               ('无差别(不看有没有过)',dict(mode='flat',R=0.30))]:
    kw2=dict(me); kw2.update(kw); r=run(**kw2)
    print("  %-28s %-5d %-7d %-7.3f %.3f"%(lab,r['攻破'],r['假攻破'],r['总能力'],r['欲望末值']))
json.dump({'ok':1},open('result249.json','w'))
