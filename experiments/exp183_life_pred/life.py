import json, random, math, glob, os, hashlib
from collections import Counter, defaultdict
random.seed(42)
BASE='/data/workspace/luoshen-o1'
def load(p):
    try: return open(p,encoding='utf-8',errors='ignore').read()
    except Exception: return ''
def find(pat):
    g=glob.glob(pat); return g[0] if g else ''
src={}
src['human_你']=load(find(BASE+'/experiments/exp180_record/u_side_full.txt')) or load(find(BASE+'/experiments/exp175_align/u_side.txt'))
src['ai_判据核']=load(find(BASE+'/evidence/失败模式库/判据核.md'))
src['code']=load(find(BASE+'/experiments/exp182_forget/*.py')) or load(find(BASE+'/experiments/*/*.py'))
src['english']=("In the beginning there was nothing, which exploded. "
 "Time is an illusion, lunchtime doubly so. "
 "The answer to the great question of life the universe and everything is forty two. "
 "I have always thought that the actions of men are the best interpreters of their thoughts. "
 "Language is the road map of a culture it tells you where its people come from and where they are going. ")*40
src['periodic_死']='abcdefgh'*1500
src['noise_死']=''.join(random.choice('abcdefghijklmnopqrstuvwxyz ') for _ in range(12000))
_d='0';_s=''
for _i in range(400):
    _d=hashlib.sha256(_d.encode()).hexdigest(); _s+=_d
src['digits_hash']=_s[:12000]
src={k:v for k,v in src.items() if len(v)>200}

def predict_acc(s,k=2,train=0.7):
    n=len(s); cut=int(n*train); tr,te=s[:cut],s[cut:]
    if len(te)<50: return None,None
    ctx=defaultdict(Counter)
    for i in range(len(tr)-k): ctx[tr[i:i+k]][tr[i+k]]+=1
    tot=Counter(tr[i+k] for i in range(len(tr)-k))
    hit=0;toto=0;surp=[]
    for i in range(len(te)-k):
        c=te[i:i+k]; nx=te[i+k]; d=ctx.get(c)
        if d:
            p=d.most_common(1)[0][0]; pr=d[nx]/sum(d.values())
        else:
            p=tot.most_common(1)[0][0]; pr=1e-6
        hit+=(p==nx); toto+=1; surp.append(-math.log2(max(pr,1e-9)))
    acc=hit/toto if toto else 0
    base=tot.most_common(1)[0][1]/max(1,sum(tot.values()))
    return acc,base,surp

def novelty(s,k=3,blocks=10):
    gs=[s[i:i+k] for i in range(len(s)-k)]
    seen=set(); out=[]; B=len(gs)//blocks
    if B<2: return []
    for b in range(blocks):
        ch=gs[b*B:(b+1)*B]
        if not ch: break
        new=sum(1 for g in ch if g not in seen)
        for g in ch: seen.add(g)
        out.append(new/len(ch))
    return out

def autocorr(x,lag=1):
    n=len(x)
    if n<10: return 0.0
    mu=sum(x)/n
    num=sum((x[i]-mu)*(x[i+lag]-mu) for i in range(n-lag))
    den=sum((v-mu)**2 for v in x)
    return num/den if den>0 else 0.0

res={}
for name,s in src.items():
    acc,base,surp=predict_acc(s,k=2)
    if acc is None: continue
    nv=novelty(s,k=3)
    res[name]={'len':len(s),'pred_acc':round(acc,4),'baseline':round(base,4),
      'lift':round(acc-base,4),
      'mean_surprise':round(sum(surp)/len(surp),4),
      'surprise_autocorr':round(autocorr(surp),4),
      'novelty_first':round(nv[0],4) if nv else None,
      'novelty_last':round(nv[-1],4) if nv else None,
      'novelty_decay':round(nv[-1]/nv[0],4) if nv and nv[0]>0 else None}
json.dump(res,open('result183.json','w'),ensure_ascii=False,indent=2)
print(json.dumps(res,ensure_ascii=False,indent=2))
print("\n--- sorted by pred_acc ---")
for k,v in sorted(res.items(),key=lambda x:x[1]['pred_acc']):
    print(f"{k:14s} pred={v['pred_acc']:.4f} lift={v['lift']:+.4f} autocorr={v['surprise_autocorr']:+.4f} nv_decay={v['novelty_decay']}")
