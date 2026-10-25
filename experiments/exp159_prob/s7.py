import json,math,random,re
from collections import Counter
rows=[l.strip() for l in open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md',encoding='utf-8') if l.strip()]
rows=[r for r in rows if len(r)>12][:2400]
rng=random.Random(7); rng.shuffle(rows)
lab=[1 if re.search(r'\d+\.\d+|\d+%',r) else 0 for r in rows]
N=len(rows)
H=-(0.234*math.log(0.234)+0.766*math.log(0.766))
tok=lambda s: re.findall(r'[A-Za-z_]+|\d+\.?\d*|[^\sA-Za-z0-9]',s)
T=[tok(r) for r in rows]
REPS={'unigram':lambda t:Counter(t),'bigram':lambda t:Counter(zip(t,t[1:])),
      'first':lambda t:Counter([('F',t[0])] if t else []),'len':lambda t:Counter([('L',len(t)//10)])}
def MI_mm(labels,keys):
    py=Counter(labels); kx=Counter(keys); joint=Counter(zip(labels,keys))
    mi=0.0
    for (y,k),c in joint.items():
        p=c/N; q=py[y]/N*kx[k]/N
        mi+=p*math.log(p/q)
    R=len(kx); S=len(py)
    bias=(R-1)*(S-1)/(2*N)          # Miller-Madow 偏差校正
    return mi, mi-bias, R
def disc(labels,keys,seed=1):
    r=random.Random(seed); idx=list(range(len(labels))); r.shuffle(idx)
    cut=int(0.7*N); tr,te=idx[:cut],idx[cut:]
    tot=Counter(labels[i] for i in tr); pri={}
    for i in tr: pri.setdefault(labels[i],Counter())[keys[i]]+=1
    V=len(set(keys)); tp=fp=tn=fn=0
    for i in te:
        sc={y: math.log(tot[y]/len(tr))+math.log((pri[y][keys[i]]+0.5)/(tot[y]+0.5*V)) for y in tot}
        p=max(sc,key=sc.get)
        if p==1 and labels[i]==1: tp+=1
        elif p==1 and labels[i]==0: fp+=1
        elif p==0 and labels[i]==0: tn+=1
        else: fn+=1
    tpr=tp/(tp+fn) if tp+fn else 0; fpr=fp/(fp+tn) if fp+tn else 0
    return abs(tpr-fpr)
print("H(label)=%.4f   N=%d\n"%(H,N))
print("%-8s %8s %8s %8s %6s %8s"%("表示","MI原","MI校正","偏差项","取值数","判别度"))
out=[]
for n_,f in REPS.items():
    keys=[tuple(sorted(f(t).items())) for t in T]
    mi,mm,R=MI_mm(lab,keys); d=disc(lab,keys)
    out.append(dict(rep=n_,mi=mi,mi_mm=mm,R=R,disc=d))
    print("%-8s %8.4f %8.4f %8.4f %6d %8.4f"%(n_,mi,mm,mi-mm,R,d))
def rank(v):
    s=sorted(range(len(v)),key=lambda i:-v[i]); r=[0]*len(v)
    for p,i in enumerate(s): r[i]=p+1
    return r
for k in ['mi','mi_mm']:
    rm=rank([o[k] for o in out]); rd=rank([o['disc'] for o in out])
    n=len(out); d2=sum((a-b)**2 for a,b in zip(rm,rd)); rho=1-6*d2/(n*(n*n-1))
    print("\nSpearman(%s, 判别度) = %+.3f"%(k,rho))
json.dump(out,open('s7.json','w'),indent=1)
