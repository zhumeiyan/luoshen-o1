import collections, json, glob, os, random, time
random.seed(11)


def acc_for_k(train, test, k, nsample=4000):
    m = collections.defaultdict(collections.Counter)
    for i in range(len(train) - k):
        m[tuple(train[i:i + k])][train[i + k]] += 1
    backs = []
    for j in range(k - 1, 0, -1):
        bj = collections.defaultdict(collections.Counter)
        for i in range(len(train) - j):
            bj[tuple(train[i:i + j])][train[i + j]] += 1
        backs.append((j, bj))
    unig = collections.Counter(train)
    top = unig.most_common(1)[0][0]
    idx = list(range(len(test) - k))
    if len(idx) > nsample:
        idx = random.sample(idx, nsample)
    hit = 0
    tot = 0
    for i in idx:
        ctx = tuple(test[i:i + k])
        tgt = test[i + k]
        pred = None
        if ctx in m and m[ctx]:
            pred = m[ctx].most_common(1)[0][0]
        else:
            for j, bj in backs:
                c2 = ctx[-j:]
                if c2 in bj and bj[c2]:
                    pred = bj[c2].most_common(1)[0][0]
                    break
        if pred is None:
            pred = top
        hit += (pred == tgt)
        tot += 1
    return hit / tot


files = sorted(glob.glob('/data/workspace/luoshen-o1/evidence/实验报告/*.md'))
allt = []
for f in files:
    allt += [c for c in open(f, encoding='utf-8', errors='ignore').read() if c.strip()]
print('合并实验报告 N =', len(allt), flush=True)

res = {}
for N in [20000, 50000, 100000]:
    if N > len(allt):
        continue
    sub = allt[:N]
    tr = int(N * 0.8)
    train = sub[:tr]
    test = sub[tr:]
    t0 = time.time()
    accs = [acc_for_k(train, test, k) for k in range(1, 8)]
    base = accs[0]
    peak = max(accs)
    gain = peak - base
    marg = [(accs[i] - accs[i - 1]) / gain for i in range(1, len(accs))]
    D = [len({tuple(sub[i:i + k]) for i in range(len(sub) - k + 1)}) for k in range(1, 7)]
    r = [D[i] / D[i - 1] for i in range(1, len(D))]
    res[N] = {'acc': accs, 'gain': gain, 'marg': marg, 'r': r, 'Dsat': D[-1] / N}
    print(f'N={N:7d} gain={gain:.5f} 饱和D6/N={D[-1]/N:.3f} ({time.time()-t0:.0f}s)', flush=True)
    print('   边际(k1->2..):', ' '.join(f'{m:.4f}' for m in marg[:5]), flush=True)
    print('   分支r(k=2..6):', ' '.join(f'{x:.4f}' for x in r), flush=True)

json.dump(res, open('size.json', 'w'))
print()
print('理论 tribonacci 边际: 0.6180 0.2211 0.0883 0.0382', flush=True)
