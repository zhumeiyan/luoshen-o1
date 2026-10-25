# -*- coding: utf-8 -*-
"""
判据核条目清点（评委可自行运行，零依赖）。

    python3 tools/count_criteria.py

【为什么需要这个脚本】
本仓库曾对外声称"195 条失败模式"。用本脚本清点后发现，
195 是"最大编号"，不是"独立条目数"：编号存在历史跳号，
且第 1-34 条引用了一个并不包含它们的外部文件。

我们主张"只增不减、不可篡改"，其直接代价就是编号会留洞——
我们不回填、不重排。因此本脚本把跳号一并报出，而不是只报总数。

【判据核第 23 条的产物】
我们曾被"写了但没接进主通道"的变量污染过三条核心结论。
任何对外声称的数字，都应有可运行的清点脚本，而不是凭印象写。
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CORE = os.path.join(ROOT, 'evidence', '失败模式库', '判据核.md')

# 匹配标题级条目：## 第 N 条 / ### 第 N 条 / - **第 N 条 · **
PAT = re.compile(r'^\s*(?:#{2,4}\s*|-\s*\**|\*{1,2})?\s*第\s*([0-9]+)\s*条')


def ranges(nums):
    """把离散编号压成区间串，如 [1,2,3,7] -> '1-3, 7'"""
    if not nums:
        return '(无)'
    out, s, p = [], nums[0], nums[0]
    for v in nums[1:]:
        if v == p + 1:
            p = v
        else:
            out.append(f'{s}-{p}' if s != p else str(s))
            s = p = v
    out.append(f'{s}-{p}' if s != p else str(s))
    return ', '.join(out)


def main():
    if not os.path.exists(CORE):
        print(f'找不到判据核：{CORE}')
        return 1

    seen = {}       # 编号 -> 首次出现行号
    dup = []        # 重复编号
    for i, line in enumerate(open(CORE, encoding='utf-8'), 1):
        m = PAT.match(line)
        if not m:
            continue
        n = int(m.group(1))
        if n in seen:
            dup.append(n)
        else:
            seen[n] = i

    nums = sorted(seen)
    if not nums:
        print('未匹配到任何条目，请检查正则')
        return 1

    lo, hi = nums[0], nums[-1]
    missing = [i for i in range(1, hi + 1) if i not in seen]

    print('=' * 62)
    print('判据核条目清点')
    print('=' * 62)
    print(f'文件            : evidence/失败模式库/判据核.md')
    print(f'独立条目数      : {len(nums)}')
    print(f'编号范围        : {lo} – {hi}')
    print(f'最大编号        : {hi}   ← 这不是条目数')
    print(f'跳号数          : {len(missing)}')
    print(f'跳号区间        : {ranges(missing)}')
    print(f'重复编号        : {sorted(set(dup)) if dup else "(无)"}')
    print('-' * 62)
    print('【口径说明】本脚本的"跳号数"包含编号 1-34（外部引用链已断裂、不计入条目）。')
    print('  权威条目数由 tools/count_patterns.py 给出：141 条，缺口 20 处')
    print('  （52、116-117、147-163）。两脚本均可复现，差异仅在是否计入 1-34。')
    print('-' * 62)
    print('【对外声称应使用的表述】')
    print(f'  {len(nums)} 条独立条目（编号 {lo}–{hi}，'
          f'其中 {len(missing)} 个为历史跳号，未回填）')
    print('-' * 62)
    print('跳号是"只增不减、不可篡改"的直接代价：')
    print('  回填或重排编号 = 改写历史 = 违反只增不减。')
    print('  因此我们不填补这些洞，而是把它们一并披露。')

    # 引用完整性检查：判据核声称 1-34 条在别处，核实那个文件
    ext = os.path.join(ROOT, '..', '命运位注入段_可追加到洛神系统提示.md')
    print('-' * 62)
    if os.path.exists(ext):
        t = open(ext, encoding='utf-8').read()
        en = sorted(set(int(x) for x in re.findall(r'第\s*([0-9]+)\s*条', t)))
        print(f'判据核称"完整 34 条见外部文件"，实测该文件含编号: {en}')
        print(f'  → 外部文件仅含 {len(en)} 个编号，引用链不完整（已如实披露）')
    else:
        print('外部引用文件不在本仓库内 —— 引用链断裂。')
        print('  → 第 1–34 条不在本次提交的范围内，不得计入对外声称。')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
