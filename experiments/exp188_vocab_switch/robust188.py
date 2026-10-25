#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""188 稳健性: Part A 多种划分 / Part B 多种起点与预算"""
import json, math, random, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run188 import load, compress, evaluate, heaps, fit_power

OUT = "/data/workspace/luoshen-o1/experiments/exp188_vocab_switch"
seq = load()
Ms = [528, 400, 200, 100, 50, 30, 16, 8, 4, 2]
Ms = [m for m in Ms if m <= len(set(seq))]

def partA_split(frac):
    split = int(len(seq) * frac)
    rows = []
    for M in Ms:
        cseq, vocab = compress(seq, M)
        tr, te = cseq[:split], cseq[split:]
        best = None
        for k in range(1, 7):
            r = evaluate(tr, te, k, vocab)
            if r is None:
                continue
            r["k"] = k
            r["reduction"] = math.log2(M) - r["bits"]
            if best is None or r["acc"] > best["acc"]:
                best = r
        if best:
            rows.append({"M": M, "V": len(set(cseq)), "k": best["k"],
                         "acc": best["acc"], "bits": best["bits"],
                         "reduction": best["reduction"]})
    return rows

resA = {}
for frac in [0.7, 0.8, 0.9]:
    rows = partA_split(frac)
    peak = max(rows, key=lambda r: r["reduction"])
    resA["split_%.1f" % frac] = {
        "rows": rows,
        "peak_reduction_V": peak["V"],
        "peak_reduction": peak["reduction"],
        "maxV_reduction": rows[0]["reduction"],
        "k_at_maxV": rows[0]["k"],
        "k_at_V30": next((r["k"] for r in rows if r["V"] <= 32), None),
    }

# Part B 稳健性
K, beta, _ = fit_power(heaps(seq))
VMAX = float(len(set(seq)))
fpts_all = sorted([(r["V"], r["reduction"]) for r in partA_split(0.8)], key=lambda x: x[0])

def f(V, fpts):
    if V <= fpts[0][0]: return fpts[0][1]
    if V >= fpts[-1][0]: return fpts[-1][1]
    for i in range(len(fpts) - 1):
        a, b = fpts[i], fpts[i + 1]
        if a[0] <= V <= b[0]:
            w = (V - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            return a[1] + w * (b[1] - a[1])
    return fpts[-1][1]

def sim(strategy, budget, V0, param=None):
    N_seen = (V0 / K) ** (1.0 / beta)
    V = V0; gain = 0.0; steps = 0
    while steps < budget:
        if strategy == "pure_exploit":
            act = "exploit"
        elif strategy == "pure_explore":
            act = "explore"
        elif strategy == "alternate":
            act = "explore" if (steps % (param + 1)) == 0 else "exploit"
        elif strategy == "greedy_switch":
            V_after = min(VMAX, K * ((N_seen + 1.0) ** beta))
            future = (f(V_after, fpts_all) - f(V, fpts_all)) * (budget - steps - 1)
            act = "explore" if future > f(V, fpts_all) else "exploit"
        else:
            act = "exploit"
        if act == "explore":
            N_seen += 1.0
            V = min(VMAX, K * (N_seen ** beta))
        else:
            gain += f(V, fpts_all)
        steps += 1
    return {"gain": gain, "final_V": V}

resB = {}
for budget in [14000, 5000, 1000]:
    for V0 in [4.0, 8.0, 30.0]:
        r = {}
        r["pure_exploit"] = sim("pure_exploit", budget, V0)
        r["pure_explore"] = sim("pure_explore", budget, V0)
        r["greedy"] = sim("greedy_switch", budget, V0)
        best_alt = None
        for a in [1, 2, 3, 5, 8, 13, 21, 34]:
            g = sim("alternate", budget, V0, a)
            if best_alt is None or g["gain"] > best_alt["gain"]:
                best_alt = {"a": a, **g}
        r["best_alternate"] = best_alt
        winner = max(r.items(), key=lambda kv: kv[1]["gain"])
        resB["B%d_V0%.0f" % (budget, V0)] = {
            "pure_exploit": r["pure_exploit"]["gain"],
            "pure_explore": r["pure_explore"]["gain"],
            "greedy": r["greedy"]["gain"],
            "best_alternate": best_alt["gain"],
            "best_a": best_alt["a"],
            "greedy_finalV": r["greedy"]["final_V"],
            "winner": winner[0],
            "switch_over_exploit": r["greedy"]["gain"] / max(r["pure_exploit"]["gain"], 1e-9),
        }

json.dump({"partA": resA, "partB": resB},
          open(os.path.join(OUT, "robust188.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print("=== Part A 稳健性: reduction 峰值在哪里 ===")
for k, v in resA.items():
    print("%s: 峰值V=%d (%.4f) | 最大V=528 时 %.4f | k@V528=%s k@V<=30=%s" % (
        k, v["peak_reduction_V"], v["peak_reduction"], v["maxV_reduction"],
        v["k_at_maxV"], v["k_at_V30"]))
print()
print("=== Part B 稳健性: 谁赢 ===")
print("%-14s %10s %10s %10s %10s %6s %8s" % ("场景", "纯利用", "纯探索", "贪心切换", "最佳交替", "a", "切换/纯利用"))
for k, v in resB.items():
    print("%-14s %10.1f %10.1f %10.1f %10.1f %6s %8.2fx" % (
        k, v["pure_exploit"], v["pure_explore"], v["greedy"],
        v["best_alternate"], v["best_a"], v["switch_over_exploit"]))
print()
wins = [v["winner"] for v in resB.values()]
print("赢家分布:", {w: wins.count(w) for w in set(wins)})
print("贪心是否总 > 纯利用:", all(v["switch_over_exploit"] > 1 for v in resB.values()))
