import os,re,json,math,collections,glob,random

BASE="/data/workspace/luoshen-o1"
OUT=f"{BASE}/experiments/exp169_fourcodes"

def load_zh():
    t=open(f"{BASE}/evidence/失败模式库/判据核.md",encoding="utf-8",errors="ignore").read()
    return [c for c in t if '\u4e00'<=c<='\u9fff']
def load_digits():
    t=open(f"{BASE}/evidence/失败模式库/判据核.md",encoding="utf-8",errors="ignore").read()
    d=[c for c in t if '0'<=c<='9']
    for p in glob.glob('/usr/lib/python3*/*.py')[:600]:
        try: d+=[c for c in open(p,encoding='utf-8',errors='ignore').read() if '0'<=c<='9']
        except Exception: pass
    return d
def load_py():
    txt=[]
    for p in glob.glob('/usr/lib/python3*/*.py')[:600]:
        try: txt.append(open(p,encoding='utf-8',errors='ignore').read())
        except Exception: pass
    return '\n'.join(txt)
def load_en(s):
    cm=re.findall(r'#[^\n]*', s)
    ds=re.findall(r'\"\"\".*?\"\"\"', s, re.S)+re.findall(r"'''.*?'''", s, re.S)
    return re.findall(r"[A-Za-z][A-Za-z']+", '\n'.join(cm)+'\n'+'\n'.join(ds))

py=load_py()
SYS={"数字":load_digits(),"汉字":load_zh(),"英文":load_en(py),
     "代码":re.findall(r"[A-Za-z_][A-Za-z0-9_]*",py)}
N=min(min(len(v) for v in SYS.values()),66379)
SEQ={k:v[:N] for k,v in SYS.items()}

KIND=["prev1","prev2","both","base"]
def ctx(kind,s,i):
    if kind=="prev1": return s[i-1]
    if kind=="prev2": return s[i-2]
    if kind=="both":  return (s[i-2],s[i-1])
    return ("M",)

def one_fold(seq,te_idx,seed):
    random.seed(seed)
    M={k:collections.defaultdict(collections.Counter) for k in KIND}
    marg=collections.Counter()
    for i in range(2,len(seq)):
        if i in te_idx: continue
        for k in KIND: M[k][ctx(k,seq,i)][seq[i]]+=1
        marg[seq[i]]+=1
    hit={k:0 for k in KIND}; n=0
    base=max(marg,key=marg.get); bh=0
    for i in sorted(te_idx):
        y=seq[i]
        # 共同覆盖：prev1/prev2/both 三个上下文在训练集中都出现过
        if not all(ctx(k,seq,i) in M[k] for k in ["prev1","prev2","both"]):
            continue
        for k in KIND:
            if max(M[k][ctx(k,seq,i)],key=M[k][ctx(k,seq,i)].get)==y: hit[k]+=1
        n+=1; bh+= (y==base)
    if n<200: return None
    acc={k:hit[k]/n for k in KIND}; acc["base"]=bh/n
    return dict(n=n,acc=acc)

RES={}
for k,v in SEQ.items():
    folds=[]
    for seed,frac in [(7,(0.0,0.3)),(11,(0.35,0.65)),(13,(0.7,1.0))]:
        random.seed(seed)
        pos=list(range(2,len(v))); random.shuffle(pos)
        a=int(len(pos)*frac[0]); b=int(len(pos)*frac[1])
        r=one_fold(v,set(pos[a:b]),seed)
        if r: folds.append(r)
    # 平均
    A={kk:sum(f["acc"][kk] for f in folds)/len(folds) for kk in KIND}
    ns=[f["n"] for f in folds]
    g1=A["prev1"]-A["base"]; g2=A["prev2"]-A["base"]; gb=A["both"]-A["base"]
    red=g1+g2-gb
    # 逐折冗余，看符号稳定性
    reds=[]
    for f in folds:
        a=f["acc"]; reds.append((a["prev1"]-a["base"])+(a["prev2"]-a["base"])-(a["both"]-a["base"]))
    RES[k]=dict(n=sum(ns)//len(ns),nfolds=len(folds),acc=A,g1=g1,g2=g2,gb=gb,
                red=red,red_norm=red/gb if gb else 0,syn=gb/g1 if g1 else 0,
                red_per_fold=reds)
    print(f"\n[{k}] 公共子集 n≈{sum(ns)//len(ns)}  folds={len(folds)}")
    print(f"  base={A['base']:.4f} prev1={A['prev1']:.4f} prev2={A['prev2']:.4f} both={A['both']:.4f}")
    print(f"  增益 g1={g1:+.4f} g2={g2:+.4f} gb={gb:+.4f}")
    print(f"  冗余={red:+.4f} 归一化={red/gb if gb else 0:+.4f}  gb/g1={gb/g1 if g1 else 0:.3f}")
    print(f"  逐折冗余={[round(x,4) for x in reds]}  符号一致={'是' if all(x>0 for x in reds) or all(x<0 for x in reds) else '否'}")

json.dump(dict(N=N,res=RES),open(f"{OUT}/result169c.json","w"),ensure_ascii=False,indent=1)
print("\nsaved")
