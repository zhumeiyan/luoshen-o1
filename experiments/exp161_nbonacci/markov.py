import json, random, math
from collections import defaultdict

txt = open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md', encoding='utf-8').read()
# 只保留实质文本，去空白
s = ''.join(ch for ch in txt if not ch.isspace())
N = len(s); V = len(set(s))
print(f"N chars={N}  V distinct={V}  theoretical k* = logN/logV = {math.log(N)/math.log(V):.4f}")

rng = random.Random(20261019)
idx = list(range(N-(8+1)))
rng.shuffle(idx)
cut = int(len(idx)*0.8)
tr = set(idx[:cut]); te = idx[cut:]
print(f"train={len(tr)} test={len(te)}")

res=[]
for k in range(1,9):
    cnt = defaultdict(lambda: defaultdict(int))
    for i in tr:
        ctx = s[i:i+k]
        cnt[ctx][s[i+k]] += 1
    # 全局回退分布
    glb = defaultdict(int)
    for i in tr: glb[s[i+k]] += 1
    tot_g = sum(glb.values()); best_g = max(glb, key=glb.get)
    hit=0; cov=0
    for i in te:
        ctx = s[i:i+k]; tgt = s[i+k]
        if ctx in cnt:
            cov += 1
            if max(cnt[ctx], key=cnt[ctx].get) == tgt: hit += 1
        else:
            if best_g == tgt: hit += 1
    acc = hit/len(te); coverage = cov/len(te)
    # 训练上自己的准确率（记忆vs泛化）
    hit_tr=0
    for i in list(tr)[:20000]:
        ctx=s[i:i+k]
        if ctx in cnt and max(cnt[ctx],key=cnt[ctx].get)==s[i+k]: hit_tr+=1
    acc_tr = hit_tr/min(20000,len(tr))
    res.append(dict(k=k, test_acc=acc, coverage=coverage, train_acc=acc_tr))
    print(f"k={k}  test_acc={acc:.4f}  coverage={coverage:.4f}  train_acc(train subset)={acc_tr:.4f}  ctx_types={len(cnt)}")

json.dump(dict(N=N,V=V,kstar_theory=math.log(N)/math.log(V),res=res),
          open('/data/workspace/luoshen-o1/experiments/exp161_nbonacci/markov.json','w'), ensure_ascii=False, indent=1)
