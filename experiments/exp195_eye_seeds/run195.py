#!/usr/bin/env python3
# 195 眼睛的两种种子对抗 —— 看清(高分辨率/短程) vs 看远(低分辨率/长程)
# 修正版：加回退插值（否则长程被稀疏性惩罚 -> 实验设计偏差，会假偏向近眼）
#   种子A = 想看清：字母表大 A↑（分辨率高）, 上下文 k↓（看得近 = 中央凹）
#   种子B = 看远  ：字母表小 A↓（分辨率低）, 上下文 k↑（看得远 = 周边）
#   对抗 -> 分歧(JS) -> 动态聚光策略；对照 = 同量随机分配
import json, math, random
from collections import defaultdict, Counter

random.seed(42)
OUT = "/data/workspace/luoshen-o1/experiments/exp195_eye_seeds"
SRC = "/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"

lines = open(SRC, encoding="utf-8").read().split("\n")
body = []
for ln in lines:
    if ln.startswith("#"):
        continue
    s = ln.rstrip()
    if not s.strip():
        continue
    if s.startswith("U") and s[1:4].isdigit() and ":" in s[:8]:
        body.append(s.split(":", 1)[1].strip())
    elif s.startswith(" ") and body:
        body[-1] += s.strip()
body = [b for b in body if b and "[同期贴入" not in b]
txt = "\n".join(body)

n = len(txt)
ntr = int(n * 0.8)
tr, te = txt[:ntr], txt[ntr:]
freq = Counter(tr)
VOCAB = list(freq.keys())
V = len(VOCAB)
order = [c for c, _ in freq.most_common()]
tot = sum(freq.values())
# 全局字符分布（含 UNK 槽），用于回退与公平地板
ALPHA_U = 0.5
P_UNI = {c: (freq[c] + ALPHA_U) / (tot + ALPHA_U * (V + 1)) for c in VOCAB}
P_UNK = ALPHA_U / (tot + ALPHA_U * (V + 1))
print(f"chars={n} train={ntr} test={len(te)} vocab={V} P_UNK={P_UNK:.2e} (-log2={-math.log2(P_UNK):.2f} bits)")


def make_bucket(A):
    m, acc, b = {}, 0.0, 0
    for c in order:
        m[c] = min(b, A - 1)
        acc += freq[c] / tot
        while b < A - 1 and acc >= (b + 1) / A:
            b += 1
    return m


GAMMA = 1.0   # 桶 -> 字符 的回退强度
MU = 2.0      # 层次插值：lambda = T/(T+MU)


class Eye:
    """分辨率 A（桶数）, 视野 k（上下文长度）；Witten-Bell 式层次插值回退"""

    def __init__(self, bmap, A, k):
        self.bmap, self.A, self.k = bmap, A, k
        self.cnt = [defaultdict(Counter) for _ in range(k + 1)]  # cnt[j]: j阶桶上下文 -> 桶计数
        self.tot = [Counter() for _ in range(k + 1)]
        self.bch = defaultdict(Counter)
        self.btot = Counter()

    def fit(self, seq):
        bs = [self.bmap.get(c, self.A - 1) for c in seq]
        for i, c in enumerate(seq):
            self.bch[bs[i]][c] += 1
            self.btot[bs[i]] += 1
            for j in range(1, self.k + 1):
                if i >= j:
                    key = tuple(bs[i - j:i])
                    self.cnt[j][key][bs[i]] += 1
                    self.tot[j][key] += 1
        # 0 阶：全局桶分布
        for b in range(self.A):
            self.tot[0][()] += self.btot.get(b, 0)
            self.cnt[0][()] = Counter(self.btot)
        self.prior_b = {}
        for b in range(self.A):
            self.prior_b[b] = (self.btot.get(b, 0) + 0.5) / (len(seq) + 0.5 * self.A)

    def _pb(self, hist):
        """层次插值后的桶分布"""
        bs = [self.bmap.get(c, self.A - 1) for c in hist]
        lo = dict(self.prior_b)

        def at(j):
            if j == 0:
                return dict(self.prior_b)
            if len(bs) < j:
                return None
            key = tuple(bs[-j:])
            T = self.tot[j].get(key, 0)
            if T == 0:
                return None
            lam = T / (T + MU)
            sub = at(j - 1)
            out = {}
            for b in range(self.A):
                hi = self.cnt[j][key].get(b, 0) / T
                out[b] = lam * hi + (1 - lam) * sub.get(b, 1.0 / self.A)
            return out
        r = at(self.k)
        return r if r is not None else lo

    def pdist(self, hist):
        pb = self._pb(hist)
        out = {}
        for b, p in pb.items():
            if p <= 0:
                continue
            ch = self.bch.get(b)
            tb = self.btot.get(b, 0)
            if not ch or tb == 0:
                continue
            for c, cc in ch.items():
                pc = (cc + GAMMA * P_UNI.get(c, P_UNK)) / (tb + GAMMA)
                out[c] = out.get(c, 0.0) + p * pc
        return out

    def prob(self, hist, c):
        return self.pdist(hist).get(c, P_UNK)


def bits_of(eye):
    s, hist = 0.0, list(tr)
    for c in te:
        p = eye.prob(hist, c)
        s -= math.log2(max(p, P_UNK))
        hist.append(c)
    return s / len(te)


BMAPS = {A: make_bucket(A) for A in [2, 4, 8, 16, 32, 64, 128, 264, V]}
grid = {}
for A in [2, 4, 8, 16, 32, 64, 128, 264, V]:
    for k in range(1, 7):
        e = Eye(BMAPS[A], A, k)
        e.fit(tr)
        b = bits_of(e)
        grid[f"A{A}_k{k}"] = {"A": A, "k": k, "states": A ** k, "bits": round(b, 4)}
        print(f"A={A:4d} k={k} states={A**k:12d} bits={b:.4f}")


