#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp147d 鱼格 v4: 真正的"捷径"
前三版三地形 REDUN=1.0 全是树, 路径唯一 -> 只验证了"认路", 未验证"捷径"
本版: 同一真实地形, 树边 vs (树边+真实 symlink 边), 唯一差异=symlink 捷径
主指标: 捷径增益 = 树路径长度 / (树+symlink)最短路长度
"""
import os, json, random, heapq
from collections import deque, defaultdict

SEED=20261018; CAP=900
CANDS=['/usr/share','/usr/lib','/etc','/usr/share/doc','/usr/lib/x86_64-linux-gnu']

def build(root, cap=CAP):
    par={}; tree=[]; sym=[]; nodes=[root]; par[root]=None; q=deque([root]); linkmap={}
    while q and len(nodes)<cap:
        d=q.popleft()
        try: subs=sorted(os.listdir(d))
        except Exception: continue
        for x in subs:
            p=os.path.join(d,x)
            if os.path.islink(p):
                try: tgt=os.path.realpath(p)
                except Exception: continue
                # symlink 指向目录 -> 记为节点+捷径边
                if os.path.isdir(tgt):
                    if p not in par: par[p]=d; nodes.append(p)
                    linkmap[p]=tgt
                continue
            if os.path.isdir(p) and p not in par:
                par[p]=d; nodes.append(p); q.append(p)
            if len(nodes)>=cap: break
    # 树边
    for n in nodes:
        if par.get(n): tree.append((par[n],n))
    # symlink 捷径边: 仅当目标已在节点集内
    nset=set(nodes)
    for p,t in linkmap.items():
        if t in nset and t!=p and t!=par.get(p): sym.append((p,t))
    return nodes,par,tree,sym

def adj_from(edges):
    a=defaultdict(set)
    for u,v in edges: a[u].add(v); a[v].add(u)
    return a

def tree_dist(par,a,b):
    A=set(); x=a
    while x is not None: A.add(x); x=par.get(x)
    x=b; n=0
    while x not in A:
        x=par.get(x)
        if x is None: return None
        n+=1
    y=a; m=0
    while y!=x:
        y=par.get(y)
        if y is None: return None
        m+=1
    return m+n

def shortest(a,src,dst):
    if src==dst: return 0
    dist={src:0}; pq=[(0,src)]; seen=set()
    while pq:
        d,u=heapq.heappop(pq)
        if u in seen: continue
        seen.add(u)
        if u==dst: return d
        for v in a[u]:
            if d+1<dist.get(v,1e9): dist[v]=d+1; heapq.heappush(pq,(d+1,v))
    return None

def run():
    rng=random.Random(SEED); out={'seed':SEED,'cap':CAP,'cands':CANDS}
    best=None
    for root in CANDS:
        nodes,par,tree,sym=build(root,CAP)
        if not sym:
            print(f'[{root}] nodes={len(nodes)} symlinks=0  SKIP'); continue
        # symlink 的树距离(跨度)
        sp=[]
        for p,t in sym:
            d=tree_dist(par,p,t)
            if d is not None: sp.append(d)
        if not sp: 
            print(f'[{root}] symlinks={len(sym)} but no tree-dist  SKIP'); continue
        sp.sort()
        info=dict(root=root,nodes=len(nodes),sym_edges=len(sym),
                  span_min=sp[0],span_med=sp[len(sp)//2],span_max=sp[-1],
                  span_mean=round(sum(sp)/len(sp),3),
                  true_shortcut=round(sum(1 for s in sp if s>2)/len(sp),4))
        print(f'[{root}]',info)
        if best is None or info['true_shortcut']>best['true_shortcut']:
            best=dict(info); best['_d']=(nodes,par,tree,sym)
    if best is None:
        out['verdict']='NO_REAL_SYMLINK_SHORTCUT_FOUND'
        json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp147_map/result147d.json','w'),ensure_ascii=False,indent=1)
        print('VERDICT: 真实文件系统未找到跨子树 symlink 捷径'); return out
    nodes,par,tree,sym=best.pop('_d')
    out.update(best)
    adjT=adj_from(tree); adjC=adj_from(tree+sym)
    # 捷径增益: 随机 (start,home) 对
    pairs=[]
    for _ in range(400):
        a,b=rng.choice(nodes),rng.choice(nodes)
        if a==b: continue
        dt=tree_dist(par,a,b)
        dc=shortest(adjC,a,b); dt2=shortest(adjT,a,b)
        if dt is None or dc is None or dt2 is None: continue
        if dt2==0: continue
        pairs.append((dt2,dc))
    gains=[x/y for x,y in pairs if y>0]
    gains.sort()
    out['shortcut']=dict(n_pairs=len(gains),
        tree_path_mean=round(sum(x for x,y in pairs)/len(pairs),3),
        cyclic_path_mean=round(sum(y for x,y in pairs)/len(pairs),3),
        gain_mean=round(sum(gains)/len(gains),4),
        gain_median=round(gains[len(gains)//2],4),
        gain_max=round(gains[-1],4),
        pct_pairs_gain_gt1=round(sum(1 for g in gains if g>1.0001)/len(gains),4))
    print('shortcut',out['shortcut'])
    json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp147_map/result147d.json','w'),ensure_ascii=False,indent=1)
    print('WROTE result147d.json'); return out

if __name__=='__main__':
    run()
