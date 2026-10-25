# -*- coding: utf-8 -*-
"""092 v2 通道层级 —— 用【实测】差异：人类通道延迟 1.391s vs 协议 0.126s (11.1x)
世界 = 真实 GitHub API 数值插值成的平滑周期序列(保序归一)
延迟建模：协议 1 拍，人类通道 11 拍（按实测比）
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5

STEPS, CUT = 600, 250
RAW=[554.0,3.0,3.0,1.0,1.0,1.0,0.0,29.0]
_l=np.log1p(np.array(RAW)); BASE=_l/_l.max()
PERIOD=80
_t=np.linspace(0,len(BASE)-1,PERIOD)
WORLD=np.interp(_t, np.arange(len(BASE)), BASE)
DL_P, DL_G = 1, 11          # 实测 11.1x 延迟

def run(seed, mode, k_seek_arr=0.6, arr_thr=0.50, sigma_in=0.10):
    life=Life5(seed=seed, sigma_in=sigma_in, k_seek=0.0,
               k_seek_arr=k_seek_arr, arr_thr=arr_thr)
    buf=[WORLD[0]]*(DL_G+2)
    frozen=None
    for t in range(STEPS):
        w=float(WORLD[t%PERIOD])
        buf.append(w)
        if   mode=='H':  v = WORLD[0] if frozen is None else frozen; frozen=v
        elif mode=='P':  v = buf[-1-DL_P]
        elif mode=='G':  v = buf[-1-DL_G]
        elif mode=='Ec': v = buf[-1-DL_G] if t<CUT else (frozen if frozen is not None else buf[-1-DL_G]); frozen=v
        elif mode=='Er': v = buf[-1-DL_G] if t<CUT else buf[-1-DL_P]
        else: raise ValueError(mode)
        life.input_val=float(v)
        r=life.step()
        if r is None: break
    cap=life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                death_t=(int(life.death_t) if life.death_t is not None else None),
                skew=float(np.std(cap)/max(np.mean(cap),1e-12)))

def cell(mode,n=16):
    rs=[run(s,mode) for s in range(n)]
    return dict(mode=mode, skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[r['skew'] for r in rs], alivev=[r['alive'] for r in rs],
                rs=rs)

def paired(a,b,nb=4000):
    a=np.asarray(a); b=np.asarray(b); d=a-b; n=len(d)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)),n=int(n))

if __name__=='__main__':
    print(f'世界: 真实值插值 PERIOD={PERIOD} min={WORLD.min():.3f} max={WORLD.max():.3f} mean={WORLD.mean():.3f}')
    res={}
    for m in ('H','P','G','Ec','Er'):
        c=cell(m); res[m]=c
        dt=[r['death_t'] for r in c['rs'] if r['death_t'] is not None]
        print(f"{m:3s} skew={c['skew']:.6f} alive={c['alive']:.3f} ndeath={len(dt)}")
    print('\n--- 配对 bootstrap ---')
    for a,b in (('G','P'),('Ec','G'),('Er','Ec'),('P','H'),('G','H')):
        p=paired(res[a]['skews'],res[b]['skews'])
        print(f"{a} - {b}: diff={p['diff']:+.6f} CI=[{p['ci'][0]:+.4f},{p['ci'][1]:+.4f}] sig={p['sig']}")
    json.dump(res, open('channel2_result.json','w'), ensure_ascii=False, indent=1)
