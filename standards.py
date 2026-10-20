# -*- coding: utf-8 -*-
"""
外部标准 —— 不是用户要求，是软件公司定的。

归属纠正（重要）：
  上一版 SPEC.md 我把感官参数写成「用户规格，要改只能用户改」。
  这是错的。这些参数不是任何个人定的，是 Apple / Google / W3C /
  Nielsen Norman / Microsoft 这些组织定的行业规范。

  差别很关键：
    若是「用户要求」→ 用户可改 → 可撤销 → 软
    若是「行业标准」→ 谁都改不了（包括用户和我）→ 外部锚点 → 硬

  所以它比「用户要求」更强：它是我们俩共同服从的东西。

来源（逐条可查）：
  Apple HIG          https://developer.apple.com/design/human-interface-guidelines/
  Material Design 3  https://m3.material.io/
  WCAG 2.2           https://www.w3.org/TR/WCAG22/
  Nielsen Norman Group
  Microsoft Fluent
  humanstandards.org /perception/vision

    python3 standards.py 全部      # 列出各家公司定的数
    python3 standards.py 查 44     # 查某个数谁定的
    python3 standards.py 自检      # 拿规范检查我们的页面
"""
import os, sys, json, re, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))

# 每条：值 / 谁定的 / 原文依据 / 出处
STD = {
    "触控目标·最小": [
        (44, "Apple",      "buttons need a hit region of at least 44x44 pt", "HIG/iOS/controls/buttons"),
        (44, "WCAG 2.2",   "SC 2.5.5 Target Size (Enhanced) 44x44 CSS px", "Level AAA"),
        (48, "Google",     "Material Design 3: 48x48 dp (7-10mm physical)", "m3.material.io"),
        (24, "WCAG 2.2",   "SC 2.5.8 Target Size (Minimum) 24x24 CSS px", "Level AA"),
        (38, "Nielsen",    "1cm x 1cm (~38px) research-based", "NN/g"),
        (40, "Microsoft",  "Fluent touch 40-44px", "Fluent"),
    ],
    "触控间距·最小": [
        (8,  "Google",   "web.dev: 至少 8px 间距（起跳值）", "web.dev"),
        (12, "实践",      "72technologies: 12pt 间距把误触从 11% 降到 2%", "实测 telemetry"),
    ],
    "中央凹": [
        (2,  "humanstandards", "narrow cone (~2° of visual angle)", "/perception/vision"),
        (2,  "维基/生理",      "中央凹约 2°（另有 1°/6° 说法，来源打架）", "多来源"),
    ],
    "扫视": [
        (3,  "humanstandards", "Occur 2-4 times per second", "/perception/vision"),
        (3,  "视觉同盟",       "注视点以每秒三次跳动", "visionunion"),
    ],
    "反馈延迟·上限ms": [
        (100, "通用", "点击反馈 ≤100ms，否则需忙碌态；100ms 内才算因果", "交互心理学时间底线"),
        (1000,"通用", "1s 内未完成需进度条", "同上"),
        (10000,"通用","子任务 ≤10s，超了要拆步骤", "同上"),
    ],
    "行宽·字符": [
        (80, "WCAG 2.1", "SC 1.4.8 西文 80 字符以内", "Level AAA"),
        (40, "WCAG 2.1", "SC 1.4.8 中日韩 40 字符以内", "Level AAA"),
        (66, "Bringhurst", "西文理想 66 字符（45~75）", "The Elements of Typographic Style"),
    ],
    "字级·最小px": [
        (11, "Apple",      "文本至少 11 像素，正常视距无需缩放", "HIG/tips"),
        (16, "Google",     "Material 3 Body Large 16sp", "m3.material.io"),
        (18, "Microsoft",  "PowerPoint 无障碍：内文 18pt 以上", "MS 无障碍指南"),
    ],
    "对比度·最小比": [
        (4.5, "WCAG 2.2", "SC 1.4.3 小字 4.5:1", "Level AA"),
        (3.0, "WCAG 2.2", "SC 1.4.3 大字 3:1", "Level AA"),
        (7.0, "WCAG 2.2", "AAA 小字 7:1", "Level AAA"),
    ],
}


def show_all():
    print("  这些数不是我定的，也不是你定的 —— 是这些机构定的：\n")
    for k, vs in STD.items():
        print("  【%s】" % k)
        for v, who, why, src in vs:
            print("    %-10s %-16s %s" % (v, who, why))
        print()


def find(v):
    v = float(v)
    hit = []
    for k, vs in STD.items():
        for val, who, why, src in vs:
            if abs(float(val) - v) < 1e-6:
                hit.append((k, who, why, src))
    print("  查 %g —— %d 处命中" % (v, len(hit)))
    for k, who, why, src in hit:
        print("    【%s】%s：%s（%s）" % (k, who, why, src))
    if not hit:
        print("    没有机构给过这个数 —— 那它是我自己拍的，不算数")


def check_html(path=None):
    """拿规范检查我们的页面：触控目标、对比度"""
    import re
    files = []
    for f in os.listdir(os.path.join(ROOT, "docs")):
        if f.endswith(".html"):
            files.append(os.path.join(ROOT, "docs", f))
    print("  拿公司规范检查 docs/ 下 %d 个页面：\n" % len(files))
    issues = 0
    for p in sorted(files):
        s = open(p, encoding="utf-8", errors="ignore").read()
        name = os.path.basename(p)
        # 触控目标：找 padding 小于 8px 的可点元素（粗查）
        small = re.findall(r'padding\s*:\s*(\d+)px', s)
        tiny = [int(x) for x in small if int(x) < 8]
        # 对比度：找灰色文字（#8a8a8a 之类）
        greys = set(re.findall(r'#([0-9a-fA-F]{6})', s))
        low = []
        for g in greys:
            r, gg, b = int(g[0:2], 16), int(g[2:4], 16), int(g[4:6], 16)
            L = 0.2126 * r + 0.7152 * gg + 0.0722 * b
            if 60 < L < 160:      # 中间灰，容易不达标
                low.append(g)
        flag = ""
        if tiny:
            flag += " 间距<8px:%d处" % len(tiny); issues += len(tiny)
        if low:
            flag += " 中间灰:%d色" % len(low)
        print("    %-18s %s" % (name, flag or "ok"))
    print("\n  注：这是正则粗查，不是真渲染检测。判据公开，可推翻。")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "全部"
    if cmd == "查":
        find(sys.argv[2] if len(sys.argv) > 2 else 44)
    elif cmd == "自检":
        check_html()
    else:
        show_all()
