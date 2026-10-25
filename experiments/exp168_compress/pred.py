import os,re,json,math,collections,random
BASE="/data/workspace/luoshen-o1"
def load_zh():
    t=open(f"{BASE}/evidence/失败模式库/判据核.md",encoding="utf-8",errors="ignore").read()
    return [c for c in t if '\u4e00'<=c<='\u9fff']
def load_code():
    txt=[]
    for root,_,fs in os.walk(BASE):
        for f in fs:
            if f.endswith(".py"):
                try: txt.append(open(os.path.join(root,f),encoding="utf-8",errors="ignore").read())
                except Exception: pass
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+","\n".join(txt))

zh=load_zh(); ct=load_code()
N=min(len(zh),len(ct))
zh=zh[:N]; ct=ct[:N]
print(f"统一 N={N}")

def ngram_acc(seq,k,name):
    # 顺序随机化切分，防漂移（156号复发病）
    idx=list(range(len(seq)-k)); random.seed(7); random.shuffle(idx)
    m=len(idx); cut=int(m*0.7)
    tr=idx[:cut]; te=idx[cut:]
    def build(ii):
        d=collections.defaultdict(collections.Counter)
        for i in ii:
            d[tuple(seq[i:i+k])][seq[i+k]]+=1
        return d
    M=build(tr)
    hit=tot=0; cov=0
    for i in te:
        ctx=tuple(seq[i:i+k]); tgt=seq[i+k]
        c=M.get(ctx)
        if c:
            cov+=1
            if max(c,key=c.get)==tgt: hit+=1
        tot+=1
    # baseline: 总是猜训练集中最频繁的符号
    allc=collections.Counter()
    for v in M.values(): allc.update(v)
    base=max(allc,key=allc.get)
    bhit=sum(1 for i in te if seq[i+k]==base)
    acc=hit/tot if tot else 0
    bacc=bhit/tot if tot else 0
    print(f"  {name} k={k}  acc={acc:.4f}  base={bacc:.4f}  gain={acc-bacc:+.4f}  覆盖率={cov/tot:.4f}")
    return dict(k=k,acc=acc,baseline=bacc,gain=acc-bacc,cov=cov/tot)

out={}
for nm,seq in [("汉字",zh),("造词标识符",ct)]:
    print(f"\n[{nm}]")
    out[nm]=[ngram_acc(seq,k,nm) for k in (1,2,3,4,5)]

for nm in out:
    best=max(out[nm],key=lambda r:r["gain"])
    print(f"\n{nm}: 峰值 k={best['k']}  gain={best['gain']:+.4f}")
json.dump(dict(N=N,res=out),open("/data/workspace/luoshen-o1/experiments/exp168_compress/pred.json","w"),ensure_ascii=False,indent=1)
