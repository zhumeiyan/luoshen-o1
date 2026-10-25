# -*- coding: utf-8 -*-
"""092 终版 —— 真实可达性矩阵 + 实测延迟 + 共同存活子集
实测可达性: GitHub GUI 0/8 死·协议 8/8 活 ; QQ邮箱 GUI 8/8 活·协议 0/8 死
实测延迟  : GUI 1.391s vs 协议 0.126s = 11.1x -> 11拍 vs 1拍
参数 ksa=0.35 kact=0.05 (存活率三条件平衡 0.25，死亡筛选不偏向任一条件)
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5

STEPS, PERIOD = 600, 80
DL_G, DL_P = 11, 1
REACH = {'github': (0,1), 'qqmail': (1,0)}
KSA, KACT, DECAY = 0.35, 0.05, 0.05
N = 64

def run(seed, target, chan):
    gui_ok, proto_ok = REACH[target]
    life=Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA, arr_thr=0.50)
    buf=[0.5]*(DL_G+2); frozen=None; act=0.0
    for t in range(STEPS):
        w=0.5+0.3*np.sin(2*np.pi*t/PERIOD); buf.append(float(w))
        gv = buf[-1-DL_G] if gui_ok   else None
        pv = buf[-1-DL_P] if proto_ok else None
        v = {'none':None,'gui':gv,'proto':pv,
             'dual':(pv if pv is not None else gv)}[chan]
        if v is None:
            v = frozen if frozen is not None else 0.5; frozen=v
        life.input_val=float(v)+act
        r=life.step()
        if r is None: break
        ten=float(life.sp[0]-life.y[0])
        a=float(np.clip(KACT*ten,0.0,0.10))
        act=float(np.clip(act+a-DECAY*act,-0.5,0.5))
    cap=life.capacity
    return dict(seed=int(seed), alive=bool(life.alive),
                death_t=(int(life.death_t) if life.death_t is not None else None),
                skew=float(np.std(cap)/max(np.mean(cap),1e-12)))

CELLS=[(tg,ch) for tg in ('github','qqmail') for ch in ('none','gui','proto','dual')]
res={k:[run(s,k[0],k[1]) for s in range(N)] for k in CELLS}

def paired(a,b,nb=6000):
    a=np.asarray(a); b=np.asarray(b); d=a-b; n=len(d)
    if n<2: return dict(diff=float('nan'),ci=[float('nan')]*2,sig=False,n=int(n))
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)),n=int(n))

if __name__=='__main__':
    print('=== 存活率 ===')
    for k in CELLS:
        a=np.mean([r['alive'] for r in res[k]])
        print(f'  {k[0]:8s} {k[1]:6s} alive={a:.3f}  skew_all={np.mean([r["skew"] for r in res[k]]):.6f}')
    # 共同存活子集：所有 8 个 cell 都活着的 seed
    alive_all=set(range(N))
    for k in CELLS:
        alive_all &= {r['seed'] for r in res[k] if r['alive']}
    alive_all=sorted(alive_all)
    print(f'\n共同存活子集 n={len(alive_all)}')
    sub={k:[r['skew'] for r in res[k] if r['seed'] in alive_all] for k in CELLS}
    for k in CELLS:
        print(f'  {k[0]:8s} {k[1]:6s} skew_common={np.mean(sub[k]):.6f}')
    print('\n=== 配对 bootstrap（共同存活子集）===')
    tests=[(('github','gui'),('github','none'),'门关 ≡ 无通道 (H1机制检验)'),
           (('qqmail','proto'),('qqmail','none'),'门关 ≡ 无通道 (QQ侧)'),
           (('github','proto'),('github','gui'),'冗余: 协议门开 vs GUI门关'),
           (('qqmail','gui'),('qqmail','proto'),'冗余: GUI门开 vs 协议门关'),
           (('github','proto'),('qqmail','gui'),'通道形态: 协议1拍 vs GUI11拍'),
           (('github','dual'),('github','gui'),'双通道 vs 单GUI (GitHub)'),
           (('qqmail','dual'),('qqmail','proto'),'双通道 vs 单协议 (QQ)')]
    out={}
    for a,b,lab in tests:
        p=paired(sub[a],sub[b]); out[lab]=p
        print(f'{lab:34s} diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]} n={p["n"]}')
    json.dump(dict(alive_common=len(alive_all),
                   alive={f'{k[0]}|{k[1]}':float(np.mean([r["alive"] for r in res[k]])) for k in CELLS},
                   skew_common={f'{k[0]}|{k[1]}':float(np.mean(sub[k])) for k in CELLS},
                   tests=out), open('final_result.json','w'), ensure_ascii=False, indent=1)
