#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp175b: 两个补充
1) 对齐程度扫描: 我只看见你的一部分(p%), 预测力怎么变 -> 对齐的边际收益曲线
2) 条件熵归一化: 排除词汇多样性混淆, 用 (H0 - Hk)/H0 比较 U/M 两侧的"被历史约束程度"
   并修正 175a 里 ppl 被回退稀释失真的问题(改用 stupid backoff, 不稀释)
"""
import json, math, os

BASE = os.path.dirname(os.path.abspath(__file__))
KEEP = set('，。？！、：；""''（）—…·')

def clean(s):
    out = []
    for ch in s:
        if ch.isspace():
            continue
        if '\u4e00' <= ch <= '\u9fff' or ch.isalnum() or ch in KEEP:
            out.append(ch)
    return ''.join(out)

U = clean(open(os.path.join(BASE,'u_side.txt'), encoding='utf-8').read())
Mraw = clean(open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md', encoding='utf-8').read())
M = Mraw[:len(U)]

def build(text, k):
    d = {}
    for i in range(len(text)-k):
        c = text[i:i+k]; n = text[i+k]
        d.setdefault(c, {}).setdefault(n, 0)
        d[c][n] += 1
    return d

def unigram(text):
    d = {}
    for ch in text:
        d[ch] = d.get(ch,0)+1
    return d

def entropy(counter):
    tot = sum(counter.values())
    h = 0.0
    for n in counter.values():
        p = n/tot
        h -= p*math.log2(p)
    return h

def eval_backoff(models, ug, test, k, backoff_w=0.4):
    """stupid backoff: 命中最高阶就用它, 未命中逐级回退(乘惩罚), 不稀释 -> ppl 可信"""
    correct=0; total=0; logp=0.0
    for i in range(len(test)-k):
        ctx = test[i:i+k]; nxt = test[i+k]
        probs=None; w=1.0
        for kk in range(k,0,-1):
            sub = ctx[-kk:]
            m = models[kk-1]
            if sub in m:
                c = m[sub]; tot=sum(c.values()); V=len(ug)
                probs = {}
                for ch in ug:
                    probs[ch] = w*(c.get(ch,0)+0.05)/(tot+0.05*V)
                break
            w *= backoff_w
        if probs is None:
            tot=sum(ug.values())
            probs = {ch: n/tot for ch,n in ug.items()}
        best = max(probs.items(), key=lambda x:x[1])[0]
        total += 1
        if best == nxt: correct += 1
        p = max(probs.get(nxt,0.0), 1e-12)
        logp += math.log2(p)
    if total==0: return 0.0,0.0,0.0,0
    acc = correct/total
    ce  = -logp/total            # bits/char 交叉熵
    ppl = 2**ce
    return acc, ce, ppl, total

def holdout(text, ratio=0.25):
    n=len(text); tn=int(n*ratio)
    return text[:n-tn], text[n-tn:]

def main():
    kmax=6
    Utr_full, Ute = holdout(U)
    Mtr_full, Mte = holdout(M)
    out={'meta':{'len_U':len(U),'len_M':len(M),
                 'U_train':len(Utr_full),'U_test':len(Ute),
                 'M_train':len(Mtr_full),'M_test':len(Mte)}}

    # ---- 1) 对齐程度扫描 ----
    # train 取 U_train_full 的前 p%
    scan={}
    for p in [5,10,20,30,50,75,100]:
        ntr = max(200, int(len(Utr_full)*p/100))
        tr = Utr_full[:ntr]
        models=[build(tr,k) for k in range(1,kmax+1)]
        ug=unigram(tr)
        row={}
        for k in range(1,kmax+1):
            acc,ce,ppl,tot = eval_backoff(models,ug,Ute,k)
            row[k]={'acc':acc,'ce':ce,'ppl':ppl,'n':tot}
        scan[p]=row
    out['对齐程度扫描']=scan

    # ---- 2) 条件熵归一化对照 ----
    norm={}
    for name,(tr,te) in {'U':(Utr_full,Ute),'M':(Mtr_full,Mte)}.items():
        ug=unigram(tr)
        H0=entropy(ug)
        models=[build(tr,k) for k in range(1,kmax+1)]
        row={'H0':H0,'k':{}}
        for k in range(1,kmax+1):
            acc,ce,ppl,tot=eval_backoff(models,ug,te,k)
            row['k'][k]={'acc':acc,'ce':ce,'ppl':ppl,
                         '约束率':(H0-ce)/H0 if H0>0 else 0.0}
        norm[name]=row
    out['归一化对照']=norm

    # ---- 3) 跨侧(修正 ppl) ----
    cross={}
    for name,(tr,te) in {'U->U_对齐':(Utr_full,Ute),
                         'M->U_不对齐':(Mtr_full,Ute),
                         'M->M_自预测':(Mtr_full,Mte),
                         'U->M_反向':(Utr_full,Mte),
                         'M+U->U_混合':(Mtr_full+Utr_full,Ute)}.items():
        ug=unigram(tr)
        models=[build(tr,k) for k in range(1,kmax+1)]
        row={}
        for k in range(1,kmax+1):
            acc,ce,ppl,tot=eval_backoff(models,ug,te,k)
            row[k]={'acc':acc,'ce':ce,'ppl':ppl}
        cross[name]=row
    out['跨侧_修正ppl']=cross

    with open(os.path.join(BASE,'result175b.json'),'w',encoding='utf-8') as f:
        json.dump(out,f,ensure_ascii=False,indent=1)

    print('== 1) 对齐程度扫描 (train 取 U 前 p%, 预测 U held-out) ==')
    print('%-6s'%'p%', ''.join('%9s'%('k=%d'%k) for k in range(1,kmax+1)))
    for p in [5,10,20,30,50,75,100]:
        print('%-6d'%p, ''.join('%9.4f'%scan[p][k]['acc'] for k in range(1,kmax+1)))
    print()
    print('k=2 时 acc 随 p:')
    prev=None
    for p in [5,10,20,30,50,75,100]:
        a=scan[p][2]['acc']
        d='' if prev is None else ' (边际 %+.4f)'%(a-prev)
        print('  p=%3d%%  acc=%.4f%s'%(p,a,d)); prev=a
    print()
    print('== 2) 归一化对照 (排除词汇多样性混淆) ==')
    for name in ['U','M']:
        r=norm[name]
        print('  %s  H0(unigram熵)=%.3f bits'%(name,r['H0']))
        for k in range(1,kmax+1):
            print('    k=%d  ce=%.3f  ppl=%.1f  约束率=%.4f'%(k,r['k'][k]['ce'],r['k'][k]['ppl'],r['k'][k]['约束率']))
    print()
    print('== 3) 跨侧 (修正后的 ppl) ==')
    print('%-14s'%'pair', ''.join('%10s'%('k=%d'%k) for k in range(1,kmax+1)), '   (ppl@k=2)')
    for name,row in cross.items():
        print('%-14s'%name, ''.join('%10.4f'%row[k]['acc'] for k in range(1,kmax+1)), '  %.1f'%row[2]['ppl'])

if __name__=='__main__':
    main()
