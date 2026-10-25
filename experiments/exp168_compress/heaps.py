import os,re,json,math,collections

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
print(f"中文汉字 N_max={len(zh)}   代码标识符 N_max={len(ct)}")

def curve(seq,name,pts):
    out=[]
    for n in pts:
        if n>len(seq): continue
        V=len(set(seq[:n]))
        out.append((n,V))
    # Heaps 指数: V = K*N^b  ->  log V = log K + b log N
    if len(out)>=2:
        xs=[math.log(n) for n,_ in out]; ys=[math.log(v) for _,v in out]
        mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
        b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
    else: b=None
    print(f"\n[{name}]  Heaps指数 b={b:.3f}" if b else f"\n[{name}]")
    prev=None
    for n,V in out:
        g=f"  (较上档 +{(V-prev)/prev*100:.1f}%)" if prev else ""
        print(f"   N={n:>8}  V={V:>6}{g}")
        prev=V
    return dict(name=name,curve=out,b=b)

import numpy as np
pts=[5000,10000,20000,40000,79386]
A=curve(zh,"中文·汉字（封闭集）",pts)
pts2=[5000,10000,50000,100000,200000,500000,1000000]
B=curve(ct,"代码·标识符（造词·开放集）",pts2)

json.dump(dict(zh=A,code=B),open("/data/workspace/luoshen-o1/experiments/exp168_compress/heaps.json","w"),ensure_ascii=False,indent=1)
