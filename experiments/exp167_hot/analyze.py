import json, random, statistics as st

NF = 13
D = json.load(open("data167.json"))
rows = D["rows"]

# ---- 构造 28 维特征：14 基础 + 14 一阶差分（组内相邻 rep）----
groups = {}
for r in rows:
    groups.setdefault((r["rnd"], r["cpu"], r["io"]), []).append(r)
for g in groups.values():
    g.sort(key=lambda x: x["rep"])

X = [None] * len(rows)
for g in groups.values():
    prev = None
    for r in g:
        f = r["f"]
        d = [f[i] - prev[i] for i in range(NF)] if prev else [0.0] * NF
        r["_x"] = f + d
        prev = f
for i, r in enumerate(rows):
    X[i] = r["_x"]

Y = [r["ratio"] for r in rows]
NP = len(X); NDIM = len(X[0])

# 标准化
NF = len(X[0])
mu = [st.mean([X[i][j] for i in range(NP)]) for j in range(NDIM)]
sd = [st.pstdev([X[i][j] for i in range(NP)]) or 1.0 for j in range(NDIM)]
Xs = [[(X[i][j] - mu[j]) / sd[j] for j in range(NDIM)] for i in range(NP)]


def quantile_cut(vals, k):
    sv = sorted(vals)
    cuts = [sv[int(len(sv) * q / k)] for q in range(1, k)]
    lab = []
    for v in vals:
        L = 0
        while L < len(cuts) and v >= cuts[L]:
            L += 1
        lab.append(L)
    return lab


def nearest_centroid_acc(Xs, lab, idx_tr, idx_te, dims):
    cent = {}
    for i in idx_tr:
        cent.setdefault(lab[i], []).append(i)
    C = {c: [st.mean([Xs[i][d] for i in ids]) for d in dims] for c, ids in cent.items()}
    ok = 0
    for i in idx_te:
        v = [Xs[i][d] for d in dims]
        best, bd = None, 1e18
        for c, cv in C.items():
            dd = sum((v[t] - cv[t]) ** 2 for t in range(len(dims)))
            if dd < bd:
                bd, best = dd, c
        ok += (best == lab[i])
    return ok / len(idx_te)


def cv_acc(Xs, lab, dims, folds=5, seed=0):
    n = len(lab)
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    accs = []
    for f in range(folds):
        te = idx[f::folds]
        tr = [i for i in idx if i not in set(te)]
        if not te:
            continue
        accs.append(nearest_centroid_acc(Xs, lab, tr, te, dims))
    return st.mean(accs)


def dim_curve(lab, dimlist, nsub=20, seed=167):
    """每档 d 随机抽 nsub 个特征子集，取平均（消除'哪 d 个'的任意性）"""
    rng = random.Random(seed)
    out = {}
    for d in dimlist:
        accs = []
        for _ in range(nsub):
            dims = rng.sample(range(NDIM), d)
            accs.append(cv_acc(Xs, lab, dims, seed=seed))
        out[d] = st.mean(accs)
    return out


DIMS = [1, 2, 4, 8, 16, 26]
res = {"S1": {}, "S2": {}}

print("=== S1 扫封装粒度 k：后果层按分位切 k 级 ===")
for k in (2, 3, 4, 5, 7, 10, 16):
    lab = quantile_cut(Y, k)
    curv = dim_curve(lab, DIMS)
    marg = []
    for a, b in zip(DIMS[:-1], DIMS[1:]):
        marg.append(round(curv[b] - curv[a], 4))
    res["S1"][k] = {"curve": {str(d): round(curv[d], 4) for d in DIMS}, "marginal": marg}
    print(f"k={k:2d}  " + "  ".join(f"d{d}:{curv[d]:.3f}" for d in DIMS) + f"   边际 {marg}")

print()
print("=== S2 后果封装 vs 物理量封装 ===")
# A 后果层（k=5）
labA = quantile_cut(Y, 5)
curvA = dim_curve(labA, DIMS)
# B 物理量层：按 (cpu进程数) 直接当标签 —— 与后果不同源
labB = [r["cpu"] for r in rows]
curvB = dim_curve(labB, DIMS)
# C 物理量层：按 io 进程数
labC = [r["io"] for r in rows]
curvC = dim_curve(labC, DIMS)

for nm, cv in (("A_后果", curvA), ("B_物理量cpu", curvB), ("C_物理量io", curvC)):
    marg = [round(cv[b] - cv[a], 4) for a, b in zip(DIMS[:-1], DIMS[1:])]
    res["S2"][nm] = {"curve": {str(d): round(cv[d], 4) for d in DIMS}, "marginal": marg}
    print(f"{nm:14s} " + "  ".join(f"d{d}:{cv[d]:.3f}" for d in DIMS) + f"   边际 {marg}")

# 后果 vs 物理量的关系（是否不可比）
print()
print("=== 附：后果 vs 物理量 的对应关系 ===")
for c in (0, 1, 2, 3):
    ys = [r["ratio"] for r in rows if r["cpu"] == c]
    print(f"cpu={c} 后果 median={st.median(ys):.3f}  min={min(ys):.3f} max={max(ys):.3f}")
for i in (0, 1, 2):
    ys = [r["ratio"] for r in rows if r["io"] == i]
    print(f"io={i}  后果 median={st.median(ys):.3f}  min={min(ys):.3f} max={max(ys):.3f}")

json.dump(res, open("result167.json", "w"), indent=1)
print("\nsaved result167.json")
