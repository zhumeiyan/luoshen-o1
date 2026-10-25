#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp147c 鱼格 v3
修正4: T_LIMIT 1500->6000, 消除 CHAIN 天花板效应(v2 succ 仅0.38)
修正5: MAP 改为"算出最短路后一次走完", 不再每步 Dijkstra(否则 O(steps*n) 不可跑)
新增: 地形预检 APL(平均路径长度) / 路径冗余度 k2(长度<=最短路+2 的路径数抽样)
"""
import os, json, random, heapq
from collections import deque, defaultdict

SEED=20261018; CAP=428; T_LIMIT=6000; TARGET_KNOWN=130; N_TRIAL=60
REAL_ROOT='/data/workspace/luoshen-o1'

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
            name=f'n{i}'; i+=1; par[name]=d; nodes.append(name); q.append(name)
    return par, nodes

def build_chain(n, rng):
    par={'c0':None}; nodes=['c0']; i=1
    while len(nodes)<n:
        main=[x for x in nodes if x.startswith('c')]; tail=main[-1]
        name=f'c{i}'; i+=1; par[name]=tail; nodes.append(name)
        if len(nodes)%8==0 and len(nodes)<n:
            lf=f'l{i}'; i+=1; par[lf]=tail; nodes.append(lf)
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

def apl(adj, nodes, sample=40, rng=None):
    rng=rng or random.Random(0)
    st=[nodes[i] for i in rng.sample(range(len(nodes)),min(sample,len(nodes)))]
    tot=0; cnt=0
    for s in st:
        dist={s:0}; q=deque([s])
        while q:
            u=q.popleft()
            for v in adj[u]:
                if v not in dist: dist[v]=dist[u]+1; q.append(v)
        for n in nodes:
            if n in dist and n!=s: tot+=dist[n]; cnt+=1
    return tot/cnt if cnt else 0.0

def redundancy(adj, nodes, rng, pairs=25, slack=2):
    """长度 <= 最短路+slack 的近最短路条数(抽样, 上限200) -> 路径冗余度"""
    out=[]
    for _ in range(pairs):
        a,b=rng.choice(nodes),rng.choice(nodes)
        if a==b: continue
        dist={a:0}; q=deque([a])
        while q:
            u=q.popleft()
            for v in adj[u]:
                if v not in dist: dist[v]=dist[u]+1; q.append(v)
        if b not in dist: continue
        D=dist[b]; cnt=0
        # DFS 计数长度 <= D+slack 的简单路径
        stack=[(a,[a])]
        while stack and cnt<200:
            u,path=stack.pop()
            if u==b:
                cnt+=1; continue
            if len(path)-1>D+slack: continue
            for v in adj[u]:
                if v not in path: stack.append((v,path+[v]))
        out.append(cnt)
    return round(sum(out)/len(out),3) if out else None

def explore_until(adj, home, target, rng, max_steps=200000):
    known=defaultdict(set); cur=home; seen={home}; route=[home]; steps=0
    while len(seen)<target and steps<max_steps:
        steps+=1
        nb=sorted(adj[cur])
        if not nb: break
        nxt=rng.choice(nb)
        known[cur].add(nxt); known[nxt].add(cur)
        seen.add(nxt); cur=nxt; route.append(cur)
    return known, route, steps

def dijkstra_path(known, src, dst):
    if src==dst: return [src]
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
    path=[dst]; x=dst
    while x!=src: x=prev[x]; path.append(x)
    return path[::-1]

def shuffle_known(known, rng):
    nodes=list(known.keys())
    if len(nodes)<3: return known
    ec=sum(len(v) for v in known.values())//2
    bad=defaultdict(set)
    for _ in range(ec):
        u=rng.choice(nodes); v=rng.choice(nodes)
        if u!=v: bad[u].add(v); bad[v].add(u)
    return bad

def navigate(adj, home, start, policy, known0, route, rng, tlimit=T_LIMIT):
    cur=start; steps=0
    known=defaultdict(set,{k:set(v) for k,v in known0.items()})
    if policy=='MAP_SHUF': known=shuffle_known(known,rng)
    rset=set(route); ridx={}
    for i,n in enumerate(route): ridx.setdefault(n,i)
    while cur!=home and steps<tlimit:
        if policy in ('MAP','MAP_SHUF'):
            path=dijkstra_path(known,cur,home)
            if path and len(path)>1:
                # 沿已知最短路直达
                for nxt in path[1:]:
                    if steps>=tlimit: break
                    steps+=1; cur=nxt
                    if cur==home: break
                continue
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        elif policy=='ROUTE':
            if cur in rset:
                i=ridx[cur]
                while i>0 and steps<tlimit:
                    steps+=1; cur=route[i-1]; i-=1
                break
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        else:
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        steps+=1
        known[cur].add(nxt); known[nxt].add(cur)
        cur=nxt
    return steps, cur==home

def boot_ci(a,b=None,n=4000,seed=1):
    rng=random.Random(seed); m=len(a); vals=[]
    for _ in range(n):
        if b is None: vals.append(sum(a[rng.randrange(m)] for _ in range(m))/m)
        else:
            idx=[rng.randrange(m) for _ in range(m)]
            vals.append(sum(a[i]-b[i] for i in idx)/m)
    vals.sort(); return round(vals[int(0.025*n)],4), round(vals[int(0.975*n)],4)

def run():
    rng=random.Random(SEED)
    out={'seed':SEED,'cap':CAP,'target_known':TARGET_KNOWN,'n_trial':N_TRIAL,'t_limit':T_LIMIT}
    parA,nA=build_real(REAL_ROOT,CAP)
    parB,nB=build_synth(len(nA),rng)
    parC,nC=build_chain(len(nA),rng)
    terr={}
    for name,(par,nodes) in {'REAL':(parA,nA),'SYNTH':(parB,nB),'CHAIN':(parC,nC)}.items():
        adj=to_adj(par,nodes); dep=depths(par,nodes)
        degs=[len(adj[n]) for n in nodes]
        c3=[n for n in nodes if dep[n]==3]
        if not c3:
            m=min(dep.values(),key=lambda d:abs(d-3)); c3=[n for n in nodes if dep[n]==m]
        home=random.Random(SEED).choice(sorted(c3))
        known,route,esteps=explore_until(adj,home,TARGET_KNOWN,random.Random(SEED))
        terr[name]=dict(adj=adj,nodes=nodes,dep=dep,home=home,known=known,route=route,
            explore_steps=esteps,coverage=round(len(known)/len(nodes),4),
            depth_mean=round(sum(dep.values())/len(dep),3),depth_max=max(dep.values()),
            deg_max=max(degs),gini_deg=round(gini(degs),4),
            apl=round(apl(adj,nodes,rng=random.Random(3)),3),
            redundancy=redundancy(adj,nodes,random.Random(4)))
        t=terr[name]
        print(f'[{name}] home_d={dep[home]} cov={t["coverage"]} depth_mean={t["depth_mean"]} '
              f'deg_max={t["deg_max"]} gini={t["gini_deg"]} APL={t["apl"]} REDUN={t["redundancy"]} esteps={esteps}')
    starts_seed=SEED+1
    for name,t in terr.items():
        nodes=t['nodes']
        starts=[nodes[i] for i in random.Random(starts_seed).sample(range(len(nodes)),N_TRIAL)]
        res={}
        for pol in ['MAP','ROUTE','RANDOM','MAP_SHUF']:
            steps=[]; succ=[]
            for k,s in enumerate(starts):
                st,ok=navigate(t['adj'],t['home'],s,pol,t['known'],t['route'],random.Random(SEED+100+k))
                steps.append(st); succ.append(1 if ok else 0)
            res[pol]=dict(mean=round(sum(steps)/len(steps),3),median=sorted(steps)[N_TRIAL//2],
                          succ=round(sum(succ)/len(succ),4),steps=steps,succ_list=succ)
        t['res']=res
        print(f'  {name}: MAP={res["MAP"]["mean"]} ROUTE={res["ROUTE"]["mean"]} '
              f'RANDOM={res["RANDOM"]["mean"]} SHUF={res["MAP_SHUF"]["mean"]} '
              f'succ M/R/Rd={res["MAP"]["succ"]}/{res["ROUTE"]["succ"]}/{res["RANDOM"]["succ"]}')
    out['tolman']={}
    for name,t in terr.items():
        a=t['res']['MAP']['steps']; b=t['res']['ROUTE']['steps']
        out['tolman'][name]=dict(map=round(sum(a)/len(a),3),route=round(sum(b)/len(b),3),
            gain=round(sum(b)/len(b)-sum(a)/len(a),3),ci=boot_ci(b,a))
    out['improve_vs_random']={}
    for name,t in terr.items():
        a=t['res']['RANDOM']['steps']; b=t['res']['MAP']['steps']
        imp=[(x-y)/x if x>0 else 0.0 for x,y in zip(a,b)]
        out['improve_vs_random'][name]=dict(improve=round(sum(imp)/len(imp),4),ci=boot_ci(imp))
    out['break']={}
    for name,t in terr.items():
        a=t['res']['MAP_SHUF']['steps']; b=t['res']['MAP']['steps']
        out['break'][name]=dict(shuf=round(sum(a)/len(a),3),map=round(sum(b)/len(b),3),
            delta=round(sum(a)/len(a)-sum(b)/len(b),3),ci=boot_ci(a,b))
    gR,gC=[b-a for a,b in zip(terr['REAL']['res']['MAP']['steps'],terr['REAL']['res']['ROUTE']['steps'])],\
          [b-a for a,b in zip(terr['CHAIN']['res']['MAP']['steps'],terr['CHAIN']['res']['ROUTE']['steps'])]
    out['inter_REAL_vs_CHAIN']=dict(gain_REAL=round(sum(gR)/len(gR),3),gain_CHAIN=round(sum(gC)/len(gC),3),
        delta=round(sum(gR)/len(gR)-sum(gC)/len(gC),3),ci=boot_ci(gR,gC))
    out['pretest']={k:{kk:vv for kk,vv in v.items() if kk not in('adj','known','route','nodes','dep','res')}
                    for k,v in terr.items()}
    return out

if __name__=='__main__':
    o=run()
    p='/data/workspace/luoshen-o1/experiments/exp147_map/result147c.json'
    json.dump(o,open(p,'w'),ensure_ascii=False,indent=1)
    print('WROTE',p)
    for k in ['tolman','improve_vs_random','break','inter_REAL_vs_CHAIN']:
        print(k,o[k])