def best_k_for(A, S):
    return min([(abs(A ** k - S), k) for k in range(1, 7)])[1]


budgets = {}
for S in [500, 5000, 50000]:
    curve = [{"A": A, "k": best_k_for(A, S), "states": A ** best_k_for(A, S),
              "bits": grid[f"A{A}_k{best_k_for(A, S)}"]["bits"]}
             for A in [2, 4, 8, 16, 32, 64, 128, 264, V]]
    budgets[f"S{S}"] = curve
    best = min(curve, key=lambda r: r["bits"])
    print(f"[预算 S={S}] 最优 A={best['A']} k={best['k']} bits={best['bits']:.4f} (states={best['states']})")

S = 5000
NEAR = Eye(BMAPS[V], V, best_k_for(V, S))
NEAR.fit(tr)
FAR_A, FAR_K = 8, best_k_for(8, S)
FAR = Eye(BMAPS[FAR_A], FAR_A, FAR_K)
FAR.fit(tr)
b_near, b_far = bits_of(NEAR), bits_of(FAR)
print(f"近眼 A={NEAR.A} k={NEAR.k} states={NEAR.A**NEAR.k} bits={b_near:.4f}")
print(f"远眼 A={FAR.A} k={FAR.K if hasattr(FAR,'K') else FAR.k} states={FAR.A**FAR.k} bits={b_far:.4f}")


def seq_probs(eye):
    out, hist = [], list(tr)
    for c in te:
        out.append(eye.pdist(hist))
        hist.append(c)
    return out


pn, pf = seq_probs(NEAR), seq_probs(FAR)
mix = []
for lam in [i / 20 for i in range(21)]:
    s = 0.0
    for i, c in enumerate(te):
        p = lam * pn[i].get(c, P_UNK) + (1 - lam) * pf[i].get(c, P_UNK)
        s -= math.log2(max(p, P_UNK))
    mix.append({"lam": lam, "bits": round(s / len(te), 4)})
best_mix = min(mix, key=lambda r: r["bits"])
print(f"最优混合 lam={best_mix['lam']} bits={best_mix['bits']:.4f} "
      f"(近 {b_near:.4f} / 远 {b_far:.4f})")


def js(p, q):
    keys = set(p) | set(q)
    s = 0.0
    for c in keys:
        a, b = max(p.get(c, P_UNK), 1e-12), max(q.get(c, P_UNK), 1e-12)
        m = 0.5 * (a + b)
        s += 0.5 * a * math.log2(a / m) + 0.5 * b * math.log2(b / m)
    return s


div = [js(pn[i], pf[i]) for i in range(len(te))]
surp = [-math.log2(max(pn[i].get(te[i], P_UNK), P_UNK)) for i in range(len(te))]
mx, my = sum(div) / len(div), sum(surp) / len(surp)
num = sum((div[i] - mx) * (surp[i] - my) for i in range(len(div)))
den = math.sqrt(sum((d - mx) ** 2 for d in div) * sum((s - my) ** 2 for s in surp))
corr = num / den if den else 0.0
print(f"分歧 vs 近眼意外 Pearson r = {corr:.4f}")

idx = sorted(range(len(te)), key=lambda i: div[i])
q = len(idx) // 5
bins = []
for b in range(5):
    seg = idx[b * q:(b + 1) * q] if b < 4 else idx[4 * q:]
    bins.append({"bin": b, "div": round(sum(div[i] for i in seg) / len(seg), 4),
                 "surp_near": round(sum(surp[i] for i in seg) / len(seg), 4),
                 "surp_far": round(sum(-math.log2(max(pf[i].get(te[i], P_UNK), P_UNK))
                                       for i in seg) / len(seg), 4)})

dyn = []
for x in [5, 10, 20, 30, 50, 70]:
    m = int(len(te) * x / 100)
    top = set(sorted(range(len(te)), key=lambda i: -div[i])[:m])
    s_dyn = sum(-math.log2(max((pn[i] if i in top else pf[i]).get(te[i], P_UNK), P_UNK))
                for i in range(len(te))) / len(te)
    acc = []
    for rep in range(30):
        rnd = set(random.sample(range(len(te)), m))
        acc.append(sum(-math.log2(max((pn[i] if i in rnd else pf[i]).get(te[i], P_UNK), P_UNK))
                       for i in range(len(te))) / len(te))
    r = sum(acc) / len(acc)
    dyn.append({"x": x, "dyn": round(s_dyn, 4), "rand": round(r, 4), "gain": round(r - s_dyn, 4)})
    print(f"聚光 {x:2d}%: 按分歧 {s_dyn:.4f}  随机 {r:.4f}  差 {r - s_dyn:+.4f}")

json.dump({"corpus": {"chars": n, "train": ntr, "test": len(te), "vocab": V},
           "grid": grid, "budgets": budgets,
           "near": {"A": NEAR.A, "k": NEAR.k, "states": NEAR.A ** NEAR.k, "bits": round(b_near, 4)},
           "far": {"A": FAR.A, "k": FAR.k, "states": FAR.A ** FAR.k, "bits": round(b_far, 4)},
           "mix": mix, "best_mix": best_mix,
           "corr": round(corr, 4), "bins": bins, "dyn": dyn},
          open(f"{OUT}/result195.json", "w"), ensure_ascii=False, indent=2)
print("saved")
