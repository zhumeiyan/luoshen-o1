#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp128 · 多重比较回溯审计 —— 断言抽取器

目标：把 110 份实验报告里"报了 95% CI 的配对结论"抽成机器可读的断言表，
      然后从 CI 反推 SE / z / p，统一做 Bonferroni 与 BH-FDR 校正。

关键设计（防止我自己骗自己）：
1. 只抽"能解析出数值 CI"的断言。抽不出来的不算数，但会统计"有多少抽不出来"
   —— 抽不出来的比例本身就是结论（可追溯性缺口）。
2. 从 CI 反推 p 是近似：CI 按 95% 正态近似处理，z = delta/SE。
   若报告里 delta 缺失，则用 CI 中心点作为 delta 的替代并标记 inferred=True。
3. 不做"只挑显著的"——全量纳入，包括跨 0 的。
"""
import os, re, json, math, glob

REPORT_DIR = "/data/workspace/luoshen-o1/evidence/实验报告"

# 兼容全角/半角负号与中英文括号
NUM = r"[-−+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
CI_PAT = re.compile(
    r"CI\s*[\[［(]\s*(" + NUM + r")\s*[,，]\s*(" + NUM + r")\s*[\]］)]"
)
DELTA_PAT = re.compile(r"(?:[ΔD]|delta|Delta)[elta]*\s*[=＝:]\s*(" + NUM + r")")
N_PAT = re.compile(r"n\s*[=＝]\s*(\d+)")


def tonum(s):
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    return float(s)


def norm_p_from_ci(delta, lo, hi, level=0.95):
    """从 95% CI 反推双侧 p（正态近似）。"""
    half = (hi - lo) / 2.0
    if half <= 0:
        return None, None, None
    zcrit = 1.959963985  # 95%
    se = half / zcrit
    z = abs(delta) / se
    # 双侧 p
    p = math.erfc(z / math.sqrt(2.0))
    return se, z, p


def main():
    claims = []
    unparsed = []
    for path in sorted(glob.glob(os.path.join(REPORT_DIR, "*.md"))):
        name = os.path.basename(path)
        try:
            txt = open(path, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            unparsed.append({"report": name, "reason": "read_fail:%s" % e})
            continue
        n_cis = len(CI_PAT.findall(txt))
        if n_cis == 0:
            unparsed.append({"report": name, "reason": "no_parsable_CI"})
            continue
        lines = txt.splitlines()
        for i, line in enumerate(lines):
            m = CI_PAT.search(line)
            if not m:
                continue
            lo, hi = tonum(m.group(1)), tonum(m.group(2))
            if lo > hi:
                lo, hi = hi, lo
            # delta：优先本行，其次上下两行
            dm = DELTA_PAT.search(line)
            src = "same_line"
            if not dm:
                for j in (i - 1, i - 2, i + 1, i + 2):
                    if 0 <= j < len(lines):
                        dm = DELTA_PAT.search(lines[j])
                        if dm:
                            src = "nearby_line"
                            break
            if dm:
                delta = tonum(dm.group(1))
                inferred = False
            else:
                delta = (lo + hi) / 2.0
                inferred = True
                src = "ci_midpoint"
            # n
            nm = N_PAT.search(line)
            n = None
            if nm:
                n = int(nm.group(1))
            else:
                for j in range(max(0, i - 3), min(len(lines), i + 4)):
                    nm2 = N_PAT.search(lines[j])
                    if nm2:
                        n = int(nm2.group(1))
                        break
            # 原文显著标记
            ctx = " ".join(lines[max(0, i - 2): i + 3])
            claimed_sig = None
            if re.search(r"不跨\s*0|全[正负]|显著", ctx):
                claimed_sig = True
            if re.search(r"跨\s*0|不显著|未测出", ctx):
                claimed_sig = False
            se, z, p = norm_p_from_ci(delta, lo, hi)
            claims.append({
                "report": name,
                "line_no": i + 1,
                "delta": delta,
                "ci_lo": lo,
                "ci_hi": hi,
                "n": n,
                "delta_source": src,
                "delta_inferred": inferred,
                "se": se,
                "z": z,
                "p_approx": p,
                "ci_excludes_zero": (lo > 0) or (hi < 0),
                "report_claimed_sig": claimed_sig,
                "context": line.strip()[:160],
            })
    out = {"claims": claims, "unparsed_reports": unparsed}
    with open("claims_raw.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("报告总数      :", len(glob.glob(os.path.join(REPORT_DIR, '*.md'))))
    print("抽出断言      :", len(claims))
    print("无CI的报告    :", sum(1 for u in unparsed if u['reason'] == 'no_parsable_CI'))
    print("delta为CI中点 :", sum(1 for c in claims if c['delta_inferred']))
    print("CI不跨0(名义) :", sum(1 for c in claims if c['ci_excludes_zero']))
    print("有n的断言     :", sum(1 for c in claims if c['n']))


if __name__ == "__main__":
    main()
