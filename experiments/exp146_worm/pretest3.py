# -*- coding: utf-8 -*-
"""pretest v3：top-level one-hot 为主特征 + 自动剔除死维度"""
import os
import numpy as np
BASE="/data/workspace/luoshen-o1"
TOPS=["experiments","overseas","evidence","paper","core","eo_io","docs","tools","fig","cloud"]

def sample_nodes(max_nodes=90):
    out=[]
    for t in TOPS:
        root=os.path.join(BASE,t)
        if not os.path.isdir(root): continue
        sub=[]
        for dp,dn,fn in os.walk(root):
            if not dn and not fn: continue
            sub.append(dp)
            if len(sub)>=12: break
        out+=sub
    return out[:max_nodes]

def content_feat(path):
    try: e=os.listdir(path)
    except OSError: return None
    nf=nd=0; ext={}
    for x in e:
        p=os.path.join(path,x)
        if os.path.isdir(p): nd+=1
        else:
            nf+=1; k=os.path.splitext(x)[1].lower(); ext[k]=ext.get(k,0)+1
    keys=[".py",".md",".json",".png",".txt",".zip",".sh",".html"]
    return [nf/50.0, nd/5.0]+[ext.get(k,0)/5.0 for k in keys]+[len(ext)/8.0]

def path_feat(path):
    rel=os.path.relpath(path,BASE); parts=rel.split(os.sep)
    top=parts[0] if parts else ""
    name=os.path.basename(path) or "."
    oh=[1.0 if top==t else 0.0 for t in TOPS]
    misc=[float(len(parts)), len(rel)/60.0,
          1.0 if any(c.isdigit() for c in name) else 0.0]
    return oh+misc

nodes=sample_nodes()
X,Y=[],[]
for p in nodes:
    c=content_feat(p)
    if c is None: continue
    X.append(path_feat(p)); Y.append(c)
X=np.array(X,float); Y=np.array(Y,float)
keep=[i for i in range(X.shape[1]) if X[:,i].std()>1e-9]
print(f"nodes={len(X)} Xraw={X.shape} kept={len(keep)} (dropped {X.shape[1]-len(keep)} dead)")
X=X[:,keep]
Xs=(X-X.mean(0))/(X.std(0)+1e-9); Ys=(Y-Y.mean(0))/(Y.std(0)+1e-9)

def loo(Xs,Ys,lam=1.0):
    n=len(Xs); e=[]
    for i in range(n):
        idx=[j for j in range(n) if j!=i]
        A=Xs[idx].T@Xs[idx]+lam*np.eye(Xs.shape[1])
        W=np.linalg.solve(A,Xs[idx].T@Ys[idx])
        e.append(np.linalg.norm(Xs[i]@W-Ys[i]))
    return float(np.mean(e))
def mloo(Ys):
    n=len(Ys); e=[]
    for i in range(n):
        m=Ys[[j for j in range(n) if j!=i]].mean(0)
        e.append(np.linalg.norm(m-Ys[i]))
    return float(np.mean(e))
rng=np.random.RandomState(7)
for nm,Yt in [("real",Ys),("noise",rng.randn(*Ys.shape)*Ys.std())]:
    r=loo(Xs,Yt); m=mloo(Yt)
    print(f"[{nm:6s}] ridge_LOO={r:.4f} mean_LOO={m:.4f} ratio={r/m:.4f} "
          f"learnable={'YES' if r<m*0.90 else 'NO'}")
np.save("X3.npy",X); np.save("Y3.npy",Y)
