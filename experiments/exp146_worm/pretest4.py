# -*- coding: utf-8 -*-
"""pretest v4：地形B = 真实文件，路径线索 -> 文件物理属性"""
import os, math, collections
import numpy as np
BASE="/data/workspace/luoshen-o1"
ROOTS=["experiments","overseas","evidence","paper","core","eo_io","docs","tools"]

def sample_files(max_n=90):
    out=[]
    for r in ROOTS:
        root=os.path.join(BASE,r)
        if not os.path.isdir(root): continue
        for dp,dn,fn in os.walk(root):
            for f in fn:
                out.append(os.path.join(dp,f))
                if len(out)>=max_n*3: break
            if len(out)>=max_n*3: break
    return out[:max_n]

EXTS=[".py",".md",".json",".png",".txt",".zip",".sh",".html"]
def path_feat(p):
    rel=os.path.relpath(p,BASE); name=os.path.basename(p)
    ext=os.path.splitext(name)[1].lower()
    oh=[1.0 if ext==e else 0.0 for e in EXTS]
    oh.append(1.0 if ext not in EXTS else 0.0)
    misc=[rel.count(os.sep)/6.0, len(name)/25.0,
          1.0 if any(c.isdigit() for c in name) else 0.0]
    return oh+misc

def content_feat(p):
    try:
        st=os.stat(p); sz=st.st_size
        with open(p,'rb') as f: head=f.read(4096)
    except OSError: return None
    if not head: return None
    ent=0.0
    c=collections.Counter(head)
    for k,v in c.items():
        pr=v/len(head); ent-=pr*math.log2(pr)
    printable=sum(1 for b in head if 32<=b<127 or b in (9,10,13))/len(head)
    return [math.log(sz+1)/12.0, ent/8.0, printable,
            sum(1 for b in head if 48<=b<=57)/len(head)]

files=sample_files()
X,Y=[],[]
for p in files:
    c=content_feat(p)
    if c is None: continue
    X.append(path_feat(p)); Y.append(c)
X=np.array(X,float); Y=np.array(Y,float)
keep=[i for i in range(X.shape[1]) if X[:,i].std()>1e-9]
print(f"files={len(X)} Xraw={X.shape} kept={len(keep)}")
X=X[:,keep]
Xs=(X-X.mean(0))/(X.std(0)+1e-9); Ys=(Y-Y.mean(0))/(Y.std(0)+1e-9)
def loo(Xs,Ys,lam=1.0):
    n=len(Xs);e=[]
    for i in range(n):
        idx=[j for j in range(n) if j!=i]
        A=Xs[idx].T@Xs[idx]+lam*np.eye(Xs.shape[1])
        W=np.linalg.solve(A,Xs[idx].T@Ys[idx])
        e.append(np.linalg.norm(Xs[i]@W-Ys[i]))
    return float(np.mean(e))
def mloo(Ys):
    n=len(Ys);e=[]
    for i in range(n):
        m=Ys[[j for j in range(n) if j!=i]].mean(0)
        e.append(np.linalg.norm(m-Ys[i]))
    return float(np.mean(e))
rng=np.random.RandomState(7)
for nm,Yt in [("real",Ys),("noise",rng.randn(*Ys.shape)*Ys.std())]:
    r=loo(Xs,Yt); m=mloo(Yt)
    print(f"[{nm:6s}] ridge_LOO={r:.4f} mean_LOO={m:.4f} ratio={r/m:.4f} "
          f"learnable={'YES' if r<m*0.90 else 'NO'}")
np.save("X4.npy",X); np.save("Y4.npy",Y)
