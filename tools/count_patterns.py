# -*- coding: utf-8 -*-
"""
================================================================
洛神 O1 · 失败模式条目计数（权威口径）
================================================================
为什么要有这个脚本：
  "我们有多少条失败模式"这个数字，此前出现过三套口径——
    最大编号 195 / 去重编号 141 / 定义行 150 / 缺口 20 处（52、116-117、147-163）。
  任何一个由人（含维护者本人与 AI）口头报出的数都可能出错。

  本脚本是唯一权威口径。文档、README、PDF 中的条目数一律引用
  本脚本的输出，并注明"由 tools/count_patterns.py 实时统计"。

判定规则（可审计）：
  只有【定义行】计入，即形如以下之一的行：
      ##/###/#### 第 N 条 ...
      **第 N 条 ...**
  仅被正文引用（如"见第 36 条"）的行不计入。

运行： python3 tools/count_patterns.py
输出： 条目数 + 编号范围 + 缺口 + 前若干条标题
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'evidence', '失败模式库', '判据核.md')

DEF_RE = re.compile(r'^第\s*(\d+)\s*条')


def parse_def(line):
    """归一化后判定是否为条目定义行，兼容三种真实写法：
        ### 第 35 条 ...
        **第 71 条 · ...**
        - **第 195 条 · ...**   ← 高层编号全是这种
    返回编号，非定义行返回 None。
    """
    s = line.strip().lstrip('-•').strip()
    s = s.lstrip('#').strip()
    s = s.lstrip('*').strip()
    m = DEF_RE.match(s)
    return int(m.group(1)) if m else None


def main():
    if not os.path.exists(PATH):
        print('[FAIL] 找不到判据核: %s' % PATH)
        return 1

    with open(PATH, encoding='utf-8') as f:
        lines = f.read().split('\n')

    defs = []      # (编号, 行号, 标题)
    for i, line in enumerate(lines, 1):
        n = parse_def(line)
        if n is not None:
            title = line.strip().lstrip('-•#*').strip()
            defs.append((n, i, title[:60]))

    nums = sorted({d[0] for d in defs})
    if not nums:
        print('[FAIL] 未解析到任何条目定义行 —— 格式可能已变，请检查 DEF_RE')
        return 1

    gaps = [i for i in range(nums[0], nums[-1] + 1) if i not in nums]

    print('=' * 58)
    print('洛神 O1 · 失败模式条目计数（权威口径）')
    print('=' * 58)
    print('判据核文件 : evidence/失败模式库/判据核.md')
    print('条目定义行 : %d' % len(defs))
    print('去重后编号 : %d' % len(nums))
    print('编号范围   : %d - %d' % (nums[0], nums[-1]))
    print('最大编号   : %d   ← 注意：这不是条目数' % nums[-1])
    print('编号缺口   : %d 处' % len(gaps))
    if gaps:
        # 缺口压缩显示
        runs = []
        s = p = gaps[0]
        for g in gaps[1:]:
            if g == p + 1:
                p = g
            else:
                runs.append((s, p))
                s = p = g
        runs.append((s, p))
        print('            ' + ', '.join(
            '%d' % a if a == b else '%d-%d' % (a, b) for a, b in runs))
    print('-' * 58)
    print('对外引用口径：')
    print('  **%d 条独立失败模式**（由 tools/count_patterns.py 实时统计；'
          '定义行 %d 条，最大编号 %d，重复编号 %d 个，编号缺口 %d 处）'
          % (len(nums), len(defs), nums[-1], len(defs) - len(nums), len(gaps)))
    print('-' * 58)
    print('末 5 条：')
    for n, i, t in defs[-5:]:
        print('  第 %d 条 | %s' % (n, t))
    print('=' * 58)

    # 供其他脚本读取
    out = {
        'n_defs': len(defs),
        'n_unique': len(nums),
        'max_id': nums[-1],
        'min_id': nums[0],
        'n_gaps': len(gaps),
        'gaps': gaps,
        'titles': [{'id': n, 'title': t} for n, i, t in defs],
    }
    op = os.path.join(ROOT, 'data', 'pattern_count.json')
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('已写出: data/pattern_count.json')
    return 0


if __name__ == '__main__':
    import json
    sys.exit(main())
