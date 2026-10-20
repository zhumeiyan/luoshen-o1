# -*- coding: utf-8 -*-
"""220c: 跳过 v4 灰度 直接上 v5 公式，在全灰度世界(g=1)下会怎样"""
import numpy as np, json
N=6000
def trial(gray_out, has_trace, has_formula, threat, g, seed):
    R=np.random.default_rng(seed)
    isg=R.random(N)<g
    y=np.where(isg,np.clip(R.normal(0.5,0.22,N),0,1),(R.random(N)<0.5).astype(float))
    x=y.copy()
    if threat=='T1噪声': x=y+R.normal(0,0.35,N)
    r=np.clip(x,0,1) if gray_out else (x>0.5).astype(float)
    if threat=='T2翻面':
        flip=R.random(N)<0.30
        if has_trace: flip=np.zeros(N,bool)
        r=np.where(flip,1-r,r)
    if threat=='T4外推':
        ood=R.random(N)<0.5
        if not has_formula: r=np.where(ood,0.5*np.ones(N),r)
    return float(np.abs(r-y).mean())

TH=['T1噪声','T2翻面','T3灰度','T4外推']
def prof(name,gray,trace,formula,g=1.0):
    v={t:round(trial(gray,trace,formula,t,g,seed=abs(hash((name,t)))%9999),4) for t in TH}
    v['mean']=round(float(np.mean(list(v.values()))),4); return name,v

out={}
for name,gray,trace,formula in [
  ('v3_阴阳扣(二值+trace)',          False,True,False),
  ('skipV4: v3+公式(无灰度)',        False,True,True),
  ('v4_灰度空间(灰度+trace)',        True, True,False),
  ('v5_公式升级(灰度+trace+公式)',   True, True,True),
]:
    n,v=prof(name,gray,trace,formula); out[n]=v

# 二值世界对照 (g=0)
out2={}
for name,gray,trace,formula in [
  ('v1/v3 二值判据 @g=0',            False,True,False),
  ('v4 灰度判据 @g=0',               True, True,False),
]:
    n,v=prof(name,gray,trace,formula,g=0.0); out2[n]=v

print(json.dumps(dict(g1=out,g0=out2),ensure_ascii=False,indent=1))
json.dump(dict(g1=out,g0=out2),open('result220c.json','w'),ensure_ascii=False,indent=1)
