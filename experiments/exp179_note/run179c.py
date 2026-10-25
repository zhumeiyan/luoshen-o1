#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""178c 稳健性：'衰减记忆反而比无笔记更差' 是否依赖平滑系数 / 是否全层衰减"""
import os, json, math
from collections import defaultdict, Counter
D="/data/workspace/luoshen-o1/experiments/exp179_note"
SRC="/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt"
lines=[l.strip() for l in open(SRC,encoding="utf-8") if l.strip()]
n_test=8; train,test=lines[:-n_test],lines[-n_test:]
tr="".join(train); te="".join(test)
vocab=sorted(set(tr)); V=len(vocab)+1; idx={c:i for i,c in enumerate(vocab)}
enc_tr=[idx.get(c,V-1) for c in tr]; enc_te=[idx.get(c,V-1) for c in te]
msg_of=[]; 
for i2,l in enumerate(train): msg_of+=[i2]*len(l)
last=len(train)-1
K=1
def build(enc,wf=None,K=1):
    m=defaultdict(Counter)
    for i in range(len(enc)-K):
        w=1.0 if wf is None else wf(i)
        m[tuple(enc[i:i+K])][enc[i+K]]+=w
    return m
def bits(layers,enc_te,ALPHA,unis):
    tot,n=0.0,0
    for i in range(len(enc_te)-1):
        nx=enc_te[i+1]; p=None
        for cnt in layers:
            c=cnt.get((enc_te[i],))
            if c:
                s=sum(c.values()); p=(c.get(nx,0.0)+ALPHA)/(s+ALPHA*V); break
        if p is None:
            u=unis; tu=sum(u.values()); p=(u.get(nx,0)+ALPHA)/(tu+ALPHA*V)
        tot-=math.log2(p); n+=1
    return tot/n
out=[]
for ALPHA in [0.01,0.05,0.1,0.5,1.0]:
    row={"ALPHA":ALPHA}
    uni=Counter(enc_tr)
    base=bits([],enc_te,ALPHA,uni)
    row["baseline"]=round(base,4)
    for lam in [0.0,0.1,0.5,2.0]:
        wf=None if lam==0 else (lambda L:(lambda i:math.exp(-L*(last-msg_of[i]))))(lam)
        lv=[build(enc_tr,wf,K)]
        row["lam%.1f"%lam]=round(bits(lv,enc_te,ALPHA,uni),4)
        # 全层衰减版
        uw=Counter()
        for i,c in enumerate(enc_tr):
            uw[c]+= 1.0 if lam==0 else math.exp(-lam*(last-msg_of[i]))
        row["lam%.1f_alldecay"%lam]=round(bits(lv,enc_te,ALPHA,uw),4)
    out.append(row)
    print("ALPHA=%-5s 无笔记基线=%.4f | lam0=%.4f lam0.1=%.4f lam0.5=%.4f lam2=%.4f | 全衰减 lam0.5=%.4f lam2=%.4f"%(
        ALPHA,row["baseline"],row["lam0.0"],row["lam0.1"],row["lam0.5"],row["lam2.0"],
        row["lam0.5_alldecay"],row["lam2.0_alldecay"]))
json.dump(out,open(os.path.join(D,"result179c.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("wrote result179c.json")
