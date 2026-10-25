import math,json
from collections import Counter,defaultdict
exec(open('run195.py').read().split('BMAPS =')[0])
def run_on(txt,name):
    n=len(txt); ntr=int(n*0.8); tr,te=txt[:ntr],txt[ntr:]
    freq=Counter(tr); tot=sum(freq.values())
    order=[c for c,_ in freq.most_common()]; V=len(freq)
    global P_UNI,P_UNK,VOCAB
    VOCAB=list(freq); P_UNI={c:(freq[c]+ALPHA_U)/(tot+ALPHA_U*(V+1)) for c in VOCAB}
    P_UNK=ALPHA_U/(tot+ALPHA_U*(V+1))
    def mb(A):
        m,acc,b={},0.0,0
        for c in order:
            m[c]=min(b,A-1); acc+=freq[c]/tot
            while b<A-1 and acc>=(b+1)/A: b+=1
        return m
    res=[]
    bm=mb(V)
    for k in range(1,7):
        e=Eye(bm,V,k); e.fit(tr)
        s=0.0; hist=list(tr)
        for c in te:
            s-=math.log2(max(e.prob(hist,c),P_UNK)); hist.append(c)
        b=s/len(te); res.append({"k":k,"bits":round(b,4)})
        print(f"{name} N={n} V={V} k={k} bits={b:.4f}")
    best=min(res,key=lambda r:r["bits"])
    pred=math.log(n)/math.log(V) if V>1 else 0
    print(f"{name}: 最优 k*={best['k']} (161号预测 log N/log V = {pred:.2f})")
    return {"name":name,"N":n,"V":V,"curve":res,"kstar":best["k"],"pred_k":round(pred,2)}
r1=run_on(open('/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt',encoding='utf-8').read(),"用户语料")
core=open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md',encoding='utf-8').read()
r2=run_on(core,"判据核")
json.dump([r1,r2],open('scale195.json','w'),ensure_ascii=False,indent=2)
print("saved")
