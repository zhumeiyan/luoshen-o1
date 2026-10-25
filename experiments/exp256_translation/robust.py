# -*- coding: utf-8 -*-
"""256 v3 · k=4 是不是稳健最优？（上一版 k 扫描非单调，必须检验）"""
import json,math,re,random
from collections import Counter
CD=json.load(open("coordinate_data.json")); CC=json.load(open("calibration_cases.json"))
CASES=CC["cases"]
def flat():
    o=[]
    for c in CD.get("L",[]): o.append((c["code"],c["name"],c["criterion"],"L"))
    for g in CD.get("M_groups",[]):
        for x in g.get("opts",[]): o.append((x["code"],x["name"],x.get("criterion") or g.get("criterion",""),"M"))
    for g in CD.get("P_groups",[]):
        for x in g.get("opts",[]): o.append((x["code"],x["name"],x.get("criterion") or g.get("criterion",""),"P"))
    return o
CORD=flat()
STOP=set("的 了 是 在 与 和 或 对 于 由 被 把 而 且 不 有 无 这 那 其 之 为 以 及 等 中 个 一 二 三 上 下 内 外 后 前 时 会 能 可 要 就 都 也 还 但 则 若 如 使 让 从 到 过 所 该 本 类 种 更 最 很 非 未 并 即 指".split())
def toks(s):
    s=re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+"," ",s or "").replace(" ","")
    return [s[i:i+2] for i in range(len(s)-1) if s[i] not in STOP and s[i+1] not in STOP] or list(s)
def vec(tk,w=None):
    c=Counter(tk); return {t:w.get(t,1.0)*c[t] for t in c} if w else dict(c)
def cos(a,b):
    if not a or not b: return 0.0
    n=sum(v*v for v in a.values())**0.5*sum(v*v for v in b.values())**0.5
    return sum(a[t]*b[t] for t in set(a)&set(b))/n if n else 0.0
def goldens(c):
    g=c["golden"]; return [v for k in ("L","M","P") for v in (g.get(k) or [])]
docs={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in CORD}
N=len(docs); df=Counter()
for t in docs.values(): df.update(set(t))
IDF={t:math.log((N+1)/(df.get(t,0)+0.5)) for t in df}
def build(k):
    sp={}
    for code,tk in docs.items():
        tf=Counter(tk); sc={t:(1+math.log(f))*IDF[t] for t,f in tf.items()}
        top=sorted(sc.items(),key=lambda x:-x[1])[:k]
        sp[code]=([t for t,_ in top],[w for _,w in top])
    return sp
def Bm(p,sp):
    q=vec(toks(p)); return max(((cos(q,vec(f,dict(zip(f,w)))),c) for c,(f,w) in sp.items()))[1]
def accB(sp,cs): return sum(1 for c in cs if Bm(c["phenomenon"],sp) in set(goldens(c)))/len(cs)
def Am(p):
    q=vec(toks(p)); return max(((cos(q,vec(toks((n or '')+' '+(cr or '')),IDF)),cd) for cd,n,cr,_ in CORD))[1]
def accA(cs): return sum(1 for c in cs if Am(c["phenomenon"]) in set(goldens(c)))/len(cs)

print("="*80)
print("实验七 · bootstrap：随机重抽 29 条案例（有放回）200 次，看 k 谁赢")
print("="*80)
KS=[4,8,12,20,30,50,80]
specs={k:build(k) for k in KS}
wins={k:0 for k in KS}; n=200
rng=random.Random(0)
diffs={k:[] for k in KS}
for _ in range(n):
    cs=[CASES[rng.randrange(len(CASES))] for _ in range(len(CASES))]
    aA=accA(cs)
    bs={k:accB(specs[k],cs) for k in KS}
    bk=max(bs,key=lambda k:bs[k])
    wins[bk]+=1
    for k in KS: diffs[k].append(bs[k]-aA)
print(f"{'k':>6}{'胜出次数':>10}{'胜率':>9}{'相对A的平均差':>15}{'标准差':>9}")
for k in KS:
    d=diffs[k]
    print(f"{k:>6}{wins[k]:>10}{wins[k]/n:>9.3f}{sum(d)/len(d):>15.3f}{(sum((x-sum(d)/len(d))**2 for x in d)/len(d))**0.5:>9.3f}")
print()
aA=accA(CASES)
print(f"  全量 A 基准 = {aA:.3f}")
for k in KS: print(f"  全量 k={k:<4} = {accB(specs[k],CASES):.3f}  ({accB(specs[k],CASES)-aA:+.3f})")
print()
top=max(wins,key=lambda k:wins[k])
print(f"  稳健性结论：k={top} 胜率 {wins[top]/n:.3f}")
if wins[top]/n < 0.5:
    print("  → 没有任何 k 稳定胜出。k 的选择**不稳健**，上一版'k=4 最优'不可引用。")
else:
    print(f"  → k={top} 相对稳健")
json.dump({"wins":wins,"n":n},open("robust_out.json","w"))
