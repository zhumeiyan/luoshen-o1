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
print("N =",N)

# 上下文取原序列的连续位置；随机选哪些位置做 test（序列不被打乱）
def ctxfn_of(kind):
    if kind=="prev1": return lambda s,i: s[i-1] if i>=2 else None
    if kind=="prev2": return lambda s,i: s[i-2] if i>=2 else None
    if kind=="both":  return lambda s,i: (s[i-2],s[i-1]) if i>=2 else None
    if kind=="base":  return lambda s,i: ("M",) if i>=2 else None

def evaluate(seq,kind,te_idx):
    fn=ctxfn_of(kind)
    d=collections.defaultdict(collections.Counter)
    marg=collections.Counter()
    for i in range(2,len(seq)):
        if i in te_idx: continue          # 训练只用非 test 位置
        d[fn(seq,i)][seq[i]]+=1
        marg[seq[i]]+=1
    tot=sum(marg.values())
    hit=0; cov=0; n=0
    for i in te_idx:
        z=fn(seq,i); y=seq[i]
        c=d.get(z)
        if c:
            cov+=1
            if max(c,key=c.get)==y: hit+=1
        n+=1
    # baseline: 总猜训练集最高频符号
    base=max(marg,key=marg.get)
    bhit=sum(1 for i in te_idx if seq[i]==base)
    return dict(acc=hit/n, cov=cov/n, base=bhit/n, n=n)

RES={}
for k,v in SEQ.items():
    random.seed(7)
    pos=list(range(2,len(v))); random.shuffle(pos)
    cut=int(len(pos)*0.3); te_idx=set(pos[:cut])
    out={}
    for kind in ["base","prev1","prev2","both"]:
        out[kind]=evaluate(v,kind,te_idx)
    g1=out["prev1"]["acc"]-out["base"]["acc"]
    g2=out["prev2"]["acc"]-out["base"]["acc"]
    gb=out["both"]["acc"]-out["base"]["acc"]
    red=g1+g2-gb                     # >0 冗余(一维)  <0 协同(多维)
    RES[k]=dict(n=out["base"]["n"],base=out["base"]["acc"],
                a1=out["prev1"]["acc"],a2=out["prev2"]["acc"],ab=out["both"]["acc"],
                cov1=out["prev1"]["cov"],covb=out["both"]["cov"],
                g1=g1,g2=g2,gb=gb,red=red,red_norm=red/gb if gb else 0,
                syn=gb/g1 if g1 else 0)
    print(f"\n[{k}]  test n={out['base']['n']}")
    print(f"  base={out['base']['acc']:.4f}  prev1={out['prev1']['acc']:.4f}  prev2={out['prev2']['acc']:.4f}  both={out['both']['acc']:.4f}")
    print(f"  覆盖率 prev1={out['prev1']['cov']:.4f} both={out['both']['cov']:.4f}")
    print(f"  增益 g1={g1:+.4f} g2={g2:+.4f} gb={gb:+.4f}   冗余={red:+.4f}  归一化={red/gb if gb else 0:+.4f}  增益比gb/g1={gb/g1 if g1 else 0:.3f}")

json.dump(dict(N=N,res=RES),open(f"{OUT}/result169b.json","w"),ensure_ascii=False,indent=1)
print("\nsaved")
