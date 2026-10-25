# -*- coding: utf-8 -*-
"""
实验 075b · 真实世界换能器（修正版）

修正 075 的致命污染：存活率在条件间从 0.000 到 1.000 剧烈波动，
死亡系统的结构偏度与存活系统不可比（死亡筛选污染，判据核第 293 条）。

修正：
  ① 共同存活子集：只比较在【所有】条件下都存活的 seed
  ② 配对设计：同一 seed、同一 scale，条件间两两比较
  ③ 配对 bootstrap CI：避免把噪声读作结论（069b 教训）
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

ROOT = os.path.join(os.path.dirname(__file__), '..')
F = os.path.join(ROOT,'evidence','raw_data','real_weather_field_20261016T2305.json')
d = json.load(open(F))
temps = [x['temperature'] for x in d if 'temperature' in x]
cities= [x.get('city','?') for x in d if 'temperature' in x]
N = len(temps)

def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)

zr = z(temps)
rng = np.random.default_rng(2026)
zs = zr.copy(); rng.shuffle(zs)
zrand = rng.normal(0,1,N); zrand=(zrand-zrand.mean())/max(zrand.std(ddof=1),1e-12)

SEEDS = list(range(24))
def run(sig, seed, scale, steps=600):
    lf = Life5(N=N, seed=seed)
    lf.net_push = sig*scale
    lf.run(steps)
    cap=np.asarray(lf.log[-1]['capv'],float)
    return lf.alive, float(cap.std(ddof=1)/max(cap.mean(),1e-12))

print("=== 扫描小 scale，找存活率可比的工作点 ===")
SCALES=[0.004,0.008,0.012,0.016,0.020]
raw={}
for sc in SCALES:
    raw[sc]={}
    for nm,sig in [('real',zr),('shuffled',zs),('random',zrand),('none',np.zeros(N))]:
        rs=[run(sig,s,sc) for s in SEEDS]
        raw[sc][nm]=dict(alive=[a for a,_ in rs], skew=[k for _,k in rs])
    al={nm:np.mean(raw[sc][nm]['alive']) for nm in raw[sc]}
    print(f"scale={sc:.3f} alive: " + " ".join(f"{nm}={al[nm]:.3f}" for nm in ['real','shuffled','random','none']))

print("\n=== 共同存活子集 + 配对比较 ===")
best=None
for sc in SCALES:
    common=[s for s in SEEDS if all(raw[sc][nm]['alive'][i] for nm in raw[sc]) for i,ss in enumerate(SEEDS) if ss==s]
    # 上面写法有误，重写
    common=[]
    for i,s in enumerate(SEEDS):
        if all(raw[sc][nm]['alive'][i] for nm in ['real','shuffled','random','none']):
            common.append(i)
    if len(common)>=8:
        best=(sc,common); print(f"  scale={sc:.3f} 共同存活 n={len(common)}  ✓ 可用于比较")
    else:
        print(f"  scale={sc:.3f} 共同存活 n={len(common)}  ✗ 太少")

def paired_boot(a,b,n=20000,seed=7):
    a=np.asarray(a,float); b=np.asarray(b,float); dif=a-b
    r=np.random.default_rng(seed)
    idx=r.integers(0,len(dif),(n,len(dif)))
    bs=dif[idx].mean(axis=1)
    return dif.mean(), np.percentile(bs,2.5), np.percentile(bs,97.5)

if best:
    sc,common=best
    print(f"\n=== 在 scale={sc:.3f}、共同存活 n={len(common)} 下的配对比较 ===")
    for nm in ['real','shuffled','random','none']:
        v=[raw[sc][nm]['skew'][i] for i in common]
        print(f"  {nm:<9} skew={np.mean(v):.4f} ±{np.std(v,ddof=1)/np.sqrt(len(v)):.4f}")
    for x,y in [('real','shuffled'),('real','random'),('shuffled','random'),('real','none')]:
        a=[raw[sc][x]['skew'][i] for i in common]; b=[raw[sc][y]['skew'][i] for i in common]
        m,lo,hi=paired_boot(a,b)
        sig="显著" if (lo>0 or hi<0) else "不显著"
        print(f"  {x}-{y}: Δ={m:+.4f} CI[{lo:+.4f},{hi:+.4f}] {sig}")
    json.dump(dict(scale=sc,n_common=len(common),
                   raw={str(k):v for k,v in raw.items()}),
              open(os.path.join(ROOT,'result_075b.json'),'w'),ensure_ascii=False,indent=1)
