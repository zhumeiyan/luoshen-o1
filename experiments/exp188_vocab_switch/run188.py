#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
188: 词汇有限与切换
用户命题 A: "我没见过那么多，所以用词很不标准" —— 词汇量 V 有限(人生有限)
用户命题 B: "欲望(挣钱) 和 这件事 是相辅相成、不停切换的"

Part A (实测): Heaps 定律 -> 词汇压缩 -> 预测收益 & 最优记忆阶 k*
Part B (模拟, 参数全部来自 Part A 实测): 预算 14000 下, 探索/利用 切换策略对比
"""
import json, math, random, os
from collections import Counter, defaultdict

BASE = "/data/workspace/luoshen-o1"
CORPUS = os.path.join(BASE, "experiments/exp180_record/u_side_full.txt")
OUT = os.path.join(BASE, "experiments/exp188_vocab_switch")
os.makedirs(OUT, exist_ok=True)

def load():
    txt = open(CORPUS, encoding="utf-8").read()
    # 只保留用户原话行 (U0xx 前缀后), 去掉编号与空行
    lines = []
    for ln in txt.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("U") and len(s) > 5 and s[1:4].isdigit():
            s = s.split(" ", 1)[1] if " " in s else s
        s = "".join(ch for ch in s if not ch.isspace())
        if s:
            lines.append(s)
    return "".join(lines)

def ngram_model(seq, k, vocab):
    idx = {c: i for i, c in enumerate(vocab)}
    V = len(vocab)
    ctx = defaultdict(Counter)
    unigram = Counter()
    for i in range(k, len(seq)):
        c = seq[i]
        h = tuple(idx.get(x, -1) for x in seq[i-k:i])
        ctx[h][idx.get(c, -1)] += 1
        unigram[idx.get(c, -1)] += 1
    return ctx, unigram, idx, V

def evaluate(train, test, k, vocab, alpha=0.1):
    """返回 top1 准确率与 bits/char (交叉熵, 自然未平滑项已处理)"""
    idx = {c: i for i, c in enumerate(vocab)}
    V = len(vocab)
    ctx = defaultdict(Counter)
    uni = Counter()
    for i in range(k, len(train)):
        h = tuple(idx.get(x, -1) for x in train[i-k:i])
        ctx[h][idx.get(train[i], -1)] += 1
        uni[idx.get(train[i], -1)] += 1
    tot_u = sum(uni.values())
    hit = 0; n = 0; logp = 0.0
    for i in range(k, len(test)):
        h = tuple(idx.get(x, -1) for x in test[i-k:i])
        tgt = idx.get(test[i], -1)
        if tgt < 0:
            continue
        cnt = ctx.get(h)
        if cnt:
            tc = sum(cnt.values())
            best = max(cnt.items(), key=lambda kv: kv[1])[0]
            p = (cnt.get(tgt, 0) + alpha) / (tc + alpha * V)
        else:
            best = max(uni.items(), key=lambda kv: kv[1])[0] if uni else -1
            p = (uni.get(tgt, 0) + alpha) / (tot_u + alpha * V)
        hit += 1 if best == tgt else 0
        n += 1
        logp += -math.log2(max(p, 1e-12))
    if n == 0:
        return None
    return {"acc": hit / n, "bits": logp / n, "n": n}

def heaps(seq):
    seen = set(); pts = []
    for i, ch in enumerate(seq):
        seen.add(ch)
        if (i + 1) % 50 == 0:
            pts.append((i + 1, len(seen)))
    pts.append((len(seq), len(seen)))
    return pts

def fit_power(pts):
    xs = [math.log(p[0]) for p in pts]; ys = [math.log(p[1]) for p in pts]
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    sxx = sum((x-mx)**2 for x in xs)
    beta = sxy/sxx; lnK = my - beta*mx
    # R^2
    ss_tot = sum((y-my)**2 for y in ys)
    ss_res = sum((y-(beta*x+lnK))**2 for x, y in zip(xs, ys))
    return math.exp(lnK), beta, 1 - ss_res/ss_tot

def compress(seq, M):
    """把词汇表压到 M 个符号: 保留 top-M 高频, 其余按左邻分布余弦最近映射过去"""
    freq = Counter(seq)
    if M >= len(freq):
        return seq, list(freq.keys())
    keep = [c for c, _ in freq.most_common(M)]
    keepset = set(keep)
    # 左邻分布
    left = defaultdict(Counter)
    for i in range(1, len(seq)):
        left[seq[i]][seq[i-1]] += 1
    def vec(c):
        return left.get(c, Counter())
    def cos(a, b):
        if not a or not b: return 0.0
        common = set(a) & set(b)
        num = sum(a[x]*b[x] for x in common)
        da = math.sqrt(sum(v*v for v in a.values())); db = math.sqrt(sum(v*v for v in b.values()))
        return num/(da*db) if da and db else 0.0
    kvec = {c: vec(c) for c in keep}
    mapping = {}
    for c in freq:
        if c in keepset:
            mapping[c] = c; continue
        v = vec(c)
        best, bs = keep[0], -1.0
        for kc in keep:
            s = cos(v, kvec[kc])
            if s > bs: bs, best = s, kc
        mapping[c] = best
    return "".join(mapping[ch] for ch in seq), keep

def main():
    seq = load()
    out = {"corpus_chars": len(seq), "corpus_vocab": len(set(seq))}

    # ---------- Part A1: Heaps ----------
    pts = heaps(seq)
    K, beta, r2 = fit_power(pts)
    out["heaps"] = {"K": K, "beta": beta, "r2": r2,
                    "curve": [{"N": p[0], "V": p[1]} for p in pts[::max(1, len(pts)//12)]],
                    "final_V": len(set(seq)), "N": len(seq)}

    # ---------- Part A2: 词汇压缩 -> 预测收益 & k* ----------
    full_vocab = sorted(set(seq))
    Ms = sorted(set([len(full_vocab), 400, 200, 100, 50, 30, 16, 8, 4, 2]),
                reverse=True)
    Ms = [m for m in Ms if m <= len(full_vocab)]
    split = int(len(seq) * 0.8)
    rows = []
    for M in Ms:
        cseq, vocab = compress(seq, M)
        tr, te = cseq[:split], cseq[split:]
        best = None; curve = []
        for k in range(1, 7):
            r = evaluate(tr, te, k, vocab)
            if r is None: continue
            r["k"] = k
            # 相对于 M 个符号均匀分布的节省 (跨 M 可比)
            r["reduction"] = math.log2(M) - r["bits"]
            curve.append(r)
            if best is None or r["acc"] > best["acc"]:
                best = r
        if best is None: continue
        rows.append({"M": M, "actual_V": len(set(cseq)),
                     "best_k": best["k"], "acc": best["acc"],
                     "bits": best["bits"], "ceiling": math.log2(M),
                     "reduction": best["reduction"],
                     "curve": curve})
    out["compression"] = rows

    # k* vs V 的关系检验: k* ~ log N / log V
    import statistics
    kv = []
    for r in rows:
        if r["actual_V"] > 1:
            pred = math.log(len(seq)) / math.log(r["actual_V"])
            kv.append({"V": r["actual_V"], "k_star": r["best_k"],
                       "pred_logN_logV": pred})
    out["kstar_vs_V"] = kv

    # ---------- Part B: 切换策略模拟 (参数来自 Part A 实测) ----------
    # f(V): 词汇量 V -> 每步有效产出 (reduction), 由实测曲线插值
    fpts = sorted([(r["actual_V"], r["reduction"]) for r in rows], key=lambda x: x[0])
    def f(V):
        if V <= fpts[0][0]: return fpts[0][1]
        if V >= fpts[-1][0]: return fpts[-1][1]
        for i in range(len(fpts)-1):
            a, b = fpts[i], fpts[i+1]
            if a[0] <= V <= b[0]:
                w = (V - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
                return a[1] + w * (b[1] - a[1])
        return fpts[-1][1]
    # N(V): 要达到词汇量 V 需见过多少 (Heaps 反函数)
    def N_of_V(V):
        return (max(V, 1) / K) ** (1.0 / beta)

    BUDGET = 14000
    V0 = 8.0
    VMAX = float(len(set(seq)))

    def sim(strategy, budget=BUDGET, param=None, seed=0):
        rnd = random.Random(seed)
        N_seen = N_of_V(V0)
        V = V0
        gain = 0.0
        steps = 0
        hist = []
        while steps < budget:
            Vcap = min(VMAX, K * (N_seen ** beta))
            if strategy == "pure_exploit":
                act = "exploit"
            elif strategy == "pure_explore":
                act = "explore"
            elif strategy == "alternate":
                a = param
                act = "explore" if (steps % (a + 1)) == 0 else "exploit"
            elif strategy == "greedy_switch":
                # 自适应: 比较"再探索一步的未来增益" vs "现在利用一步"
                dN = 1.0
                V_after = min(VMAX, K * ((N_seen + dN) ** beta))
                gain_if_explore = f(V_after) - f(V)
                # 探索让后续每步都升值, 剩余步数 (budget-steps-1)
                future = gain_if_explore * (budget - steps - 1)
                now = f(V)
                act = "explore" if future > now else "exploit"
            else:
                act = "exploit"
            if act == "explore":
                N_seen += 1.0
                V = min(VMAX, K * (N_seen ** beta))
            else:
                gain += f(V)
            steps += 1
            hist.append((steps, V, gain))
        return {"strategy": strategy, "param": param, "total_gain": gain,
                "final_V": V, "hist": hist[::max(1, len(hist)//50)]}

    results = []
    results.append(sim("pure_exploit"))
    results.append(sim("pure_explore"))
    for a in [1, 2, 3, 5, 8, 13, 21]:
        results.append(sim("alternate", param=a))
    results.append(sim("greedy_switch"))
    out["partB"] = {"budget": BUDGET, "V0": V0, "VMAX": VMAX,
                    "K": K, "beta": beta, "results": results}

    json.dump(out, open(os.path.join(OUT, "result188.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---------- 打印 ----------
    print("=" * 60)
    print("语料: %d 字符, %d 不同字" % (len(seq), len(set(seq))))
    print("Heaps: V = %.3f * N^%.3f   (R2=%.3f)" % (K, beta, r2))
    print("-" * 60)
    print("%6s %6s %5s %8s %8s %8s %8s" % ("M", "实V", "k*", "acc", "bits", "上限", "节省"))
    for r in rows:
        print("%6d %6d %5d %8.4f %8.4f %8.4f %8.4f" % (
            r["M"], r["actual_V"], r["best_k"], r["acc"], r["bits"],
            r["ceiling"], r["reduction"]))
    print("-" * 60)
    print("k* vs logN/logV:")
    for kv1 in kv:
        print("  V=%4d  k*=%d  pred=%.2f" % (kv1["V"], kv1["k_star"], kv1["pred_logN_logV"]))
    print("-" * 60)
    print("Part B (预算 %d, 模拟):" % BUDGET)
    for r in sorted(results, key=lambda x: -x["total_gain"]):
        print("  %-16s param=%-5s  总产出=%.1f  终V=%.1f" % (
            r["strategy"], r["param"], r["total_gain"], r["final_V"]))

if __name__ == "__main__":
    main()
