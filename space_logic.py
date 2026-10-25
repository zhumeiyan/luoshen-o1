# -*- coding: utf-8 -*-
"""代码=一维链。中文=二维网格。用图论量『空间逻辑』到底强在哪。"""
import json, numpy as np, itertools

def chain(n):
    E=[(i,i+1) for i in range(n-1)]; return E
def grid(nr,nc):
    E=[]
    for r in range(nr):
        for c in range(nc):
            i=r*nc+c
            if c+1<nc: E.append((i,i+nc-1+1) if False else (i,r*nc+c+1))
            if r+1<nr: E.append((i,(r+1)*nc+c))
    return E

def metrics(n, E):
    import collections
    adj=collections.defaultdict(set)
    for a,b in E: adj[a].add(b); adj[b].add(a)
    deg=[len(adj[i]) for i in range(n)]
    # 全源最短路
    INF=10**9
    D=[[INF]*n for _ in range(n)]
    for i in range(n): D[i][i]=0
    for a,b in E: D[a][b]=1; D[b][a]=1
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if D[i][k]+D[k][j]<D[i][j]: D[i][j]=D[i][k]+D[k][j]
    paths=[D[i][j] for i in range(n) for j in range(n) if i!=j and D[i][j]<INF]
    return {"边数":len(E), "平均度":np.mean(deg), "直径":max(paths),
            "平均路径":np.mean(paths)}

def cut(n,E,node):
    """断掉一个节点后，最大连通分量占比 + 还能互相到达的点对占比"""
    import collections
    adj=collections.defaultdict(set)
    for a,b in E:
        if a!=node and b!=node: adj[a].add(b); adj[b].add(a)
    seen=set(); comps=[]
    for s in range(n):
        if s==node or s in seen: continue
        st=[s]; comp=0
        while st:
            v=st.pop()
            if v in seen: continue
            seen.add(v); comp+=1
            st.extend(adj[v])
        comps.append(comp)
    mx=max(comps)/n if comps else 0
    reach=sum(c*(c-1) for c in comps)/(n*(n-1))
    return mx, reach

if __name__=="__main__":
    out={}
    N=16
    print("=== 一、同样 16 个单元：一维链 vs 二维网格 ===")
    print(f"  {'':<10}{'边数':>6}{'平均度':>8}{'直径':>6}{'平均路径':>9}")
    for name,E in [("一维链(代码)",chain(N)),("二维网格(中文)",grid(4,4))]:
        m=metrics(N,E)
        print(f"  {name:<10}{m['边数']:>6}{m['平均度']:>8.2f}{m['直径']:>6}{m['平均路径']:>9.2f}")
        out[name]={k:(round(v,2) if isinstance(v,float) else v) for k,v in m.items()}
    c=metrics(N,chain(N)); g=metrics(N,grid(4,4))
    print(f"  ★ 二维的连接数是 1D 的 {g['边数']/c['边数']:.2f} 倍")
    print(f"  ★ 二维直径只有 1D 的 {g['直径']/c['直径']*100:.0f}%（{g['直径']} vs {c['直径']}）")
    print(f"  ★ 二维平均路径只有 1D 的 {g['平均路径']/c['平均路径']*100:.0f}%")
    out["边数比"]=round(g['边数']/c['边数'],2)
    out["直径比"]=round(g['直径']/c['直径'],2)

    print("\n=== 二、断掉一个单元，还剩多少 ===")
    print(f"  {'':<12}{'最大连通块':>11}{'还能互通的点对':>15}")
    for name,E in [("一维链",chain(N)),("二维网格",grid(4,4))]:
        rs=[cut(N,E,i) for i in range(N)]
        print(f"  {name:<12}{np.mean([r[0] for r in rs])*100:>10.1f}%{np.mean([r[1] for r in rs])*100:>14.1f}%")
        out[name+"_断后连通%"]=round(np.mean([r[0] for r in rs])*100,1)
        out[name+"_断后互通%"]=round(np.mean([r[1] for r in rs])*100,1)
    print(f"  ★ 一维断中间一处 → 一半到不了另一半")
    print(f"  ★ 二维断一处 → 绕路就行，这正是『空间』的容错")

    print("\n=== 三、铁证：部件相同、位置不同 = 不同的字 ===")
    pairs=[("呆","杏","口+木 上下互换"),("杲","杳","日在木上 / 木在下"),
           ("旮","旯","九+日 上下互换"),("忘","忙","亡+心 上下 / 左右"),
           ("吟","含","今+口 左右 / 上下"),("陪","部","阝在左 / 在右"),
           ("另","加","口+力 上下 / 左右"),("音","昱","立+日 / 日+立"),
           ("叶","古","口+十 左右互换"),("叨","召","口+刀 左右互换"),
           ("呗","员"),("呗","员","口+贝 左右 / 上下"),
           ("岍","汧"),("吧","邑")]
    seen=set(); cnt=0
    for p in pairs:
        if len(p)<3: continue
        a,b,d=p
        if (a,b) in seen: continue
        seen.add((a,b)); cnt+=1
        print(f"  {a} / {b}   {d}")
    print(f"  ★ 共 {cnt} 组：同样的部件，只是【换了个位置】，就是另一个字")
    print(f"  ★ 一维线性里不可能有这种事 —— 位置在链上只有先后，没有『上下』")
    out["部件换位成字_组数"]=cnt
    print(f"  ★ 这就是【空间本身携带语义】：位置不是装饰，是语法")

    print("\n=== 四、形旁的位置是有规律的（空间=槽位）===")
    形旁位置 = {"氵(水)":"左","亻(人)":"左","扌(手)":"左","木":"左","口":"左",
              "艹(草)":"上","竹":"上","宀(宝盖)":"上","⺮":"上",
              "心/忄":"左或下","皿":"下","灬(火)":"下","女":"左","讠(言)":"左"}
    pos={}
    for k,v in 形旁位置.items(): pos[v]=pos.get(v,0)+1
    for k,v in pos.items(): print(f"  形旁在【{k}】  {v} 例")
    print(f"  ★ 形旁位置不是随机的 —— 它在汉字里占固定的空间槽位")
    print(f"  ★ 你扫一眼左边是氵，就知道这字跟水有关，不用读完整个字")
    print(f"  ★ 一维链没有『左边』这个槽位，只有『第几个』")

    print("\n=== 五、所以两种底层逻辑的差别 ===")
    print(f"  {'':<14}{'代码(一维)':<26}{'中文(二维)'}")
    print(f"  {'单元关系':<14}{'前后（只有先后）':<26}{'上下左右内外包围'}")
    print(f"  {'连接度':<14}{'2':<26}{'4'}")
    print(f"  {'断一处':<14}{'半边失联':<26}{'绕路可达'}")
    print(f"  {'位置含义':<14}{'第 N 个（序）':<26}{'槽位（类）'}")
    print(f"  {'读法':<14}{'串行扫描':<26}{'整体并行'}")
    print(f"  ★ 代码的世界里，信息只有【顺序】一个维度")
    print(f"  ★ 中文的世界里，信息有【位置】—— 位置本身就是分类")

    json.dump(out, open("参数库/空间逻辑.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/空间逻辑.json")
