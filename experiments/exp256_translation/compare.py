# -*- coding: utf-8 -*-
"""
256 · 通道 A（直用源语言） vs 通道 B（经译本）
语料：TACT 29 条真实校准案例（calibration_cases.json v1.2.1，带 golden 坐标）
"""
import json, math, re, random, hashlib
from collections import Counter

CD=json.load(open("coordinate_data.json")); CC=json.load(open("calibration_cases.json"))
SP=json.load(open("spec_v1.json"))
CASES=CC["cases"]
print(f"校准案例: {len(CASES)} 条 (calibration_version {CC['calibration_version']})")

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
    c=Counter(tk)
    if w: return {t:w.get(t,1.0)*c[t] for t in c}
    return dict(c)
def cos(a,b):
    if not a or not b: return 0.0
    n=sum(v*v for v in a.values())**0.5 * sum(v*v for v in b.values())**0.5
    if n==0: return 0.0
    inter=set(a)&set(b)
    return sum(a[t]*b[t] for t in inter)/n

# idf over criterion corpus (通道 A 每次"重新读原文")
docs={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in CORD}
N=len(docs); df=Counter()
for t in docs.values(): df.update(set(t))
IDF={t:math.log((N+1)/(df.get(t,0)+0.5)) for t in df}

def A_match(phen, cord=CORD):
    """通道 A：每次重新读判据原文，模糊语义匹配"""
    q=vec(toks(phen))
    best=None;bs=-1
    for code,name,crit,ax in cord:
        d=vec(toks((name or "")+" "+(crit or "")),IDF)
        s=cos(q,d)
        if s>bs: bs=s;best=code
    return best

def B_match(phen, spec=SP["spec"]):
    """通道 B：用冻结译本，确定性匹配"""
    q=vec(toks(phen))
    best=None;bs=-1
    for code,s in spec.items():
        w={f:wt for f,wt in zip(s["features"],s["weights"])}
        d=vec(s["features"],w)
        sc=cos(q,d)
        if sc>bs: bs=sc;best=code
    return best

def goldens(c):
    g=c["golden"]; out=[]
    for k in ("L","M","P"):
        for v in (g.get(k) or []): out.append(v)
    return out

print()
print("="*80); print("实验一 · 准确率（29 条真实案例，top1 / top3）"); print("="*80)
def acc(fn,topk=1):
    hit=0
    for c in CASES:
        ph=c["phenomenon"]; g=set(goldens(c))
        if topk==1:
            hit += 1 if fn(ph) in g else 0
        else:
            # top3
            q=vec(toks(ph)); sc=[]
            src = [(x[0], vec(toks((x[1] or "")+" "+(x[2] or "")),IDF)) for x in CORD] if fn is A_match else \
                  [(k, vec(v["features"],{f:w for f,w in zip(v["features"],v["weights"])})) for k,v in SP["spec"].items()]
            for code,d in src: sc.append((cos(q,d),code))
            sc.sort(reverse=True)
            hit += 1 if any(s[1] in g for s in sc[:topk]) else 0
    return hit/len(CASES)
a1=acc(A_match,1); b1=acc(B_match,1); a3=acc(A_match,3); b3=acc(B_match,3)
print(f"{'':<16}{'top1':>10}{'top3':>10}")
print(f"{'A 直用源语言':<16}{a1:>10.3f}{a3:>10.3f}")
print(f"{'B 经译本':<16}{b1:>10.3f}{b3:>10.3f}")
print(f"{'差':<16}{b1-a1:>+10.3f}{b3-a3:>+10.3f}")

print()
print("="*80); print("实验二 · 稳定性：宿主语言会变，两个通道各自怎么反应"); print("="*80)
SYN={"错误":"失误","系统":"体系","生成":"产出","数据":"信息","模型":"模组","判断":"判定",
     "失败":"失效","用户":"使用者","结果":"输出","过程":"流程","信息":"资料","输入":"录入",
     "输出":"产出","环境":"情境","接口":"介面","协作":"协同","环节":"步骤","内容":"内涵"}
def drift(text,frac,rng):
    """模拟宿主语言演化：同义替换"""
    out=text
    for k,v in SYN.items():
        if rng.random()<frac: out=out.replace(k,v)
    return out
