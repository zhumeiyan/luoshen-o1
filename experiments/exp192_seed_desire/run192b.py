# -*- coding: utf-8 -*-
"""
192b: 种子 + 欲望（修正版）
- 度量换成 bits/字符（连续，不被量化）
- 选择单位改成 20 字窗口（预算真正可分）
- 堆量改成"加模型阶数 k"（重复数据是假堆量：计数按比例缩放，概率不变）
- 预算压到小区间，差异才显现
"""
import json, math, random, re, hashlib

SRC="/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"
OUT="/data/workspace/luoshen-o1/experiments/exp192_seed_desire/result192b.json"

msgs=[]
for line in open(SRC,encoding="utf-8"):
    m=re.match(r"^(U\d{3}):\s*(.*)$",line.rstrip("\n"))
    if m:
        t=m.group(2).strip()
        if t.startswith("[同期贴入"): continue
        if t: msgs.append(t)
print(f"[corpus] {len(msgs)} msgs / {sum(len(m) for m in msgs)} chars")

DESIRE=["想","要","欲望","挣","钱","目标","目的","希望","愿","欲","贪","打算","梦想"]
def dscore(w): return sum(w.count(x) for x in DESIRE)

def build(text,k):
    cnt=[dict() for _ in range(k+1)]; cctx=[dict() for _ in range(k+1)]
    for i in range(len(text)):
        for j in range(1,k+1):
            if i-(j-1)<0: break
            c=text[i-(j-1):i]
            cnt[j][(j,c,text[i])]=cnt[j].get((j,c,text[i]),0)+1
    for j in range(1,k+1):
        for (jj,c,ch),v in cnt[j].items(): cctx[j][c]=cctx[j].get(c,0)+v
    return cnt,cctx

def prob(cnt,cctx,V,ctx,ch,K):
    p=None
    for j in range(K,0,-1):
        c=ctx[-(j-1):] if j>1 else ""
        nc=cctx[j].get(c,0); np_=cnt[j].get((j,c,ch),0); Vj=max(len(V),1)
        pj=(np_+0.5)/(nc+0.5*Vj)
        p=pj if p is None else (nc/(nc+1.0))*pj+(1-nc/(nc+1.0))*p
    return p

def bits_of(train,test,V,K):
    cnt,cctx=build(train,K)
    b=0.0
    for i in range(len(test)):
        ctx=test[max(0,i-(K-1)):i]
        b+=-math.log2(max(prob(cnt,cctx,V,ctx,test[i],K),1e-12))
    return b/len(test)

SEEDS=[11,22,33,44,55,66,77,88]
FRACS=[0.1,0.2,0.3,0.5,0.7,1.0]
W=20  # 窗口
K=3
res={"per_seed":{},"agg":{}}
V_all=set("".join(msgs))

for sd in SEEDS:
    r=random.Random(sd); idx=list(range(len(msgs))); r.shuffle(idx)
    nt=max(1,int(len(idx)*0.4)); test_i=sorted(idx[:nt]); train_i=idx[nt:]
    test_txt="".join(msgs[i] for i in test_i)
    train_txt="".join(msgs[i] for i in train_i)
    wins=[train_txt[i:i+W] for i in range(0,len(train_txt),W) if len(train_txt[i:i+W])>=5]
    nw=len(wins)
    # 惊奇打分：用 10% 均匀种子
    seed_txt=train_txt[:max(50,int(len(train_txt)*0.10))]
    cnt,cctx=build(seed_txt,K)
    sc=[]
    for w in wins:
        b=0.0
        for i in range(len(w)):
            b+=-math.log2(max(prob(cnt,cctx,V_all,w[max(0,i-K+1):i],w[i],K),1e-12))
        sc.append(b/len(w))
    per={}
    for B in FRACS:
        nb=max(1,int(nw*B))
        rr=random.Random(sd*13+int(B*100))
        # random
        o=list(range(nw)); rr.shuffle(o); o=o[:nb]
        per.setdefault("random",{})[B]=bits_of("".join(wins[i] for i in o),test_txt,V_all,K)
        # desire（有对象）
        od=sorted(range(nw),key=lambda i:-dscore(wins[i])/max(len(wins[i]),1))[:nb]
        per.setdefault("desire",{})[B]=bits_of("".join(wins[i] for i in od),test_txt,V_all,K)
        # surprise（瞎贪婪：跟随我的错误）
        os_=sorted(range(nw),key=lambda i:-sc[i])[:nb]
        per.setdefault("surprise",{})[B]=bits_of("".join(wins[i] for i in os_),test_txt,V_all,K)
        # least-surprise（反向对照：专挑我最会的地方）
        ol=sorted(range(nw),key=lambda i:sc[i])[:nb]
        per.setdefault("easy",{})[B]=bits_of("".join(wins[i] for i in ol),test_txt,V_all,K)
    per["all"]=bits_of(train_txt,test_txt,V_all,K)
    res["per_seed"][sd]=per

# 真堆量：加阶数
heap={}
for k in [1,2,3,4,5]:
    vals=[]
    for sd in SEEDS:
        r=random.Random(sd); idx=list(range(len(msgs))); r.shuffle(idx)
        nt=max(1,int(len(idx)*0.4)); test_i=sorted(idx[:nt]); train_i=idx[nt:]
        test_txt="".join(msgs[i] for i in test_i); train_txt="".join(msgs[i] for i in train_i)
        vals.append(bits_of(train_txt,test_txt,V_all,k))
    # 参数量
    cnt,cctx=build("".join(msgs),k)
    npar=sum(len(v) for v in cnt[1:])
    heap[str(k)]={"bits":sum(vals)/len(vals),"params":npar}
    print(f"[heap k={k}] bits={sum(vals)/len(vals):.4f} params={npar}")

for kk in ["random","desire","surprise","easy"]:
    res["agg"][kk]={str(B):sum(res["per_seed"][sd][kk][B] for sd in SEEDS)/len(SEEDS) for B in FRACS}
res["agg"]["all"]=sum(res["per_seed"][sd]["all"] for sd in SEEDS)/len(SEEDS)
res["heap"]=heap
json.dump(res,open(OUT,"w"),ensure_ascii=False,indent=1)
print("\n=== AGG bits/char (越低越好) ===")
for kk in ["random","desire","surprise","easy"]:
    print(f"{kk:9s} "+" ".join(f"{B}:{res['agg'][kk][str(B)]:.4f}" for B in FRACS))
print(f"all(全量) = {res['agg']['all']:.4f}")
print("[sha]",hashlib.sha256(open(OUT,'rb').read()).hexdigest()[:12])
