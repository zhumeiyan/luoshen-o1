# -*- coding: utf-8 -*-
"""092 v3 —— 用【真实测得的可达性矩阵】驱动
实测：GitHub  GUI 0/8 死 · 协议 8/8 活
      QQ邮箱  GUI 8/8 活 · 协议 0/8 死
实测延迟：GUI(渲染+上屏+采集+OCR) 1.391s · 协议(直连API) 0.126s → 11.1x → 11拍 vs 1拍
世界：平滑正弦（已验证可活）
条件：单GUI / 单协议 / 双通道 × 目标(GitHub, QQ邮箱)
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5

STEPS, PERIOD = 600, 80
DL_G, DL_P = 11, 1            # 实测 11.1x

# 真实测得的可达性（0=门关 1=门开）
REACH = {  # (target): (gui_ok, proto_ok)
    'github': (0, 1),
    'qqmail': (1, 0),
}

def run(seed, target, chan, k_seek_arr=0.6, arr_thr=0.50, sigma_in=0.10):
    gui_ok, proto_ok = REACH[target]
    life=Life5(seed=seed, sigma_in=sigma_in, k_seek=0.0,
               k_seek_arr=k_seek_arr, arr_thr=arr_thr)
    buf=[0.5]*(DL_G+2); frozen=None
    for t in range(STEPS):
        w=0.5+0.3*np.sin(2*np.pi*t/PERIOD)
        buf.append(float(w))
        gv = buf[-1-DL_G] if gui_ok   else None
        pv = buf[-1-DL_P] if proto_ok else None
        if   chan=='gui':    v = gv
        elif chan=='proto':  v = pv
        elif chan=='dual':   v = pv if pv is not None else gv   # 协议优先(低延迟)
        elif chan=='none':   v = None
        else: raise ValueError(chan)
        if v is None:                       # 门关：拿不到新数据 → 冻结
            v = frozen if frozen is not None else 0.5
            frozen = v
        life.input_val=float(v)
        r=life.step()
        if r is None: break
    cap=life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                death_t=(int(life.death_t) if life.death_t is not None else None),
                skew=float(np.std(cap)/max(np.mean(cap),1e-12)))

def cell(target, chan, n=16):
    rs=[run(s,target,chan) for s in range(n)]
    return dict(target=target, chan=chan,
                skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[r['skew'] for r in rs], alivev=[r['alive'] for r in rs], rs=rs)

def paired(a,b,nb=4000):
    a=np.asarray(a); b=np.asarray(b); d=a-b; n=len(d)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)),n=int(n))

if __name__=='__main__':
    res={}
    print('=== 实测可达性矩阵驱动 ===')
    for tg in ('github','qqmail'):
        for ch in ('none','gui','proto','dual'):
            c=cell(tg,ch); res[(tg,ch)]=c
            print(f'{tg:8s} {ch:6s} skew={c["skew"]:.6f} alive={c["alive"]:.3f}')
    print('\n=== 配对 bootstrap（结构偏度）===')
    tests=[(('github','gui'),('github','dual'),'冗余是否救命(GitHub:GUI门关)'),
           (('qqmail','proto'),('qqmail','dual'),'冗余是否救命(QQ:协议门关)'),
           (('github','proto'),('qqmail','gui'),'通道形态:协议低延迟 vs GUI高延迟'),
           (('github','gui'),('github','none'),'GUI门关 ≡ 无通道?'),
           (('qqmail','proto'),('qqmail','none'),'协议门关 ≡ 无通道?')]
    for a,b,lab in tests:
        p=paired(res[a]['skews'],res[b]['skews'])
        print(f'{lab:38s} diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]}')
    json.dump({f'{k[0]}|{k[1]}':{kk:vv for kk,vv in v.items() if kk!='rs'} for k,v in res.items()},
              open('channel3_result.json','w'), ensure_ascii=False, indent=1)
