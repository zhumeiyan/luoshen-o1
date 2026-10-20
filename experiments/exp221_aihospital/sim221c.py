# -*- coding: utf-8 -*-
"""221c · 修复溯源：tag 必须与真实污染状态关联（221b 里 tag 是随机的，无效）"""
import numpy as np, json
rng = np.random.default_rng(20261022)
T=40000; P_PASS_TRUE=0.90; P_CLEAN_ACC=0.75

def run(d, rho, N, prov=False, q=0.90, drop=False):
    y = rng.integers(0,2,T)
    sp = (rng.random(T) < np.where(y==1,P_PASS_TRUE,d)).astype(float)
    err_self=float((sp!=y).mean())
    clean = rng.random((T,N)) > rho
    ag = rng.random((T,N)) < P_CLEAN_ACC
    sig = np.where(clean,
                   np.where(y[:,None]==1, ag, ~ag).astype(float),
                   np.broadcast_to(sp[:,None],(T,N)).copy())
    if not prov:
        w=np.ones((T,N))
    else:
        r1=rng.random((T,N)); r2=rng.random((T,N))
        # tag=True 表示"被判定为污染"：污染被识破概率q，干净被误判概率1-q
        tag = np.where(clean, r1 < (1-q), r2 < q)
        w = np.where(tag, 0.0 if drop else 0.15, 1.0)
    den=w.sum(1); den=np.where(den==0,1,den)
    v=(sig*w).sum(1)/den
    verdict=(v>0.5).astype(int)
    return err_self, float((verdict!=y).mean()), float(np.abs(v-0.5).mean()*2), \
           float(((verdict!=y)&(np.abs(v-0.5)>0.25)).mean())

print("=== 修复后：溯源精度扫描 (d=0.95 自评比随机还差, rho=0.7, N=40) ===")
print(f"{'q':>6} {'err':>9} {'置信度':>9} {'确信错':>9}")
qs=[]
for q in [0.0,0.3,0.5,0.7,0.8,0.9,0.95,1.0]:
    _,e,c,ce=run(0.95,0.7,40,True,q); qs.append(dict(q=q,err=round(e,4),conf=round(c,4),cerr=round(ce,4)))
    print(f"{q:>6.2f} {e:>9.4f} {c:>9.4f} {ce:>9.4f}")

print("\n=== 修复后：无溯源 vs 带溯源 (N=40) ===")
print(f"{'d':>5} {'rho':>5} {'自评错':>8} {'无溯源':>8} {'带溯源q.9':>10} {'带溯源q1.0':>11} {'救回':>8}")
pv=[]
for d in [0.40,0.80,0.95]:
    for rho in [0.3,0.5,0.7,0.9]:
        es,e0,_,_=run(d,rho,40,False)
        _,e9,_,_=run(d,rho,40,True,0.90)
        _,e1,_,_=run(d,rho,40,True,1.0)
        pv.append(dict(d=d,rho=rho,es=round(es,4),e0=round(e0,4),e9=round(e9,4),e1=round(e1,4)))
        print(f"{d:>5.2f} {rho:>5.1f} {es:>8.4f} {e0:>8.4f} {e9:>10.4f} {e1:>11.4f} {e0-e1:>8.4f}")

print("\n=== 高污染下 N 增大做什么？(d=0.95, rho=0.7, 无溯源) ===")
print(f"{'N':>6} {'err':>9} {'置信度':>9} {'确信错':>9}")
ns=[]
for N in [10,40,160,640]:
    _,e,c,ce=run(0.95,0.7,N,False); ns.append(dict(N=N,err=round(e,4),conf=round(c,4),cerr=round(ce,4)))
    print(f"{N:>6} {e:>9.4f} {c:>9.4f} {ce:>9.4f}")

json.dump(dict(qscan=qs, prov=pv, nscan=ns),
 open("/data/workspace/luoshen-o1/experiments/exp221_aihospital/result221c.json","w"), ensure_ascii=False, indent=1)
print("\n[saved] result221c.json")
