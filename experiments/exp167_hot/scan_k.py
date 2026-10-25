import json, random, statistics as st

NF = 13
D = json.load(open("data167.json"))
rows = D["rows"]

groups = {}
for r in rows:
    groups.setdefault((r["rnd"], r["cpu"], r["io"]), []).append(r)
for g in groups.values():
    g.sort(key=lambda x: x["rep"])
for g in groups.values():
    prev = None
    for r in g:
        f = r["f"]
        d = [f[i] - prev[i] for i in range(NF)] if prev else [0.0] * NF
        r["_x"] = f + d
        prev = f
X = [r["_x"] for r in rows]
Y = [r["ratio"] for r in rows]
NP = len(X); NDIM = len(X[0])
mu = [st.mean([X[i][j] for i in range(NP)]) for j in range(NDIM)]
sd = [st.pstdev([X[i][j] for i in range(NP)]) or 1.0 for j in range(NDIM)]
Xs = [[(X[i][j] - mu[j]) / sd[j] for j in range(NDIM)] for i in range(NP)]


def quantile_cut(vals, k):
    sv = sorted(vals)
    cuts = [sv[int(len(sv) * q / k)] for q in range(1, k)]
    out = []
    for v in vals:
        L = 0
        while L < len(cuts) and v >= cuts[L]:
            L += 1
        out.append(L)
    return out


def nc_acc(lab, tr, te, dims):
    cent = {}
    for i in tr:
        cent.setdefault(lab[i], []).append(i)
    C = {c: [st.mean([Xs[i][d] for i in ids]) for d in dims] for c, ids in cent.items()}
    ok = 0
    for i in te:
        v = [Xs[i][d] for d in dims]
        best, bd = None, 1e18
        for c, cv in C.items():
            dd = sum((v[t] - cv[t]) ** 2 for t in range(len(dims)))
            if dd < bd:
                bd, best = dd, c
        ok += (best == lab[i])
    return ok / len(te)


def cv_acc(lab, dims, folds=5, seed=0):
    idx = list(range(len(lab)))
    random.Random(seed).shuffle(idx)
    a = []
    for f in range(folds):
        te = idx[f::folds]
        tr = [i for i in idx if i not in set(te)]
        a.append(nc_acc(lab, tr, te, dims))
    return st.mean(a)


DIMS = [1, 2, 4, 8, 16, 26]
out = {}
print("k    d1     d2     d4     d8     d16    d26    | 高维边际(8→16→26)")
for k in (2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20):
    lab = quantile_cut(Y, k)
    curv = {d: [] for d in DIMS}
    for seed in (167, 271, 919):
        rng = random.Random(seed)
        for _ in range(15):
            sub = rng.sample(range(NDIM), 26)   # 固定特征顺序，前缀取 d 个
            for d in DIMS:
                curv[d].append(cv_acc(lab, sub[:d], seed=seed))
    m = {d: st.mean(curv[d]) for d in DIMS}
    hi = st.mean([m[16] - m[8], m[26] - m[16]])
    out[k] = {"curve": {str(d): round(m[d], 4) for d in DIMS}, "high_marginal": round(hi, 4)}
    print(f"{k:<4d} " + "  ".join(f"{m[d]:.3f}" for d in DIMS) + f"   | {hi:+.4f}")

json.dump(out, open("scan_k.json", "w"), indent=1)
print("\nsaved scan_k.json")
