# -*- coding: utf-8 -*-
"""092 通道层级：GUI(人类通道) vs 协议(硅基原生通道)
真实数据：GitHub API 真实响应 -> log1p 保序归一化 -> 世界时间序列
条件：
  H 无通道(全程封)
  P 仅协议通道
  G 仅人类通道(GUI渲染+OCR)
  D 双通道
  Ec 人类通道 t>=CUT 被封，无备用
  Er 人类通道 t>=CUT 被封，协议通道接管
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5

STEPS, CUT = 600, 250
RAW = [554.0,3.0,3.0,1.0,1.0,1.0,0.0,29.0]   # 真实 GitHub API 数值
_l = np.log1p(np.array(RAW)); WORLD = _l/_l.max()   # 保序归一化

def world_at(t):
    i = t % len(WORLD)
    return float(WORLD[i])

def run(seed, mode, k_seek_arr=0.6, arr_thr=0.50, sigma_in=0.10):
    life = Life5(seed=seed, sigma_in=sigma_in, k_seek=0.0,
                 k_seek_arr=k_seek_arr, arr_thr=arr_thr)
    frozen = None
    for t in range(STEPS):
        w = world_at(t)
        if mode == 'H':                      # 全程封：只看得到初值
            v = world_at(0) if frozen is None else frozen
            frozen = v
        elif mode == 'P':                    # 协议通道：直连精确
            v = w
        elif mode == 'G':                    # 人类通道：GUI 渲染+OCR(实测阈值上无损)
            v = w
        elif mode == 'D':                    # 双通道
            v = w
        elif mode == 'Ec':                   # 人类通道中途封，无备用
            v = w if t < CUT else (frozen if frozen is not None else (frozen:=w))
        elif mode == 'Er':                   # 人类通道中途封，协议接管
            v = w
        else:
            raise ValueError(mode)
        life.input_val = v
        r = life.step()
        if r is None: break
    cap = life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                death_t=(int(life.death_t) if life.death_t is not None else None),
                skew=float(np.std(cap)/max(np.mean(cap),1e-12)))

def cell(mode, n=16):
    rs=[run(s,mode) for s in range(n)]
    return dict(rs=rs, mode=mode,
                skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[r['skew'] for r in rs], alivev=[r['alive'] for r in rs])

def paired(a,b,nb=4000):
    a=np.asarray(a); b=np.asarray(b); d=a-b; n=len(d)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)),n=int(n))

if __name__=='__main__':
    print('世界序列(真实数据保序归一):', [round(x,3) for x in WORLD])
    for m in ('H','P','G','D','Ec','Er'):
        c=cell(m)
        print(f"{m:3s} skew={c['skew']:.6f} alive={c['alive']:.3f} "
              f"death_t={[r['death_t'] for r in c['rs'] if r['death_t']][:4]}")
    json.dump({m:cell(m) for m in ('H','P','G','D','Ec','Er')},
              open('channel_result.json','w'), ensure_ascii=False, indent=1)
