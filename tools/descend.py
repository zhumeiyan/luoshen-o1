#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下沉星 · Descend —— 洛神第 64 节
================================
视差星只干一件事：指出"这一格是我编的"（BLOCK）。
它不告诉你下一格在哪。这颗星干的是第二步：

    停在哪 → 往下钻一层 → 挖出那个点 → 补回去 → 再看灯

下沉规则（每条 BLOCK 灯对应一个具体动作，不是泛泛的"继续查"）：

    L1 残差   → 把 B 的时间线/空间线拆开，找【起点错位】
                 我错过的从来不是"数值差多少"，是"我从哪开始算的"
    L2 未接入 → 去源码 grep 这个参数名。grep 不到 = 它就是我编的，删掉
    L3 假梯度 → 停止在自编模型里扫参数。改成只在实测数字上做算术
    L4b 不声明 → 写下"我不知道的"清单，逐条给出去哪能验证

用法：
    python3 tools/descend.py                 # 跑案例库，看每颗星是怎么挖出来的
    python3 tools/descend.py --fix case.json # 对 BLOCK 给出下一步具体动作
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(ROOT, ".sense", "parallax_cases.jsonl")
STARS = os.path.join(ROOT, ".sense", "stars.md")

# 每条 BLOCK 灯 → 往下钻的具体动作 + 挖到之后怎么验
PLAYBOOK = {
    "L1": {
        "name": "残差",
        "ask": "我从哪一步开始算的？实测从哪一步开始？",
        "how": "把通道 B 的时间线（或空间线）逐段拆开，"
               "与通道 A 的实测锚点对齐。找【起点】，不是找【误差】。",
        "found_when": "拆完之后，预测区间与实测区间的间隙落进测量误差内。",
        "example": "omarchy#16146：我第一个 reload 放在 +6ms，实测 +128ms。"
                   "错位 122ms。拆开才发现 eval 内部还有 arrange 的 24 个 dispatch。",
    },
    "L2": {
        "name": "未接入",
        "ask": "这个参数，源码里有没有它的名字？",
        "how": "在目标源码里 grep 参数名。grep 到 → 补上行号；"
               "grep 不到 → 它就是我编的，从模型里删掉，不许当作已知条件。",
        "found_when": "每个参数要么有 文件:行号，要么被删除。没有第三种状态。",
        "example": "omarchy#16146：floating_ready_resets_on_reload 与 "
                   "race_plugin_list_lags 两条 grep 不到 → 删。剩 3 条都有行号。",
    },
    "L3": {
        "name": "假梯度",
        "ask": "我的消融表，扫的是真系统还是我自己编的模型？",
        "how": "若扫的是自编模型，梯度是假的。改成：只在实测数字上做加减乘除，"
               "再把结果做成一个【别人按一下就能证伪】的预测。",
        "found_when": "预测能被人用一个动作（少开几个窗口 / 换个参数）当场推翻。",
        "example": "omarchy#16146：改成纯算术后给出 wall = 22.5 + 6N×4.5 ms，"
                   "并写明『窗口从 4 减到 1，若不掉到 ~50ms 就是我错』。",
    },
    "L4b": {
        "name": "不声明",
        "ask": "我没跑过它，读者会不会以为我跑过？",
        "how": "写下『我不知道的』清单，逐条标注去哪能验证（真机 / RPC / 谁有设备）。",
        "found_when": "清单里每条都有明确的验证途径，或明确写死『无人可验』。",
        "example": "omarchy#16146：4 次 reload 只溯到 2 条来源，"
                   "剩 2 条写『我不知道』，终止机制写『怀疑 plugin.load 幂等，未验证』。",
    },
}


def load_cases():
    out = []
    if not os.path.exists(CASES):
        return out
    with open(CASES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def lamps_of(c):
    """复刻 parallax.judge 的判定，返回 BLOCK 灯的 tag 列表"""
    tags = []
    a, b = c["channel_a"]["value"], c["channel_b"]["value"]
    tol = c.get("tolerance", 1)
    if abs(b - a) > tol:
        tags.append("L1")
    if any(not p.get("src") for p in c.get("params", [])):
        tags.append("L2")
    if c.get("ablation_inside_model_only"):
        tags.append("L3")
    if not c.get("ran_real_system") and not c.get("declared_unknowns"):
        tags.append("L4b")
    return tags


def descend(c):
    tags = lamps_of(c)
    print("=" * 70)
    print(f" 下沉星 · {c.get('case','未命名')}")
    print("=" * 70)
    a, b = c["channel_a"]["value"], c["channel_b"]["value"]
    print(f"   通道 A {a} {c['channel_a']['unit']}  |  通道 B {b} {c['channel_b']['unit']}")
    print(f"   残差 R = {b - a:+g} {c['channel_a']['unit']}")
    print()
    if not tags:
        print("   ✦ 无 BLOCK —— 这颗星已经亮过了，不用再挖。")
        print("   （视差星没停点的地方，下沉星也不下钻。）")
        return []
    print(f"   🚨 停点 {len(tags)} 处，逐层下钻：\n")
    for t in tags:
        p = PLAYBOOK[t]
        print(f"   ── [{t}] {p['name']} " + "─" * (52 - len(p['name'])))
        print(f"      问  ：{p['ask']}")
        print(f"      挖  ：{p['how']}")
        print(f"      成了：{p['found_when']}")
        print(f"      旧例：{p['example']}")
        print()
    print("=" * 70)
    print(" 挖到之后：把新做法重跑一次视差星，看 BLOCK 掉到几盏。")
    print("   python3 tools/parallax.py --new '<新的 case.json>'")
    print("=" * 70)
    return tags


def main():
    args = sys.argv[1:]
    if args and args[0] == "--fix":
        return 0 if not descend(json.load(open(args[1], encoding="utf-8"))) else 1
    cases = load_cases()
    print("=" * 70)
    print(" 下沉星 · 案例库")
    print("=" * 70)
    print(f"   {len(cases)} 个案例，看每颗星是怎么从停点挖出来的\n")
    for c in cases:
        tags = lamps_of(c)
        mark = "✦" if not tags else "🚨" + ",".join(tags)
        print(f"   [{mark}] {c.get('case','?')}")
        print(f"         {(c.get('lesson') or c.get('verdict') or '')[:88]}")
        print()
    print("=" * 70)
    print(" 这颗星会亮在：视差星判完 BLOCK 之后。")
    print("   视差星说『这一格是编的』，下沉星说『往下一格挖这里』。")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
