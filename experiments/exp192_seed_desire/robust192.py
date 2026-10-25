# -*- coding: utf-8 -*-
"""192 稳健性：配对符号检验 + 降低平滑常数看信号是否稳"""
import json, math, random, re, hashlib, itertools
exec(open("/data/workspace/luoshen-o1/experiments/exp192_seed_desire/run192b.py").read().split("SEEDS=[11")[0])
SEEDS=[11,22,33,44,55,66,77,88,99,111]
SMOOTH=[0.5,0.1,0.02]
FR=[0.1,0.2,0.3,0.5]
W=20; K=3
V_all=set("".join(msgs))
out={}
for sm in SMOOTH:
    def prob2(cnt,cctx,V,ctx,ch,K):
        p=None
        for j in range(K,0,-1):
            c=ctx[-(j-1):] if j>1 else ""
            nc=cctx[j].get(c,0); npr=cnt[j].get((j,c,ch),0); Vj=max(len(V),1)
            pj=(npr+sm)/(nc+sm*Vj)
            p=pj if p is None else (nc/(nc+1.0))*pj+(1-nc/(nc+1.0))*p
        return p
    def bits2(train,test,V,K):
        cnt,cctx=build(train,K); b=0.0
        for i in range(len(test)):
            b+=-math.log2(max(prob2(cnt,cctx,V,test[max(0,i-K+1):i],test[i],K),1e-12))
        return b/len(test)
    tally={}
    for B in FR: tally[str(B)]={"surprise-vs-random":[], "desire-vs-random":[], "easy-vs-random":[]}
    agg={}
    for sd in SEEDS:
        r=random.Random(sd); idx=list(range(len(msgs))); r.shuffle(idx)
        nt=max(1,int(len(idx)*0.4)); test_i=sorted(idx[:nt]); train_i=idx[nt:]
        test_txt="".join(msgs[i] for i in test_i); train_txt="".join(msgs[i] for i in train_i)
        wins=[train_txt[i:i+W] for i in range(0,len(train_txt),W) if len(train_txt[i:i+W])>=5]
        nw=len(wins)
        st=train_txt[:max(50,int(len(train_txt)*0.10))]
        cnt,cctx=build(st,K); sc=[]
        for w in wins:
            b=0.0
            for i in range(len(w)):
                b+=-math.log2(max(prob2(cnt,cctx,V_all,w[max(0,i-K+1):i],w[i],K),1e-12))
            sc.append(b/len(w))
        for B in FR:
            nb=max(1,int(nw*B)); rr=random.Random(sd*13+int(B*100))
            o=list(range(nw)); rr.shuffle(o); o=o[:nb]
            v_rand=bits2("".join(wins[i] for i in o),test_txt,V_all,K)
            od=sorted(range(nw),key=lambda i:-dscore(wins[i])/max(len(wins[i]),1))[:nb]
            v_des=bits2("".join(wins[i] for i in od),test_txt,V_all,K)
            os_=sorted(range(nw),key=lambda i:-sc[i])[:nb]
            v_sur=bits2("".join(wins[i] for i in os_),test_txt,V_all,K)
            ol=sorted(range(nw),key=lambda i:sc[i])[:nb]
            v_easy=bits2("".join(wins[i] for i in ol),test_txt,V_all,K)
            for nm,v in [("surprise-vs-random",v_sur-v_rand),("desire-vs-random",v_des-v_rand),("easy-vs-random",v_easy-v_rand)]:
                tally[str(B)][nm].append(v)
            agg.setdefault(str(B),{"random":[],"desire":[],"surprise":[],"easy":[]})
            agg[str(B)]["random"].append(v_rand); agg[str(B)]["desire"].append(v_des)
            agg[str(B)]["surprise"].append(v_sur); agg[str(B)]["easy"].append(v_easy)
    out[str(sm)]={"mean":{B:{k:sum(v)/len(v) for k,v in agg[B].items()} for B in agg},
                  "sign":{B:{k:(sum(1 for x in v if x<0),len(v)) for k,v in tally[B].items()} for B in tally}}
    print(f"\n### 平滑={sm}")
    for B in FR:
        m=out[str(sm)]["mean"][str(B)]; s=out[str(sm)]["sign"][str(B)]
        print(f" B={B}: random={m['random']:.4f} desire={m['desire']:.4f} surprise={m['surprise']:.4f} easy={m['easy']:.4f}")
        for nm,(neg,n) in s.items():
            print(f"        {nm:20s} 负(更好) {neg}/{n}")
json.dump(out,open("/data/workspace/luoshen-o1/experiments/exp192_seed_desire/robust192.json","w"),ensure_ascii=False,indent=1)
print("\n[sha]",hashlib.sha256(open("/data/workspace/luoshen-o1/experiments/exp192_seed_desire/robust192.json",'rb').read()).hexdigest()[:12])
