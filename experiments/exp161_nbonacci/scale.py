import json, random, math
from collections import defaultdict

txt = open('/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md', encoding='utf-8').read()
s = ''.join(ch for ch in txt if not ch.isspace())
V = len(set(s))
rng = random.Random(7)

def run(N, seed):
    sub = s[:N]
    r = random.Random(seed)
    idx = list(range(N-9)); r.shuffle(idx)
    cut = int(len(idx)*0.8); tr=set(idx[:cut]); te=idx[cut:]
    out={}
    for k in range(1,8):
        cnt=defaultdict(lambda: defaultdict(int))
        for i in tr: cnt[sub[i:i+k]][sub[i+k]]+=1
        glb=defaultdict(int)
        for i in tr: glb[sub[i+k]]+=1
        best_g=max(glb,key=glb.get)
        hit=0
        for i in te:
            ctx=sub[i:i+k]
            p = max(cnt[ctx],key=cnt[ctx].get) if ctx in cnt else best_g
            if p==sub[i+k]: hit+=1
        out[k]=hit/len(te)
    bestk=max(out,key=out.get)
    return out,bestk

print(f"V={V}")
print(f"{'N':>8} {'k*_theory':>10} {'best_k':>7}  " + "  ".join(f"k={k}" for k in range(1,7)))
rows=[]
for N in [5000,10000,20000,40000,80000,142336]:
    out,bestk = run(N, 1000+N)
    kt = math.log(N)/math.log(V)
    print(f"{N:>8} {kt:>10.3f} {bestk:>7}  " + "  ".join(f"{out[k]:.4f}" for k in range(1,7)))
    rows.append(dict(N=N,kstar_theory=kt,best_k=bestk,acc=out))
json.dump(rows, open('/data/workspace/luoshen-o1/experiments/exp161_nbonacci/scale.json','w'), ensure_ascii=False, indent=1)
