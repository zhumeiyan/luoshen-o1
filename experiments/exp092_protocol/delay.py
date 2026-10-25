# -*- coding: utf-8 -*-
"""092 延迟剂量反应：通道延迟到底在哪一拍开始起作用"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5
STEPS, PERIOD = 600, 80
KSA, KACT, DECAY = 0.35, 0.05, 0.05
N = 32
def run(seed, delay):
    life=Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA, arr_thr=0.50)
    buf=[0.5]*(80); act=0.0
    for t in range(STEPS):
        w=0.5+0.3*np.sin(2*np.pi*t/PERIOD); buf.append(float(w))
        v=buf[-1-delay]
        life.input_val=float(v)+act
        r=life.step()
        if r is None: break
        ten=float(life.sp[0]-life.y[0]); a=float(np.clip(KACT*ten,0.0,0.10))
        act=float(np.clip(act+a-DECAY*act,-0.5,0.5))
    c=life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                skew=float(np.std(c)/max(np.mean(c),1e-12)))
DELAYS=[1,2,4,8,11,16,24,32,48,64]
res={d:[run(s,d) for s in range(N)] for d in DELAYS}
alive_all=set(range(N))
for d in DELAYS: alive_all &= {r['seed'] for r in res[d] if r['alive']}
alive_all=sorted(alive_all)
print(f'共同存活 n={len(alive_all)}')
print('delay  skew_common  alive')
rows=[]
for d in DELAYS:
    sk=[r['skew'] for r in res[d] if r['seed'] in alive_all]
    al=np.mean([r['alive'] for r in res[d]])
    rows.append(dict(delay=d, skew=float(np.mean(sk)), alive=float(al)))
    print(f'{d:5d}  {np.mean(sk):.6f}  {al:.3f}')
def paired(a,b,nb=6000):
    a=np.asarray(a);b=np.asarray(b);d=a-b;n=len(d)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)))
print('\n各延迟 vs 最小延迟(1拍):')
base=[r['skew'] for r in res[1] if r['seed'] in alive_all]
for d in DELAYS[1:]:
    p=paired([r['skew'] for r in res[d] if r['seed'] in alive_all], base)
    print(f'  delay={d:3d}: diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]}')
json.dump(dict(rows=rows, common=len(alive_all)), open('delay_result.json','w'), indent=1)
