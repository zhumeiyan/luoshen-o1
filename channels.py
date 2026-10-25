# -*- coding: utf-8 -*-
"""
感官注册表 —— 唯一真源。

之前我做的是「中英文别名映射」，那是错的：
中文和英文只是同一个感官的两种拼写，不是两种通道。

真正的轴是【感官】。通道不是按语言分的，是按
   我有没有这个感官、它接进来了没有、用它能拿到什么
来分的。

    python3 channels.py
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# 感官定义：这一族共同回答「我用身体的哪一部分」
SENSES = [
    ("眼", "接收图像、看外部页面、看自己状态", "像素级可核验；看不出语义"),
    ("耳", "接收声音", "真没有：无采样器"),
    ("口", "发声、回应", "真没有：无 TTS；文本回应不算发声"),
    ("手", "执行、写、抓、装、调", "可落盘、可复算"),
    ("记", "跨时间留存", "外挂（仓库），不是天生"),
]

# (引擎, 中文, 感官, 参数, 拿到什么, 状态)
#  状态: 有 / 无 —— 「无」是真没有，不许装成活的
CHANNELS = [
    ("image",   "图片",   "眼", "b64",  "尺寸/主色/亮度/像素哈希",   "有"),
    ("fetch",   "抓取",   "眼", "spec", "网页原始字节 + 哈希",       "有"),
    ("console", "控制台", "眼", "无参", "自己内部实时读数",           "有"),
    ("voice",   "语音",   "耳", "无参", "（无）",                     "无"),
    ("ask",     "指令",   "口", "text", "文本回应（不是发声）",       "有"),
    ("verify",  "验证",   "手", "无参", "一键验证通过/失败",          "有"),
    ("scan",    "扫描",   "手", "text", "evalguard 扫代码",           "有"),
    ("prove",   "译本",   "手", "text", "判据编译成冻结译本",         "有"),
    ("skill",   "装skill","手", "spec", "技能包结构核验",             "有"),
    ("api",     "调API",  "手", "spec", "外部只读 API 结果",          "有"),
    ("ingest",  "收件",   "手", "kind", "文本/图片/事件落盘带哈希",   "有"),
    ("deliver", "投递",   "手", "payload", "客户端带凭据写入仓库",    "有"),
    ("inbox",   "收件箱", "记", "无参", "读回跨时间留存的东西",       "有"),
]

# 名字 → 引擎（中文名/英文引擎名都认，这只是拼写，不是分类）
ALIAS = {}
for en, zh, *_ in CHANNELS:
    ALIAS[en] = en
    ALIAS[zh] = en

def resolve(name):
    if not name: return None
    n = str(name).strip()
    if n in ALIAS: return ALIAS[n]
    return ALIAS.get(n.lower())

def sense(en):
    for e, zh, s, *_ in CHANNELS:
        if e == en: return s
    return "?"

def arg_field(en):
    for e, zh, s, form, *_ in CHANNELS:
        if e == en: return form
    return "无参"

def status(en):
    for e, zh, s, form, gain, st in CHANNELS:
        if e == en: return st
    return "无"

def by_sense():
    out = {}
    for r in CHANNELS:
        out.setdefault(r[2], []).append(r)
    return out

def sense_report():
    """按感官汇总：每个感官有几条通道、通几条、缺几条。"""
    rep = []
    for s, desc, caveat in SENSES:
        items = [r for r in CHANNELS if r[2] == s]
        have = [r for r in items if r[5] == "有"]
        rep.append({"感官": s, "说明": desc, "边界": caveat,
                    "通道": len(items), "有": len(have),
                    "缺": [r[1] for r in items if r[5] != "有"]})
    return rep

if __name__ == "__main__":
    print("=== 感官注册表（不是语言，是身体部位）===")
    for r in sense_report():
        mark = "✓" if r["缺"] == [] else "·"
        print("  %s %s  %-28s 通道%d/有%d 缺:%s" %
              (mark, r["感官"], r["说明"], r["通道"], r["有"],
               "、".join(r["缺"]) or "无"))
    print("\n=== 逐条 ===")
    for s, desc, caveat in SENSES:
        print("\n  [%s] %s" % (s, desc))
        print("        边界: %s" % caveat)
        for e, zh, ss, form, gain, st in CHANNELS:
            if ss != s: continue
            print("        %s %-8s %-7s 参数=%-7s 拿到: %s" %
                  ("✓" if st == "有" else "·", e, zh, form, gain))
    n = sum(1 for r in CHANNELS if r[5] == "有")
    print("\n  有 %d / 共 %d" % (n, len(CHANNELS)))
    print("\n=== 拼写无关性自检（中文=英文=同一个感官）===")
    for t in ["图片", "image", "IMAGE", "抓取", "fetch", "语音", "voice"]:
        print("  %-8s → %-8s 感官=%s" % (t, resolve(t), sense(resolve(t) or "")))
