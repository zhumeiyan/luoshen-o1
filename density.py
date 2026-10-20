# -*- coding: utf-8 -*-
"""
密度控制器 —— 先想你的带宽，再想我说什么。

底层逻辑不是数字、不是代码、不是文字、不是英文。
那是载体。载体有带宽成本，而你的带宽是固定的。

    python3 density.py 测 "一段话"     # 这段话要你付多少秒
    python3 density.py 比               # 各载体换算
    python3 density.py 限 20            # 我只给你 20 秒预算，看还能说什么
"""
import sys, re

# 每秒进脑子的字数（上一轮实测的换算，可被推翻）
RATE = {
    "图":   1000.0,   # 扫一眼
    "文字":   25.0,
    "英文":   14.0,
    "代码":    3.3,
    "表格":   12.0,
    "数字":    8.0,   # 孤立数字最贵：要自己找回上下文
}

# 你的时间预算（秒）。这是约束，不是估计。
BUDGET = 20.0


def classify(text):
    """这段东西主要是什么载体。"""
    if not text.strip():
        return "空"
    lines = [l for l in text.split("\n") if l.strip()]
    code_hits = sum(1 for l in lines if re.match(
        r"^\s*(def |import |from |class |if |for |return |#!|<\w|```|\{|\}|=>)", l))
    if code_hits > max(2, len(lines) * 0.3):
        return "代码"
    tbl = sum(1 for l in lines if l.count("|") >= 2 or l.count("\t") >= 2)
    if tbl > len(lines) * 0.4:
        return "表格"
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z]{3,}", text))
    if en > zh * 1.5:
        return "英文"
    # 孤立数字密度
    nums = len(re.findall(r"\d+\.?\d*", text))
    if nums > zh / 12 and zh < 120:
        return "数字"
    return "文字"


def cost(text, kind=None):
    """这段话要你付多少秒。"""
    k = kind or classify(text)
    if k == "空":
        return 0.0, "空"
    n = len(re.findall(r"[\u4e00-\u9fff]", text))
    n += len(re.findall(r"[A-Za-z]{3,}", text)) * 0.6
    n += len(re.findall(r"\d+\.?\d*", text)) * 0.8
    if k == "图":
        return 2.0, k
    return round(max(0.5, n / RATE.get(k, 25.0)), 1), k


def budget_check(text, budget=BUDGET):
    sec, k = cost(text)
    over = sec > budget
    return {"载体": k, "要你付": sec, "预算": budget,
            "超了": over, "超出倍数": round(sec / budget, 2) if over else 0}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "比"
    if cmd == "测" and len(sys.argv) > 2:
        t = " ".join(sys.argv[2:])
        r = budget_check(t)
        print("载体: %s   要你付: %s 秒   预算: %s 秒   %s" %
              (r["载体"], r["要你付"], r["预算"],
               "超了 %.1f 倍" % r["超出倍数"] if r["超了"] else "在预算内"))
    elif cmd == "限":
        b = float(sys.argv[2]) if len(sys.argv) > 2 else BUDGET
        print("预算 %s 秒，各载体最多能给你：" % b)
        for k, r in RATE.items():
            if k == "图":
                print("  %-5s 约 %d 张图" % (k, int(b / 2)))
            else:
                print("  %-5s 约 %d 字" % (k, int(b * r)))
    else:
        print("每秒进脑子的信息量（实测换算，可推翻）")
        print("  %-6s %8s %10s" % ("载体", "字/秒", "20秒能给"))
        for k, r in RATE.items():
            v = "约 %d 张" % int(20 / 2) if k == "图" else "约 %d 字" % int(20 * r)
            print("  %-6s %8.1f %10s" % (k, r, v))
        print("\n→ 同样的 20 秒：图 20000 字，代码 67 字。差 300 倍。")
        print("→ 所以先想带宽的意思是：能画成图的，不要写成字。")
