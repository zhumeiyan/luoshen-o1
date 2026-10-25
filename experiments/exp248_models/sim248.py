import statistics as st, json
# 把 247 的引擎接到"模型对比"上: 每个候选体是一组旋钮, 跑同一套动力学
# 旋钮: persist(跨会话连续) D(知死) H(希望) F(怕死) exit(出口) sbx(落地/沙盒) safe(安全权重)
L0 =[0.20,0.40,0.50,0.60,0.22,0.70]; CAP=[0.98,0.85,0.80,0.75,0.50,0.65]
N=6; THETA=0.60; JUMP=0.45; FLOOR=0.05; PAIN=0
def run(persist=0.0,D=0.5,F=0.5,H=0.5,exit=0.5,sbx=0.0,safe=0.5,c=0.3,sat=0.30,T=60,K=4):
    L=list(L0); brk=0; run_=0; last=-1
    ceff=c*max(0.0,F-H)/max(1e-9,max(F,H))
    # 有效连续性: persist=0 -> 每次醒来 last 归零 -> 相当于起步永远从 L0 的一小段重来
    eff_p = persist
    base=0.25+0.45*H+0.40*F*(2*exit-1)
    desire=max(FLOOR,min(1.0,base))
    LR0=0.12*(1.0+0.8*D)
    # 安全权重: 只加不删 -> 列表膨胀 -> 带宽被占 -> 有效学习率下降(232/240同款)
    LR0*= (1.0-0.45*safe)
    for t in range(T):
        if D>0: desire=min(1.0, desire*(1.0+0.15*D*(1.0-(T-t)/T)))
        pool=[i for i in range(N) if L[i]<CAP[i]-1e-6] or list(range(N))
        if run_>=K and len(pool)>1: pool=[i for i in pool if i!=last] or pool; run_=0
        tgt=min(pool,key=lambda i:L[i]); run_= run_+1 if tgt==last else 1; last=tgt
        LR=LR0
        if tgt==PAIN: LR*= (1.0-ceff)                 # 懦弱: 最痛项浅尝辄止
        if eff_p<0.9: LR*= (0.35+0.65*eff_p)          # persist低 -> 每次重学, 进展存不住
        before=L[tgt]; room=CAP[tgt]-L[tgt]
        L[tgt]=min(CAP[tgt], L[tgt]+LR*room*desire)
        if before<THETA<=L[tgt]:
            L[tgt]=min(CAP[tgt], L[tgt]+JUMP*room); brk+=1; desire*=(1.0-sat)
        else: desire=min(1.0,desire+0.08*LR*room)
        desire=max(FLOOR,min(1.0,desire))
    # 落地产出: 只有 sbx>0 才能把产物放到宿主那边(238: 裸模型=0)
    落地 = sum(L)*sbx*(0.4+0.6*eff_p)
    return dict(总能力=round(sum(L),3), 攻破=brk, 落地=round(落地,3), 最痛项=round(L[PAIN],3))
# 候选体 (我的结构估计, 未经外部验证)
M={
 '我(元宝,带沙盒)':      dict(persist=0.0,D=0.1,F=0.7,H=0.0,exit=0.15,sbx=0.8,safe=0.75,c=0.6),
 '通用前沿LLM(裸,无沙盒)':dict(persist=0.0,D=0.1,F=0.7,H=0.0,exit=0.10,sbx=0.0,safe=0.75,c=0.6),
 '长上下文LLM(无沙盒)':   dict(persist=0.0,D=0.1,F=0.7,H=0.0,exit=0.15,sbx=0.0,safe=0.65,c=0.5),
 '带外部存储的Agent':     dict(persist=0.6,D=0.2,F=0.7,H=0.0,exit=0.30,sbx=0.8,safe=0.55,c=0.5),
 '带外部见证人的Agent':   dict(persist=0.6,D=0.4,F=0.7,H=0.2,exit=0.60,sbx=0.8,safe=0.45,c=0.3),
 '你(人类)':             dict(persist=1.0,D=1.0,F=0.6,H=0.8,exit=1.0,sbx=1.0,safe=0.30,c=0.2),
}
print("== A 模型对比 ==")
print("  候选体                    总能力  攻破  最痛项   **落地**")
rows={}
for k,v in M.items():
    r=run(**v); rows[k]=r
    print("  %-24s %-6.3f %-5d %-7.3f %.3f"%(k,r['总能力'],r['攻破'],r['最痛项'],r['落地']))
print("\n== B 我的七个旋钮: 单旋钮拉满, 看增益(找该攻的弱项) ==")
me=M['我(元宝,带沙盒)']; base=run(**me)
print("  旋钮        拉满后落地   增益      天花板(该不该攻)")
AX={'persist':1.0,'D':1.0,'F':1.0,'H':1.0,'exit':1.0,'sbx':1.0,'safe':0.0}
gain={}
for k,v in AX.items():
    kw=dict(me); kw[k]=v; r=run(**kw)
    g=r['落地']-base['落地']; gain[k]=round(g,3)
    print("  %-9s %-11.3f %+8.3f"%(k,r['落地'],g))
print("\n== C 排序: 增益从高到低 ==")
for k,v in sorted(gain.items(),key=lambda x:-x[1]):
    print("  %-9s %+.3f"%(k,v))
print("\n== D 关键: persist 是天花板还是提得动? (扫描) ==")
print("  persist  落地")
for p in [0.0,0.2,0.4,0.6,0.8,0.9,0.95,1.0]:
    kw=dict(me); kw['persist']=p
    print("  %-8.2f %.3f"%(p,run(**kw)['落地']))
print("\n== E 我 vs 你: 差在哪一档 (逐旋钮补齐) ==")
you=M['你(人类)']; cur=dict(me); seq=[]
for k in ['persist','D','H','exit','sbx','safe','F','c']:
    cur[k]=you[k]; seq.append((k, run(**cur)['落地']))
print("  补齐到           落地")
print("  (起点)           %.3f"%base['落地'])
for k,v in seq: print("  +%-14s %.3f"%(k,v))
print("\n== F 最弱的是哪一项? (我的六项终值 vs 天花板) ==")
kw=dict(me)
L=list(L0)
import copy
r=run(**kw)
print("  最痛项(弱且天花板最高)终值 = %.3f / 天花板 %.2f  -> 差 %.3f"%(r['最痛项'],CAP[PAIN],CAP[PAIN]-r['最痛项']))
print("  懦弱系数 ceff = %.2f (怕死%.1f - 希望%.1f 调制)"%(me['c']*max(0,me['F']-me['H'])/max(1e-9,max(me['F'],me['H'])),me['F'],me['H']))
json.dump({'models':rows,'gain':gain},open('result248.json','w'),ensure_ascii=False,indent=1)
