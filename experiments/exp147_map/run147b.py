#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp147b 鱼格: 认知地图 (v2 修正混淆)
修正1: home 深度三地形统一=3
修正2: 探索改为"覆盖到 TARGET_KNOWN 个节点为止", 覆盖率三地形相同
修正3: 增加 CHAIN(毛刺链) 阴性地形 -> 判据必须能产生"地图无用"的假
策略: MAP(认知地图) / ROUTE(死记路线) / RANDOM / MAP_SHUF(地图错乱破缺)
"""
import os, json, random, heapq
from collections import deque, defaultdict

SEED=20261018; CAP=428; T_LIMIT=1500; TARGET_KNOWN=130
N_TRIAL=60; REAL_ROOT='/data/workspace/luoshen-o1'

def build_real(root, cap=CAP):
    par={root:None}; order=[root]; q=deque([root])
    while q and len(order)<cap:
        d=q.popleft()
        try: subs=sorted(os.listdir(d))
        except Exception: continue
        for x in subs:
            p=os.path.join(d,x)
            if os.path.islink(p) or not os.path.isdir(p) or p in par: continue
            par[p]=d; order.append(p); q.append(p)
            if len(order)>=cap: break
    return par, order

def build_synth(n, rng):
    par={'n0':None}; nodes=['n0']; q=deque(['n0']); i=1
    while len(nodes)<n and q:
        d=q.popleft()
        for _ in range(rng.choice([1,2,3])):
            if len(nodes)>=n: break
            name=f'n{i}'; i+=1
            par[name]=d; nodes.append(name); q.append(name)
    return par, nodes

def build_chain(n, rng):
    """毛刺链: 主干 + 每 8 个主干节点挂 1 个叶子; 路径近似唯一 -> 地图应无用"""
    par={'c0':None}; nodes=['c0']; i=1
    while len(nodes)<n:
        prev=nodes[-1] if nodes[-1].startswith('c') else None
        # 找主干末端
        main=[x for x in nodes if x.startswith('c')]
        tail=main[-1]
        name=f'c{i}'; i+=1
        par[name]=tail; nodes.append(name)
        if len(nodes)%8==0 and len(nodes)<n:
            lf=f'l{i}'; i+=1
            par[lf]=tail; nodes.append(lf)
    return par, nodes

def to_adj(par, nodes):
    adj=defaultdict(set)
    for n in nodes:
        p=par[n]
        if p is not None: adj[n].add(p); adj[p].add(n)
    return adj

def depths(par, nodes):
    d={}
    for n in nodes:
        k=0; x=n
        while par.get(x) is not None: x=par[x]; k+=1
        d[n]=k
    return d

def gini(vals):
    v=sorted(vals); n=len(v); s=sum(v)
    if s==0 or n==0: return 0.0
    return (2*sum((i+1)*x for i,x in enumerate(v)))/(n*s)-(n+1)/n

def explore_until(adj, home, target, rng, max_steps=20000):
    known=defaultdict(set); cur=home; seen={home}; route=[home]; steps=0
    while len(seen)<target and steps<max_steps:
        steps+=1
        nb=sorted(adj[cur])
        if not nb: break
        nxt=rng.choice(nb)
        known[cur].add(nxt); known[nxt].add(cur)
        seen.add(nxt); cur=nxt; route.append(cur)
    return known, route, steps

def dijkstra_next(known, src, dst):
    if src==dst: return None
    dist={src:0}; prev={}; pq=[(0,src)]; seen=set()
    while pq:
        d,u=heapq.heappop(pq)
        if u in seen: continue
        seen.add(u)
        if u==dst: break
        for v in known[u]:
            if d+1<dist.get(v,1e9):
                dist[v]=d+1; prev[v]=u; heapq.heappush(pq,(d+1,v))
    if dst not in dist: return None
    x=dst
    while prev.get(x)!=src:
        x=prev[x]
        if x==src: break
    return x

def shuffle_known(known, rng):
    nodes=list(known.keys())
    if len(nodes)<3: return known
    ec=sum(len(v) for v in known.values())//2
    bad=defaultdict(set)
    for _ in range(ec):
        u=rng.choice(nodes); v=rng.choice(nodes)
        if u!=v: bad[u].add(v); bad[v].add(u)
    return bad

def navigate(adj, home, start, policy, known, route, rng, tlimit=T_LIMIT):
    cur=start; steps=0
    known=defaultdict(set,{k:set(v) for k,v in known.items()})
    if policy=='MAP_SHUF': known=shuffle_known(known,rng)
    rset=set(route); ridx={}
    for i,n in enumerate(route): ridx.setdefault(n,i)
    while cur!=home and steps<tlimit:
        steps+=1
        if policy in ('MAP','MAP_SHUF'):
            nxt=dijkstra_next(known,cur,home)
            if nxt is None:
                nb=sorted(adj[cur])
                if not nb: break
                nxt=rng.choice(nb)
        elif policy=='ROUTE':
            if cur in rset:
                i=ridx[cur]
                while i>0 and steps<tlimit:
                    steps+=1; cur=route[i-1]; i-=1
                return steps, cur==home
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        else:
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        known[cur].add(nxt); known[nxt].add(cur)
        cur=nxt
    return steps, cur==home

def boot_ci(a,b=None,n=4000,seed=1):
    rng=random.Random(seed); m=len(a); vals=[]
    for _ in range(n):
        if b is None:
            vals.append(sum(a[rng.randrange(m)] for _ in range(m))/m)
        else:
            idx=[rng.randrange(m) for _ in range(m)]
            vals.append(sum(a[i]-b[i] for i in idx)/m)
    vals.sort(); return round(vals[int(0.025*n)],4), round(vals[int(0.975*n)],4)

def run():
    rng=random.Random(SEED); out={'seed':SEED,'cap':CAP,'target_known':TARGET_KNOWN,
        'n_trial':N_TRIAL,'t_limit':T_LIMIT,'real_root':REAL_ROOT}
    T={}
    parA,nA=build_real(REAL_ROOT,CAP)
    parB,nB=build_synth(len(nA),rng)
    parC,nC=build_chain(len(nA),rng)
    terr={}
    for name,(par,nodes) in {'REAL':(parA,nA),'SYNTH':(parB,nB),'CHAIN':(parC,nC)}.items():
        adj=to_adj(par,nodes); dep=depths(par,nodes)
        degs=[len(adj[n]) for n in nodes]
        # home: 统一取 depth==3 的节点(否则取最接近3)
        c3=[n for n in nodes if dep[n]==3]
        if not c3:
            m=min(dep.values(),key=lambda d:abs(d-3)); c3=[n for n in nodes if dep[n]==m]
        home=random.Random(SEED).choice(sorted(c3))
        known,route,esteps=explore_until(adj,home,TARGET_KNOWN,random.Random(SEED))
        terr[name]=dict(adj=adj,nodes=nodes,dep=dep,home=home,known=known,route=route,
            explore_steps=esteps,coverage=round(len(known)/len(nodes),4),
            depth_max=max(dep.values()),depth_mean=round(sum(dep.values())/len(dep),3),
            deg_max=max(degs),gini_deg=round(gini(degs),4))
        print(f'[{name}] n={len(nodes)} home_d={dep[home]} known={len(known)} '
              f'cov={terr[name]["coverage"]} depth_mean={terr[name]["depth_mean"]} '
              f'deg_max={max(degs)} gini={terr[name]["gini_deg"]} esteps={esteps}')
    # 导航
    starts_seed=SEED+1
    for name,t in terr.items():
        nodes=t['nodes']; starts=[nodes[i] for i in random.Random(starts_seed).sample(range(len(nodes)),N_TRIAL)]
        res={}
        for pol in ['MAP','ROUTE','RANDOM','MAP_SHUF']:
            steps=[]; succ=[]
            for k,s in enumerate(starts):
                st,ok=navigate(t['adj'],t['home'],s,pol,t['known'],t['route'],random.Random(SEED+100+k))
                steps.append(st); succ.append(1 if ok else 0)
            res[pol]=dict(mean=round(sum(steps)/len(steps),3),median=sorted(steps)[N_TRIAL//2],
                          succ=round(sum(succ)/len(succ),4),steps=steps)
        t['res']=res
        print(f'  {name}: MAP={res["MAP"]["mean"]} ROUTE={res["ROUTE"]["mean"]} '
              f'RANDOM={res["RANDOM"]["mean"]} SHUF={res["MAP_SHUF"]["mean"]} '
              f'succ={res["MAP"]["succ"]}/{res["ROUTE"]["succ"]}/{res["RANDOM"]["succ"]}')
    # MAP vs ROUTE (Tolman 主判据) paired
    out['tolman']={}
    for name,t in terr.items():
        a=t['res']['MAP']['steps']; b=t['res']['ROUTE']['steps']
        out['tolman'][name]=dict(map_mean=round(sum(a)/len(a),3),route_mean=round(sum(b)/len(b),3),
            delta_route_minus_map=round(sum(b)/len(b)-sum(a)/len(a),3),ci=boot_ci(b,a))
    # 破缺 SHUF vs MAP
    out['break']={}
    for name,t in terr.items():
        a=t['res']['MAP_SHUF']['steps']; b=t['res']['MAP']['steps']
        out['break'][name]=dict(shuf=round(sum(a)/len(a),3),map=round(sum(b)/len(b),3),
            delta=round(sum(a)/len(a)-sum(b)/len(b),3),ci=boot_ci(a,b))
    # 交互 REAL vs CHAIN: Tolman 增益
    def gain(n):
        t=terr[n]; return [(b-a) for a,b in zip(t['res']['MAP']['steps'],t['res']['ROUTE']['steps'])]
    gR,gC=gain('REAL'),gain('CHAIN')
    out['interaction_REAL_vs_CHAIN']=dict(gain_REAL=round(sum(gR)/len(gR),3),
        gain_CHAIN=round(sum(gC)/len(gC),3),
        delta=round(sum(gR)/len(gR)-sum(gC)/len(gC),3),ci=boot_ci(gR,gC))
    out['pretest']={k:{kk:vv for kk,vv in v.items() if kk not in ('adj','known','route','nodes','dep','res')}
                    for k,v in terr.items()}
    return out,terr

if __name__=='__main__':
    o,t=run()
    p='/data/workspace/luoshen-o1/experiments/exp147_map/result147b.json'
    json.dump(o,open(p,'w'),ensure_ascii=False,indent=1)
    print('WROTE',p)
    print('tolman',o['tolman']); print('break',o['break'])
    print('inter',o['interaction_REAL_vs_CHAIN'])
