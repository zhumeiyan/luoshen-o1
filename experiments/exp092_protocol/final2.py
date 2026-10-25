# -*- coding: utf-8 -*-
"""092 终版2 —— 存活工作点 E0=0.95 basal=0.001 (实测 alive=1.000)
A. 延迟剂量反应（实测 11.1x 落在哪）
B. 真实可达性矩阵 2x2（GitHub: GUI关/协议开 ; QQ邮箱: GUI开/协议关）
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5
STEPS, PERIOD = 600, 80
KSA, KACT, DECAY = 0.35, 0.05, 0.05
E0, BASAL = 0.95, 0.001
N = 64
REACH = {'github': (0,1), 'qqmail': (1,0)}

def mk(seed):
    return Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA,
                 arr_thr=0.50, E0=E0, basal=BASAL)

def run_delay(seed, delay):
    life=mk(seed); buf=[0.5]*80; act=0.0
    for t in range(STEPS):
        buf.append(float(0.5+0.3*np.sin(2*np.pi*t/PERIOD)))
        life.input_val=float(buf[-1-delay])+act
        r=life.step()
        if r is None: break
        ten=float(life.sp[0]-life.y[0]); a=float(np.clip(KACT*ten,0.0,0.10))
        act=float(np.clip(act+a-DECAY*act,-0.5,0.5))
    c=life.capacity
    return dict(seed=seed, alive=bool(life.alive),
                skew=float(np.std(c)/max(np.mean(c),1e-12)))

def run_chan(seed, target, chan):
    gui_ok, proto_ok = REACH[target]
    life=mk(seed); buf=[0.5]*(80); frozen=None; act=0.0
    for t in range(STEPS):
        buf.append(float(0.5+0.3*np.sin(2*np.pi*t/PERIOD)))
        gv = buf[-1-11] if gui_ok   else None
        pv = buf[-1-1]  if proto_ok else None
        v = {'none':None,'gui':gv,'proto':pv,'dual':(pv if pv is not None else gv)}[chan]
        if v is None:
            v = frozen if frozen is not None else 0.5; frozen=v
        life.input_val=float(v)+act
        r=life.step()
        if r is None: break
        ten=float(life.sp[0]-life.y[0]); a=float(np.clip(KACT*ten,0.0,0.10))
        act=float(np.clip(act+a-DECAY*act,-0.5,0.5))
    c=life.capacity
    return dict(seed=seed, alive=bool(life.alive),
                skew=float(np.std(c)/max(np.mean(c),1e-12)))

def paired(a,b,nb=6000):
    a=np.asarray(a);b=np.asarray(b);d=a-b;n=len(d)
    if n<2: return dict(diff=float('nan'),ci=[0,0],sig=False,n=n)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()),ci=[lo,hi],sig=bool((lo>0)==(hi>0)),n=int(n))

DELAYS=[1,2,4,8,11,16,24,32,48,64]
rd={d:[run_delay(s,d) for s in range(N)] for d in DELAYS}
CELLS=[(tg,ch) for tg in ('github','qqmail') for ch in ('none','gui','proto','dual')]
rc={k:[run_chan(s,k[0],k[1]) for s in range(N)] for k in CELLS}

print('=== A. 延迟剂量反应 ===')
print('delay  skew      alive')
drows=[]
for d in DELAYS:
    sk=np.mean([r['skew'] for r in rd[d]]); al=np.mean([r['alive'] for r in rd[d]])
    drows.append(dict(delay=d,skew=float(sk),alive=float(al)))
    print(f'{d:5d}  {sk:.6f}  {al:.3f}')
print('\nvs delay=1:')
dt={}
for d in DELAYS[1:]:
    p=paired([r['skew'] for r in rd[d]],[r['skew'] for r in rd[1]])
    dt[d]=p
    print(f'  d={d:3d}: diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]}')
print('  Spearman(延迟,偏度) =', end=' ')
from scipy.stats import spearmanr
sk=[r['skew'] for d in DELAYS for r in rd[d]]; dl=[d for d in DELAYS for r in rd[d]]
print(f'{spearmanr(dl,sk).correlation:.4f}')

print('\n=== B. 可达性矩阵 ===')
print('target  chan   skew      alive')
for k in CELLS:
    print(f'{k[0]:8s}{k[1]:6s} {np.mean([r["skew"] for r in rc[k]]):.6f} {np.mean([r["alive"] for r in rc[k]]):.3f}')
print('\n配对 bootstrap:')
ct={}
tests=[(('github','gui'),('github','none'),'门关≡无通道(GitHub侧)'),
       (('qqmail','proto'),('qqmail','none'),'门关≡无通道(QQ侧)'),
       (('github','proto'),('qqmail','gui'),'通道形态:协议1拍 vs GUI11拍'),
       (('github','proto'),('github','gui'),'有门 vs 无门(GitHub)'),
       (('qqmail','gui'),('qqmail','proto'),'有门 vs 无门(QQ)')]
for a,b,lab in tests:
    p=paired([r['skew'] for r in rc[a]],[r['skew'] for r in rc[b]]); ct[lab]=p
    print(f'{lab:30s} diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]}')
json.dump(dict(delay_rows=drows, delay_tests={str(k):v for k,v in dt.items()},
               cells={f'{k[0]}|{k[1]}':dict(skew=float(np.mean([r['skew'] for r in rc[k]])),
                                            alive=float(np.mean([r['alive'] for r in rc[k]]))) for k in CELLS},
               chan_tests=ct, params=dict(N=N,KSA=KSA,KACT=KACT,E0=E0,BASAL=BASAL)),
          open('final2_result.json','w'), ensure_ascii=False, indent=1)
