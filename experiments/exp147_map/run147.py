#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp147 鱼格: 认知地图
先答"这片地形值不值得画", 再验收"从任意点能否走捷径回家"
地形 A=真实目录树(/data/workspace/luoshen-o1)  地形 B=合成均匀扇出树(同规模)
策略 MAP(认知地图) / ROUTE(死记路线) / RANDOM(随机) / MAP_SHUF(地图错乱破缺)
"""
import os, json, math, random, heapq, sys
from collections import deque, defaultdict, Counter

SEED      = 20261018
CAP       = 428
T_LIMIT   = 800
EXPLORE   = 400
N_TRIAL   = 60
REAL_ROOT = '/data/workspace/luoshen-o1'

# ---------------- 地形 ----------------
def build_real(root, cap=CAP):
    par={root:None}; order=[root]; q=deque([root])
    while q and len(order)<cap:
        d=q.popleft()
        try: subs=sorted(os.listdir(d))
        except Exception: continue
        for x in subs:
            p=os.path.join(d,x)
            if os.path.islink(p): continue
            if os.path.isdir(p) and p not in par:
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

def to_adj(par, nodes):
    adj=defaultdict(set)
    for n in nodes:
        p=par[n]
        if p is not None:
            adj[n].add(p); adj[p].add(n)
    return adj

# ---------------- 预检: 地形值不值得画 ----------------
def gini(vals):
    v=sorted(vals); n=len(v); s=sum(v)
    if s==0 or n==0: return 0.0
    return (2*sum((i+1)*x for i,x in enumerate(v)))/(n*s)-(n+1)/n

def avg_path_len(adj, nodes, sample=120, rng=None):
    """从 sample 个起点 BFS 的平均距离(抽样)"""
    rng = rng or random.Random(0)
    starts=[nodes[i] for i in rng.sample(range(len(nodes)), min(sample,len(nodes)))]
    tot=0; cnt=0
    for s in starts:
        dist={s:0}; q=deque([s])
        while q:
            u=q.popleft()
            for v in adj[u]:
                if v not in dist:
                    dist[v]=dist[u]+1; q.append(v)
        for n in nodes:
            if n in dist and n!=s: tot+=dist[n]; cnt+=1
    return tot/cnt if cnt else 0.0

def hub_effect(adj, nodes, k=5, rng=None):
    """移除 top-k 高度数节点后平均路径长度的增幅(枢纽性)"""
    base=avg_path_len(adj,nodes,rng=rng)
    deg=sorted(nodes,key=lambda n:-len(adj[n]))[:k]
    keep=[n for n in nodes if n not in set(deg)]
    sub=defaultdict(set)
    for u in keep:
        for v in adj[u]:
            if v in set(keep): sub[u].add(v)
    return base, avg_path_len(sub,keep,rng=rng)

def pretest(adj, nodes, name, rng):
    degs=[len(adj[n]) for n in nodes]
    g=gini(degs)
    b0,b1=hub_effect(adj,nodes,5,rng)
    return dict(terrain=name, n_nodes=len(nodes), n_edges=sum(degs)//2,
                deg_max=max(degs), deg_mean=round(sum(degs)/len(degs),3),
                gini_deg=round(g,4),
                apl_base=round(b0,3), apl_nohub=round(b1,3),
                hub_gain=round((b1-b0)/b0,4) if b0 else None)

# ---------------- 导航 ----------------
def explore(adj, home, budget, rng):
    known=defaultdict(set); cur=home; route=[home]
    for _ in range(budget):
        nb=sorted(adj[cur])
        if not nb: break
        nxt=rng.choice(nb)
        known[cur].add(nxt); known[nxt].add(cur)
        cur=nxt; route.append(cur)
    return known, route

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
    # 回溯第一步
    x=dst
    while prev.get(x)!=src:
        x=prev[x]
        if x==src: break
    return x

def shuffle_known(known, rng):
    """保持边数, 随机重连 -> 地图内容错乱(破缺对照)"""
    nodes=list(known.keys())
    if len(nodes)<3: return known
    ecount=sum(len(v) for v in known.values())//2
    bad=defaultdict(set)
    for _ in range(ecount):
        u=rng.choice(nodes); v=rng.choice(nodes)
        if u!=v: bad[u].add(v); bad[v].add(u)
    return bad

def navigate(adj, nodes, home, start, policy, known, route, rng, tlimit=T_LIMIT):
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
                nb=sorted(adj[cur]); 
                if not nb: break
                nxt=rng.choice(nb)
            else:
                nxt=nxt
        elif policy=='ROUTE':
            if cur in rset:
                # 沿 route 逆序回家
                i=ridx[cur]
                while i>0 and steps<tlimit:
                    steps+=1; cur=route[i-1]; i-=1
                return steps, cur==home
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        else: # RANDOM
            nb=sorted(adj[cur])
            if not nb: break
            nxt=rng.choice(nb)
        known[cur].add(nxt); known[nxt].add(cur)
        cur=nxt
    return steps, cur==home

# ---------------- 统计 ----------------
def boot_ci(a, b=None, n=4000, seed=1):
    """a: 样本; b 不为 None 时算 paired diff 的 CI"""
    rng=random.Random(seed); m=len(a)
    if b is None:
        vals=[]
        for _ in range(n):
            s=[a[rng.randrange(m)] for _ in range(m)]
            vals.append(sum(s)/m)
    else:
        vals=[]
        for _ in range(n):
            idx=[rng.randrange(m) for _ in range(m)]
            vals.append(sum(a[i]-b[i] for i in idx)/m)
    vals.sort()
    return round(vals[int(0.025*n)],4), round(vals[int(0.975*n)],4)

def run():
    rng=random.Random(SEED)
    out={'seed':SEED,'cap':CAP,'explore':EXPLORE,'n_trial':N_TRIAL,'t_limit':T_LIMIT,
         'real_root':REAL_ROOT}
    terrains={}

    parA,nodesA=build_real(REAL_ROOT,CAP)
    parB,nodesB=build_synth(len(nodesA),rng)
    adjA=to_adj(parA,nodesA); adjB=to_adj(parB,nodesB)

    out['pretest']=[pretest(adjA,nodesA,'REAL(DIR_TREE)',random.Random(7)),
                    pretest(adjB,nodesB,'SYNTH(UNIFORM)',random.Random(7))]

    for tname,(adj,nodes) in {'REAL':(adjA,nodesA),'SYNTH':(adjB,nodesB)}.items():
        # home 固定选一个较深节点
        par = parA if tname=='REAL' else parB
        depth={}
        for n in nodes:
            d=0; x=n
            while par.get(x) is not None: x=par[x]; d+=1
            depth[n]=d
        cand=[n for n in nodes if depth[n]>=3]
        home=random.Random(SEED).choice(cand) if cand else nodes[0]
        known,route=explore(adj,home,EXPLORE,random.Random(SEED))
        known_nodes=len(known)
        res={}
        starts=[nodes[i] for i in random.Random(SEED+1).sample(range(len(nodes)),N_TRIAL)]
        for pol in ['MAP','ROUTE','RANDOM','MAP_SHUF']:
            steps=[]; succ=[]
            for k,s in enumerate(starts):
                st,ok=navigate(adj,nodes,home,s,pol,known,route,random.Random(SEED+100+k))
                steps.append(st); succ.append(1 if ok else 0)
            res[pol]=dict(steps_mean=round(sum(steps)/len(steps),3),
                          steps_median=sorted(steps)[len(steps)//2],
                          success=round(sum(succ)/len(succ),4),
                          steps=steps, succ=succ)
        terrains[tname]=dict(home_depth=depth[home], known_nodes=known_nodes,
                             coverage=round(known_nodes/len(nodes),4),
                             route_len=len(route), res=res)
        print(f'[{tname}] home_depth={depth[home]} known={known_nodes}/{len(nodes)} '
              f'MAP={res["MAP"]["steps_mean"]} ROUTE={res["ROUTE"]["steps_mean"]} '
              f'RANDOM={res["RANDOM"]["steps_mean"]} SHUF={res["MAP_SHUF"]["steps_mean"]}')

    # 交互: MAP 相对 RANDOM 的改进率 A vs B
    def imp(t):
        r=terrains[t]['res']
        return [(a-b)/a for a,b in zip(r['RANDOM']['steps'],r['MAP']['steps'])]
    iA,iB=imp('REAL'),imp('SYNTH')
    out['interaction']=dict(
        improve_REAL=round(sum(iA)/len(iA),4), improve_SYNTH=round(sum(iB)/len(iB),4),
        delta=round(sum(iA)/len(iA)-sum(iB)/len(iB),4),
        ci_delta=boot_ci(iA,iB))
    # 破缺: MAP_SHUF vs MAP
    def pair(t,p,q):
        return terrains[t]['res'][p]['steps'], terrains[t]['res'][q]['steps']
    out['break']={}
    for t in ['REAL','SYNTH']:
        a,b=pair(t,'MAP_SHUF','MAP')
        out['break'][t]=dict(shuf_mean=round(sum(a)/len(a),3), map_mean=round(sum(b)/len(b),3),
                             delta=round(sum(a)/len(a)-sum(b)/len(b),3), ci=boot_ci(a,b))
    out['terrains']=terrains
    return out

if __name__=='__main__':
    o=run()
    p='/data/workspace/luoshen-o1/experiments/exp147_map/result147.json'
    json.dump(o,open(p,'w'),ensure_ascii=False,indent=1)
    print('WROTE',p)
    print('interaction',o['interaction'])
    print('break',o['break'])
