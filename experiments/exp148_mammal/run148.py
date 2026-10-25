import json, math
import numpy as np

D=json.load(open('real_series.json'))
LAG=3

def feats(x, i, mu, sd):
    if i < LAG: return None
    f=[1.0]+[ (x[i-1-k]-mu)/sd for k in range(LAG)]
    return np.asarray(f)

def update(w, f, y, lr, clip=5.0):
    e = float(np.dot(w,f) - y)
    g = e*f
    gn = float(np.linalg.norm(g))
    if gn > clip: g = g*clip/gn
    w = w - lr*g
    return w, e

def run(seq, dream='none', gate=False, seed=0, lr0=0.03, k=3.0, dream_rounds=3):
    rng=np.random.default_rng(seed)
    x=np.asarray(seq); N=len(x); half=N//2
    # 归一化参数：仅用白天段估计（无未来泄漏）
    mu=float(x[:half].mean()); sd=float(x[:half].std())+1e-9
    w=np.zeros(LAG+1)
    # ---------- 白天 ----------
    buf=[]; errs=[]
    lr=lr0
    hist_e=[]
    for i in range(LAG, half):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        w,e=update(w,f,y,lr)
        buf.append((f.copy(), y)); errs.append(abs(e)); hist_e.append(abs(e))
        if gate:
            base=np.mean(hist_e) if hist_e else 1.0
            rel=abs(e)/(base+1e-9)
            lr=lr0*(1.0+k*min(rel-1.0, 2.0)) if rel>1.0 else lr0*(1.0-0.3*(1.0-rel))
            lr=float(np.clip(lr, lr0*0.2, lr0*5.0))
    if not np.isfinite(w).all(): return float('nan')
    # ---------- 睡眠 ----------
    if dream!='none' and dream_rounds>0:
        if dream=='real':      order=list(range(len(buf)))
        elif dream=='shuf':    order=list(rng.permutation(len(buf)))
        elif dream=='noise':   order=None
        for _ in range(dream_rounds):
            if dream=='noise':
                arr=np.asarray([b[1] for b in buf])
                m_,s_=float(arr.mean()), float(arr.std())+1e-9
                ys=rng.normal(m_, s_, size=len(buf))
                for j,(f,_) in enumerate(buf):
                    w=update(w,f,float(ys[j]),lr0)[0]
            else:
                for j in order:
                    f,y=buf[j]; w=update(w,f,y,lr0)[0]
        if not np.isfinite(w).all(): return float('nan')
    # ---------- 测试 ----------
    te=[]; hist_e2=list(errs[-20:])
    lr=lr0
    for i in range(half, N):
        f=feats(x,i,mu,sd); y=(x[i]-mu)/sd
        yh=float(np.dot(w,f)); te.append(abs(yh-y))
        w,e=update(w,f,y,lr)
        hist_e2.append(abs(e))
        if gate:
            base=np.mean(hist_e2[-50:]) if hist_e2 else 1.0
            rel=abs(e)/(base+1e-9)
            lr=lr0*(1.0+k*min(rel-1.0,2.0)) if rel>1.0 else lr0*(1.0-0.3*(1.0-rel))
            lr=float(np.clip(lr, lr0*0.2, lr0*5.0))
    # baseline: predict last
    bl=[abs(x[i]-x[i-1])/sd for i in range(half,N)]
    return float(np.mean(te)), float(np.mean(bl))

if __name__=='__main__':
    # sanity
    for p in ['stable','drift','square']:
        row=[]
        for d in ['none','real','shuf','noise']:
            v=[run(D[p][s], dream=d, gate=False, seed=s) for s in range(8)]
            m=np.mean([a for a,b in v]); row.append(f"{d}={m:.4f}")
        bl=np.mean([run(D[p][s], dream='none', seed=s)[1] for s in range(8)])
        print(p, " ".join(row), f"| baseline_last={bl:.4f}")
    print("--- gate check ---")
    for p in ['stable','drift','square']:
        a=[run(D[p][s], dream='none', gate=True, seed=s)[0] for s in range(8)]
        b=[run(D[p][s], dream='none', gate=False, seed=s)[0] for s in range(8)]
        d=np.asarray(b)-np.asarray(a)
        print(p, f"gate={np.mean(a):.4f} fixed={np.mean(b):.4f} gain={d.mean():+.4f}")