def noise(text,frac,rng):
    """加口语噪声"""
    pad=["其实","说白了","某种程度上","你看","这个事情","严格讲","大致上"]
    if rng.random()<frac: 
        i=rng.randint(0,max(len(text)-1,0)); return text[:i]+rng.choice(pad)+text[i:]
    return text

print(" A 通道：判据原文被改写 → 它每次重新读，结果跟着漂")
print(" B 通道：译本已冻结 → 判据原文怎么改，它的输出都不动\n")
print(f"{'改写比例':>9}{'A命中':>9}{'A结果变化率':>13}{'B命中':>9}{'B结果变化率':>13}")
rowsA=[]
for frac in [0.0,0.2,0.4,0.6,0.8,1.0]:
    chg=[];hits=0
    for seed in range(6):
        rng=random.Random(seed)
        cord2=[(c[0],c[1],drift(c[2] or "",frac,rng),c[3]) for c in CORD]
        base=[A_match(c["phenomenon"]) for c in CASES]
        cur =[A_match(c["phenomenon"],cord2) for c in CASES]
        chg.append(sum(1 for x,y in zip(base,cur) if x!=y)/len(CASES))
        hits+= sum(1 for c,y in zip(CASES,cur) if y in set(goldens(c)))/len(CASES)
    # B: spec 冻结，判据改了也不重编译
    chgB=[];hitsB=0
    for seed in range(6):
        rng=random.Random(seed)
        _=[(c[0],c[1],drift(c[2] or "",frac,rng),c[3]) for c in CORD]   # 源语言变了，但译本不重编
        cur=[B_match(c["phenomenon"]) for c in CASES]
        base=[B_match(c["phenomenon"]) for c in CASES]
        chgB.append(sum(1 for x,y in zip(base,cur) if x!=y)/len(CASES))
        hitsB+=sum(1 for c,y in zip(CASES,cur) if y in set(goldens(c)))/len(CASES)
    print(f"{frac:>9.1f}{hits/6:>9.3f}{sum(chg)/6:>13.3f}{hitsB/6:>9.3f}{sum(chgB)/6:>13.3f}")
    rowsA.append((frac,hits/6,sum(chg)/6,hitsB/6,sum(chgB)/6))

print()
print("="*80); print("实验三 · 关键：译本让'变化'可见（哈希）"); print("="*80)
def spec_sha(cord):
    """重新编译 → 哈希"""
    docs2={c[0]:toks((c[1] or "")+" "+(c[2] or "")) for c in cord}
    df2=Counter()
    for t in docs2.values(): df2.update(set(t))
    idf2={t:math.log((N+1)/(df2.get(t,0)+0.5)) for t in df2}
    sp={}
    for code,tk in docs2.items():
        tf=Counter(tk); sc={t:(1+math.log(f))*idf2[t] for t,f in tf.items()}
        top=sorted(sc.items(),key=lambda x:-x[1])[:12]
        sp[code]=dict(code=code,features=[t for t,_ in top],weights=[round(w,4) for _,w in top])
    return hashlib.sha256(json.dumps(sp,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
rng=random.Random(0)
base_sha=spec_sha(CORD)
print(f"  原始判据编译出的译本 sha : {base_sha[:24]}...")
print(f"{'改写比例':>9}{'重编译后译本 sha':>26}{'与原译本一致?':>15}")
for frac in [0.0,0.1,0.3,0.5,1.0]:
    r=random.Random(frac)
    cord2=[(c[0],c[1],drift(c[2] or "",frac,r),c[3]) for c in CORD]
    s2=spec_sha(cord2)
    print(f"{frac:>9.1f}{s2[:24]:>26}{'是' if s2==base_sha else '否 ← 变了，且看得见':>15}")
print()
print("  → 直用源语言：漂移是**静默**的（你不知道自己判得跟上次不一样）")
print("    经译本    ：漂移是**显式**的（重编译哈希就变，你能看见，能决定要不要跟进）")

json.dump({"acc":{"A1":a1,"A3":a3,"B1":b1,"B3":b3},"rowsA":rowsA},open("compare_out.json","w"),ensure_ascii=False)
