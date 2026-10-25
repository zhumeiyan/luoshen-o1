#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp207b: 干净对照 —— 同样字符预算，来源不同（公共网络 vs 私有记忆）"""
import json, math, random, os, time

K = 2
ALPHA = 0.10
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/data/workspace/luoshen-o1"

def read(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()

def clean(s):
    out = []
    for ch in s:
        if ch.isspace():
            continue
        o = ord(ch)
        if 0x4e00 <= o <= 0x9fff or o < 128 or ch in "，。！？、；：""''（）《》—…·":
            out.append(ch)
    return "".join(out)

class NG:
    __slots__ = ("k", "alpha", "ctx", "tot")
    def __init__(self, k=K, alpha=ALPHA):
        self.k = k; self.alpha = alpha; self.ctx = {}; self.tot = {}
    def train(self, s):
        s = ("^" * self.k) + s
        ctx, tot, a, kk = self.ctx, self.tot, self.alpha, self.k
        for i in range(kk, len(s)):
            c = s[i - kk:i]; n = s[i]
            d = ctx.get(c)
            if d is None:
                d = ctx[c] = {}; tot[c] = 0
            d[n] = d.get(n, 0) + 1; tot[c] += 1
    def prob(self, ctx, ch, V):
        d = self.ctx.get(ctx)
        t = self.tot.get(ctx, 0) if d is not None else 0
        c = d.get(ch, 0) if d is not None else 0
        return (c + self.alpha) / (t + self.alpha * V)

def eval_mix(models, weights, test, V, k=K):
    s = ("^" * k) + test
    tot = 0.0; n = 0; hit = 0
    for i in range(k, len(s)):
        ctx = s[i - k:i]; ch = s[i]
        p = 0.0; best_p = -1.0; best_ch = None
        for wi, m in enumerate(models):
            w = weights[wi]
            if w == 0.0:
                continue
            d = m.ctx.get(ctx); t = m.tot.get(ctx, 0) if d is not None else 0
            pr = (d.get(ch, 0) if d is not None else 0)
            p += w * (pr + m.alpha) / (t + m.alpha * V)
            if d is not None:
                for c2, cnt in d.items():
                    pv = (cnt + m.alpha) / (t + m.alpha * V)
                    if pv > best_p:
                        best_p = pv; best_ch = c2
        tot += -math.log2(max(p, 1e-12)); n += 1
        if best_ch == ch:
            hit += 1
    return tot / max(n, 1), hit / max(n, 1)

def top1_of(m, ctx, V):
    d = m.ctx.get(ctx)
    if d is None:
        return None
    t = m.tot.get(ctx, 0)
    bc = None; bp = -1.0
    for c, cnt in d.items():
        pv = (cnt + m.alpha) / (t + m.alpha * V)
        if pv > bp:
            bp = pv; bc = c
    return bc

t0 = time.time()
PUB = clean(read(os.path.join(ROOT, "evidence/失败模式库/判据核.md")))
USR = clean(read(os.path.join(ROOT, "experiments/exp180_record/u_side_full.txt")))
cut = int(len(USR) * 0.8)
PRIV, TEST = USR[:cut], USR[cut:]
V = len(set(PUB) | set(PRIV) | set(TEST))

M_P = NG(); M_P.train(PUB)
b_pub, a_pub = eval_mix([M_P], [1.0], TEST, V)
M_full = NG(); M_full.train(PRIV)
b_one, a_one = eval_mix([M_P, M_full], [0.5, 0.5], TEST, V)
print(f"[anchor] pub={b_pub:.4f} pub+fullpriv={b_one:.4f} V={V} TEST={len(TEST)}", flush=True)

BUDGET = len(PRIV)
LAM = 0.5
out = {"config": {"K": K, "ALPHA": ALPHA, "V": V, "BUDGET": BUDGET, "LAM": LAM,
                  "PUB": len(PUB), "PRIV": len(PRIV), "TEST": len(TEST),
                  "pub_bits": b_pub, "pub_acc": a_pub,
                  "one_bits": b_one, "one_acc": a_one}, "rows": []}

def make_seeds(src, N, rnd):
    parts = []
    if src == "priv":
        for j in range(N):
            parts.append(PRIV[j::N])
    else:
        for j in range(N):
            st = rnd.randrange(0, max(1, len(PUB) - BUDGET))
            parts.append(PUB[st:st + BUDGET])
    return parts

def divergence(models, nmax=16):
    idxs = list(range(len(models)))
    if len(idxs) > nmax:
        random.shuffle(idxs); idxs = idxs[:nmax]
    sctx = [TEST[i:i + K] for i in range(0, min(len(TEST) - K, 200), 11)]
    agree = 0; pairs = 0
    for c in sctx:
        preds = [top1_of(models[i], c, V) for i in idxs]
        for x in range(len(preds)):
            for y in range(x + 1, len(preds)):
                pairs += 1
                if preds[x] == preds[y]:
                    agree += 1
    return 1 - agree / max(pairs, 1)

for src in ("pub", "priv"):
    for N in (1, 2, 4, 8, 16):
        accs = {"winner": 0, "ens": 0, "div": 0, "chars_per_seed": 0, "mean": 0}
        for sd in (0, 1, 2):
            rnd = random.Random(sd)
            parts = make_seeds(src, N, rnd)
            ms = []
            for p in parts:
                m = NG(); m.train(p); ms.append(m)
            bits_j = [eval_mix([M_P, m], [1 - LAM, LAM], TEST, V)[0] for m in ms]
            b_ens, _ = eval_mix([M_P] + ms, [1 - LAM] + [LAM / N] * N, TEST, V)
            row = {"src": src, "N": N, "seed": sd, "winner": min(bits_j),
                   "mean": sum(bits_j) / N, "ens": b_ens,
                   "spread": max(bits_j) - min(bits_j),
                   "div": divergence(ms) if N > 1 else 0.0,
                   "chars_per_seed": sum(len(p) for p in parts) / N}
            out["rows"].append(row)
            for kk in accs:
                accs[kk] += row[kk]
        print(f"[{src} N={N:3d}] winner={accs['winner']/3:.4f} ens={accs['ens']/3:.4f} "
              f"div={accs['div']/3:.3f} chars={accs['chars_per_seed']/3:.0f} ({time.time()-t0:.0f}s)", flush=True)

def run_war(N, gens, seed):
    rnd = random.Random(seed)
    parts = [PRIV[j::N] for j in range(N)]
    hist = []
    for g in range(gens):
        ms = []
        for p in parts:
            m = NG(); m.train(p); ms.append(m)
        bj = [eval_mix([M_P, m], [1 - LAM, LAM], TEST, V)[0] for m in ms]
        order = sorted(range(N), key=lambda i: bj[i])
        ks = max(1, N // 4)
        surv, dead = order[:ks], order[ks:]
        if dead:
            merged = "".join(parts[i] for i in dead)
            per = max(1, len(merged) // ks)
            for t, i in enumerate(surv):
                parts[i] = parts[i] + merged[t * per:(t + 1) * per]
        new = [parts[i] for i in surv]
        while len(new) < N:
            new.append(parts[rnd.choice(surv)])
        parts = new
        ms2 = []
        for p in parts:
            m = NG(); m.train(p); ms2.append(m)
        b2 = [eval_mix([M_P, m], [1 - LAM, LAM], TEST, V)[0] for m in ms2]
        hist.append({"gen": g, "best": min(b2), "mean": sum(b2) / N,
                     "unique": len(set(parts))})
    return hist

out["war"] = {}
for sd in (0, 1, 2):
    h = run_war(16, 8, sd)
    out["war"][f"s{sd}"] = h
    print(f"[war16 s={sd}] " + " ".join(f"{x['best']:.3f}" for x in h)
          + f"   | N=1直接全量 = {b_one:.3f}", flush=True)

with open(os.path.join(HERE, "result207b.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"[done] {time.time()-t0:.0f}s")
