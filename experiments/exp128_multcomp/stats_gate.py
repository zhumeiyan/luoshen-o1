#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp128 · stats_gate —— 结论发布前的统计闸门

三道闸，任一道不过就不能写"显著"：
  G1 效应量闸  : |delta| 必须 >= min_effect（默认 1e-3 绝对量 且 相对量 >= 1%）
                —— 拦 116 那类"CI 不跨 0 但 Δ=−9.8e−09"的伪显著
  G2 多重比较闸: BH-FDR 校正后 q <= alpha（默认 0.05）
                —— 拦"做得越多假阳性越多"
  G3 数据充足闸: n >= n_min（默认 8）且 n 必须显式给出
                —— 拦"没记 n 的结论"

设计原则（来自判据核）：
  * 闸门必须自己可证伪 —— 内置 SELFTEST，输入"必然该拦"和"必然该放"的样本，
    两者都必须有正确输出，否则闸门本身不合格。
"""
import math, json, sys

Z95 = 1.959963985


def norm_p2(z):
    return math.erfc(abs(z) / math.sqrt(2.0))


def bh_fdr(pvals, alpha=0.05):
    """Benjamini-Hochberg：返回 (qvals, reject_flags)，按原始顺序。"""
    m = len(pvals)
    if m == 0:
        return [], []
    idx = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(idx), start=1):
        k = m - rank + 1  # 从大到小的名次
        val = min(prev, pvals[i] * m / k)
        q[i] = min(1.0, val)
        prev = q[i]
    rej = [q[i] <= alpha for i in range(m)]
    return q, rej


def bonferroni(pvals, alpha=0.05):
    m = len(pvals)
    if m == 0:
        return [], []
    return [min(1.0, p * m) for p in pvals], [p * m <= alpha for p in pvals]


def check_one(claim, min_effect=1e-3, min_rel=0.01, n_min=8, alpha=0.05):
    """单条断言的三闸判定（不含 FDR，FDR 需全批一起算）。"""
    reasons = []
    d = claim.get("delta")
    n = claim.get("n")
    se = claim.get("se")
    lo, hi = claim.get("ci_lo"), claim.get("ci_hi")

    # G3 数据充足
    if n is None:
        reasons.append("G3_FAIL: n 未记录")
    elif n < n_min:
        reasons.append("G3_FAIL: n=%d < %d" % (n, n_min))

    # G1 效应量
    if d is None or se is None:
        reasons.append("G1_FAIL: delta/SE 不可得")
    else:
        if abs(d) < min_effect:
            reasons.append("G1_FAIL: |Δ|=%.3g < %.3g（绝对量过小）" % (abs(d), min_effect))
        # 相对量：以 SE 为尺度的噪声水平作参照
        if se > 0 and abs(d) / se < min_rel * Z95:
            reasons.append("G1_FAIL: |Δ|/SE=%.3g 相对量 < %.1f%%" % (abs(d) / se, min_rel * 100))
        if lo is not None and hi is not None and (lo <= 0 <= hi):
            reasons.append("G1_FAIL: CI 跨 0")

    return reasons


def gate_batch(claims, min_effect=1e-3, min_rel=0.01, n_min=8, alpha=0.05):
    """对一批断言做完整闸门：G1/G3 逐条，G2 全批 BH-FDR。"""
    usable = []
    for c in claims:
        se = c.get("se")
        d = c.get("delta")
        # 退化保护：SE<=0 或 效应量本身低于阈值时，不得参与"显著"排序。
        # 否则 se=0 会让 z=inf、p=0，BH 把一条零效应比较排在最显著位置。
        if (c.get("p_approx") is None or se is None or se <= 0 or
                d is None or abs(d) < min_effect):
            c["_p"] = 1.0
            c["_p_missing"] = True
        else:
            c["_p"] = c["p_approx"]
            c["_p_missing"] = False
        usable.append(c)
    ps = [c["_p"] for c in usable]
    q, rej = bh_fdr(ps, alpha)
    pb, rejb = bonferroni(ps, alpha)
    for i, c in enumerate(usable):
        c["q_bh"] = q[i]
        c["reject_bh"] = rej[i]
        c["p_bonf"] = pb[i]
        c["reject_bonf"] = rejb[i]
        r = check_one(c, min_effect, min_rel, n_min, alpha)
        if not c["reject_bh"]:
            r.append("G2_FAIL: BH q=%.4g > %.2g" % (c["q_bh"], alpha))
        c["gate_reasons"] = r
        c["PASS"] = (len(r) == 0)
    return usable


def selftest():
    """闸门自检：必须同时抓到"该拦的"和"该放的"，否则闸门本身不合格。"""
    print("=" * 62)
    print("SELFTEST · 闸门本身是否可证伪")
    print("=" * 62)
    # 必须拦：116 类 —— Δ=-9.8e-09，CI 极窄不跨 0，n=48
    se116 = 1.0e-9
    c_bad = {
        "name": "116_伪显著",
        "delta": -9.8e-09,
        "se": se116,
        "ci_lo": -9.8e-09 - Z95 * se116,
        "ci_hi": -9.8e-09 + Z95 * se116,
        "n": 48,
    }
    c_bad["p_approx"] = norm_p2(c_bad["delta"] / c_bad["se"])
    # 必须放：112 类 —— Δ=+0.1535，CI 全正，n=48
    se112 = 0.0704  # (0.1921-0.1533)/2/1.96 ≈ 0.0099 → 用实际量级
    lo, hi = 0.1533, 0.1921
    se112 = (hi - lo) / (2 * Z95)
    d112 = (lo + hi) / 2
    c_ok = {"name": "112_真显著", "delta": d112, "se": se112,
            "ci_lo": lo, "ci_hi": hi, "n": 48}
    c_ok["p_approx"] = norm_p2(d112 / se112)
    # 必须拦：缺 n
    c_non = {"name": "缺n", "delta": 0.5, "se": 0.1, "ci_lo": 0.304, "ci_hi": 0.696, "n": None}
    c_non["p_approx"] = norm_p2(5.0)
    # 必须拦：CI 跨 0
    c_cross = {"name": "跨0", "delta": 0.001, "se": 0.01,
               "ci_lo": -0.0186, "ci_hi": 0.0206, "n": 16}
    c_cross["p_approx"] = norm_p2(0.1)

    batch = [c_bad, c_ok, c_non, c_cross]
    res = gate_batch(batch)
    expect = {"116_伪显著": False, "112_真显著": True, "缺n": False, "跨0": False}
    ok = True
    for c in res:
        exp = expect[c["name"]]
        got = c["PASS"]
        flag = "OK " if got == exp else "FAIL"
        if got != exp:
            ok = False
        print("  [%s] %-12s 期望PASS=%-5s 实际=%-5s  q=%.3g  %s"
              % (flag, c["name"], exp, got, c["q_bh"],
                 "; ".join(c["gate_reasons"]) or "-"))
    print("  → 闸门自检: %s" % ("PASS（同时抓到该拦与该放）" if ok else "FAIL（闸门不可证伪）"))
    return ok


def main():
    ok = selftest()
    print()
    print("=" * 62)
    print("对 110 份报告回溯：抽出断言的 FDR 校正")
    print("=" * 62)
    try:
        data = json.load(open("claims_raw.json", encoding="utf-8"))
    except Exception as e:
        print("读取失败:", e)
        return
    claims = data["claims"]
    res = gate_batch(claims)
    npass = sum(1 for c in res if c["PASS"])
    print("断言总数        :", len(res))
    print("名义不跨0       :", sum(1 for c in res if c["ci_excludes_zero"]))
    print("BH-FDR 后存活   :", sum(1 for c in res if c["reject_bh"]))
    print("Bonferroni 存活 :", sum(1 for c in res if c["reject_bonf"]))
    print("三闸全过        :", npass)
    print()
    for c in res:
        print("  %-28s Δ=%-12.5g q=%-9.3g %s %s"
              % (c["report"][:28], c["delta"], c["q_bh"],
                 "PASS" if c["PASS"] else "BLOCK",
                 "; ".join(c["gate_reasons"])[:70]))
    json.dump(res, open("claims_gated.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print()
    print("无 CI 的报告数  :", sum(1 for u in data["unparsed_reports"]
                                    if u["reason"] == "no_parsable_CI"))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# G4 稳健性闸（新增）
#
# 由来：G1/G2/G3 只检查"数算得对不对"，不检查"量测得对不对"。
# exp126 的教训：practice_open 在 burn=0 下 fg=0.0079131、3/16 存活、CI 不跨 0，
#   三闸全过；但 burn=20 后塌到 0.00072、0/16 存活 —— 那个"学会"是估计器瞬态造的。
# G4 判据：结论必须在【合理的分析变体】下同时保住方向且保住量级。
#   量级保持率 = |值(变体)| / |值(原分析)|，默认要求 >= 0.5
#   且定性结论（如存活）不得翻转。
# ---------------------------------------------------------------------------

def g4_robustness(claim, variants, min_keep=0.5):
    """variants: [(variant_name, value, qualitative_ok), ...] 不含原分析"""
    reasons = []
    base = abs(claim.get("delta", 0.0))
    if base <= 0:
        return ["G4_NA: 原效应为 0，稳健性无意义"]
    for name, val, qual_ok in variants:
        keep = abs(val) / base
        if keep < min_keep:
            reasons.append("G4_FAIL: %s 量级只剩 %.2f (<%.2f)" % (name, keep, min_keep))
        if qual_ok is False:
            reasons.append("G4_FAIL: %s 定性结论翻转" % name)
    return reasons


def g4_demo():
    """用 126c 的真实 burn-in 剂量扫描演示 G4 能抓住 G1/G2/G3 放行的假象。"""
    print()
    print("=" * 62)
    print("G4 演示 · 三闸全过的断言，是否真的站得住（126c 真实数据）")
    print("=" * 62)
    # 真实数据（result126c.json）：burn 0 / 20 / 100 下的 fg 与存活
    rows = {
        "closed(相倚·真学习)": [(0, 0.164098, 16), (20, 0.142586, 15),
                                (100, 0.103676, 15)],
        "open(相继·估计器假象)": [(0, 0.0079131, 3), (20, 0.00071858, 0),
                                  (100, 0.00091236, 0)],
    }
    out = {}
    for name, series in rows.items():
        base_v, base_n = series[0][1], series[0][2]
        variants = []
        for b, v, n in series[1:]:
            variants.append(("burn=%d" % b, v, (n > 0) == (base_n > 0)))
        c = {"delta": base_v, "n": 16}
        r = g4_robustness(c, variants)
        out[name] = {"base": base_v, "reasons": r,
                     "keep100": abs(series[-1][1]) / abs(base_v)}
        print("  %-24s 基准fg=%.6g  burn=100保持率=%.3f  → %s"
              % (name, base_v, out[name]["keep100"],
                 "PASS" if not r else "BLOCK"))
        for x in r:
            print("       └", x)
    return out
