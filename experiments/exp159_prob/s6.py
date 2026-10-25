import json,math,random,re
from collections import Counter
# 真语料：判据核真实行
rows=[l.strip() for l in open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md',encoding='utf-8') if l.strip()]
rows=[r for r in rows if len(r)>12][:2400]
rng=random.Random(7); rng.shuffle(rows)
# 真实二分类标签：该行是否含数字指标（判据核里"有量化指标"的行 vs 纯叙述行）
lab=[1 if re.search(r'\d+\.\d+|\d+%',r) else 0 for r in rows]
print("真语料 %d 行，正例率 %.3f"%(len(rows),sum(lab)/len(lab)))
tok=lambda s: re.findall(r'[A-Za-z_]+|\d+\.?\d*|[^\sA-Za-z0-9]',s)
T=[tok(r) for r in rows]

def rep_unigram(t): return Counter(t)
def rep_bigram(t):  return Counter(zip(t,t[1:]))
def rep_first(t):   return Counter([('F',t[0])] if t else [])
def rep_len(t):     return Counter([('L',len(t)//10)])
REPS={'unigram':rep_unigram,'bigram':rep_bigram,'first':rep_first,'len':rep_len}

def MI(labels, keys_list):
    # 离散互信息 I(label; 表示)，用频率估计（真实数据，无分布假设）
    N=len(labels); py=Counter(labels)
    joint=Counter(); kx=Counter()
    for y,k in zip(labels,keys_list):
        kx[k]+=1; joint[(y,k)]+=1
    mi=0.0
    for (y,k),c in joint.items():
        p=c/N; pyk=py[y]/N*kx[k]/N
        if p>0 and pyk>0: mi+=p*math.log(p/pyk)
    return mi

def disc(labels, keys_list, seed=1):
    # 朴素贝叶斯判别度 |TPR-FPR|（真实训练/测试切分）
    r=random.Random(seed); idx=list(range(len(labels))); r.shuffle(idx)
    cut=int(0.7*len(idx)); tr,te=idx[:cut],idx[1*0:] 
    tr,te=idx[:cut],idx[cut:]
    pri={}; tot=Counter(labels[i] for i in tr)
    for i in tr:
        pri.setdefault(labels[i],Counter())[keys_list[i]]+=1
    tp=fp=tn=fn=0
    for i in te:
        sc={}
        for y in tot:
            sc[y]=math.log(tot[y]/len(tr))+math.log((pri[y][keys_list[i]]+0.5)/(tot[y]+0.5*len(set(keys_list))))
        pred=max(sc,key=sc.get)
        if pred==1 and labels[i]==1: tp+=1
        elif pred==1 and labels[i]==0: fp+=1
        elif pred==0 and labels[i]==0: tn+=1
        else: fn+=1
    tpr=tp/(tp+fn) if tp+fn else 0; fpr=fp/(fp+tn) if fp+tn else 0
    return abs(tpr-fpr), tpr, fpr

out=[]
for name,f in REPS.items():
    keys=[tuple(sorted(f(t).items())) for t in T]
    mi=MI(lab,keys)
    d,tpr,fpr=disc(lab,keys)
    out.append(dict(rep=name,MI=mi,disc=d,tpr=tpr,fpr=fpr))
    print("%-8s I(label;rep)=%.4f   判别度|TPR-FPR|=%.4f  (TPR %.3f FPR %.3f)"%(name,mi,d,tpr,fpr))
json.dump(out,open('s6.json','w'),indent=1)
# 排序一致性
def rank(v):
    s=sorted(range(len(v)),key=lambda i:-v[i]); r=[0]*len(v)
    for p,i in enumerate(s): r[i]=p+1
    return r
rm=rank([o['MI'] for o in out]); rd=rank([o['disc'] for o in out])
n=len(out); d2=sum((a-b)**2 for a,b in zip(rm,rd))
rho=1-6*d2/(n*(n*n-1))
print("\nSpearman(互信息排序, 判别度排序) = %.3f"%rho)
print("互信息最高的表示:",max(out,key=lambda o:o['MI'])['rep'],
      "| 判别度最高的表示:",max(out,key=lambda o:o['disc'])['rep'])
