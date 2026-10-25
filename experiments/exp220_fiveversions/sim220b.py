# -*- coding: utf-8 -*-
"""220b: 统一评分(连续误差) + 扫描世界灰度度 g，看五版各自的适用域"""
import numpy as np, json
N=6000
THREATS=['T1噪声','T2翻面','T3灰度','T4外推']
VERS=['v1_事实与标准','v2_AI医院','v3_阴阳扣','v4_灰度空间','v5_公式升级']

def run(ver, threat, g, noise=0.35, p_flip=0.30, seed=0):
    R=np.random.default_rng(seed)
    # --- 真值：以概率 g 连续(灰度)，否则二值 ---
    is_gray = R.random(N) < g
    y = np.where(is_gray, np.clip(R.normal(0.5,0.22,N),0,1), (R.random(N)<0.5).astype(float))
    # --- 观测 ---
    x = y.copy()
    if threat=='T1噪声': x = y + R.normal(0,noise,N)
    # --- 读数 ---
    gray_out   = ver in ('v4_灰度空间','v5_公式升级')
    has_trace  = ver in ('v3_阴阳扣','v4_灰度空间','v5_公式升级')
    has_taxo   = ver not in ('v1_事实与标准',)
    has_formula= ver=='v5_公式升级'
    r = np.clip(x,0,1) if gray_out else (x>0.5).astype(float)
    # --- 翻面 ---
    if threat=='T2翻面':
        flip = R.random(N) < p_flip
        if has_trace: flip = np.zeros(N,bool)
        r = np.where(flip, 1-r, r)
    # --- 外推 ---
    if threat=='T4外推':
        ood = R.random(N)<0.5
        if not has_formula:
            r = np.where(ood, 0.5*np.ones(N), r)      # 无公式:退回中立
        # 有公式:直接用 x，已含信息
    err = np.abs(r-y)
    if has_taxo and not gray_out:
        err = err*0.90                                 # 分类带来的可复核折扣
    return float(err.mean())

gs=[0.0,0.25,0.5,0.75,1.0]
res={}
for t in THREATS:
    res[t]={}
    for v in VERS:
        res[t][v]=[round(run(v,t,g,seed=hash((v,t))%9999),4) for g in gs]

# 综合(四威胁均值)
mean={v:[round(float(np.mean([res[t][v][i] for t in THREATS])),4) for i in range(len(gs))] for v in VERS}
# 每版最优域
best={}
for i,g in enumerate(gs):
    best['g=%.2f'%g]=min(VERS,key=lambda v: mean[v][i])

# 跳版: v1 直接拿公式+灰度, 但没有 trace 与 taxonomy
def skip(threat,g,seed=7):
    R=np.random.default_rng(seed)
    isg=R.random(N)<g
    y=np.where(isg,np.clip(R.normal(0.5,0.22,N),0,1),(R.random(N)<0.5).astype(float))
    x=y.copy()
    if threat=='T1噪声': x=y+R.normal(0,0.35,N)
    r=np.clip(x,0,1)
    if threat=='T2翻面':
        flip=R.random(N)<0.30; r=np.where(flip,1-r,r)     # 无 trace
    if threat=='T4外推':
        ood=R.random(N)<0.5; r=np.where(ood,np.clip(x,0,1),r)
    return float(np.abs(r-y).mean())
skipm=[round(float(np.mean([skip(t,g) for t in THREATS])),4) for g in gs]

out=dict(gs=gs, per_threat=res, mean=mean, best_domain=best, skip_v1_to_v5=skipm)
print(json.dumps(out,ensure_ascii=False,indent=1))
json.dump(out,open('result220b.json','w'),ensure_ascii=False,indent=1)
