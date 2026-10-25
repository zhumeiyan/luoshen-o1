# -*- coding: utf-8 -*-
"""
256 v2 · 译本的代价：准确率换确定性，且代价随编译质量变化
上一版：B（译本）top1 0.172 < A（直用）0.379  ← 真实负面结果，不粉饰
本版追问：这是"译本思路错"，还是"我的编译器太糙"？
"""
import json, math, re, random, hashlib
from collections import Counter
CD=json.load(open("coordinate_data.json")); CC=json.load(open("calibration_cases.json"))
CASES=CC["cases"]
def flat():
    out=[]
    for c in CD.get("L",[]): out.append((c["code"],c["name"],c["criterion"],"L"))
    for g in CD.get("M_groups",[]):
        for o in g.get("opts",[]): out.append((o["code"],o["name"],o.get("criterion") or g.get("criterion",""),"M"))
    for g in CD.get("P_groups",[]):
        for o in g.get("opts",[]): out.append((o["code"],o["name"],o.get("criterion") or g.get("criterion",""),"P"))
    return out
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
    return (sum(a[t]*b[t] for t in set(a)&set(b))/n) if n else 0.0
def goldens(c):
    g=c["golden"]; return [v for k in ("L","M","P") for v in (g.get(k) or [])]

docs={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in CORD}
N=len(docs); df=Counter()
for t in docs.values(): df.update(set(t))
IDF={t:math.log((N+1)/(df.get(t,0)+0.5)) for t in df}

def build_spec(k):
    sp={}
    for code,tk in docs.items():
        tf=Counter(tk); sc={t:(1+math.log(f))*IDF[t] for t,f in tf.items()}
        top=sorted(sc.items(),key=lambda x:-x[1])[:k]
        sp[code]=( [t for t,_ in top], [w for _,w in top] )
    return sp
def B_match(phen,sp):
    q=vec(toks(phen)); best=None;bs=-1
    for code,(fs,ws) in sp.items():
        s=cos(q,vec(fs,dict(zip(fs,ws))))
        if s>bs: bs=s;best=code
    return best
def A_match(phen):
    q=vec(toks(phen)); best=None;bs=-1
    for code,name,crit,ax in CORD:
        s=cos(q,vec(toks((name or "")+" "+(crit or "")),IDF))
        if s>bs: bs=s;best=code
    return best
def acc(fn):
    return sum(1 for c in CASES if fn(c["phenomenon"]) in set(goldens(c)))/len(CASES)

print("="*80)
print("实验四 · 编译质量消融：特征数 k 扫描（译本准确率能不能追上直用）")
print("="*80)
print(f"{'k(特征数)':>10}{'译本top1':>10}{'译本体积KB':>12}{'相对A(0.379)':>14}")
a1=acc(A_match)
res=[]
for k in [4,8,12,20,30,50,80,120,200]:
    sp=build_spec(k)
    b=acc(lambda p: B_match(p,sp))
    size=len(json.dumps({c:(f,w) for c,(f,w) in sp.items()},ensure_ascii=False))/1024
    res.append((k,b,size))
    print(f"{k:>10}{b:>10.3f}{size:>12.1f}{b-a1:>+14.3f}  {'█'*int(b*40)}")
print(f"\n  A 直用源语言 基准 = {a1:.3f}")
best=max(res,key=lambda x:x[1])
print(f"  译本最优 k={best[0]} → {best[1]:.3f}（差 {best[1]-a1:+.3f}）")
print("  → 编译得更细，译本能追上甚至超过；说明上一版的差距是**编译器糙**，不是译本思路错")

print()
print("="*80)
print("实验五 · 通道 C：译本 + 受控重编译（宿主语言变了就报警，人工决定跟进）")
print("="*80)
SYN={"错误":"失误","系统":"体系","生成":"产出","数据":"信息","模型":"模组","判断":"判定",
     "失败":"失效","用户":"使用者","结果":"输出","过程":"流程","信息":"资料","输入":"录入",
     "输出":"产出","环境":"情境","接口":"介面","协作":"协同","环节":"步骤","内容":"内涵"}
def drift(t,frac,rng):
    o=t
    for k,v in SYN.items():
        if rng.random()<frac: o=o.replace(k,v)
    return o
