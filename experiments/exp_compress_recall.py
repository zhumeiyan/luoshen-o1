#!/usr/bin/env python3
"""
真实验证 #3：压缩不报"压缩率"，改报【关键事实召回率】。

做法：
  造一段真实形状的长上下文，里面埋 N 个【必须活下来】的事实
  （分散在各层：system / pinned / tool_out 的头、中、尾 / history）。
  压完之后回查这些事实还在不在。

判据不是"压了多少"，是"该留的留下了没有"。
只报压缩率不说丢了什么 = 没说。所以这里两个都报：
  压缩率   —— 省了多少
  召回率   —— 该留的留了几个
  并列出每一条【丢了的关键事实】
"""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools.context_compress import compress

# 埋点：每条是一个必须活下来的事实，标注它埋在哪一层
FACTS = [
    ("system",   "判据核 #854 三遍挂一遍即禁止交付"),
    ("pinned",   "洛神星图 ★3 落在 time 轴"),
    ("tool_out_head", "残差 R = +1 单"),
    ("tool_out_mid",  "威海地方真太阳时比北京早 22.8 分钟"),
    ("tool_out_tail", "capacity 只降不升"),
    ("history",       "omarchy 有 reload 186-333ms 无 reload 37-113ms"),
    ("history",       "paraspell 已付款 56 单"),
]

def build():
    """造一段真实形状的长上下文"""
    filler = ("这是一段用来撑长度的中间内容，模拟真实工具输出里那些"
              "看了也没用的行。它唯一的作用是把关键事实推到远处，"
              "好检验压缩会不会把它一起丢掉。") * 40
    items = [
        {"layer": "system", "text": "系统约束：" + FACTS[0][1] + "。此外还有若干固定条款。"},
        {"layer": "pinned", "text": "用户钉住：" + FACTS[1][1] + "。不许压。", "pinned": True},
        {"layer": "tool_out", "text":
            FACTS[2][1] + "\n" + filler + "\n" + FACTS[3][1] + "\n" + filler},
        {"layer": "tool_out", "text":
            filler + "\n" + FACTS[4][1]},
        {"layer": "history", "text":
            "早前结论一：" + FACTS[5][1] + "。" + filler[:600]},
        {"layer": "history", "text":
            "早前结论二：" + FACTS[6][1] + "。" + filler[:600]},
    ]
    return items

def main():
    items = build()
    before = sum(len(i["text"]) for i in items)

    out = compress(items)
    text = json.dumps(out, ensure_ascii=False) if not isinstance(out, str) else out
    after = len(text)

    print("=" * 68)
    print(" 真实验证 #3 · 压缩的【关键事实召回率】")
    print("=" * 68)
    print(f"\n压前 {before} 字符 → 压后 {after} 字符")
    print(f"压缩率 {100*(1-after/before):.1f}%")

    print(f"\n{'层':<16}{'关键事实':<44}{'还在?':<8}")
    print("-" * 72)
    kept = 0
    lost = []
    for layer, fact in FACTS:
        ok = fact in text
        kept += ok
        if not ok: lost.append((layer, fact))
        print(f"{layer:<16}{fact[:42]:<44}{'✅' if ok else '❌ 丢了':<8}")

    n = len(FACTS)
    print(f"\n召回 {kept}/{n} = {100*kept/n:.0f}%")
    if lost:
        print(f"\n丢了 {len(lost)} 条（这才是压缩真正的代价）：")
        for layer, fact in lost:
            print(f"   [{layer}] {fact}")

    # 账：压了多少、留了什么、丢了什么，三者都要能列
    print(f"\n判据：")
    print(f"  {'✅' if kept >= 1 else '❌'} 至少保住 pinned/system（不可压层）")
    pinned_sys = [f for l, f in FACTS if l in ('system', 'pinned')]
    ps_ok = all(f in text for f in pinned_sys)
    print(f"  {'✅' if ps_ok else '❌'} system+pinned 全部保留 ({sum(f in text for f in pinned_sys)}/{len(pinned_sys)})")
    print(f"  {'✅' if after < before else '❌'} 确实变小了")
    print(f"  {'✅' if lost else '⚠️'} 丢失清单可列出（{len(lost)} 条）—— 能列出来才算有账")
    return kept, n, len(lost)

if __name__ == "__main__":
    main()
