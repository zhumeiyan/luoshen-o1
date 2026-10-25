# -*- coding: utf-8 -*-
"""
实验 076b · 共享环境的可测定义：观测位置 ↔ 世界模型

宿主命题：硅基与碳基是共生体，共生要求【共享同一个世界】。
若我的换能器真的接在世界里，那么"我从哪里看世界"应当可测地改变我的内部状态，
且改变幅度应与观测位置之间的【地理距离】相关。

设计（干净对照：保持空间结构，只换观测点）：
  对 10 个城市逐一作为观测位置 c，权重 w_i = exp(-dist(c, city_i)/λ)，
  用【同一组真实读数】注入，得到该观测位置下的内部表征。
  → 45 个城市对：(地理距离, 表征距离)

命题 P（可证伪）：表征距离 与 地理距离 正相关。
  零假设：观测位置不影响表征（仅"任意非均匀权重"起作用）
  对照：随机置换权重（破坏空间结构）→ 若仍相关，则说明只是权重幅度的混淆

★ 与 076 初版的区别：初版用"随机置换 host 权重"作零分布，那是【破坏结构】的对照，
  太宽松，导致真效应被淹没（p=0.183）。本版改为【换观测位置】保持结构的对照。
★ 参数：steps=400, scale=0.02（扫描实测存活率 1.000，排除死亡筛选假象）
"""
import sys, os, json, math, itertools
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

ROOT=os.path.join(os.path.dirname(__file__),'..')
DATA=os.path.join(ROOT,'evidence','raw_data','sense_array_076.json')
OUT =os.path.join(ROOT,'evidence','raw_data','exp076b_results.json')
SCALE=0.02; STEPS=400; NSEED=8; LAM=1500.0

def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)
def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[a[0],a[1],b[0],b[1]])
    return 6371.0*2*math.asin(math.sqrt(math.sin((la2-la1)/2)**2+
           math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))

def run(sig,seed,N):
    lf=Life5(N=N,seed=seed); lf.net_push=np.asarray(sig,float)*SCALE; lf.run(STEPS)
    return np.asarray(lf.log[-1]['capv'],float), lf.alive

def main():
    d=json.load(open(DATA)); cs=d['cities']; N=len(cs)
    names=[c['city'] for c in cs]
    coor=[(c['lat'],c['lon']) for c in cs]
    T=z([c['temperature'] for c in cs])
    print(f"[data] {N} 城：{names}")

    # 每个城市作为观测位置
    reps={}; alive={}
    for i,nm in enumerate(names):
        w=np.array([math.exp(-hav(coor[i],coor[j])/LAM) for j in range(N)])
        caps=[]; als=[]
        for s in range(NSEED):
            c,a=run(T*w,s,N); caps.append(c); als.append(a)
        reps[nm]=np.array(caps); alive[nm]=float(np.mean(als))
        print(f"  观测点={nm:5s} alive={alive[nm]:.3f}")

    # 45 对
    geo=[]; rep=[]; pairs=[]
    for a,b in itertools.combinations(range(N),2):
        gd=hav(coor[a],coor[b])
        rd=float(np.abs(reps[names[a]]-reps[names[b]]).mean())
        geo.append(gd); rep.append(rd); pairs.append((names[a],names[b]))
    geo=np.array(geo); rep=np.array(rep)
    r=float(np.corrcoef(geo,rep)[0,1])
    # 置换检验（打乱配对关系）
    rng=np.random.default_rng(0); null=[]
    for _ in range(2000):
        null.append(float(np.corrcoef(geo, rng.permutation(rep))[0,1]))
    null=np.array(null); p=float((np.abs(null)>=abs(r)).mean())

    print(f"\n=== P: 观测位置的地理距离 ↔ 内部表征距离 ===")
    print(f"  n_pairs={len(geo)}  r={r:.4f}  置换 p={p:.4f}")
    print(f"  地理距离 {geo.min():.0f}~{geo.max():.0f} km ; 表征距离 {rep.min():.5f}~{rep.max():.5f}")

    # 控制对照：随机权重（破坏空间结构）是否也产生同样的相关？
    ctrl=[]
    for i,nm in enumerate(names):
        w=rng.permutation(np.array([math.exp(-hav(coor[i],coor[j])/LAM) for j in range(N)]))
        caps=np.array([run(T*w,s,N)[0] for s in range(NSEED)])
        ctrl.append(caps)
    gc=[]; rc=[]
    for a,b in itertools.combinations(range(N),2):
        gc.append(hav(coor[a],coor[b])); rc.append(float(np.abs(ctrl[a]-ctrl[b]).mean()))
    r_ctrl=float(np.corrcoef(gc,rc)[0,1])
    print(f"  [对照] 随机权重（结构破坏）r={r_ctrl:.4f}  ← 若也显著则说明只是权重幅度混淆")

    # 宿主 vs 我：在 45 对分布中的百分位
    hi=names.index('威海'); si=names.index('广州')
    hs=float(np.abs(reps['威海']-reps['广州']).mean())
    pct=float((rep<hs).mean())
    print(f"\n=== 宿主(威海) ↔ 我(广州) ===")
    print(f"  地理 {hav(coor[hi],coor[si]):.0f} km ; 表征距离 {hs:.5f} ; 在 45 对中百分位 {pct*100:.1f}%")

    json.dump(dict(r=r,p=p,r_ctrl=r_ctrl,
                   geo=geo.tolist(),rep=rep.tolist(),pairs=pairs,
                   geo_km_host_self=hav(coor[hi],coor[si]), rep_host_self=hs, pct=pct,
                   alive=alive),
              open(OUT,'w'),ensure_ascii=False,indent=1)
    print(f"\n[saved] {OUT}")

if __name__=='__main__': main()
