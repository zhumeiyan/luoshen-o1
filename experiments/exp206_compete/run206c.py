#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
206c: 生态位分化能救多样性吗？
206b 显示：不同 k 的 agent 竞争同一份资源、同一个测试集 → 三档规模全部 entropy→0、灭绝 3/4。
Gause 竞争排斥：生态位相同 → 必然排斥，改分配规则（absolute/marginal）都救不了。
本实验扫描"生态位分化度 d"：
  d = 每个 agent 独占数据段的比例（0=完全同质竞争，1=完全分化）
看共存（entropy / 灭绝数）如何随 d 变化。
"""
import json, os, math, random
from collections import defaultdict

BASE = "/data/workspace/luoshen-o1"
CORPUS = f"{BASE}/experiments/exp180_record/u_side_full.txt"
OUT = f"{BASE}/experiments/exp206_compete"
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


def sample_text(src, n_tok, rng, seg=40):
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


def main():
    lines = [l.strip() for l in open(CORPUS, encoding="utf-8") if l.strip()]
    nt = max(4, int(len(lines) * 0.2))
    pool = "\n".join(lines[:-nt])
    test = "\n".join(lines[-nt:])
    gv = set(pool) | set(test)

    NAG = 4
    L = len(pool)
    seg_len = L // NAG
    segs = [pool[i * seg_len:(i + 1) * seg_len] for i in range(NAG)]
    if NAG * seg_len < L:
        segs[-1] += pool[NAG * seg_len:]

    B = 24000
    rounds = 10
    beta = 3.0
    out = {"n_agents": NAG, "B": B, "rounds": rounds, "scan": {}}

    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        for seed in (SEED, SEED + 1, SEED + 2):
            rng = random.Random(seed)
            shares = {i: 1.0 / NAG for i in range(NAG)}
            ents = []
            for r in range(rounds):
                models = {}
                for i in range(NAG):
                    tok = int(shares[i] * B)
                    m = NGram(2, gv=gv)
                    m.train(sample_text(segs[i], int(tok * d), rng))
                    m.train(sample_text(pool, int(tok * (1 - d)), rng))
                    models[i] = m
                ents.append(round(entropy(list(shares.values())), 5))
                ab = aligned_bits(list(models.values()), test)
                fit = {i: -ab[id(models[i])] for i in range(NAG)}
                v = [fit[i] for i in range(NAG)]
                mu = sum(v) / len(v)
                sd = (sum((x - mu) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
                new = {i: shares[i] * math.exp(beta * (fit[i] - mu) / sd) for i in range(NAG)}
                tot = sum(new.values())
                shares = {i: new[i] / tot for i in range(NAG)}
            fm = []
            for i in range(NAG):
                tok = int(shares[i] * B)
                m = NGram(2, gv=gv)
                m.train(sample_text(segs[i], int(tok * d), random.Random(seed + 5)))
                m.train(sample_text(pool, int(tok * (1 - d)), random.Random(seed + 6)))
                fm.append(m)
            key = f"d={d}"
            out["scan"].setdefault(key, []).append({
                "seed": seed,
                "entropy_end": round(entropy(list(shares.values())), 5),
                "n_extinct": sum(1 for i in range(NAG) if shares[i] < 0.01),
                "final_shares": [round(shares[i], 5) for i in range(NAG)],
                "system_bits": round(ens_bits(fm, test), 5),
            })
        rows = out["scan"][f"d={d}"]
        ee = [x["entropy_end"] for x in rows]
        nx = [x["n_extinct"] for x in rows]
        sb = [x["system_bits"] for x in rows]
        out["scan"][f"d={d}"] = {
            "runs": rows,
            "entropy_end_mean": round(sum(ee) / len(ee), 5),
            "n_extinct_mean": round(sum(nx) / len(nx), 3),
            "system_bits_mean": round(sum(sb) / len(sb), 5),
        }
        print(f"[d={d}] entropy_end={out['scan'][f'd={d}']['entropy_end_mean']} extinct={out['scan'][f'd={d}']['n_extinct_mean']} sys_bits={out['scan'][f'd={d}']['system_bits_mean']}")

    with open(f"{OUT}/result206c.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("[saved]", f"{OUT}/result206c.json")


if __name__ == "__main__":
    main()
