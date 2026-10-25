import json,math,random
from collections import Counter,defaultdict
random.seed(7)
BASE='/data/workspace/luoshen-o1'
def load(p):
    try: return open(p,encoding='utf-8',errors='ignore').read()
    except Exception: return ''
raw=load(BASE+'/experiments/exp180_record/u_side_full.txt') or load(BASE+'/experiments/exp175_align/u_side.txt')

def metrics(s,k=2,train=0.7):
    n=len(s);cut=int(n*train);tr,te=s[:cut],s[cut:]
    ctx=defaultdict(Counter)
    for i in range(len(tr)-k): ctx[tr[i:i+k]][tr[i+k]]+=1
    tot=Counter(tr[i+k] for i in range(len(tr)-k))
    hit=0;toto=0;surp=[]
    for i in range(len(te)-k):
        c=te[i:i+k];nx=te[i+k];d=ctx.get(c)
        if d: p=d.most_common(1)[0][0];pr=d[nx]/sum(d.values())
        else: p=tot.most_common(1)[0][0];pr=1e-6
        hit+=(p==nx);toto+=1;surp.append(-math.log2(max(pr,1e-9)))
    acc=hit/max(1,toto); base=tot.most_common(1)[0][1]/max(1,sum(tot.values()))
    def ac(x,lag=1):
        m=len(x)
        if m<10: return 0.0
        mu=sum(x)/m
        return sum((x[i]-mu)*(x[i+lag]-mu) for i in range(m-lag))/ (sum((v-mu)**2 for v in x) or 1)
    # novelty decay
    g3=[s[i:i+3] for i in range(len(s)-3)];seen=set();nv=[]
    B=len(g3)//10 or 1
    for b in range(10):
        ch=g3[b*B:(b+1)*B]
        if not ch: break
        nv.append(sum(1 for g in ch if g not in seen)/len(ch))
        for g in ch: seen.add(g)
    return {'pred':round(acc,4),'lift':round(acc-base,4),'autocorr':round(ac(surp),4),
            'nv_decay':round(nv[-1]/nv[0],4) if nv and nv[0]>0 else None}

out={}
out['repeat_x1']=metrics(raw)
for r in (2,4,8):
    out[f'repeat_x{r}']=metrics(raw*r)
# 打乱（破坏时间结构，保留字符分布）
L=list(raw); random.shuffle(L)
out['shuffled']=metrics(''.join(L))
print(json.dumps(out,ensure_ascii=False,indent=2))
json.dump(out,open('result183b.json','w'),ensure_ascii=False,indent=2)
