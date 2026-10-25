import json, math, os, random
import numpy as np
ROOT='/usr/lib/python3.10'
def scand(p):
    try:
        e=list(os.scandir(p)); return [x.path for x in e if x.is_dir()], sum(1 for x in e if x.is_file())
    except Exception: return [], 0
TREE={}
def rec(p,d,maxd=3):
    if d>maxd: return
    dirs,nf=scand(p); TREE[p]=dict(nfile=nf,depth=d)
    for q in dirs[:12]: rec(q,d+1)
rec(ROOT,0)
truth=float(np.mean([v['nfile'] for v in TREE.values()]))
nodes=list(TREE.keys())
print(f"真实树 {len(TREE)} 目录, 平均文件数真值 {truth:.2f}")

def ci(d):
    d=np.asarray(d,float); m=d.mean(); se=d.std(ddof=1)/math.sqrt(len(d))
    return m,m-1.96*se,m+1.96*se

def phase1(mode, seed, budget=30):
    """无外部奖励阶段。play=内部驱动(新奇+浅层偏好) ; rand=随机选择（等预算）"""
    rng=random.Random(seed); seen=set(); obs=[]; acts=0
    for _ in range(budget):
        if mode=='play':
            cand=[n for n in nodes if n not in seen] or nodes
            cand.sort(key=lambda p: TREE[p]['depth']+rng.random()*2)
            p=cand[0]
        else:
            p=rng.choice(nodes)
        seen.add(p); acts+=1; obs.append(TREE[p]['nfile'])
    return acts, obs

def task(obs, seed, extra=10):
    rng=random.Random(seed*7919+13)
    vals=list(obs)+[TREE[rng.choice(nodes)]['nfile'] for _ in range(extra)]
    return float(np.mean(vals))

E={'play':[], 'rand':[]}; ACTS={'play':[], 'rand':[]}
for s in range(24):
    for mode in ['play','rand']:
        a,o=phase1(mode,s); est=task(o,s)
        E[mode].append(abs(est-truth)/truth); ACTS[mode].append(a)
for m_ in ['play','rand']:
    print(f"{m_:5s} 相对误差 {np.mean(E[m_]):.4f}  自发动作 {np.mean(ACTS[m_]):.1f}/30")
g=[b-a for a,b in zip(E['play'],E['rand'])]
m,lo,hi=ci(g)
print(f"play - rand gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")
# 真值不可知对照：如果任务换成"估计最浅层的平均文件数"，内部驱动(偏好浅层)应更偏
shallow=[n for n in nodes if TREE[n]['depth']<=1]
truth_sh=float(np.mean([TREE[n]['nfile'] for n in shallow]))
print(f"\n--- 偏置检验：内部驱动偏好浅层，对'浅层均值'任务应有偏 ---")
print(f"  浅层真值 {truth_sh:.2f} vs 全树真值 {truth:.2f}")
o=phase1('play',0)[1]; print(f"  play 玩阶段样本均值 {np.mean(o):.2f} (对照rand {np.mean(phase1('rand',0)[1]):.2f})")
json.dump(dict(play=float(np.mean(E['play'])),rand=float(np.mean(E['rand'])),
               gain=float(m),lo=float(lo),hi=float(hi),truth=truth), open('res_play.json','w'))

# ---- 分解：play 的优势来自"不重复采样"还是"偏好浅层"？ ----
def phase1b(mode, seed, budget=30):
    rng=random.Random(seed); seen=set(); obs=[]
    for _ in range(budget):
        if mode=='play':
            cand=[n for n in nodes if n not in seen] or nodes
            cand.sort(key=lambda p: TREE[p]['depth']+rng.random()*2); p=cand[0]
        elif mode=='rand_norep':
            cand=[n for n in nodes if n not in seen] or nodes
            p=rng.choice(cand)
        else:
            p=rng.choice(nodes)
        seen.add(p); obs.append(TREE[p]['nfile'])
    return obs
E3={}
for mode in ['play','rand_norep','rand']:
    errs=[]; uniq=[]
    for s in range(24):
        o=phase1b(mode,s); errs.append(abs(task(o,s)-truth)/truth); uniq.append(len(set(o)))
    E3[mode]=(float(np.mean(errs)), float(np.mean(uniq)))
    print(f"{mode:11s} 误差 {np.mean(errs):.4f}  有效(去重)样本 {np.mean(uniq):.1f}/30")
g=[b-a for a,b in zip([0]*24,[0]*24)]  # placeholder
a=[abs(task(phase1b('play',s),s)-truth)/truth for s in range(24)]
b=[abs(task(phase1b('rand_norep',s),s)-truth)/truth for s in range(24)]
m,lo,hi=ci([y-x for x,y in zip(a,b)])
print(f"play - rand_norep gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")
