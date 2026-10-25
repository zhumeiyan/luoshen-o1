import os,re,json,math,collections,glob

BASE="/data/workspace/luoshen-o1"
OUT=f"{BASE}/experiments/exp169_fourcodes"
os.makedirs(OUT,exist_ok=True)

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
    body='\n'.join(cm)+'\n'+'\n'.join(ds)
    return re.findall(r"[A-Za-z][A-Za-z']+", body)

py=load_py()
SYS={"数字":load_digits(),"汉字":load_zh(),"英文":load_en(py),
     "代码":re.findall(r"[A-Za-z_][A-Za-z0-9_]*", py)}
for k,v in SYS.items(): print(f"{k}: raw N={len(v)} V={len(set(v))}")

N=min(len(v) for v in SYS.values())
SEQ={k:v[:N] for k,v in SYS.items()}
print("\n统一 N =",N)

def heaps(seq):
    pts=[]
    n=len(seq)
    for frac in [0.02,0.05,0.1,0.25,0.5,1.0]:
        m=max(10,int(n*frac))
        pts.append((m,len(set(seq[:m]))))
    xs=[math.log(p[0]) for p in pts]; ys=[math.log(p[1]) for p in pts]
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys)); den=sum((x-mx)**2 for x in xs)
    return pts,(num/den if den>0 else 0.0)

def ent(c,t): return -sum((x/t)*math.log2(x/t) for x in c.values())
def cond_mm(pairs):
    d=collections.defaultdict(collections.Counter)
    for x,y in pairs: d[x][y]+=1
    tot=len(pairs); h=0.0
    for x,cy in d.items():
        nx=sum(cy.values()); h+=(nx/tot)*(ent(cy,nx)+(len(cy)-1)/(2*nx))
    return h
def marg_mm(s):
    c=collections.Counter(s); return ent(c,len(s))+(len(c)-1)/(2*len(s))

HEAP={};RES={};COMB={}
for k,v in SEQ.items():
    n=len(v)
    pts,b=heaps(v); HEAP[k]=dict(curve=pts,b=b,V=len(set(v)))
    H=marg_mm(v)
    H1=cond_mm([(v[i-1],v[i]) for i in range(1,n)])
    H2=cond_mm([(v[i-2],v[i]) for i in range(2,n)])
    H12=cond_mm([((v[i-2],v[i-1]),v[i]) for i in range(2,n)])
    I1,I2,I12=H-H1,H-H2,H-H12
    red=I1+I2-I12
    # 变量自由度：出度/入度
    outd=collections.defaultdict(set); ind=collections.defaultdict(set)
    for i in range(1,n): outd[v[i-1]].add(v[i]); ind[v[i]].add(v[i-1])
    ao=sum(len(s) for s in outd.values())/len(outd)
    ai=sum(len(s) for s in ind.values())/len(ind)
    RES[k]=dict(H=H,H1=H1,H12=H12,I1=I1,I2=I2,I12=I12,red=red,
                red_norm=red/I12 if I12 else 0, gain=I12/max(I1,1e-9),
                slot1=2**H1, outd=ao, ind=ai, V=len(set(v)))
    bg=[(v[i],v[i+1]) for i in range(n-1)]
    pb,b2=heaps(bg)
    V1,V2=len(set(v)),len(set(bg))
    COMB[k]=dict(V1=V1,V2=V2,ratio=V2/V1,b1=b,b2=b2,sat=V2/(V1*V1))
    print(f"\n[{k}] V={V1}")
    print(f"  Heaps b={b:.4f}   2gram b={b2:.4f}  V2/V1={V2/V1:.2f}  2gram空间占用={V2/(V1*V1):.4f}")
    print(f"  H={H:.3f} I1={I1:.4f} I12={I12:.4f} 冗余={red:.4f} 归一化={red/I12:.4f} 增益I12/I1={I12/max(I1,1e-9):.3f}")
    print(f"  槽位自由度={2**H1:.1f}  平均出度={ao:.1f} 入度={ai:.1f}")

json.dump(dict(N=N,heaps=HEAP,info=RES,comb=COMB),
          open(f"{OUT}/result169.json","w"),ensure_ascii=False,indent=1)
print("\nsaved")
