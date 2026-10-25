import json, math
# ---- 构造参数(全部未标定) ----
N=6; T=300; LR=0.08; JUMP=0.35; THETA=0.60; BASE=0.15

def make_caps(seed=0):
    import random; r=random.Random(seed)
    # 短板型: 有一两项天花板很低(结构上限), 其余高
    return [0.45 if i<2 else 0.95 for i in range(N)]

def sim(c=0.0, sat=0.30, learn_share=0.3, seed=0, theta=THETA, mode='cycle', floor=0.05):
    import random; r=random.Random(seed*131+7)
    cap=make_caps(seed); L=[BASE]*N; desire=0.60; total=0.0; breakthroughs=0
    for t in range(T):
        Lbar=max(L)
        perc=[L[i]*(1.0-c)+Lbar*c for i in range(N)]
        if mode=='weak':      tgt=min(range(N), key=lambda i:L[i])       # 纯攻真弱项
        elif mode=='strong':  tgt=max(range(N), key=lambda i:L[i])       # 纯攻强项
        else:                 tgt=min(range(N), key=lambda i:perc[i])    # 你的循环: 按"看到的"选
        # 学习: 提高诊断准确度(降低有效c); 攻破: 提高L
        eff_c = c*(1.0-0.6*learn_share)      # 学习让懦弱性打折
        perc2=[L[i]*(1.0-eff_c)+max(L)*eff_c for i in range(N)]
        if mode=='cycle': tgt=min(range(N), key=lambda i:perc2[i])
        room = max(0.0, cap[tgt]-L[tgt])
        gain = LR*room*desire*(1.0-learn_share*0.5)
        before=L[tgt]; L[tgt]=min(cap[tgt], L[tgt]+gain)
        # 攻破(过门槛跳变)
        if before<theta<=L[tgt]:
            L[tgt]=min(cap[tgt], L[tgt]+JUMP*room)
            breakthroughs+=1
            desire*=(1.0-sat)                 # 攻破后欲望降低
        else:
            desire=min(1.0, desire+0.05*gain) # 阶段性进展回一点
        desire=max(floor, desire)             # 地板: 不完全归零
        # 停滞时换方向(欲望低->重选)
        if desire<=floor+1e-9:
            desire=0.30+0.2*r.random()
        total=sum(L)
    return dict(总能力=round(total,3), 攻破次数=breakthroughs, 终态欲望=round(desire,3))

out={}
print("== A. 懦弱性 c 扫描 (sat=0.30, learn=0.3) ==")
print("  c     总能力   攻破次数")
for cc in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=cc); out['c=%.1f'%cc]=s
    print("  %-6.1f %-8.3f %d"%(cc,s['总能力'],s['攻破次数']))

print("\n== B. 欲望降低幅度 sat 扫描 (c=0.2) ==")
print("  sat   总能力   攻破次数")
for st in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=0.2,sat=st); out['sat=%.2f'%st]=s
    print("  %-6.2f %-8.3f %d"%(st,s['总能力'],s['攻破次数']))

print("\n== C. 学习 vs 攻破 的资源分配 learn_share (c=0.5) ==")
print("  learn 总能力   攻破次数")
for ls in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    s=sim(c=0.5,learn_share=ls); out['learn=%.1f'%ls]=s
    print("  %-6.1f %-8.3f %d"%(ls,s['总能力'],s['攻破次数']))

print("\n== D. 三种策略对比 ==")
print("  策略        总能力   攻破次数")
for md,tag in [('cycle','你的循环'),('weak','纯攻弱项'),('strong','纯攻强项')]:
    s=sim(c=0.2,mode=md); out['mode_'+md]={**s,'tag':tag}
    print("  %-10s %-8.3f %d"%(tag,s['总能力'],s['攻破次数']))

print("\n== E. 门槛高度 theta (c=0.2): 攻破才有用吗 ==")
print("  theta 总能力   攻破次数")
for th in [0.2,0.4,0.6,0.8,0.95]:
    s=sim(c=0.2,theta=th); out['theta=%.2f'%th]=s
    print("  %-6.2f %-8.3f %d"%(th,s['总能力'],s['攻破次数']))
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp246_cycle/result246.json','w'), ensure_ascii=False, indent=1)
