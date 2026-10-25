import json, math, collections, random
SRC="/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt"
raw=open(SRC,encoding="utf-8",errors="ignore").read()
seq="\n".join([l.strip() for l in raw.splitlines() if l.strip()])
n=len(seq); cut=int(n*0.8); tr,te=seq[:cut],seq[cut:]
uni=collections.Counter(tr); N=sum(uni.values()); V=len(uni)
bi=collections.Counter(zip(tr,tr[1:])); biprev=collections.Counter(tr[:-1])
def lp_uni(c): return math.log((uni[c]+0.5)/(N+0.5*V))
def lp_bi(a,b):
    pbi=(bi[(a,b)]+0.5)/(biprev[a]+0.5*V)
    return math.log(0.8*pbi+0.2*math.exp(lp_uni(b)))
# only POSITIVE-surprise transitions (those that actually contradict the summary)
surp={}
for (a,b),c in bi.items():
    if c<2: continue
    pbi=(bi[(a,b)]+0.5)/(biprev[a]+0.5*V); pu=math.exp(lp_uni(b))
    s=c*math.log((0.8*pbi+0.2*pu)/pu)
    if s>0: surp[(a,b)]=s
ranked=sorted(surp.items(),key=lambda kv:-kv[1])
TOT=sum(v for _,v in ranked)
print("positive-surprise transitions:",len(ranked),"total mass %.3f"%TOT)

def bits(keep):
    ll=0.0;tot=0
    for i in range(len(te)):
        ctx = tr[-1] if i==0 else te[i-1]; c=te[i]
        ll += lp_bi(ctx,c) if (ctx,c) in keep else lp_uni(c); tot+=1
    return -ll/tot
def acc(keep):
    ok=0;tot=0
    for i in range(len(te)):
        ctx = tr[-1] if i==0 else te[i-1]; c=te[i]
        bv=-1e18;bc=None
        for x in uni:
            v = lp_bi(ctx,x) if (ctx,x) in keep else lp_uni(x)
            if v>bv: bv=v;bc=x
        ok+= (bc==c); tot+=1
    return ok/tot

sum_bits=bits(set()); full_all=set(bi.keys()); full_bits=bits(full_all)
print("SUMMARY  bits=%.4f"%sum_bits)
print("FULL-ALL bits=%.4f  (every transition, incl. negative-surprise)"%full_bits)
best=bits(set(k for k,_ in ranked))
print("SEL-FULL bits=%.4f  (only positive-surprise)"%best)

grid=[0,1,2,3,5,8,12,20,30,50,80,120,180,250,len(ranked)]
curve=[]
for Nk in grid:
    keep=set(k for k,_ in ranked[:Nk])
    m=sum(v for _,v in ranked[:Nk])/TOT
    curve.append({"N":Nk,"bits":bits(keep),"acc":acc(keep),"mass":round(m,3)})
    print("N=%4d  bits=%.4f  acc=%.4f  mass=%.3f"%(Nk,curve[-1]["bits"],curve[-1]["acc"],m))

# random-negation control at matched N
rnd={}
random.seed(7)
for Nk in [5,20,50,120,250]:
    vals=[]
    for _ in range(5):
        keep=set(random.sample(list(surp.keys()),min(Nk,len(surp))))
        vals.append(bits(keep))
    rnd[Nk]=sum(vals)/len(vals)
    print("random N=%3d bits=%.4f"%(Nk,rnd[Nk]))
json.dump({"n_chars":n,"train":len(tr),"test":len(te),"V":V,
  "summary_bits":sum_bits,"full_all_bits":full_bits,"selective_full_bits":best,
  "n_pos":len(ranked),"curve":curve,"random_control":rnd},
  open("/data/workspace/luoshen-o1/experiments/exp177_sumneg/result177b.json","w"),ensure_ascii=False,indent=1)
print("WROTE b")
