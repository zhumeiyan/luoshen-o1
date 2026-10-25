#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp175c: 排除 exp175b 中"对齐程度扫描"的时间局部性混淆
175b 里 train 取 U 的前 p%, 而 held-out 是 U 的最后 25% ->
p 增大同时意味着"看见更多"和"离测试集更近", 两者混在一起。

175c 改为: 按消息(行)随机划分, 多次种子平均
  - 随机 25% 行作 held-out
  - 从剩余行中随机取 p% 作 train
  - 20 次种子平均 -> 排除时间远近
"""
import json, math, os, random

BASE=os.path.dirname(os.path.abspath(__file__))
KEEP=set('，。？！、：；""''（）—…·')
def clean(s):
    out=[]
    for ch in s:
        if ch.isspace(): continue
        if '\u4e00'<=ch<='\u9fff' or ch.isalnum() or ch in KEEP: out.append(ch)
    return ''.join(out)

lines=[clean(l) for l in open(os.path.join(BASE,'u_side.txt'),encoding='utf-8') if clean(l)]
print('消息条数=%d  总字符=%d'%(len(lines),sum(map(len,lines))))

def build(text,k):
    d={}
    for i in range(len(text)-k):
        c=text[i:i+k]; n=text[i+k]
        d.setdefault(c,{}).setdefault(n,0); d[c][n]+=1
    return d
def unigram(text):
    d={}
    for ch in text: d[ch]=d.get(ch,0)+1
    return d
def eval_acc(models,ug,test,k,lam=0.5):
    correct=0;total=0
    for i in range(len(test)-k):
        ctx=test[i:i+k]; nxt=test[i+k]
        probs={}; w=1.0
        for kk in range(k,0,-1):
            sub=ctx[-kk:]; m=models[kk-1]
            if sub in m:
                c=m[sub]; tot=sum(c.values()); V=len(ug)
                for ch,n in c.items(): probs[ch]=probs.get(ch,0.0)+w*lam*n/tot
                for ch in ug: probs[ch]=probs.get(ch,0.0)+w*lam*0.01/(tot+0.01*V)
            w*=(1-lam)
        tot=sum(ug.values())
        for ch,n in ug.items(): probs[ch]=probs.get(ch,0.0)+w*n/tot
        if not probs: continue
        total+=1
        if max(probs.items(),key=lambda x:x[1])[0]==nxt: correct+=1
    return (correct/total if total else 0.0), total

def main():
    kmax=6
    seeds=list(range(20))
    ps=[5,10,20,30,50,75,100]
    res={p:{k:[] for k in range(1,kmax+1)} for p in ps}

    for sd in seeds:
        rnd=random.Random(sd)
        idx=list(range(len(lines))); rnd.shuffle(idx)
        nte=max(1,int(len(idx)*0.25))
        te_idx=idx[:nte]; rest=idx[nte:]
        te=''.join(lines[i] for i in te_idx)
        for p in ps:
            ntr=max(1,int(len(rest)*p/100))
            tr_idx=rnd.sample(rest,ntr)
            tr=''.join(lines[i] for i in tr_idx)
            if len(tr)<200 or len(te)<50: continue
            models=[build(tr,k) for k in range(1,kmax+1)]
            ug=unigram(tr)
            for k in range(1,kmax+1):
                a,_=eval_acc(models,ug,te,k)
                res[p][k].append(a)

    out={'seeds':len(seeds),'ps':ps,'kmax':kmax,'res':{}}
    print()
    print('随机划分(20种子平均) acc:')
    print('%-6s'%'p%', ''.join('%9s'%('k=%d'%k) for k in range(1,kmax+1)))
    for p in ps:
        row='%-6d'%p
        means={}
        for k in range(1,kmax+1):
            v=res[p][k]; m=sum(v)/len(v) if v else 0.0
            means[k]=m; row+='%9.4f'%m
        out['res'][p]={'mean':means,'n':len(res[p][1])}
        print(row)

    print()
    print('k=2 边际 (随机划分):')
    prev=None
    for p in ps:
        m=out['res'][p]['mean'][2]
        d='' if prev is None else ' 边际 %+.4f'%(m-prev)
        print('  p=%3d%%  acc=%.4f%s'%(p,m,d)); prev=m

    json.dump(out,open(os.path.join(BASE,'result175c.json'),'w',encoding='utf-8'),
              ensure_ascii=False,indent=1)

if __name__=='__main__': main()
