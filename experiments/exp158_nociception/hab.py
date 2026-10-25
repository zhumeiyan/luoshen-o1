#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 真实习惯化：感官通道 = 真实 /proc/<pid> 存在性检查
  habit 采样预算随暴露次数衰减（习惯了 -> 越查越少）
  pain  采样预算恒定（不习惯化）
真实量：检查是真实 /proc 读取、kill 真实、fork 真实
建模量：只有"预算如何随暴露变化"这条规则
"""
import os, sys, json, random, time, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell import Body

N=12; ROUNDS=36; K0=6; HEAL_COST=2; CASCADE=4

def alive_real(pid):
    """真实感官通道：读 /proc"""
    return os.path.exists('/proc/%d' % pid)

def run(kind, seed):
    rng=random.Random(seed); b=Body(N)
    wounds=set(); pending={}; exposures=0
    miss=0; found_delay=[]; checked_total=0
    birth_t={}   # cid -> 被发现时的轮
    inj_t={}
    try:
        for t in range(ROUNDS):
            # 真实损伤：每轮固定死 1 个（低强度持续刺激）
            av=list(b.cells.keys())
            if av:
                v=rng.choice(av)
                if b.kill(v):
                    wounds.add(v); inj_t[v]=t

            # 采样预算
            if kind=='habit':
                k=max(1,int(K0*(0.90**exposures)))
            else:
                k=K0
            exposures+=1

            # 真实检查：随机抽 k 个槽位，查它是否还活着
            slots=list(range(N))
            rng.shuffle(slots)
            found=[]
            for cid in slots[:k]:
                checked_total+=1
                if cid in b.cells:
                    alive_real(b.cells[cid])      # 真实 /proc 读取
                elif cid in wounds:
                    found.append(cid)
            for cid in found:
                if cid not in pending:
                    pending[cid]=HEAL_COST
                    found_delay.append(t-inj_t.get(cid,t))
                    wounds.discard(cid)

            for c in list(pending):
                pending[c]-=1
                if pending[c]<=0:
                    b.heal(c); del pending[c]

            # 漏检->连锁
            for cid in list(wounds):
                if t-inj_t.get(cid,t) >= CASCADE:
                    nbrs=[x for x in range(N) if x!=cid and x in b.cells and x not in wounds]
                    if nbrs:
                        nv=rng.choice(nbrs)
                        if b.kill(nv): wounds.add(nv); inj_t[nv]=t
                        miss+=1
                    wounds.discard(cid)
        res=dict(kind=kind, alive=b.alive(), miss=miss,
                 delay=(sum(found_delay)/len(found_delay) if found_delay else -1.0),
                 n_found=len(found_delay), checked=checked_total)
    finally:
        b.reap()
    return res

def ci(v):
    m=st.mean(v); s=st.stdev(v)/len(v)**0.5 if len(v)>1 else 0.0
    return (m-1.96*s, m+1.96*s)

REPS=10
out={}
for kind in ['habit','pain']:
    rs=[run(kind, 31*i+5) for i in range(REPS)]
    al=[r['alive'] for r in rs]; ms=[r['miss'] for r in rs]
    ck=[r['checked'] for r in rs]; dl=[r['delay'] for r in rs]
    out[kind]=dict(alive=al, miss=ms, checked=ck, delay=dl,
                   alive_mean=st.mean(al), miss_mean=st.mean(ms),
                   checked_mean=st.mean(ck), delay_mean=st.mean(dl),
                   ci_alive=ci(al), ci_miss=ci(ms))
    print('%-6s alive %5.2f CI[%.2f,%.2f] | 漏检-连锁 %5.2f | 检查次数 %6.1f | 发现延迟 %.2f'
          % (kind, st.mean(al), ci(al)[0], ci(al)[1], st.mean(ms), st.mean(ck), st.mean(dl)))
json.dump(out, open('result_hab.json','w'), indent=1)

a=[x-y for x,y in zip(out['pain']['alive'], out['habit']['alive'])]
m=[x-y for x,y in zip(out['pain']['miss'], out['habit']['miss'])]
print()
print('pain - habit  alive 差 %.3f CI[%.3f,%.3f]' % (st.mean(a), ci(a)[0], ci(a)[1]))
print('pain - habit  漏检差 %.3f CI[%.3f,%.3f]' % (st.mean(m), ci(m)[0], ci(m)[1]))
