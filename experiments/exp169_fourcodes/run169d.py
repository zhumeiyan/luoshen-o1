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
SYS={"汉字":load_zh(),"英文":load_en(py),"代码":re.findall(r"[A-Za-z_][A-Za-z0-9_]*",py)}
V0=1000
# 各系统只保留最高频 V0 个符号，删除其他符号 -> 序列变短
CUT={}
for k,v in SYS.items():
    c=collections.Counter(v)
    keep=set(x for x,_ in c.most_common(V0))
    CUT[k]=[x for x in v if x in keep]
    print(f"{k}: 原始 N={len(v)} 截V0后 N={len(CUT[k])}")

N=min(len(v) for v in CUT.values())
print("受控 N =",N, " V =",V0, " N/V =",N/V0)

RES={}
for k,v in CUT.items():
    v=v[:N]
    outd=collections.defaultdict(set)
    for i in range(len(v)-1): outd[v[i]].add(v[i+1])
    ao=sum(len(s) for s in outd.values())/len(outd)
    bg=set((v[i],v[i+1]) for i in range(len(v)-1))
    V2=len(bg)
    # 每个符号的条件槽位（归一化用，避免 n_z 混杂）
    RES[k]=dict(V=V0,N=N,nv=N/V0,outd=ao,outd_norm=ao/V0,
                V2=V2,ratio=V2/V0,sat=V2/(V0*V0))
    print(f"\n[{k}] V={V0} N={N} N/V={N/V0:.1f}")
    print(f"  平均出度={ao:.2f}   归一化出度(出度/V)={ao/V0:.4f}")
    print(f"  2gram V2={V2}  V2/V1={V2/V0:.2f}  2gram空间占用={V2/(V0*V0):.4f}")

json.dump(dict(V0=V0,N=N,res=RES),open(f"{OUT}/result169d.json","w"),ensure_ascii=False,indent=1)
print("\nsaved")
