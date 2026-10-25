import json, math, collections, os
SRC="/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt"
raw=open(SRC,encoding="utf-8",errors="ignore").read()
# keep only non-empty lines (user turns)
seq="\n".join([l.strip() for l in raw.splitlines() if l.strip()])
n=len(seq); cut=int(n*0.8)
tr,te=seq[:cut],seq[cut:]
print("chars total",n,"train",len(tr),"test",len(te))

uni=collections.Counter(tr); N=sum(uni.values()); V=len(uni)
bi=collections.Counter(zip(tr,tr[1:]))
biprev=collections.Counter(tr[:-1])
EPS=1e-9
logN=math.log(N)

def lp_uni(c): return math.log((uni[c]+0.5)/(N+0.5*V))
def lp_bi(a,b):
    # interpolated bigram
    pbi=(bi[(a,b)]+0.5)/(biprev[a]+0.5*V)
    return math.log(0.8*pbi+0.2*math.exp(lp_uni(b)))

# surprise = total extra info carried by this transition, vs unigram
surp={}
for (a,b),c in bi.items():
    if c<2: continue
    pbi=(bi[(a,b)]+0.5)/(biprev[a]+0.5*V)
    pu=math.exp(lp_uni(b))
    surp[(a,b)]=c*math.log((0.8*pbi+0.2*pu)/pu)
ranked=sorted(surp.items(),key=lambda kv:-kv[1])
print("total transitions",len(bi),"with count>=2 and modeled",len(ranked))

def evaluate(keep):
    """keep = set of transitions to model as bigram; others fall back to unigram"""
    correct=0; tot=0; ll=0.0
    for i in range(len(te)):
        ctx = tr[-1] if i==0 else te[i-1]
        c = te[i]
        if (ctx,c) in keep:
            lp=lp_bi(ctx,c)
        else:
            lp=lp_uni(c)
        ll+=lp; tot+=1
        # top1: compare with best alternative
        if (ctx,c) in keep:
            best=max(uni,key=lambda x: lp_bi(ctx,x)-1e9*0) if False else None
        # approximate top-1 by scoring full alphabet under the same rule
        # (cheap: restrict to observed chars)
        bestc=None;bestv=-1e18
        for x in uni:
            v = lp_bi(ctx,x) if (ctx,x) in keep else lp_uni(x)
            if v>bestv: bestv=v;bestc=x
        if bestc==c: correct+=1
    return correct/tot, -ll/tot

# baseline: pure summary (unigram only, no transition retained)
acc_sum,ce_sum = evaluate(set())
print("SUMMARY(unigram only): acc=%.4f bits=%.4f"%(acc_sum,ce_sum))
# full: all modeled transitions
allkeep=set(k for k,_ in ranked)
acc_full,ce_full = evaluate(allkeep)
print("FULL(all transitions): acc=%.4f bits=%.4f"%(acc_full,ce_full))

curve=[]
for Nk in [0,1,2,3,5,10,20,50,100,200,400,800,len(ranked)]:
    keep=set(k for k,_ in ranked[:Nk])
    a,c=evaluate(keep)
    # fraction of full-surprise mass retained
    mass=sum(v for _,v in ranked[:Nk])/sum(v for _,v in ranked) if ranked else 0
    curve.append({"negate_topN":Nk,"acc":a,"bits":c,"surprise_mass":mass})
    print("negate N=%5d acc=%.4f bits=%.4f mass=%.3f"%(Nk,a,c,mass))

json.dump({"n_chars":n,"train":len(tr),"test":len(te),"V":V,
           "summary_acc":acc_sum,"summary_bits":ce_sum,
           "full_acc":acc_full,"full_bits":ce_full,
           "n_ranked":len(ranked),"curve":curve},
          open("/data/workspace/luoshen-o1/experiments/exp177_sumneg/result177.json","w"),
          ensure_ascii=False,indent=1)
print("WROTE")
