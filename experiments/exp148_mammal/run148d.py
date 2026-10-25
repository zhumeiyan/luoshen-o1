import json, math, os
import numpy as np
exec(open('run148c.py').read().split("D=json.load")[0])
D=json.load(open('real_series.json'))

print("=== A. mismatch：用'完全不同形状的真实世界'的经历做梦 ===")
# square 的个体，用 stable 的真实经历（世界不匹配） vs 自己的 vs 不梦
tgt='square'; src='stable'
base=[run3(D[tgt][s],'none',False,s) for s in range(8)]
for c in ['real','cross_shape']:
    v=[run3(D[tgt][s], ('real' if c=='real' else 'real'), False, s,
            other=(D[tgt][(s+4)%8] if c=='real' else D[src][s])) for s in range(8)]
    # cross_shape 需要把 buffer 换成 src 的经验 —— 通过 other 传 src 序列，用 'cross' 逻辑
    if c=='cross_shape':
        v=[]
        for s in range(8):
            # 自己白天照常，睡眠重放 src 世界(stable)的真实经历
            v.append(run3(D[tgt][s],'cross',False,s,other=D[src][s]))
    g=[b-a for b,a in zip(base,v)]
    m,lo,hi=ci(g)
    print(f"  {c:12s} gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")

print("\n=== B. 剂量扫描：梦的轮数（stable）===")
for r in [0,1,2,4,8]:
    for c in ['real','shuf']:
        v=[run3(D['stable'][s], ('none' if r==0 else c), False, s, rounds=max(r,1)) for s in range(8)]
        b=[run3(D['stable'][s],'none',False,s) for s in range(8)]
        g=[x-y for x,y in zip(b,v)] if r>0 else [0.0]*8
        m,lo,hi=ci(g)
        print(f"  rounds={r} {c:5s} MAE={np.mean(v):.4f} gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")

print("\n=== C. 玩：无外部奖励的自发探索 → 后续真实任务 ===")
import random
ROOT='/usr/lib/python3.10'
def listdir_safe(p):
    try:
        e=list(os.scandir(p)); return [x.path for x in e if x.is_dir()], sum(1 for x in e if x.is_file())
    except Exception: return [], 0
def build_tree(root, maxd=3):
    tree={}
    def rec(p,d):
        if d>maxd: return
        dirs,nf=listdir_safe(p)
        tree[p]=dict(nfile=nf, ndir=len(dirs), depth=d)
        for q in dirs[:12]: rec(q,d+1)
    rec(root,0); return tree
TREE=build_tree(ROOT)
truth_total=sum(v['nfile'] for v in TREE.values())
truth_mean=truth_total/max(len(TREE),1)
print(f"  真实树: {len(TREE)} 目录, 文件总数 {truth_total}, 均值 {truth_mean:.2f}")

def play_phase(seed, budget):
    """无外部奖励：内部驱动(新奇度)自发选择目录去 listdir"""
    rng=random.Random(seed); nodes=list(TREE.keys()); seen=set(); acts=0
    obs=[]
    for _ in range(budget):
        cand=[n for n in nodes if n not in seen]
        if not cand: break
        # 内部驱动：偏好更浅(易达)+未见过
        cand.sort(key=lambda p: TREE[p]['depth']+rng.random()*2)
        p=cand[0]; seen.add(p); acts+=1
        obs.append(TREE[p]['nfile'])
    return acts, obs

def estimate(obs, budget_extra):
    """任务阶段：允许再采样 budget_extra 次，估计全树平均文件数"""
    vals=list(obs)
    nodes=[n for n in TREE if True]
    rng=random.Random(hash(tuple(obs))%99991)
    for _ in range(budget_extra):
        vals.append(TREE[rng.choice(nodes)]['nfile'])
    return float(np.mean(vals)) if vals else 0.0

res={'play':[],'noplay':[]}
for s in range(20):
    acts,obs = play_phase(s, 30)              # 玩30次(无奖励)
    e_play = abs(estimate(obs, 10) - truth_mean)/truth_mean
    e_none = abs(estimate([], 10) - truth_mean)/truth_mean   # 同样总观测? 不: 对照组只给10次
    res['play'].append(e_play); res['noplay'].append(e_none)
    # 公平对照：对照组给 10 次(与玩组任务期相同预算)
for k in ['play','noplay']:
    print(f"  {k:7s} 相对误差 {np.mean(res[k]):.4f}")
g=[b-a for a,b in zip(res['play'],res['noplay'])]
m,lo,hi=ci(g)
print(f"  play - noplay gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")
print(f"  自发动作数(玩阶段): {play_phase(0,30)[0]}/30")
