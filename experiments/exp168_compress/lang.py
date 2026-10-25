import os,re,json,math,collections,random

BASE="/data/workspace/luoshen-o1"

# ---------- 语料 ----------
def load_zh():
    p=f"{BASE}/evidence/失败模式库/判据核.md"
    t=open(p,encoding="utf-8",errors="ignore").read()
    # 只留汉字，去掉数字/标点/空白 -> 汉字是封闭符号集
    return [c for c in t if '\u4e00'<=c<='\u9fff']

def load_code():
    txt=[]
    for root,_,fs in os.walk(BASE):
        for f in fs:
            if f.endswith(".py"):
                try: txt.append(open(os.path.join(root,f),encoding="utf-8",errors="ignore").read())
                except Exception: pass
    return "\n".join(txt)

def code_chars(t):
    return [c for c in t if c.strip()]

def code_tokens(t):
    # 标识符 + 关键字 + 数字 = 代码的"词"，正是不断新造的那一层
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+",t)

zh=load_zh()
code=load_code()
cc=code_chars(code)
ct=code_tokens(code)

print(f"中文汉字    N={len(zh)}")
print(f"代码字符    N={len(cc)}")
print(f"代码标识符  N={len(ct)}")

# ---------- 截断到相同 N ----------
NT=200000
def cut(s,n):
    return s[:n] if len(s)>=n else s
zh_c=cut(zh,NT); cc_c=cut(cc,NT); ct_c=cut(ct,NT)
N=min(len(zh_c),len(cc_c),len(ct_c))
zh_c=zh_c[:N]; cc_c=cc_c[:N]; ct_c=ct_c[:N]
print(f"\n统一截断 N={N}")

# ---------- 词表统计 ----------
def stats(seq,name):
    c=collections.Counter(seq)
    V=len(c)
    hapax=sum(1 for v in c.values() if v==1)
    ent=-sum((v/len(seq))*math.log2(v/len(seq)) for v in c.values())
    kstar=math.log(N)/math.log(V) if V>1 else 0
    print(f"\n[{name}]")
    print(f"  V(词表)        = {V}")
    print(f"  N/V(平均频次)  = {N/V:.1f}")
    print(f"  只出现1次占比  = {hapax/V*100:.1f}%  ({hapax}个)")
    print(f"  熵 H           = {ent:.3f} bits/符号")
    print(f"  理论有效阶 k*  = log N/log V = {kstar:.3f}")
    return dict(name=name,N=N,V=V,hapax=hapax,hapax_pct=hapax/V*100,
                ent=ent,kstar=kstar,nv=N/V)

R=[]
R.append(stats(zh_c,"中文·汉字"))
R.append(stats(cc_c,"代码·字符"))
R.append(stats(ct_c,"代码·标识符"))

json.dump(dict(N=N,stats=R),open("/data/workspace/luoshen-o1/experiments/exp168_compress/stats.json","w"),ensure_ascii=False,indent=1)