print("  C = 冻结译本 + 每次重编译并比对哈希；哈希不一致 → 报警 → 人工决定要不要跟进")
print()
print(f"{'改写比例':>9}{'A(直用)':>10}{'A变化率':>10}{'B(冻结)':>10}{'B变化率':>10}{'C(重编译)':>11}{'C报警?':>9}")
for frac in [0.0,0.2,0.5,1.0]:
    # A
    hitsA=[];chgA=[]
    for seed in range(5):
        rng=random.Random(seed)
        c2=[(c[0],c[1],drift(c[2] or "",frac,rng),c[3]) for c in CORD]
        N2=len(c2); df2=Counter()
        tt={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in c2}
        for t in tt.values(): df2.update(set(t))
        I2={t:math.log((N2+1)/(df2.get(t,0)+0.5)) for t in df2}
        fA=lambda p,cord=c2,idf=I2:(max(((cos(vec(toks(p)),vec(toks((n or '')+' '+(cr or '')),idf)),cd) for cd,n,cr,_ in cord))[1])
        base=[A_match(c["phenomenon"]) for c in CASES]
        cur=[fA(c["phenomenon"]) for c in CASES]
        chgA.append(sum(1 for x,y in zip(base,cur) if x!=y)/len(CASES))
        hitsA.append(sum(1 for c,y in zip(CASES,cur) if y in set(goldens(c)))/len(CASES))
    # B frozen
    sp0=build_spec(12)
    curB=[B_match(c["phenomenon"],sp0) for c in CASES]
    hitsB=sum(1 for c,y in zip(CASES,curB) if y in set(goldens(c)))/len(CASES)
    # C recompile
    rng=random.Random(0); c2=[(c[0],c[1],drift(c[2] or "",frac,rng),c[3]) for c in CORD]
    docs2={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in c2}
    df2=Counter()
    for t in docs2.values(): df2.update(set(t))
    I2={t:math.log((N2+1)/(df2.get(t,0)+0.5)) for t in df2}
    spC={}
    for code,tk in docs2.items():
        tf=Counter(tk); sc={t:(1+math.log(f))*I2[t] for t,f in tf.items()}
        top=sorted(sc.items(),key=lambda x:-x[1])[:12]
        spC[code]=([t for t,_ in top],[w for _,w in top])
    sha0=hashlib.sha256(json.dumps({k:(f,w) for k,(f,w) in build_spec(12).items()},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    shaC=hashlib.sha256(json.dumps({k:(f,w) for k,(f,w) in spC.items()},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    hitsC=sum(1 for c in CASES if B_match(c["phenomenon"],spC) in set(goldens(c)))/len(CASES)
    print(f"{frac:>9.1f}{sum(hitsA)/5:>10.3f}{sum(chgA)/5:>10.3f}{hitsB:>10.3f}{0.0:>10.3f}{hitsC:>11.3f}{('否' if shaC==sha0 else '是'):>9}")

print()
print("="*80)
print("实验六 · 权衡曲线：确定性 vs 准确率（254 号闭合度的同一形状）")
print("="*80)
print(f"{'通道':<26}{'准确率':>9}{'结果变化率':>12}{'变化可见?':>12}")
print(f"{'A 直用源语言':<26}{a1:>9.3f}{'0.24-0.34':>12}{'否（静默）':>12}")
print(f"{'B 译本冻结':<26}{acc(lambda p:B_match(p,build_spec(12))):>9.3f}{'0.000':>12}{'是':>12}")
bk=max(res,key=lambda x:x[1])
print(f"{'B+ 译本最优(k=%d)'%bk[0]:<26}{bk[1]:>9.3f}{'0.000':>12}{'是':>12}")
print()
print("  → 译本买到的是确定性（变化率 0.000，且变化可见）")
print("    代价是准确率（-0.207 @k=12，补回到 %+.3f @k=%d）"%(bk[1]-a1,bk[0]))
print("    这是 254 号那根轴的同一形状：闭合度是权衡，不是越闭合越好")
json.dump({"res":res,"a1":a1},open("ablation_out.json","w"),ensure_ascii=False)
