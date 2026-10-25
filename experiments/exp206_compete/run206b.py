#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
206b: 环境资源充足度决定生态结构
206 主实验里 A 出现 k=1 垄断、k=2 灭绝，与 176 号"k=2 最优"矛盾。
假设：不是矛盾，是语料太小（N/V=6.5）导致高阶模型数据稀疏必输。
本实验做"语料规模梯度"，看 winner k 与多样性如何随资源变化。
"""
import json, os, math, random
from collections import defaultdict

BASE = "/data/workspace/luoshen-o1"
CORPUS = f"{BASE}/experiments/exp180_record/u_side_full.txt"
JK = f"{BASE}/evidence/失败模式库/判据核.md"
OUT = f"{BASE}/experiments/exp206_compete"
os.makedirs(OUT, exist_ok=True)
SEED = 20261019


class NGram:
    def __init__(self, k, alpha=0.05, gv=None):
        self.k, self.alpha, self.gv = k, alpha, (gv or set())
        self.c = defaultdict(lambda: defaultdict(float))
        self.t = defaultdict(float)
        self.vocab = set()

    def train(self, text):
        k = self.k
        c, t, vb = self.c, self.t, self.vocab
        for i in range(len(text) - k):
            ctx, ch = text[i:i + k], text[i + k]
            c[ctx][ch] += 1.0
            t[ctx] += 1.0
            vb.add(ch)

    def prob(self, ctx, ch):
        V = max(len(self.vocab | self.gv), 1)
        cc = self.c.get(ctx)
        return ((cc.get(ch, 0.0) if cc else 0.0) + self.alpha) / (self.t.get(ctx, 0.0) + self.alpha * V)


def aligned_bits(models, text):
    if not models:
        return {}
    kmax = max(m.k for m in models)
    res = {}
    for m in models:
        tot, n = 0.0, 0
        for t in range(kmax, len(text)):
            tot += -math.log2(max(m.prob(text[t - m.k:t], text[t]), 1e-12))
            n += 1
        res[id(m)] = (tot / n) if n else 99.0
    return res


def ens_bits(models, text):
    if not models:
        return None
    kmax = max(m.k for m in models)
    if len(text) <= kmax:
        return None
    w = 1.0 / len(models)
    tot, n = 0.0, 0
    for t in range(kmax, len(text)):
        p = sum(w * m.prob(text[t - m.k:t], text[t]) for m in models)
        tot += -math.log2(max(p, 1e-12))
        n += 1
    return tot / n


def sample_text(src, n_tok, rng, seg=60):
    if n_tok <= 0 or not src:
        return ""
    if len(src) <= seg:
        return (src * (int(n_tok // len(src)) + 1))[:n_tok]
    out, got = [], 0
    while got < n_tok:
        i = rng.randrange(0, len(src) - seg)
        out.append(src[i:i + seg])
        got += seg
    return "".join(out)[:n_tok]


def entropy(sh):
    s = [x for x in sh if x > 1e-12]
    tot = sum(s)
    if tot <= 0:
        return 0.0
    return -sum((x / tot) * math.log(x / tot) for x in s)


def step(shares, fit, beta):
    ks = list(shares.keys())
    v = [fit[k] for k in ks]
    mu = sum(v) / len(v)
    sd = (sum((x - mu) ** 2 for x in v) / len(v)) ** 0.5
    if sd < 1e-12:
        return dict(shares)
    new = {k: shares[k] * math.exp(beta * (fit[k] - mu) / sd) for k in ks}
    tot = sum(new.values())
    return {k: new[k] / tot for k in ks}


def replicator(pool, test, gv, ks, B, rounds, beta, seed, rule="absolute"):
    rng = random.Random(seed)
    shares = {k: 1.0 / len(ks) for k in ks}
    ents = []
    for r in range(rounds):
        models = {}
        for k in ks:
            m = NGram(k, gv=gv)
            m.train(sample_text(pool, int(shares[k] * B), rng))
            models[k] = m
        ents.append(round(entropy([shares[k] for k in ks]), 5))
        ab = aligned_bits([models[k] for k in ks], test)
        if rule == "absolute":
            fit = {k: -ab[id(models[k])] for k in ks}
        else:
            full = ens_bits([models[k] for k in ks], test)
            fit = {}
            for k in ks:
                sub = ens_bits([models[j] for j in ks if j != k], test)
                fit[k] = (sub - full) if (sub is not None and full is not None) else 0.0
        shares = step(shares, fit, beta)
    fm = {}
    for k in ks:
        m = NGram(k, gv=gv)
        m.train(sample_text(pool, int(shares[k] * B), random.Random(seed + 77)))
        fm[k] = m
    ab = aligned_bits([fm[k] for k in ks], test)
    win = max(ks, key=lambda k: shares[k])
    return {
        "winner_k": win,
        "winner_share": round(shares[win], 5),
        "final_shares": {str(k): round(shares[k], 5) for k in ks},
        "final_bits": {str(k): round(ab[id(fm[k])], 5) for k in ks},
        "entropy_start": ents[0], "entropy_end": round(entropy([shares[k] for k in ks]), 5),
        "entropy_history": ents,
        "system_bits": round(ens_bits([fm[k] for k in ks], test), 5) if ens_bits([fm[k] for k in ks], test) else None,
        "n_extinct": sum(1 for k in ks if shares[k] < 0.01),
    }


def build(name):
    if name == "small":
        lines = [l.strip() for l in open(CORPUS, encoding="utf-8") if l.strip()]
    else:
        jk = open(JK, encoding="utf-8").read()
        cap = {"mid": 30000, "large": 80000}[name]
        jk = jk[:cap]
        lines = [l for l in jk.split("\n") if l.strip()]
    nt = max(4, int(len(lines) * 0.2))
    tr, te = lines[:-nt], lines[-nt:]
    pool, test = "\n".join(tr), "\n".join(te)
    gv = set(pool) | set(test)
    return pool, test, gv, len(pool), len(gv)


def main():
    ks = (1, 2, 3, 4)
    out = {"ks": list(ks), "scale_scan": {}, "large_allocation": {}}
    for name in ("small", "mid", "large"):
        pool, test, gv, npool, nv = build(name)
        B = max(20000, int(npool * 1.5))
        r = replicator(pool, test, gv, ks, B, rounds=6, beta=3.0, seed=SEED)
        r["corpus_chars"] = npool
        r["vocab"] = nv
        r["N_over_V"] = round(npool / max(nv, 1), 3)
        r["B"] = B
        out["scale_scan"][name] = r
        print(f"[{name}] N={npool} V={nv} N/V={r['N_over_V']} -> winner k={r['winner_k']} share={r['winner_share']} entropy {r['entropy_start']}->{r['entropy_end']} extinct={r['n_extinct']}")
    # 大语料下 absolute vs marginal
    pool, test, gv, npool, nv = build("large")
    B = max(20000, int(npool * 1.5))
    for rule in ("absolute", "marginal"):
        r = replicator(pool, test, gv, ks, B, rounds=6, beta=3.0, seed=SEED, rule=rule)
        out["large_allocation"][rule] = r
        print(f"[large/{rule}] winner k={r['winner_k']} entropy_end={r['entropy_end']} extinct={r['n_extinct']} sys_bits={r['system_bits']}")
    with open(f"{OUT}/result206b.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("[saved]", f"{OUT}/result206b.json")


if __name__ == "__main__":
    main()
