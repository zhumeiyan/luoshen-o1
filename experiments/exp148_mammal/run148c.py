import json, math
import numpy as np
exec(open('run148.py').read().split("if __name__")[0])
def ci(d):
    d=np.asarray(d,float); n=len(d); m=d.mean(); se=d.std(ddof=1)/math.sqrt(n)
    return m, m-1.96*se, m+1.96*se
def _gate(lr0,e,base,k):
    rel=e/(base+1e-9)
    v=lr0*(1.0+k*min(rel-1.0,2.0)) if rel>1.0 else lr0*(1.0-0.3*(1.0-rel))
    return float(np.clip(v,lr0*0.2,lr0*5.0))

def build(seq, half):
    x=np.asarray(seq); mu=float(x[:half].mean()); sd=float(x[:half].std())+1e-9
    return x,mu,sd

def run3(seq, dream='none', gate=False, seed=0, lr0=0.03, k=3.0, rounds=3, other=None):
    rng=np.random.default_rng(seed)
    x=np.asarray(seq); N=len(x); half=N//2
    mu=float(x[:half].mean()); sd=float(x[:half].std())+1e-9
    w=np.zeros(LAG+1); buf=[]; hist=[]; lr=lr0
    for i in range(LAG,half):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        w,e=update(w,f,y,lr); buf.append((f.copy(),y)); hist.append(abs(e))
        if gate: lr=_gate(lr0,abs(e),float(np.mean(hist)),k)
    if not np.isfinite(w).all(): return float('nan')
    if dream!='none':
        if dream=='cross':
            # 别人的真实经历：另一条独立采集的真实序列（同 profile），用它构造经验
            ox=np.asarray(other); om=float(ox[:half].mean()); os_=float(ox[:half].std())+1e-9
            ob=[]
            for i in range(LAG,half):
                f=feats(ox,i,om,os_); ob.append((f, (ox[i]-om)/os_))
            buf2=ob
        else:
            buf2=buf
        idx=list(range(len(buf2)))
        order={'real':idx,'rev':idx[::-1],'shuf':list(rng.permutation(len(buf2))),
               'cross':idx,'noise':None}.get(dream, idx)
        for _ in range(rounds):
            if dream=='noise':
                arr=np.asarray([b[1] for b in buf2]); m_,s_=arr.mean(),arr.std()+1e-9
                ys=rng.normal(m_,s_,size=len(buf2))
                for j,(f,_) in enumerate(buf2): w=update(w,f,float(ys[j]),lr0)[0]
            else:
                for j in order:
                    f,y=buf2[j]; w=update(w,f,y,lr0)[0]
        if not np.isfinite(w).all(): return float('nan')
    te=[]; hist2=list(hist[-20:]); lr=lr0
    for i in range(half,N):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        te.append(abs(float(np.dot(w,f))-y))
        w,e=update(w,f,y,lr); hist2.append(abs(e))
        if gate: lr=_gate(lr0,abs(e),float(np.mean(hist2[-50:])),k)
    return float(np.mean(te))

D=json.load(open('real_series.json'))
CONDS=['real','rev','shuf','cross','noise']
out={}
print("=== 梦：gain 相对 none（正=更好），* = CI不跨0 ===")
for p in ['stable','drift','square']:
    base=[run3(D[p][s],'none',False,s) for s in range(8)]
    row=[]
    for c in CONDS:
        v=[run3(D[p][s],c,False,s,other=D[p][(s+4)%8]) for s in range(8)]
        g=[b-a for b,a in zip(base,v)]
        m,lo,hi=ci(g); out[f"{p}|{c}"]=dict(mae=float(np.mean(v)),gain=float(m),lo=float(lo),hi=float(hi))
        row.append(f"{c}{m:+.4f}[{lo:+.3f},{hi:+.3f}]{'*' if (lo>0 or hi<0) else ''}")
    print(f"{p:7s} none={np.mean(base):.4f} | "+"  ".join(row))
json.dump(out, open('res148c.json','w'), indent=1)
