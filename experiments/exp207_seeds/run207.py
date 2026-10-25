#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp207: 种子之间是厮杀还是趋同？
（优化版：bits 只需 P(target_char)，O(1)/位置；完整分布只在少量采样位上构造）
"""
import json, math, random
from collections import defaultdict

BASE = "/data/workspace/luoshen-o1"
POOL = f"{BASE}/evidence/失败模式库/判据核.md"
TARGET = f"{BASE}/experiments/exp180_record/u_side_full.txt"
OUT = f"{BASE}/experiments/exp207_seeds"

K = 2
SMOOTH = 0.1
N_SEEDS_LIST = [1, 2, 4, 8, 16]
FRAC = 0.02
N_REPEAT = 3
POOL_CAP = 150000      # 池截断
VOCAB_MIN_CNT = 5      # 池中出现>=5次才进 vocab（压缩词表）

def load(p, cap=None):
    with open(p, encoding="utf-8", errors="ignore") as f:
        t = f.read()
    return t[:cap] if cap else t

def train(text):
    ctx = defaultdict(lambda: defaultdict(float))
    tot = defaultdict(float)
    for i in range(len(text) - K):
        c = text[i:i+K]
        ctx[c][text[i+K]] += 1.0
        tot[c] += 1.0
    return ctx, tot

def p_one(model, c, ch, V):
    """只算一个字符的概率，O(1)"""
    ctx, tot = model
    d = ctx.get(c)
    n = tot.get(c, 0.0) if d else 0.0
    if not d:
        return 1.0 / V
    return (d.get(ch, 0.0) + SMOOTH) / (n + SMOOTH * V)

def full_dist(model, c, vocab, V):
    ctx, tot = model
    d = ctx.get(c)
    if not d:
        return {ch: 1.0 / V for ch in vocab}
    n = tot[c]
    return {ch: (d.get(ch, 0.0) + SMOOTH) / (n + SMOOTH * V) for ch in vocab}

def bits_of(model, test, V):
    s, n = 0.0, 0
    for i in range(len(test) - K):
        p = p_one(model, test[i:i+K], test[i+K], V)
        s += -math.log2(max(p, 1e-12)); n += 1
    return s / max(n, 1)

def ens_bits(models, test, V):
    s, n = 0.0, 0
    for i in range(len(test) - K):
        c = test[i:i+K]; ch = test[i+K]
        acc = sum(p_one(m, c, ch, V) for m in models)
        s += -math.log2(max(acc / len(models), 1e-12)); n += 1
    return s / max(n, 1)

def js(p, q):
    m = 0.0
    for k in set(p) | set(q):
        a, b = p.get(k, 0.0), q.get(k, 0.0)
        mu = (a + b) / 2 + 1e-12
        m += 0.5 * (a * math.log2((a + 1e-12) / mu) + b * math.log2((b + 1e-12) / mu))
    return m

def main():
    pool = load(POOL, POOL_CAP)
    target = load(TARGET)
    n = len(target)
    va_s, te_s = int(n * 0.5), int(n * 0.75)
    tgt_val, tgt_test = target[va_s:te_s], target[te_s:]

    cnt = defaultdict(int)
    for ch in pool:
        cnt[ch] += 1
    vocab = sorted({ch for ch, v in cnt.items() if v >= VOCAB_MIN_CNT} | set(target))
    V = len(vocab)
    # 采样位（用于一致率 / JS，避免全量展开）
    step = max(1, (len(tgt_test) - K) // 150)
    pos = list(range(0, len(tgt_test) - K, step))

    res = {"meta": {"K": K, "SMOOTH": SMOOTH, "FRAC": FRAC, "POOL_CAP": POOL_CAP,
                    "VOCAB_MIN_CNT": VOCAB_MIN_CNT, "pool_chars": len(pool),
                    "target_chars": len(target), "val_chars": len(tgt_val),
                    "test_chars": len(tgt_test), "vocab": V, "sample_pos": len(pos)},
           "perN": []}

    for N in N_SEEDS_LIST:
        rows = []
        for rep in range(N_REPEAT):
            rng = random.Random(1000 + rep * 97)
            L = int(len(pool) * FRAC)
            models = []
            for _ in range(N):
                st = rng.randrange(0, max(1, len(pool) - L))
                models.append(train(pool[st:st + L]))

            vb = [bits_of(m, tgt_val, V) for m in models]
            wi = min(range(len(vb)), key=lambda i: vb[i])
            kill_bits = bits_of(models[wi], tgt_test, V)
            ens_bits_v = ens_bits(models, tgt_test, V)
            avg_bits = sum(bits_of(m, tgt_test, V) for m in models) / N

            # 一致率 + JS（只在采样位上展开完整分布）
            tops = []
            for m in models:
                tops.append([max(full_dist(m, tgt_test[t:t+K], vocab, V).items(),
                                 key=lambda kv: kv[1])[0] for t in pos])
            ag = []
            for i in range(N):
                for j in range(i + 1, N):
                    ag.append(sum(1 for a, b in zip(tops[i], tops[j]) if a == b) / len(pos))
            mean_agree = sum(ag) / len(ag) if ag else 1.0

            jv = []
            for i in range(N):
                for j in range(i + 1, N):
                    s = 0.0
                    for t in pos[:40]:
                        c = tgt_test[t:t+K]
                        s += js(full_dist(models[i], c, vocab, V),
                                full_dist(models[j], c, vocab, V))
                    jv.append(s / max(1, len(pos[:40])))
            mean_js = sum(jv) / len(jv) if jv else 0.0

            rows.append({"rep": rep, "kill_bits": kill_bits, "ens_bits": ens_bits_v,
                         "avg_bits": avg_bits, "top1_agree": mean_agree, "mean_js": mean_js})
            print(f"  N={N} rep={rep} done", flush=True)

        agg = {k: sum(r[k] for r in rows) / len(rows)
               for k in ("kill_bits", "ens_bits", "avg_bits", "top1_agree", "mean_js")}
        res["perN"].append({"N": N, **agg, "raw": rows})

    full = train(pool)
    res["full_pool_bits"] = bits_of(full, tgt_test, V)
    res["uniform_bits"] = math.log2(V)
    res["random_top1_agree"] = 1.0 / V

    with open(f"{OUT}/result207.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    print("\n N | 厮杀(挑最优) | 协作(集成) | 平均单seed | top1一致率 | 平均JS")
    for r in res["perN"]:
        print(f"{r['N']:3d} | {r['kill_bits']:11.4f} | {r['ens_bits']:10.4f} |"
              f" {r['avg_bits']:10.4f} | {r['top1_agree']:10.4f} | {r['mean_js']:7.4f}")
    print(f"\n全池单模型 bits={res['full_pool_bits']:.4f}  均匀基线={res['uniform_bits']:.4f} "
          f" 随机一致率={res['random_top1_agree']:.4f}  V={V}")

if __name__ == "__main__":
    main()
