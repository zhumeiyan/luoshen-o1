import json, random, math
from collections import defaultdict

txt = open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md', encoding='utf-8').read()
s = ''.join(ch for ch in txt if not ch.isspace())

def cls(ch):
    if '\u4e00' <= ch <= '\u9fff': return 'H'   # 汉字
    if ch.isdigit(): return 'D'                  # 数字
    if ch.isalpha(): return 'A'                  # 拉丁字母
    return 'O'                                   # 其他/标点
s2 = ''.join(cls(c) for c in s)
print("class stream (first 60):", s2[:60])
N=len(s2); V=len(set(s2))
print(f"coarse: N={N} V={V}  k*_theory=logN/logV={math.log(N)/math.log(V):.3f}")
print(f"fine  : N={len(s)} V={len(set(s))}  k*_theory={math.log(len(s))/math.log(len(set(s))):.3f}")

rng=random.Random(3)
idx=list(range(N-15)); rng.shuffle(idx)
cut=int(len(idx)*0.8); tr=set(idx[:cut]); te=idx[cut:]
print(f"\n{'k':>3} {'test_acc':>9} {'coverage':>9} {'ctx_types':>10}")
out={}
for k in range(1,14):
    cnt=defaultdict(lambda: defaultdict(int))
    for i in tr: cnt[s2[i:i+k]][s2[i+k]]+=1
    glb=defaultdict(int)
    for i in tr: glb[s2[i+k]]+=1
    best=max(glb,key=glb.get)
    hit=0;cov=0
    for i in te:
        ctx=s2[i:i+k]
        if ctx in cnt:
            cov+=1
            p=max(cnt[ctx],key=cnt[ctx].get)
        else: p=best
        if p==s2[i+k]: hit+=1
    out[k]=hit/len(te)
    print(f"{k:>3} {out[k]:>9.4f} {cov/len(te):>9.4f} {len(cnt):>10}")
bestk=max(out,key=out.get)
print(f"\nbest_k(coarse V={V}) = {bestk}   vs best_k(fine V=1648) = 2")
json.dump(dict(V=V,N=N,kstar_theory=math.log(N)/math.log(V),best_k=bestk,acc=out),
          open('/data/workspace/luoshen-o1/experiments/exp161_nbonacci/vocab.json','w'),ensure_ascii=False,indent=1)
