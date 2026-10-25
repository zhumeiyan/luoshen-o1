import numpy as np, json, os
from collections import defaultdict

rng = np.random.default_rng(42)
N = 20000; V = 10
OUT = "/data/workspace/luoshen-o1/experiments/exp185_phi_ladder"

def quantize(x, V=10):
    qs = np.quantile(x, np.linspace(0,1,V+1)[1:-1])
    return np.digitize(x, qs)

def ou(n, tau=20, sd=0.5):
    x=np.zeros(n); e=rng.normal(0,sd,n)
    for i in range(1,n): x[i]=x[i-1]*(1-1/tau)+e[i]
    return x
def rhythm(n,f=0.05,sd=0.3):
    t=np.arange(n); return np.sin(2*np.pi*f*t)+rng.normal(0,sd,n)
def vdp(n,mu=1.0,dt=0.1,sd=0.05):
    x=np.zeros(n); v=np.zeros(n); x[0]=1.0
    e=rng.normal(0,sd,n)
    for i in range(1,n):
        dx=v[i-1]; dv=mu*(1-x[i-1]**2)*v[i-1]-x[i-1]
        x[i]=x[i-1]+dx*dt+e[i]*0.1; v[i]=v[i-1]+dv*dt
    return x
def feedback(n):
    x=np.zeros(n); e=rng.normal(0,0.3,n)
    for i in range(3,n): x[i]=1.2*x[i-1]-0.6*x[i-2]+0.3*x[i-3]+e[i]
    return x
def heritage(n):
    x=np.zeros(n); e=rng.normal(0,0.3,n); P=97
    for i in range(3,n):
        x[i]=1.1*x[i-1]-0.5*x[i-2]+e[i]
        if i%P==0: x[i]+=0.8*x[max(0,i-P)]
    return x

layers = {
 "L0_涨落(白噪声)": rng.normal(0,1,N),
 "L1_惯性(OU)": ou(N),
 "L2_节律(正弦)": rhythm(N),
 "L3_自持(极限环)": vdp(N),
 "L4_感知(反馈AR3)": feedback(N),
 "L5_传承(二阶+回放)": heritage(N),
}

def markov_acc(seq,k,train_frac=0.8):
    n=len(seq); ntr=int(n*train_frac); tr,te=seq[:ntr],seq[ntr:]
    ctx=defaultdict(lambda: defaultdict(float))
    for i in range(k,len(tr)): ctx[tuple(tr[i-k:i])][tr[i]]+=1
    correct=0.0; tot=0
    for i in range(k,len(te)):
        c=tuple(te[i-k:i]); tot+=1
        if c in ctx:
            pred=max(ctx[c],key=ctx[c].get); correct+= (pred==te[i])
        else: correct+=1.0/V
    return correct/tot if tot else 0.0

def shuf_acc(seq,k,seed=0):
    r=np.random.default_rng(seed); s=seq.copy(); r.shuffle(s)
    return markov_acc(s,k)

res={}
for name,sig in layers.items():
    q=quantize(sig,V)
    accs={k:markov_acc(q,k) for k in range(1,8)}
    shuf={k:shuf_acc(q,k,seed=k) for k in range(1,8)}
    bk=max(accs,key=accs.get)
    res[name]={"acc":{str(k):round(accs[k],5) for k in accs},
               "shuffled":{str(k):round(shuf[k],5) for k in shuf},
               "best_k":bk,"best_acc":round(accs[bk],5),
               "lift":round(accs[bk]-shuf[bk],5)}
    print(f"{name:22s} best_k={bk} acc={accs[bk]:.4f} lift={res[name]['lift']:+.4f}")
    print("     ", {k:round(accs[k],4) for k in accs})
    print("     理论k*=log(16000)/log(10)=", round(np.log(16000)/np.log(V),3))
json.dump(res,open(OUT+"/result185.json","w"),indent=2,ensure_ascii=False)
print("saved", OUT)
