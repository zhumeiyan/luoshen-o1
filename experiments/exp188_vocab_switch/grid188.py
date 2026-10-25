# -*- coding: utf-8 -*-
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run188 import load, compress, evaluate, heaps, fit_power
seq = load(); K, beta, _ = fit_power(heaps(seq)); VMAX=float(len(set(seq)))
split=int(len(seq)*0.8); fpts=[]
for M in [528,400,200,100,50,30,16,8,4,2]:
    if M>len(set(seq)): continue
    c,v=compress(seq,M); best=None
    for k in range(1,7):
        r=evaluate(c[:split],c[split:],k,v)
        if r and (best is None or r["acc"]>best["acc"]): best=r
    fpts.append((len(set(c)), math.log2(M)-best["bits"]))
fpts.sort()
def f(V):
    if V<=fpts[0][0]: return fpts[0][1]
    if V>=fpts[-1][0]: return fpts[-1][1]
    for i in range(len(fpts)-1):
        a,b=fpts[i],fpts[i+1]
        if a[0]<=V<=b[0]: return a[1]+(V-a[0])/(b[0]-a[0])*(b[1]-a[1])
    return fpts[-1][1]
def sim(strategy,budget,V0,param=None):
    N=(V0/K)**(1/beta); V=V0; g=0.0; s=0
    while s<budget:
        if strategy=="alternate": act="explore" if s%(param+1)==0 else "exploit"
        elif strategy=="greedy":
            Va=min(VMAX,K*((N+1.0)**beta))
            act="explore" if (f(Va)-f(V))*(budget-s-1)>f(V) else "exploit"
        else: act=strategy
        if act=="explore": N+=1.0; V=min(VMAX,K*(N**beta))
        else: g+=f(V)
        s+=1
    return g
grid=list(range(1,41))
rows=[]
for a in grid:
    g=sim("alternate",14000,8.0,a)
    fib = a in {1,2,3,5,8,13,21,34}
    rows.append({"a":a,"gain":g,"is_fibonacci":fib})
top=sorted(rows,key=lambda r:-r["gain"])[:10]
nonfib=sorted([r for r in rows if not r["is_fibonacci"]],key=lambda r:-r["gain"])[:5]
greedy=sim("greedy",14000,8.0)
json.dump({"grid_scan":rows,"top10":top,"top5_nonfibonacci":nonfib,"greedy":greedy},
          open("grid188.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("全网格 top10 (a, 产出, 是否斐波那契):")
for r in top: print("  a=%2d  %10.1f  fib=%s"%(r["a"],r["gain"],r["is_fibonacci"]))
print("非斐波那契 top5:")
for r in nonfib: print("  a=%2d  %10.1f"%(r["a"],r["gain"]))
print("贪心切换: %.1f"%greedy)
best_overall=max(rows,key=lambda r:r["gain"])
print("最优 a = %d (fib=%s), 贪心 vs 最优固定交替: %.1f vs %.1f"%(best_overall["a"],best_overall["is_fibonacci"],greedy,best_overall["gain"]))
# 检查 a=13 附近是否平滑（真峰值 vs 网格假象）
print("a=10..17:", [(r["a"],round(r["gain"])) for r in rows if 10<=r["a"]<=17])
