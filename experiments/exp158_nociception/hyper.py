#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 真实痛觉过敏：伤口存在时阈值下降，注意力重分配
  const 采样预算恒定 K=6
  hyper 平时 K=3（省开销），有伤口时 K=9（过敏：加强监视）
问题：过敏是"过度反应"还是"资源重分配"？
"""
import os, sys, json, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell import Body
N=12; ROUNDS=36; HEAL_COST=2; CASCADE=4

def run(kind, seed, p=0.5):
    rng=random.Random(seed); b=Body(N)
    wounds={}; pending={}; checked=0; miss=0
    try:
        for t in range(ROUNDS):
            av=list(b.cells.keys())
            if av and rng.random()<p:
                v=rng.choice(av)
                if b.kill(v): wounds[v]=t
            k = 6 if kind=='const' else (9 if wounds else 3)
            slots=list(range(N)); rng.shuffle(slots)
            for cid in slots[:k]:
                checked+=1
                if cid in b.cells:
                    os.path.exists('/proc/%d'%b.cells[cid])
                elif cid in wounds and cid not in pending:
                    pending[cid]=HEAL_COST; wounds.pop(cid,None)
            for c in list(pending):
                pending[c]-=1
                if pending[c]<=0: b.heal(c); del pending[c]
            for cid in list(wounds):
                if t-wounds[cid]>=CASCADE:
                    nb=[x for x in range(N) if x!=cid and x in b.cells and x not in wounds]
                    if nb:
                        nv=rng.choice(nb)
                        if b.kill(nv): wounds[nv]=t
                        miss+=1
                    wounds.pop(cid,None)
        res=dict(kind=kind, alive=b.alive(), checked=checked, miss=miss)
    finally:
        b.reap()
    return res

def ci(v):
    m=st.mean(v); s=st.stdev(v)/len(v)**0.5 if len(v)>1 else 0.0
    return (m-1.96*s, m+1.96*s)

REPS=10; out={}
for p in [0.3, 0.5, 0.7]:
    for kind in ['const','hyper']:
        rs=[run(kind, 77*i+3, p) for i in range(REPS)]
        al=[r['alive'] for r in rs]; ck=[r['checked'] for r in rs]
        out['p%.1f_%s'%(p,kind)]=dict(alive=al, checked=ck,
            alive_mean=st.mean(al), checked_mean=st.mean(ck))
        print('p=%.1f %-6s alive %5.2f CI[%.2f,%.2f]  检查 %6.1f'
              %(p,kind,st.mean(al),ci(al)[0],ci(al)[1],st.mean(ck)))
    print()
json.dump(out, open('result_hyper.json','w'), indent=1)

print('=== 效率比（每存活细胞耗检查次数）===')
for p in [0.3,0.5,0.7]:
    for kind in ['const','hyper']:
        d=out['p%.1f_%s'%(p,kind)]
        e=d['checked_mean']/max(0.5,d['alive_mean'])
        print('p=%.1f %-6s 效率 %.1f'%(p,kind,e))
