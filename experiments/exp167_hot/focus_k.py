import json, random, statistics as st

NF = 13
D = json.load(open("data167.json"))
rows = D["rows"]
groups = {}
for r in rows:
    groups.setdefault((r["rnd"], r["cpu"], r["io"]), []).append(r)
for g in groups.values():
    g.sort(key=lambda x: x["rep"])
    prev = None
    for r in g:
        f = r["f"]
        r["_x"] = f + ([f[i] - prev[i] for i in range(NF)] if prev else [0.0] * NF)
        prev = f
X = [r["_x"] for r in rows]
Y = [r["ratio"] for r in rows]
NP = len(X); NDIM = len(X[0])
mu = [st.mean([X[i][j] for i in range(NP)]) for j in range(NDIM)]
sd = [st.pstdev([X[i][j] for i in range(NP)]) or 1.0 for j in range(NDIM)]
Xs = [[(X[i][j] - mu[j]) / sd[j] for j in range(NDIM)] for i in range(NP)]


def qcut(vals, k):
    sv = sorted(vals)
    cuts = [sv[int(len(sv) * q / k)] for q in range(1, k)]
    o = []
    for v in vals:
        L = 0
        while L < len(cuts) and v >= cuts[L]:
            L += 1
        o.append(L)
    return o


def nca(lab, tr, te, dims):
    cent = {}
    for i in tr:
        cent.setdefault(lab[i], []).append(i)
    C = {c: [st.mean([Xs[i][d] for i in ids]) for d in dims] for c, ids in cent.items()}
    ok = 0
    for i in te:
        v = [Xs[i][d] for d in dims]
        b, bd = None, 1e18
        for c, cv in C.items():
            dd = sum((v[t] - cv[t]) ** 2 for t in range(len(dims)))
            if dd < bd:
                bd, b = dd, c
        ok += (b == lab[i])
    return ok / len(te)


def cva(lab, dims, folds=5, seed=0):
    idx = list(range(len(lab)))
    random.Random(seed).shuffle(idx)
    a = []
    for f in range(folds):
        te = idx[f::folds]
        tr = [i for i in idx if i not in set(te)]
        a.append(nca(lab, tr, te, dims))
    return st.mean(a)


out = {}
print("k    d8→d26 增益   跨seed标准误   判定")
for k in (5, 6, 7, 8, 9, 10, 11, 12, 14, 16):
    lab = qcut(Y, k)
    gains = []
    for seed in (11, 23, 37, 59, 71, 97, 131, 167):
        rng = random.Random(seed)
        sub = rng.sample(range(NDIM), 26)
        g = cva(lab, sub[:26], seed=seed) - cva(lab, sub[:8], seed=seed)
        gains.append(g)
    m = st.mean(gains)
    se = (st.pstdev(gains) / len(gains) ** 0.5) if len(gains) > 1 else 0.0
    verdict = "收敛" if m <= 0.012 else "不收敛(发散)"
    out[k] = {"gain_d8_to_d26": round(m, 4), "se": round(se, 4), "verdict": verdict}
    print(f"{k:<4d} {m:+.4f}        ±{se:.4f}       {verdict}")

json.dump(out, open("focus_k.json", "w"), indent=1)
print("\nsaved focus_k.json")
