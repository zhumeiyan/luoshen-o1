#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp128 · 建立"机器可读断言日志"并用真实配对数据跑一遍

来源：exp126（6 臂 × 16 seed，含每 seed 的 fg 原始值）、exp127D（续学配对）
做法：同 seed 配对做差 → delta / SE / 95%CI / n → 全批 BH-FDR + Bonferroni → 三闸

目的不是"重新得出更好的结论"，而是回答一个问题：
  一次实验里顺手做的 15 组两两比较，校正后还剩几条站得住？
"""
import json, math, itertools, os

Z = 1.959963985


def paired(a, b):
    """同 seed 配对：返回 delta, se, lo, hi, n"""
    n = min(len(a), len(b))
    d = [b[i] - a[i] for i in range(n)]
    m = sum(d) / n
    if n > 1:
        var = sum((x - m) ** 2 for x in d) / (n - 1)
        se = math.sqrt(var / n)
    else:
        se = float("nan")
    return m, se, m - Z * se, m + Z * se, n, d


def norm_p(m, se):
    if se == 0 or math.isnan(se):
        return 0.0
    return math.erfc(abs(m / se) / math.sqrt(2.0))


def main():
    src = "/data/workspace/luoshen-o1/experiments/exp126_wean2/result126.json"
    d = json.load(open(src, encoding="utf-8"))["result"]
    arms = {k: [r["fg"] for r in v["raw"]] for k, v in d.items() if v.get("raw")}
    print("臂数:", len(arms), "每臂 seed:", {k: len(v) for k, v in arms.items()})

    claims = []
    for a, b in itertools.combinations(sorted(arms), 2):
        m, se, lo, hi, n, _ = paired(arms[a], arms[b])
        claims.append({
            "claim_id": "126:%s_vs_%s" % (b, a),
            "family": "exp126_wean2/fg",
            "metric": "fg(学到的觅食效率)",
            "n": n, "delta": m, "se": se, "ci_lo": lo, "ci_hi": hi,
            "p_approx": norm_p(m, se),
            "direction": "positive" if m > 0 else "negative",
        })

    # 追加 127D 续学配对（已存 delta/se/lo/hi）
    p127 = "/data/workspace/luoshen-o1/experiments/exp127_stress_anneal/result127D.json"
    if os.path.exists(p127):
        e = json.load(open(p127, encoding="utf-8"))
        cp = e.get("continue_pair", {})
        for arm, v in cp.items():
            if all(k in v for k in ("delta", "se", "lo", "hi")):
                claims.append({
                    "claim_id": "127D:continue_%s" % arm,
                    "family": "exp127/continue_learning",
                    "metric": "Δfg_good − Δfg_bad",
                    "n": 24, "delta": v["delta"], "se": v["se"],
                    "ci_lo": v["lo"], "ci_hi": v["hi"],
                    "p_approx": norm_p(v["delta"], v["se"]),
                    "direction": "positive" if v["delta"] > 0 else "negative",
                })

    # 追加 127C 退火对比（用 fg 值，n=16 但未存 raw → 标 n=None 走 G3）
    p127c = "/data/workspace/luoshen-o1/experiments/exp127_stress_anneal/result127C.json"
    if os.path.exists(p127c):
        c = json.load(open(p127c, encoding="utf-8")).get("anneal", {})
        base = c.get("slow", {}).get("fg")
        for arm in ("constant", "fast", "cool"):
            if arm in c and base is not None:
                claims.append({
                    "claim_id": "127C:anneal_%s_vs_slow" % arm,
                    "family": "exp127/anneal",
                    "metric": "fg",
                    "n": None, "delta": c[arm]["fg"] - base,
                    "se": None, "ci_lo": None, "ci_hi": None,
                    "p_approx": None, "direction": "positive",
                })

    print("断言总数:", len(claims))
    json.dump(claims, open("claim_log.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return claims


if __name__ == "__main__":
    main()
