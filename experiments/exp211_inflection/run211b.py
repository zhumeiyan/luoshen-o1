# -*- coding: utf-8 -*-
"""
211b: 拐点 —— 区分「漂变多样性」vs「选择维持的多样性」
关键改：跑40代看末代/末5代平均熵（漂变会衰减，选择会维持）
numpy 加速，8 seeds，β 网格加密在 0 附近
"""
import json, random, math, collections
import numpy as np

KMAX, NA, GENS, TRAIN, TEST = 5, 10, 40, 30000, 4000
BETAS  = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
SEEDS  = [1,2,3,4,5,6,7,8]
LAMB   = 0.05

def load():
    t = open("/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md",
             encoding="utf-8", errors="ignore").read()
    return "".join(c for c in t if ord(c) > 31)

def build(text, k):
    """返回 (argmax_ctx dict, global_best)"""
    vocab = collections.Counter(text)
    gbest = vocab.most_common(1)[0][0]
    if k == 0:
        return ({}, gbest)
    d = collections.defaultdict(collections.Counter)
    for i in range(k, len(text)):
        d[text[i-k:i]][text[i]] += 1
    am = {c: v.most_common(1)[0][0] for c, v in d.items()}
    return (am, gbest)

def okvec(am, gbest, test, k):
    return np.fromiter(
        (1 if am.get(test[i-k:i], gbest) == test[i] else 0
         for i in range(KMAX, len(test))), dtype=np.int8,
        count=len(test)-KMAX)

def main():
    text = load()
    pool, test = text[:len(text)-TEST], text[len(text)-TEST:]
    print(f"[corpus] {len(text)}  pool={len(pool)} test={len(test)}")

    out = []
    for seed in SEEDS:
        rng = random.Random(seed)
        samples = []
        for a in range(NA):
            s = rng.randrange(0, max(1, len(pool)-TRAIN))
            samples.append(pool[s:s+TRAIN])
        cache = {}
        for a in range(NA):
            for k in range(KMAX+1):
                am, gb = build(samples[a], k)
                cache[(a,k)] = okvec(am, gb, test, k)
        T = len(cache[(0,0)])
        print(f"[seed {seed}] cache ok T={T}")

        for beta in BETAS:
            r2 = random.Random(seed*7919 + int(beta*1000))
            pop = [0]*NA
            ents = []
            for g in range(GENS):
                M   = np.array([cache[(a, pop[a])] for a in range(NA)])
                col = M.sum(0)                       # 每位置多少人答对
                own = (M * (col == 1)).sum(1)        # 独占答对
                tot = M.sum(1)
                uniq = own / np.maximum(tot, 1)
                acc  = tot / T
                fit  = acc + beta * uniq
                c = collections.Counter(pop)
                ents.append(-sum((v/NA)*math.log2(v/NA) for v in c.values()))
                w = fit - fit.min() + 1e-6
                cs = np.cumsum(w); tot_w = cs[-1]
                new = []
                for _ in range(NA):
                    r = r2.random()*tot_w
                    idx = int(np.searchsorted(cs, r))
                    kk = pop[min(idx, NA-1)]
                    if r2.random() < 0.25:
                        kk = max(0, min(KMAX, kk + (1 if r2.random()<0.5 else -1)))
                    new.append(kk)
                pop = new
            M   = np.array([cache[(a, pop[a])] for a in range(NA)])
            acc = M.sum() / (NA*T)
            c   = collections.Counter(pop)
            H   = -sum((v/NA)*math.log2(v/NA) for v in c.values())
            out.append({
                "seed": seed, "beta": beta,
                "entropy_final": round(H,4),
                "entropy_last5": round(float(np.mean(ents[-5:])),4),
                "entropy_first5": round(float(np.mean(ents[:5])),4),
                "n_layers": len(c), "k_hist": dict(c),
                "acc": round(float(acc),5),
                "k_max": max(pop), "k_min": min(pop),
                "pop": sorted(pop), "ents": [round(e,3) for e in ents],
            })
            print(f"  s{seed} b={beta:<5} Hfin={H:.3f} Hlast5={np.mean(ents[-5:]):.3f} "
                  f"Hfirst5={np.mean(ents[:5]):.3f} L={len(c)} acc={acc:.4f} pop={sorted(pop)}")

    json.dump({"KMAX":KMAX,"NA":NA,"GENS":GENS,"TRAIN":TRAIN,"TEST":TEST,
               "BETAS":BETAS,"SEEDS":SEEDS,"results":out},
              open("result211b.json","w"), ensure_ascii=False, indent=1)
    print("saved result211b.json")

if __name__ == "__main__":
    main()
