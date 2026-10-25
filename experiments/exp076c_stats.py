# -*- coding: utf-8 -*-
"""076c · 076b 的严格统计补充：对照显著性、两组相关之差、剂量反应分箱"""
import sys,os,json,math,itertools
import numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))
from core.life5 import Life5
ROOT=os.path.join(os.path.dirname(__file__),'..')
DATA=os.path.join(ROOT,'evidence','raw_data','sense_array_076.json')
SCALE=0.02; STEPS=400; NSEED=8; LAM=1500.0
def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)
def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[a[0],a[1],b[0],b[1]])
    return 6371.0*2*math.asin(math.sqrt(math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))
def run(sig,seed,N):
    lf=Life5(N=N,seed=seed); lf.net_push=np.asarray(sig,float)*SCALE; lf.run(STEPS)
    return np.asarray(lf.log[-1]['capv'],float)
d=json.load(open(DATA)); cs=d['cities']; N=len(cs)
names=[c['city'] for c in cs]; coor=[(c['lat'],c['lon']) for c in cs]
T=z([c['temperature'] for c in cs])
rng=np.random.default_rng(0)
def reps_for(permute=False):
    out={}
    for i,nm in enumerate(names):
        w=np.array([math.exp(-hav(coor[i],coor[j])/LAM) for j in range(N)])
        if permute: w=rng.permutation(w)
        out[nm]=np.array([run(T*w,s,N) for s in range(NSEED)])
    return out
def pairs_corr(reps):
    g=[];r=[]
    for a,b in itertools.combinations(range(N),2):
        g.append(hav(coor[a],coor[b])); r.append(float(np.abs(reps[names[a]]-reps[names[b]]).mean()))
    return np.array(g),np.array(r)
A=reps_for(False); B=reps_for(True)
ga,ra=pairs_corr(A); gb,rb=pairs_corr(B)
ra_=np.corrcoef(ga,ra)[0,1]; rb_=np.corrcoef(gb,rb)[0,1]
# 各自置换检验
def perm_p(g,r,n=3000):
    rg=np.random.default_rng(1); nul=np.array([np.corrcoef(g,rg.permutation(r))[0,1] for _ in range(n)])
    return float((np.abs(nul)>=abs(np.corrcoef(g,r)[0,1])).mean())
pa=perm_p(ga,ra); pb=perm_p(gb,rb)
print(f"真实权重   r={ra_:.4f}  p={pa:.4f}")
print(f"随机权重   r={rb_:.4f}  p={pb:.4f}   (对照：若显著→存在权重幅度混淆)")
# 两组相关之差（bootstrap over pairs）
rg=np.random.default_rng(2); diffs=[]
for _ in range(3000):
    idx=rg.integers(0,len(ga),len(ga))
    if len(set(idx))<3: continue
    diffs.append(np.corrcoef(ga[idx],ra[idx])[0,1]-np.corrcoef(gb[idx],rb[idx])[0,1])
diffs=np.array(diffs); obs=ra_-rb_
p_diff=float((diffs<=0).mean())
ci=np.percentile(diffs,[2.5,97.5])
print(f"Δr = {obs:.4f}  bootstrap 95%CI [{ci[0]:.4f},{ci[1]:.4f}]  p(Δr<=0)={p_diff:.4f}")
# 剂量反应：地理距离分箱
print("\n剂量反应（地理距离分箱 → 表征距离）")
bins=[(0,500),(500,1000),(1000,1500),(1500,2200),(2200,3000)]
for lo,hi in bins:
    m=(ga>=lo)&(ga<hi)
    if m.sum()==0: continue
    print(f"  {lo:4d}-{hi:4d} km  n={m.sum():2d}  表征距离={ra[m].mean():.5f} ± {ra[m].std(ddof=1):.5f}")
# 单调性
r_spear=float(np.corrcoef(np.argsort(np.argsort(ga)),np.argsort(np.argsort(ra)))[0,1])
print(f"  Spearman(秩相关) = {r_spear:.4f}")
json.dump(dict(r_real=float(ra_),p_real=pa,r_ctrl=float(rb_),p_ctrl=pb,
   delta_r=float(obs),ci=[float(ci[0]),float(ci[1])],p_delta=p_diff,spearman=r_spear,
   geo=ga.tolist(),rep=ra.tolist(),geo_ctrl=gb.tolist(),rep_ctrl=rb.tolist()),
   open(os.path.join(ROOT,'evidence','raw_data','exp076c_results.json'),'w'),ensure_ascii=False,indent=1)
