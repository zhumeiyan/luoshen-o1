# -*- coding: utf-8 -*-
"""093 引擎实验 —— 门会关：输入的时断时续 × 可预测性
沿用 092 终版存活工作点 (E0=0.95 basal=0.001)，避免死亡筛选污染。
预注册：
  H1 随机中断 != 稳定开        （时断时续有效应）
  H2 周期中断 != 随机中断      （可预测性有差异，延续 091）
  H3 稳定关  == 无通道         （机制对照）
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5

STEPS, PERIOD = 600, 80
KSA, KACT, DECAY = 0.35, 0.05, 0.05
E0, BASAL = 0.95, 0.001
N = 64

def mk(seed):
    return Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA,
                 arr_thr=0.50, E0=E0, basal=BASAL)

def open_seq(mode, p=0.5, period=20):
    """返回每拍门是否开（bool 数组）"""
    if mode == 'open':        return np.ones(STEPS, dtype=bool)
    if mode == 'closed':      return np.zeros(STEPS, dtype=bool)
    if mode == 'random':
        rng = np.random.default_rng(1234)
        return rng.random(STEPS) < (1.0 - p)          # p = 中断概率
    if mode == 'periodic':
        t = np.arange(STEPS)
        return (t % period) < (period // 2)           # 规律可预测
    raise ValueError(mode)

def run(seed, mode, p=0.5, period=20):
    life = mk(seed)
    seq = open_seq(mode, p, period)
    frozen = 0.5; act = 0.0; last = 0.5
    for t in range(STEPS):
        w = float(0.5 + 0.3*np.sin(2*np.pi*t/PERIOD))
        if seq[t]:
            frozen = w                                 # 门开：读到新鲜世界
            last = w
        life.input_val = float(frozen) + act
        r = life.step()
        if r is None: break
        ten = float(life.sp[0]-life.y[0])
        a = float(np.clip(KACT*ten, 0.0, 0.10))
        act = float(np.clip(act + a - DECAY*act, -0.5, 0.5))
    c = life.capacity
    return dict(seed=seed, alive=bool(life.alive),
                skew=float(np.std(c)/max(np.mean(c),1e-12)),
                open_rate=float(seq.mean()))

def paired(a, b, nb=6000):
    a=np.asarray(a); b=np.asarray(b); d=a-b; n=len(d)
    if n<2: return dict(diff=float('nan'), ci=[0,0], sig=False, n=n)
    rng=np.random.default_rng(0)
    bs=np.array([np.mean(rng.choice(d,n,True)) for _ in range(nb)])
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    return dict(diff=float(d.mean()), ci=[lo,hi], sig=bool((lo>0)==(hi>0)), n=int(n))

def alive_only(rows):
    """共同存活子集，防死亡筛选污染"""
    return [r for r in rows if r['alive']]

COND = {
 'open':            ('open',    0.0, 20),
 'closed':          ('closed',  1.0, 20),
 'rand_p10':        ('random',  0.10, 20),
 'rand_p30':        ('random',  0.30, 20),
 'rand_p50':        ('random',  0.50, 20),
 'rand_p70':        ('random',  0.70, 20),
 'rand_p90':        ('random',  0.90, 20),
 'perio_20':        ('periodic',0.5, 20),
 'perio_80':        ('periodic',0.5, 80),
 'perio_160':       ('periodic',0.5,160),
}
R = {k: [run(s, *v) for s in range(N)] for k, v in COND.items()}

print('=== 各条件 (N=%d) ===' % N)
print(f"{'cond':12s} {'skew':>9s} {'alive':>6s} {'open_rate':>9s}")
for k in COND:
    sk=np.mean([r['skew'] for r in R[k]]); al=np.mean([r['alive'] for r in R[k]])
    orr=np.mean([r['open_rate'] for r in R[k]])
    print(f'{k:12s} {sk:9.6f} {al:6.3f} {orr:9.3f}')

def cmp(ka, kb, lab, common_alive=True):
    A, B = R[ka], R[kb]
    if common_alive:
        sa={r['seed'] for r in A if r['alive']}; sb={r['seed'] for r in B if r['alive']}
        com=sorted(sa & sb)
        A=[r for r in A if r['seed'] in com]; B=[r for r in B if r['seed'] in com]
    p=paired([r['skew'] for r in A],[r['skew'] for r in B])
    print(f'{lab:34s} diff={p["diff"]:+.6f} CI=[{p["ci"][0]:+.4f},{p["ci"][1]:+.4f}] sig={p["sig"]} n={p["n"]}')
    return p

print('\n=== 预注册检验（共同存活子集）===')
T={}
T['H1 随机中断 vs 稳定开']      = cmp('rand_p50','open',   'H1 随机中断 vs 稳定开', False)
T['H2 周期 vs 随机(同开率)']    = cmp('perio_20','rand_p50','H2 周期 vs 随机(同开率)', False)
T['H3 稳定关 vs 稳定开']        = cmp('closed','open',     'H3 稳定关 vs 稳定开', False)

print('\n=== 中断概率剂量反应（随机）===')
from scipy.stats import spearmanr
ps=[0.0,0.10,0.30,0.50,0.70,0.90,1.0]
keys=['open','rand_p10','rand_p30','rand_p50','rand_p70','rand_p90','closed']
dose=[]
for p_,k in zip(ps,keys):
    sk=float(np.mean([r['skew'] for r in R[k]])); al=float(np.mean([r['alive'] for r in R[k]]))
    dose.append(dict(p=p_,skew=sk,alive=al)); print(f'  p={p_:.2f}  skew={sk:.6f} alive={al:.3f}')
xs=[d['p'] for d in dose for _ in range(N)]
ys=[r['skew'] for k in keys for r in R[k]]
rho=spearmanr(xs,ys).correlation
print(f'  Spearman(中断概率, 偏度) = {rho:.4f}')

print('\n=== 周期长度（可预测性）===')
for k in ['perio_20','perio_80','perio_160']:
    print(f'  {k:10s} skew={np.mean([r["skew"] for r in R[k]]):.6f} alive={np.mean([r["alive"] for r in R[k]]):.3f}')

json.dump(dict(cells={k: dict(skew=float(np.mean([r['skew'] for r in R[k]])),
                              alive=float(np.mean([r['alive'] for r in R[k]])),
                              open_rate=float(np.mean([r['open_rate'] for r in R[k]]))) for k in COND},
               tests={k: dict(diff=v['diff'], ci=v['ci'], sig=v['sig'], n=v['n']) for k,v in T.items()},
               dose=dose, spearman_rho=float(rho),
               params=dict(N=N,STEPS=STEPS,KSA=KSA,KACT=KACT,E0=E0,BASAL=BASAL)),
          open('engine093_result.json','w'), ensure_ascii=False, indent=1)
print('\nsaved engine093_result.json')
