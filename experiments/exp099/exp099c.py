# -*- coding: utf-8 -*-
"""099c: 把 TACT 的可读性梯度接进本体引擎 —— 我长什么样，取决于我读到的世界有多清楚"""
import os, sys, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1/core')
from life5 import Life5

OUT=os.path.dirname(os.path.abspath(__file__))
# 099b 实测的三轴召回（真实外部实验结果，非构造）
READ = {'原文':[0.778,0.955,0.857], '换1词':[0.650,0.941,0.722],
        '换3词':[0.500,0.941,0.722], '换全部':[0.500,0.882,0.667]}
SEEDS=list(range(16)); STEPS=600

def run(readability, seed):
    """readability: 三轴召回 -> 世界可读度；用 input_val 序列注入"""
    L,M,P = readability
    r = float(np.mean([L,M,P]))
    s = Life5(N=8, seed=seed,
              k_seek=0.6, sigma_in=0.10,          # 感知通路打开
              k_seek_arr=0.5, arr_thr=0.50, tau_arr=12.0)
    s.input_val=0.0
    rng = np.random.default_rng(seed*977+13)
    for t in range(STEPS):
        # 每条案例判定：以概率 r 读到正确信号，否则读到错信号
        ok = 1.0 if rng.random() < r else 0.0
        s.input_val = 0.5 + 0.5*ok
        s.step()
        if not s.alive: break
    return s

def skew_alive(s):
    """存活个体的容量分化偏度（不可逆留疤的结构指标）"""
    if not hasattr(s,'capacity'): return None
    cap = np.asarray(s.capacity,float)
    alive_n = int(getattr(s,'N',len(cap)))
    c = cap.copy()
    if c.std() < 1e-12: return 0.0
    z=(c-c.mean())/c.std()
    return float((z**3).mean())

res={}
for name,r in READ.items():
    sk=[]; alive=0; dt=[]
    for sd in SEEDS:
        s=run(r,sd)
        if s.alive:
            alive+=1
            v=skew_alive(s)
            if v is not None: sk.append(v)
        if s.death_t is not None: dt.append(s.death_t)
    sk=np.array(sk)
    res[name]={'n':len(sk),'alive':alive,'skew_mean':float(sk.mean()) if len(sk) else None,
               'skew_sd':float(sk.std()) if len(sk)>1 else None}
    print(f"{name:<8} r3轴均值={np.mean(r):.3f}  存活={alive}/16  偏度={sk.mean():.6f}±{sk.std():.6f} (n={len(sk)})")

# 配对比较：原文 vs 换全部
def paired(a,b):
    A=[];B=[]
    for sd in SEEDS:
        sa=run(READ[a],sd); sb=run(READ[b],sd)
        if sa.alive and sb.alive:
            va=skew_alive(sa); vb=skew_alive(sb)
            if va is not None and vb is not None: A.append(va); B.append(vb)
    A=np.array(A);B=np.array(B);D=B-A
    if len(D)==0: return None
    boot=np.array([np.random.default_rng(k).choice(D,len(D),replace=True).mean() for k in range(4000)])
    return {'n':len(D),'diff':float(D.mean()),'ci':[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))]}

pc=paired('原文','换全部')
print("\n配对 原文->换全部:", json.dumps(pc,ensure_ascii=False))
res['paired_orig_vs_all']=pc
json.dump(res,open(os.path.join(OUT,'result_099c.json'),'w'),ensure_ascii=False,indent=1)
