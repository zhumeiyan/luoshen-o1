import json, math
import numpy as np
exec(open('run148.py').read().split("if __name__")[0])

def ci(d):
    d=np.asarray(d,float); n=len(d); m=d.mean()
    se=d.std(ddof=1)/math.sqrt(n) if n>1 else float('nan')
    return m, m-1.96*se, m+1.96*se

# 扩展 dream：rev（逆序重放，对应海马反向重放）
def run2(seq, dream='none', gate=False, seed=0, lr0=0.03, k=3.0, rounds=3):
    rng=np.random.default_rng(seed)
    x=np.asarray(seq); N=len(x); half=N//2
    mu=float(x[:half].mean()); sd=float(x[:half].std())+1e-9
    w=np.zeros(LAG+1); buf=[]; hist=[]
    lr=lr0
    for i in range(LAG, half):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        w,e=update(w,f,y,lr); buf.append((f.copy(),y)); hist.append(abs(e))
        if gate: lr=_gate(lr0,abs(e),np.mean(hist),k)
    if not np.isfinite(w).all(): return float('nan')
    if dream!='none':
        idx=list(range(len(buf)))
        if dream=='real': order=idx
        elif dream=='rev': order=idx[::-1]
        elif dream=='shuf': order=list(rng.permutation(len(buf)))
        elif dream=='noise': order=None
        for _ in range(rounds):
            if dream=='noise':
                arr=np.asarray([b[1] for b in buf]); m_,s_=arr.mean(),arr.std()+1e-9
                ys=rng.normal(m_,s_,size=len(buf))
                for j,(f,_) in enumerate(buf): w=update(w,f,float(ys[j]),lr0)[0]
            else:
                for j in order:
                    f,y=buf[j]; w=update(w,f,y,lr0)[0]
        if not np.isfinite(w).all(): return float('nan')
    te=[]; hist2=list(hist[-20:]); lr=lr0
    for i in range(half,N):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        te.append(abs(float(np.dot(w,f))-y))
        w,e=update(w,f,y,lr); hist2.append(abs(e))
        if gate: lr=_gate(lr0,abs(e),np.mean(hist2[-50:]),k)
    return float(np.mean(te))

def _gate(lr0, e, base, k):
    rel=e/(base+1e-9)
    v=lr0*(1.0+k*min(rel-1.0,2.0)) if rel>1.0 else lr0*(1.0-0.3*(1.0-rel))
    return float(np.clip(v, lr0*0.2, lr0*5.0))

D=json.load(open('real_series.json'))
CONDS=['none','real','rev','shuf','noise']
print("=== 梦：测试期 MAE（越低越好），相对 none 的增益 ===")
res={}
for p in ['stable','drift','square']:
    base=[run2(D[p][s],'none',False,s) for s in range(8)]
    line=[]
    for c in CONDS:
        v=[run2(D[p][s],c,False,s) for s in range(8)]
        g=[b-a for b,a in zip(base,v)]
        m,lo,hi=ci(g); res[(p,c)]=(float(np.mean(v)),float(m),float(lo),float(hi))
        flag='*' if (lo>0 or hi<0) else ' '
        line.append(f"{c}:{np.mean(v):.4f}(gain{m:+.4f}[{lo:+.3f},{hi:+.3f}]){flag}")
    print(f"{p:7s} none={np.mean(base):.4f} | "+" ".join(line))
print()
print("=== 情绪门：gate - fixed 的增益（正=gate更好）===")
for p in ['stable','drift','square']:
    a=[run2(D[p][s],'none',True,s) for s in range(8)]
    b=[run2(D[p][s],'none',False,s) for s in range(8)]
    g=[y-x for x,y in zip(a,b)]
    m,lo,hi=ci(g); flag='*' if (lo>0 or hi<0) else ' '
    print(f"{p:7s} gate={np.mean(a):.4f} fixed={np.mean(b):.4f} gain={m:+.4f}[{lo:+.3f},{hi:+.3f}]{flag}")
json.dump({f"{k[0]}|{k[1]}":v for k,v in res.items()}, open('res148b.json','w'), indent=1)
