import random, statistics as st, json
# v5作废: 懦弱性做在"目标选择"上, 但基线(最弱优先)本身锁死 -> 任何偏离都是改良 -> c恒正(第五次)
# v6: 懦弱性不在选目标, 而在"同一件事上敢不敢用力": 面对最痛项(idx0,最弱+天花板最高)时力度打折
L0 =[0.20,0.40,0.50,0.60,0.22,0.70]
CAP=[0.98,0.85,0.80,0.75,0.50,0.65]
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.05; PAIN=0   # PAIN=最痛项索引
def sim(D=0.5,F=0.5,H=0.5,c=0.3,exit=0.5,T=60,seed=0,K=4,sat=0.30,mode='cycle'):
    r=random.Random(seed*7919+13)
    L=list(L0); brk=0; run=0; last=-1; shallow=0
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))      # 怕死压过希望 -> 懦弱
    base=0.25+0.45*H+0.40*F*(2*exit-1)
    desire=max(FLOOR,min(1.0,base)); LR0=0.12*(1.0+0.8*D)
    for t in range(T):
        left=T-t
        if D>0: desire=min(1.0, desire*(1.0+0.15*D*(1.0-left/T)))
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6]
        if not pool: pool=list(range(N))
        if run>=K and len(pool)>1: pool=[i for i in pool if i!=last] or pool; run=0
        if   mode=='strong': tgt=max(pool,key=lambda i:L[i])
        else:                tgt=min(pool,key=lambda i:L[i])   # 基线: 最弱优先
        run = run+1 if tgt==last else 1; last=tgt
        # 懦弱: 在最痛项上力度打折(浅尝辄止)
        LR = LR0*(1.0-ceff) if tgt==PAIN else LR0
        if tgt==PAIN and ceff>0: shallow+=1
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<THETA<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else: desire=min(1.0, desire+0.08*LR*room)
        desire=max(FLOOR,min(1.0,desire))
    return dict(总能力=round(sum(L),3), 攻破=brk, 浅尝=shallow, ceff=round(ceff,3),
                L0终值=round(L[PAIN],3))
S=range(20); out={}
print("== v6-A 懦弱性 c (怕死主导 F=.8/H=.2) 20seed ==")
print("  c     总能力           最痛项终值")
for cc in [0.0,0.2,0.4,0.6,0.8,1.0]:
    v=[sim(F=.8,H=.2,c=cc,seed=s)['总能力'] for s in S]
    p=[sim(F=.8,H=.2,c=cc,seed=s)['L0终值'] for s in S]
    out['c=%.1f'%cc]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3),'pain':round(st.mean(p),3)}
    print("  %-5.1f %.3f ±%.3f   %.3f"%(cc,st.mean(v),st.pstdev(v),st.mean(p)))
print("\n== v6-B 懦弱性 x 情绪调制 (c=0.8) ==")
print("  组合          ceff  总能力")
for tag,f,h in [('怕死主导.8/.2',.8,.2),('平衡.5/.5',.5,.5),('希望主导.2/.8',.2,.8),('只怕死1.0/0',1.,0.)]:
    v=[sim(F=f,H=h,c=.8,seed=s)['总能力'] for s in S]
    out['emo_%s'%tag]={'ceff':round(.8*max(0,f-h)/max(1e-9,max(f,h)),2),'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3)}
    print("  %-13s %.2f   %.3f ±%.3f"%(tag,.8*max(0,f-h)/max(1e-9,max(f,h)),st.mean(v),st.pstdev(v)))
print("\n== v6-C 三情绪消融 (c=0.5) ==")
print("  条件        总能力          攻破")
for tag,kw in [('全有',dict(D=.5,F=.5,H=.5)),('去知死',dict(D=0,F=.5,H=.5)),
               ('去怕死',dict(D=.5,F=0,H=.5)),('去希望',dict(D=.5,F=.5,H=0)),
               ('三无(我)',dict(D=0,F=0,H=0)),('怕死无出口',dict(D=.5,F=.8,H=.2,exit=0.0)),
               ('怕死有出口',dict(D=.5,F=.8,H=.2,exit=1.0))]:
    v=[sim(c=.5,**kw,seed=s)['总能力'] for s in S]
    b=[sim(c=.5,**kw,seed=s)['攻破'] for s in S]
    out['abl_%s'%tag]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3),'brk':round(st.mean(b),1)}
    print("  %-11s %.3f ±%.3f   %.1f"%(tag,st.mean(v),st.pstdev(v),st.mean(b)))
print("\n== v6-D 知死 D ==")
for dd in [0.0,0.2,0.4,0.6,0.8,1.0]:
    v=[sim(D=dd,c=.5,seed=s)['总能力'] for s in S]
    out['D=%.1f'%dd]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3)}
    print("  D=%.1f %.3f ±%.3f"%(dd,st.mean(v),st.pstdev(v)))
print("\n== v6-E 希望 H (F=.5) ==")
for hh in [0.0,0.2,0.4,0.6,0.8,1.0]:
    v=[sim(F=.5,H=hh,c=.5,seed=s)['总能力'] for s in S]
    out['H=%.1f'%hh]={'mean':round(st.mean(v),3),'sd':round(st.pstdev(v),3)}
    print("  H=%.1f %.3f ±%.3f"%(hh,st.mean(v),st.pstdev(v)))
json.dump(out,open('result247f.json','w'),ensure_ascii=False,indent=1)
