#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料数字漂移检查器
==================
问题背景：每跑一轮新实验就会往判据核追加条目，而物料（PDF/问答卡/deck/README…）
里的条数是手写的，永远不会自动同步。历史上出现过 139/141/152/159/182/195 六个数字打架。

本脚本做一件事：**扫全部物料，找出与权威口径不一致的条数表述**。
权威口径由 tools/count_patterns.py 实时给出，本脚本不硬编码任何数字。

用法：
    python3 tools/check_materials.py            # 报告模式
    python3 tools/check_materials.py --fix      # 自动替换可安全替换处
退出码：0 = 无漂移；1 = 发现漂移。比赛前推送建议接入自校验。
"""
import os
import re
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTER = os.path.join(ROOT, "tools", "count_patterns.py")

# 物料文件：docs/ 下全部 md/html + 根目录 README + deck 源
TARGETS = []
for d in ("docs",):
    for f in sorted(os.listdir(os.path.join(ROOT, d))):
        if f.endswith((".md", ".html")):
            TARGETS.append(os.path.join(d, f))
for f in ("README.md", "CONTRIBUTING.md", "GOVERNANCE.md", "ROADMAP.md"):
    if os.path.exists(os.path.join(ROOT, f)):
        TARGETS.append(f)


def authoritative_count():
    """调权威脚本拿条数，绝不自己数。"""
    out = subprocess.run([sys.executable, COUNTER], cwd=ROOT,
                         capture_output=True, text=True).stdout
    m = re.search(r"\*\*(\d+) 条独立失败模式\*\*", out)
    if not m:
        raise RuntimeError("无法从 count_patterns.py 解析条数，权威口径失效")
    return int(m.group(1)

               ) if False else int(m.group(1))


def authoritative_reports():
    d = os.path.join(ROOT, "evidence", "实验报告")
    return len([f for f in os.listdir(d) if f.endswith(".md")]) if os.path.isdir(d) else -1


def main():
    fix = "--fix" in sys.argv
    n = authoritative_count()
    nr = authoritative_reports()
    print("=" * 60)
    print(f"权威口径：{n} 条独立失败模式（来自 tools/count_patterns.py）")
    print("=" * 60)

    # 匹配形如「182 条」「141条」「195 条失败模式」
    pat = re.compile(r"(\d{2,3})\s*条")
    # 这些数字是合法的、不该被改（比如「三条硬约束」「5 条反馈」）
    ALLOW = {n}
    bad = []
    hist = []

    for rel in TARGETS:
        p = os.path.join(ROOT, rel)
        txt = open(p, encoding="utf-8", errors="ignore").read()
        for mm in pat.finditer(txt):
            val = int(mm.group(1))
            if val in ALLOW or val < 100:
                continue
            line_no = txt[:mm.start()].count("\n") + 1
            # 判据粒度必须是「数字周边窗口」而非整行：
            # HTML/JS 物料常把整篇讲稿压成一行，按行判断会把真漂移误判为历史披露而放过。
            W = 30
            ctx = txt[max(0, mm.start() - W): mm.end() + W].replace("\n", " ")
            line = txt.split("\n")[line_no - 1].strip()
            # 只针对「失败模式 / 判据核 / 条目」语境
            if not re.search(r"失败模式|判据核|条(?!件)|模式库|条目", ctx):
                continue
            # 历史披露语境：这是如实记录的纠错史，改掉等于抹掉史实 → 保留并单列
            if re.search(r"此前|曾对外称|曾称|曾写|当时|原先|已更正|片头|实际标注|误当|不是条目数", ctx):
                hist.append((rel, line_no, val, ctx[:100]))
                continue
            # 条目编号而非总数（如「第 111 条」「第 23 条」）
            if re.search(r"第\s*%d\s*条" % val, ctx):
                continue
            bad.append((rel, line_no, val, ctx[:100], "n"))

    # 报告数
    pat_r = re.compile(r"(\d{2,3})\s*份")
    for rel in TARGETS:
        txt0 = open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore").read()
        for mm in pat_r.finditer(txt0):
            v = int(mm.group(1))
            if v == nr or v < 30:
                continue
            W = 30
            ctx = txt0[max(0, mm.start()-W):mm.end()+W].replace("\n", " ")
            if not re.search(r"实验报告|报告", ctx):
                continue
            if re.search(r"此前|曾|已更正", ctx):
                hist.append((rel, txt0[:mm.start()].count("\n")+1, v, ctx[:100]))
                continue
            bad.append((rel, txt0[:mm.start()].count("\n")+1, v, ctx[:100], "r"))

    if hist:
        print(f"○ {len(hist)} 处为【历史披露】（如实记录的纠错史，保留不改）：")
        for rel, ln, val, line, *_ in hist:
            print(f"    {rel}:{ln}  [{val}]  {line[:70]}")
        print()

    if not bad:
        print("✓ 全部物料条数一致，无漂移")
        return 0

    print(f"✗ 发现 {len(bad)} 处条数漂移：\n")
    for rel, ln, val, line, kind in bad:
        tgt = n if kind == "n" else nr
        print(f"  {rel}:{ln}  [{val} → {tgt}]")
        print(f"      {line}")

    if fix:
        from collections import defaultdict
        grouped = defaultdict(list)
        for rel, ln, val, line, kind in bad:
            grouped[rel].append((ln, val, kind))
        for rel, items in grouped.items():
            fp = os.path.join(ROOT, rel)
            lines = open(fp, encoding="utf-8").read().split("\n")
            for ln, val, kind in items:
                i = ln - 1
                tgt = n if kind == "n" else nr
                unit = "条" if kind == "n" else "份"
                # 只替换该行内的这一个数字（含【】包裹的讲稿写法）
                lines[i] = re.sub(r"(?<![\d.])%d(?=\s*%s)" % (val, unit), str(tgt), lines[i], count=1)
            open(fp, "w", encoding="utf-8").write("\n".join(lines))
        print(f"\n已逐处精确修正 {len(bad)} 处 → {n} 条 / {nr} 份")
    else:
        print("\n（加 --fix 自动替换）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
