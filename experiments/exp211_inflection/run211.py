# -*- coding: utf-8 -*-
"""
211: 找拐点 —— 独特性权重 β 的临界值
种群从最原子层 k=0 起步，往上厮杀。
适应度 = 预测增益 + β × 独特性
扫 β，找"多样性从 0 跳起来"的那个点，以及预测力开始掉的那个点。
"""
import json, random, math, os, collections

KMAX = 5
NA   = 12          # agent 数
GENS = 15
TRAIN = 30000      # 每 agent 训练字符
TEST  = 5000       # 共享测试集字符

def load_corpus():
    p = "/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md"
    t = open(p, encoding="utf-8", errors="ignore").read()
    t = "".join(ch for ch in t if ord(ch) > 31)
    return t

def build_model(text, k, lamb=0.05):
    """k阶马尔可夫，返回 (ctx->Counter, vocab)"""
    if k == 0:
        cnt = collections.Counter(text)
        V = len(cnt)
        tot = sum(cnt.values()) + lamb * V
        return ({}, cnt, V, tot, k)
    d = collections.defaultdict(collections.Counter)
    for i in range(k, len(text)):
        d[text[i-k:i]][text[i]] += 1
    vocab = collections.Counter(text)
    V = len(vocab)
    return (d, vocab, V, None, k)

def prob(m, ctx, ch):
    d, vocab, V, tot, k = m
    if k == 0:
        return (vocab[ch] + 0.05) / tot
    c = d.get(ctx)
    if c is None:
        return (vocab[ch] + 0.05) / (sum(vocab.values()) + 0.05 * V)
    s = sum(c.values()) + 0.05 * V
    return (c[ch] + 0.05) / s

def evaluate(m, test):
    """返回 (top1正确布尔列表, bits总和)"""
    d, vocab, V, tot, k = m
    ok = []
    bits = 0.0
    n = len(test)
    for i in range(KMAX, n):
        ctx = test[i-k:i] if k > 0 else ""
        ch  = test[i]
        p = prob(m, ctx, ch)
        bits -= math.log2(p)
        # top1
        if k == 0:
            best = vocab.most_common(1)[0][0]
        else:
            c = d.get(ctx)
            if c:
                best = c.most_common(1)[0][0]
            else:
                best = vocab.most_common(1)[0][0]
        ok.append(1 if best == ch else 0)
    return ok, bits / max(1, len(ok))

def main():
    text = load_corpus()
    print(f"[corpus] {len(text)} chars, vocab {len(set(text))}")
    # 划分：训练池 / 测试集
    split = len(text) - TEST
    pool  = text[:split]
    test  = text[split:]
    print(f"[split] pool={len(pool)} test={len(test)}")

    results = []
    BETAS = [0.0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5, 0.75, 1.0, 1.5, 2.5]
    SEEDS = [1, 2, 3]

    for seed in SEEDS:
        rng = random.Random(seed)
        # 每个 agent 一个固定的 bootstrap 样本（run 内固定）
        samples = []
        for a in range(NA):
            start = rng.randrange(0, max(1, len(pool) - TRAIN))
            samples.append(pool[start:start + TRAIN])
        # 预计算 (agent, k) -> ok向量, bits
        cache = {}
        for a in range(NA):
            for k in range(KMAX + 1):
                m = build_model(samples[a], k)
                ok, bits = evaluate(m, test)
                cache[(a, k)] = (ok, bits)
        T = len(cache[(0, 0)][0])
        print(f"[seed {seed}] cache done, T={T}")

        for beta in BETAS:
            rng2 = random.Random(seed * 1000 + int(beta * 100))
            # 初始全员 k=0（最原子层）
            pop = [0] * NA
            hist = []
            for g in range(GENS):
                # 计算每个 agent 的正确位置集合
                oks = [cache[(a, pop[a])][0] for a in range(NA)]
                # 独特性 = 我对而多数人错的位置比例
                uniq = []
                for a in range(NA):
                    cnt = 0
                    others = 0
                    for t in range(T):
                        if oks[a][t]:
                            others += 1
                            nok = sum(1 for b in range(NA) if b != a and oks[b][t])
                            if nok == 0:
                                cnt += 1
                    uniq.append(cnt / max(1, others))
                fit = []
                for a in range(NA):
                    acc = sum(oks[a]) / T
                    fit.append(acc + beta * uniq[a])
                hist.append({"gen": g, "pop": list(pop),
                             "acc": round(sum(sum(o) for o in oks) / (NA * T), 5),
                             "uniq": round(sum(uniq) / NA, 5),
                             "fit": round(sum(fit) / NA, 5)})
                # 轮盘赌复制 + 突变
                mn = min(fit)
                w = [f - mn + 1e-6 for f in fit]
                s = sum(w)
                newpop = []
                for _ in range(NA):
                    r = rng2.random() * s
                    acc_w = 0
                    pick = 0
                    for i, wi in enumerate(w):
                        acc_w += wi
                        if acc_w >= r:
                            pick = i
                            break
                    k = pop[pick]
                    if rng2.random() < 0.25:
                        k = max(0, min(KMAX, k + (1 if rng2.random() < 0.5 else -1)))
                    newpop.append(k)
                pop = newpop
            # 终代统计
            cnt = collections.Counter(pop)
            H = -sum((v / NA) * math.log2(v / NA) for v in cnt.values())
            oks = [cache[(a, pop[a])][0] for a in range(NA)]
            acc = sum(sum(o) for o in oks) / (NA * T)
            bits = sum(cache[(a, pop[a])][1] for a in range(NA)) / NA
            results.append({
                "seed": seed, "beta": beta,
                "final_pop": list(pop),
                "k_hist": dict(cnt),
                "entropy": round(H, 4),
                "n_layers": len(cnt),
                "acc": round(acc, 5),
                "bits": round(bits, 5),
                "k_max_reached": max(pop),
                "hist": hist,
            })
            print(f"  seed={seed} beta={beta:<5} ent={H:.3f} layers={len(cnt)} "
                  f"acc={acc:.4f} bits={bits:.4f} pop={sorted(pop)}")

    out = {"KMAX": KMAX, "NA": NA, "GENS": GENS, "TRAIN": TRAIN, "TEST": TEST,
           "BETAS": BETAS, "SEEDS": SEEDS, "results": results}
    json.dump(out, open("result211.json", "w"), ensure_ascii=False, indent=1)
    print("saved result211.json")

if __name__ == "__main__":
    main()
