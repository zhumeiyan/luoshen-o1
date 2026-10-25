#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
206: 竞争、物种多样性与厮杀
A: 复制子动力学 —— 不同记忆阶数 k 争夺同一份资源，是单一种群还是共存？
B: 保险假说 —— 环境漂移下，单一最优 vs 多样性组合，谁活？
C: 分配规则 —— 按"绝对表现"分配 vs 按"边际贡献(留一法)"分配，谁保住多样性、谁让系统更强？
D: 我的策略（追自己最意外的=192/198 所称"瞎贪婪"）在竞争中会不会第一个灭绝？

修复记录（第一轮跑出来的三个 bug，发布前必须修）：
  B1 空模型 vocab 为空 → 平滑 prob=1.0 → bits=0.0 伪装成完美。改用全局字符表。
  B2 bootstrap 小样本逐字随机采样 → 文本被打乱，资源多寡变成"结构破坏程度"。改为连续片段采样。
  B3 marginal 的 fit 符号写反；D 每轮用空模型打分导致 surprise/progress 退化成同一策略。
"""
import json, os, math, random
from collections import defaultdict

BASE = "/data/workspace/luoshen-o1"
CORPUS = f"{BASE}/experiments/exp180_record/u_side_full.txt"
OUT = f"{BASE}/experiments/exp206_compete"
os.makedirs(OUT, exist_ok=True)

SEED = 20261019
random.seed(SEED)

lines = [l.strip() for l in open(CORPUS, encoding="utf-8") if l.strip()]
n_test = max(4, int(len(lines) * 0.2))
train_lines, test_lines = lines[:-n_test], lines[-n_test:]
pool = "\n".join(train_lines)
test = "\n".join(test_lines)
GVOCAB = set(pool) | set(test)          # B1: 全局字符表
print(f"[corpus] lines={len(lines)} train_chars={len(pool)} test_chars={len(test)} vocab={len(GVOCAB)}")


class NGram:
    def __init__(self, k, alpha=0.05, gvocab=None):
        self.k, self.alpha = k, alpha
        self.gv = gvocab or set()
        self.c = defaultdict(lambda: defaultdict(float))
        self.t = defaultdict(float)
        self.vocab = set()

    def train(self, text):
        k = self.k
        for i in range(len(text) - k):
            ctx, ch = text[i:i + k], text[i + k]
            self.c[ctx][ch] += 1.0
            self.t[ctx] += 1.0
            self.vocab.add(ch)

    def prob(self, ctx, ch):
        V = max(len(self.vocab | self.gv), 1)     # B1
        c = self.c.get(ctx)
        t = self.t.get(ctx, 0.0)
        got = c.get(ch, 0.0) if c else 0.0
        return (got + self.alpha) / (t + self.alpha * V)

    def bits(self, text):
        k = self.k
        if len(text) <= k:
            return math.log2(max(len(self.vocab | self.gv), 2))
        tot, n = 0.0, 0
        for i in range(len(text) - k):
            tot += -math.log2(self.prob(text[i:i + k], text[i + k]))
            n += 1
        return tot / max(n, 1)


def aligned_bits(models, text):
    """在同一组目标字符上评估每个模型（不同 k 才可公平比较）"""
    if not models:
        return {}
    kmax = max(m.k for m in models)
    res = {}
    for m in models:
        tot, n = 0.0, 0
        for t in range(kmax, len(text)):
            tot += -math.log2(max(m.prob(text[t - m.k:t], text[t]), 1e-12))
            n += 1
        res[id(m)] = (tot / n) if n else math.log2(max(len(m.vocab | m.gv), 2))
    return res


def ens_bits(models, text):
    """不同阶集成：所有模型预测同一目标字符，各自用自己长度的上下文"""
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
    """B2: 连续片段采样，保持序列结构。资源多 = 见到更多连续经验。"""
    if n_tok <= 0 or not src:
        return ""
    if len(src) <= seg:
        reps = int(n_tok // len(src)) + 1
        return (src * reps)[:n_tok]
    out, got = [], 0
    while got < n_tok:
        i = rng.randrange(0, len(src) - seg)
        out.append(src[i:i + seg])
        got += seg
    return "".join(out)[:n_tok]


def entropy(shares):
    s = [x for x in shares if x > 1e-12]
    tot = sum(s)
    if tot <= 0:
        return 0.0
    p = [x / tot for x in s]
    return -sum(x * math.log(x) for x in p)


def step(shares, fit, beta):
    ks = list(shares.keys())
    vals = [fit[k] for k in ks]
    mu = sum(vals) / len(vals)
    sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    if sd < 1e-12:
        return {k: shares[k] for k in ks}
    new = {k: shares[k] * math.exp(beta * (fit[k] - mu) / sd) for k in ks}
    tot = sum(new.values())
    return {k: new[k] / tot for k in ks}


# ---------------- A: 复制子动力学 ----------------
def partA(ks=(1, 2, 3, 4, 6, 8), B=20000, rounds=14, beta=3.0, seed=SEED):
    rng = random.Random(seed)
    shares = {k: 1.0 / len(ks) for k in ks}
    hist, ents = [], []
    for r in range(rounds):
        models = {}
        for k in ks:
            m = NGram(k, gvocab=GVOCAB)
            m.train(sample_text(pool, int(shares[k] * B), rng))
            models[k] = m
        ab = aligned_bits([models[k] for k in ks], test)
        fit = {k: -ab[id(models[k])] for k in ks}
        hist.append({str(k): round(shares[k], 5) for k in ks})
        ents.append(round(entropy([shares[k] for k in ks]), 5))
        shares = step(shares, fit, beta)
    fm = {}
    for k in ks:
        m = NGram(k, gvocab=GVOCAB)
        m.train(sample_text(pool, int(shares[k] * B), random.Random(seed + 999)))
        fm[k] = m
    ab = aligned_bits([fm[k] for k in ks], test)
    winner = max(ks, key=lambda k: shares[k])
    return {
        "ks": list(ks), "rounds": rounds, "B": B,
        "shares_history": hist, "entropy_history": ents,
        "final_shares": {str(k): round(shares[k], 5) for k in ks},
        "final_bits": {str(k): round(ab[id(fm[k])], 5) for k in ks},
        "winner_k": winner, "winner_share": round(shares[winner], 5),
        "entropy_start": ents[0], "entropy_end": ents[-1],
        "extinct": {str(k): (shares[k] < 0.01) for k in ks},
    }


# ---------------- B: 保险假说 ----------------
def partB(ks=(1, 2, 3, 4, 6, 8), B=20000, seed=SEED):
    half = max(1, len(train_lines) // 2)
    A_pool = "\n".join(train_lines[:half])
    B_test = "\n".join(train_lines[half:] + test_lines)
    rng = random.Random(seed)
    models = {}
    for k in ks:
        m = NGram(k, gvocab=GVOCAB)
        m.train(sample_text(A_pool, B, rng))
        models[k] = m
    ab_orig = aligned_bits([models[k] for k in ks], test)
    mono_k = min(ks, key=lambda k: ab_orig[id(models[k])])
    ab_shift = aligned_bits([models[k] for k in ks], B_test)
    mono_shift = ab_shift[id(models[mono_k])]
    port_shift = ens_bits([models[k] for k in ks], B_test)
    copies = []
    for i in range(3):
        m = NGram(mono_k, gvocab=GVOCAB)
        m.train(sample_text(A_pool, B, random.Random(seed + i)))
        copies.append(m)
    pseudo_shift = ens_bits(copies, B_test)
    return {
        "shift_test_chars": len(B_test),
        "mono_k": mono_k,
        "mono_bits_under_shift": round(mono_shift, 5),
        "portfolio_bits_under_shift": round(port_shift, 5),
        "pseudo_diversity_bits_under_shift": round(pseudo_shift, 5),
        "diversity_gain": round(mono_shift - port_shift, 5),
        "pseudo_vs_true": round(pseudo_shift - port_shift, 5),
        "note": "pseudo=三个同阶副本(伪多样性,无差异); portfolio=不同阶真多样性",
    }


# ---------------- C: 分配规则 ----------------
def partC(ks=(1, 2, 3, 4, 6, 8), B=20000, rounds=10, beta=3.0, seed=SEED):
    res = {}
    for rule in ("absolute", "marginal"):
        rng = random.Random(seed)
        shares = {k: 1.0 / len(ks) for k in ks}
        ents = []
        for r in range(rounds):
            models = {}
            for k in ks:
                m = NGram(k, gvocab=GVOCAB)
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
                    # B3: 拿掉我系统变差多少 = 我的边际贡献（越大越好）
                    fit[k] = (sub - full) if (sub is not None and full is not None) else 0.0
            shares = step(shares, fit, beta)
        fm = {}
        for k in ks:
            m = NGram(k, gvocab=GVOCAB)
            m.train(sample_text(pool, int(shares[k] * B), random.Random(seed + 77)))
            fm[k] = m
        sys_bits = ens_bits([fm[k] for k in ks], test)
        ab_f = aligned_bits([fm[k] for k in ks], test)
        solo = {str(k): round(ab_f[id(fm[k])], 5) for k in ks}
        alive_solo = {k: v for k, v in solo.items() if shares[int(k)] >= 0.01}
        res[rule] = {
            "final_shares": {str(k): round(shares[k], 5) for k in ks},
            "entropy_start": ents[0], "entropy_end": ents[-1],
            "entropy_history": ents,
            "extinct": {str(k): (shares[k] < 0.01) for k in ks},
            "system_bits": round(sys_bits, 5),
            "solo_bits_alive_only": alive_solo,
            "best_alive_single_bits": round(min(alive_solo.values()), 5) if alive_solo else None,
        }
    res["entropy_end"] = {"absolute": res["absolute"]["entropy_end"], "marginal": res["marginal"]["entropy_end"]}
    res["system_bits"] = {"absolute": res["absolute"]["system_bits"], "marginal": res["marginal"]["system_bits"]}
    res["system_better_under"] = ("marginal" if res["marginal"]["system_bits"] < res["absolute"]["system_bits"] else "absolute")
    return res


# ---------------- D: 策略竞争 ----------------
def partD(B=18000, rounds=10, beta=3.0, seed=SEED, nchunk=40):
    L = len(pool)
    cl = max(30, L // nchunk)
    chunks = [pool[i * cl:(i + 1) * cl] for i in range(nchunk) if i * cl < L]
    cut = max(1, len(chunks) // 5)
    priv = chunks[:cut]
    shared = chunks[cut:]

    def sample_for(s, prev, n_tok, rng):
        if s == "niche":
            return sample_text("\n".join(priv), n_tok, rng)
        if s == "random" or prev is None:
            return sample_text("\n".join(shared), n_tok, rng)
        scored = [(prev.bits(ch), ch) for ch in shared if len(ch) > 5]
        if not scored:
            return sample_text("\n".join(shared), n_tok, rng)
        scored.sort(key=lambda x: x[0], reverse=(s == "surprise"))
        take = scored[:max(1, len(scored) // 2)]
        return sample_text("".join(c for _, c in take), n_tok, rng)

    strats = ["random", "surprise", "progress", "niche"]
    shares = {s: 1.0 / len(strats) for s in strats}
    prev = {s: None for s in strats}          # B3: 跨轮保留模型用于打分
    ents, hist = [], []
    for r in range(rounds):
        models = {}
        for s in strats:
            m = NGram(2, gvocab=GVOCAB)
            m.train(sample_for(s, prev[s], int(shares[s] * B), random.Random(seed + r * 31 + len(s))))
            models[s] = m
        prev = models
        ab = aligned_bits([models[s] for s in strats], test)
        fit = {s: -ab[id(models[s])] for s in strats}
        hist.append({s: round(shares[s], 5) for s in strats})
        ents.append(round(entropy([shares[s] for s in strats]), 5))
        shares = step(shares, fit, beta)
    ab = aligned_bits([models[s] for s in strats], test)
    return {
        "strategies": strats, "rounds": rounds,
        "shares_history": hist, "entropy_history": ents,
        "final_shares": {s: round(shares[s], 5) for s in strats},
        "final_bits": {s: round(ab[id(models[s])], 5) for s in strats},
        "extinct": {s: (shares[s] < 0.01) for s in strats},
        "entropy_start": ents[0], "entropy_end": ents[-1],
    }


def main():
    out = {
        "corpus": {"lines": len(lines), "train_chars": len(pool), "test_chars": len(test), "vocab": len(GVOCAB)},
        "A_replicator": partA(),
        "B_insurance": partB(),
        "C_allocation": partC(),
        "D_strategy": partD(),
    }
    with open(f"{OUT}/result206.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("[saved]", f"{OUT}/result206.json")


if __name__ == "__main__":
    main()
