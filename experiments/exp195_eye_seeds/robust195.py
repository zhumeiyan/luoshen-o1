import json,math,random,statistics
from collections import Counter,defaultdict
exec(open('run195.py').read().split('BMAPS =')[0])
# --- 重建近眼/远眼 ---
def make_bucket(A,order,freq,tot):
    m,acc,b={},0.0,0
    for c in order:
        m[c]=min(b,A-1); acc+=freq[c]/tot
        while b<A-1 and acc>=(b+1)/A: b+=1
    return m
V=len(VOCAB)
NEAR=Eye(make_bucket(V,order,freq,tot),V,1); NEAR.fit(tr)
FAR=Eye(make_bucket(8,order,freq,tot),8,4); FAR.fit(tr)
def seq_probs(eye):
    out,hist=[],list(tr)
    for c in te:
        out.append(eye.pdist(hist)); hist.append(c)
    return out
pn,pf=seq_probs(NEAR),seq_probs(FAR)
def js(p,q):
    keys=set(p)|set(q); s=0.0
    for c in keys:
        a,b=max(p.get(c,P_UNK),1e-12),max(q.get(c,P_UNK),1e-12); m=.5*(a+b)
        s+=.5*a*math.log2(a/m)+.5*b*math.log2(b/m)
    return s
div=[js(pn[i],pf[i]) for i in range(len(te))]
out=[]
for x in [5,10,20,30,50,70]:
    m=int(len(te)*x/100)
    top=set(sorted(range(len(te)),key=lambda i:-div[i])[:m])
    d=sum(-math.log2(max((pn[i] if i in top else pf[i]).get(te[i],P_UNK),P_UNK)) for i in range(len(te)))/len(te)
    acc=[]
    for _ in range(300):
        rnd=set(random.sample(range(len(te)),m))
        acc.append(sum(-math.log2(max((pn[i] if i in rnd else pf[i]).get(te[i],P_UNK),P_UNK)) for i in range(len(te)))/len(te))
    mu,sd=statistics.mean(acc),statistics.pstdev(acc)
    z=(mu-d)/sd if sd else 0
    out.append({"x":x,"dyn":round(d,4),"rand_mu":round(mu,4),"rand_sd":round(sd,4),"gain":round(mu-d,4),"z":round(z,2)})
    print(f"x={x:2d}%  dyn={d:.4f}  rand={mu:.4f}±{sd:.4f}  gain={mu-d:+.4f}  z={z:.2f}")
json.dump(out,open('robust195.json','w'),ensure_ascii=False,indent=2)
