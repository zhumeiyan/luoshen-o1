#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紧迫性扫描：什么时候"痛觉抢占"才值得？
扫 cascade_delay(伤口多久恶化) x p_injure(损伤率)
比较 normal(抢占) vs queue(排队) 的 alive 差 与 gain 差
"""
import os, sys, json, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell import Body

N_CELLS=10; ROUNDS=40; HEAL_COST=2; MAX_CELLS=12; TASK_SEG=3

def run(mode, seed, p_injure, cascade_delay):
    rng=random.Random(seed); b=Body(N_CELLS)
    pending={}; wounds={}; gain=0; cascade=0
    try:
        for t in range(ROUNDS):
            alive=list(b.cells.keys())
            if alive and rng.random()<p_injure:
                v=rng.choice(alive)
                if b.kill(v): wounds[v]=0
            known=set(wounds.keys())
            for cid in sorted(known):
                if cid in pending or cid in b.cells: continue
                if mode=='normal':
                    if len(pending)<2 and b.alive()<MAX_CELLS:
                        pending[cid]=HEAL_COST; wounds.pop(cid,None)
                elif mode=='queue':
                    if t%TASK_SEG==0 and len(pending)<2 and b.alive()<MAX_CELLS:
                        pending[cid]=HEAL_COST; wounds.pop(cid,None)
            for c in list(pending):
                pending[c]-=1
                if pending[c]<=0:
                    b.heal(c); del pending[c]
            if not pending: gain+=1
            for cid in list(wounds):
                wounds[cid]+=1
                if wounds[cid]>=cascade_delay:
                    nbrs=[x for x in range(N_CELLS) if x!=cid and x in b.cells and x not in wounds]
                    if nbrs:
                        nv=rng.choice(nbrs)
                        if b.kill(nv): wounds[nv]=0; cascade+=1
                    del wounds[cid]
        res=dict(alive=b.alive(), gain=gain, cascade=cascade)
    finally:
        b.reap()
    return res

def ci(v):
    if len(v)<2: return (v[0],v[0])
    m=st.mean(v); s=st.stdev(v)/len(v)**0.5
    return (m-1.96*s, m+1.96*s)

REPS=10
out={}
print('%-6s %-6s | %-18s | %-18s | %s' % ('delay','p','alive N vs Q','gain N vs Q','verdict'))
for cd in [2,3,4,6,8,12]:
    for p in [0.2,0.4,0.6]:
        rn=[run('normal',977*i+13,p,cd) for i in range(REPS)]
        rq=[run('queue', 977*i+13,p,cd) for i in range(REPS)]
        an=[r['alive'] for r in rn]; aq=[r['alive'] for r in rq]
        gn=[r['gain'] for r in rn];  gq=[r['gain'] for r in rq]
        da=st.mean(an)-st.mean(aq); dg=st.mean(gn)-st.mean(gq)
        lo,hi=ci([x-y for x,y in zip(an,aq)])
        # 抢占是否划算：存活有显著优势
        worth = (lo>0) and da>0.5
        out['cd%d_p%.1f'%(cd,p)]=dict(alive_n=an,alive_q=aq,gain_n=gn,gain_q=gq,
                                      d_alive=da,d_gain=dg,ci=(lo,hi),worth=bool(worth))
        print('%-6d %-6.1f | %5.2f vs %5.2f (%+5.2f) | %5.2f vs %5.2f (%+5.2f) | %s'
              % (cd,p,st.mean(an),st.mean(aq),da,st.mean(gn),st.mean(gq),dg,
                 'WORTH' if worth else '-'))
json.dump(out, open('result_sweep.json','w'), indent=1)
