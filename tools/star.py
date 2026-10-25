#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多维度星图 · star.py —— 洛神第 64 节
====================================
用户定的流程：
    找到 bug → 扔给洛神 → 看它在哪停 → 往下钻 → 挖到那个点 → 添一颗星

这颗星不是挂在一条线上，是挂在多维坐标上。
哪一维亮，星就落在哪一维。下次同类问题撞进来，同一坐标自己会亮。

五条轴
------
    time     时间 —— 我从哪一步开始算的？实测从哪一步开始？（起点错位）
    space    空间 —— 这个东西落在哪个文件/哪台机器/哪个进程？
    channel  通道 —— 这条事实来自源码，还是来自我的脑子？
    layer    层级 —— 我在哪一层说话？真系统 / 模型 / 模型里的模型？
    source   来源 —— 这个数字是谁测的？我能复现吗？

每条 BLOCK 灯天生落在一条轴上：
    L1 残差   → time     （起点错位，不是误差）
    L2 未接入 → channel  （源码里没这个名字 = 我编的）
    L3 假梯度 → layer    （在自编模型内部扫 = 假梯度）
    L4b 不声明→ space    （真系统那块空间我根本没进去）

用法
----
    python3 tools/star.py                    # 看星图（按维度分组）
    python3 tools/star.py case.json          # 判 + 挖 + 报告落点
    python3 tools/star.py case.json --add    # 以上 + 把星钉进星图

退出码：0 = 可交付；1 = 有 BLOCK，禁止交付
"""
import json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAP = os.path.join(ROOT, ".sense", "star_map.md")

sys.path.insert(0, HERE)
import parallax, descend

# ---- 灯 → 轴 ----
LAMP_AXIS = {"L1": "time", "L2": "channel", "L3": "layer", "L4b": "space"}

AXES = {
    "time":    "我从哪一步开始算的？实测从哪一步开始？",
    "space":   "这个东西落在哪个文件 / 哪台机器 / 哪个进程？",
    "channel": "这条事实来自源码，还是来自我的脑子？",
    "layer":   "我在哪一层说话？真系统 / 模型 / 模型里的模型？",
    "source":  "这个数字是谁测的？我能复现吗？",
}

# ---- 每条轴的钻法 ----
DRILL = {
    "time":    ("把 B 的时间线逐段拆开，与 A 的实测锚点对齐。",
                "找【起点】，不是找【误差】。"),
    "space":   ("写出『我没进去的那块空间』，逐条标注去哪能验证。",
                "真机 / RPC / 谁有设备。写不出途径就写死『无人可验』。"),
    "channel": ("在目标源码里 grep 参数名。",
                "grep 到 → 补上行号；grep 不到 → 它就是我编的，删掉。"),
    "layer":   ("停止在自编模型里扫参数。",
                "改成只在实测数字上做算术，再把结果做成别人一下能证伪的预测。"),
    "source":  ("问这个数字是谁测的、用什么测的。",
                "不是我测的就必须标名，不许并进我的结果里。"),
}


def lamps_blocking(c):
    """复刻 parallax.judge 的 BLOCK 判定，返回灯 tag 列表"""
    tags = []
    a, b = c["channel_a"]["value"], c["channel_b"]["value"]
    if abs(b - a) > c.get("tolerance", 1):
        tags.append("L1")
    if any(not p.get("src") for p in c.get("params", [])):
        tags.append("L2")
    if c.get("ablation_inside_model_only"):
        tags.append("L3")
    if not c.get("ran_real_system") and not c.get("declared_unknowns"):
        tags.append("L4b")
    return tags


def place(c, tags):
    """把灯落到轴上；case 自带的 dims 可以显式指定额外落点"""
    hits = {}
    for t in tags:
        hits.setdefault(LAMP_AXIS[t], []).append(t)
    for d in (c.get("dims") or []):
        hits.setdefault(d, []).append("显式")
    return hits


def add_star(c, tags, hits):
    os.makedirs(os.path.dirname(MAP), exist_ok=True)
    fresh = not os.path.exists(MAP)
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    body = open(MAP, encoding="utf-8").read() if not fresh else ""
    n = body.count("## ★")

    out = []
    if fresh:
        out.append("# 星图 —— 洛神每次停下来的地方，留一颗星\n")
        out.append("星不挂在线上，挂在多维坐标上。哪一维亮就落哪一维。\n")
    out.append(f"\n## ★{n + 1} {c.get('case', '未命名')} · {now}\n")
    ca, cb = c["channel_a"], c["channel_b"]
    out.append(f"- 停点：{', '.join(tags) if tags else '无（直接跑通）'}\n")
    out.append(f"- 双通道：A {ca['label']} = {ca['value']}{ca['unit']}"
               f" ／ B {cb['label']} = {cb['value']}{cb['unit']}\n")
    out.append(f"- 残差 R = {cb['value'] - ca['value']:+g} {ca['unit']}\n")
    if hits:
        out.append("- 落在：\n")
        for ax, ls in hits.items():
            out.append(f"  - **{ax}** ← {','.join(ls)}：{AXES.get(ax, '')}\n")
    if c.get("lesson"):
        out.append(f"- 挖到的：{c['lesson']}\n")
    if c.get("declared_unknowns"):
        out.append("- 我不知道的：\n")
        for u in c["declared_unknowns"]:
            out.append(f"  - {u}\n")

    with open(MAP, "a", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return n + 1


def show_map():
    print("=" * 70)
    print(" 多维度星图")
    print("=" * 70)
    if not os.path.exists(MAP):
        print("   星图还没建。")
    else:
        txt = open(MAP, encoding="utf-8").read()
        print(txt.rstrip())
    print()
    print("=" * 70)
    print(" 五条轴，哪一维亮就往哪一维放：")
    for k, v in AXES.items():
        print(f"   {k:<8} {v}")
    print()
    print(" 扔一个 bug 进来：python3 tools/star.py case.json [--add]")
    print("=" * 70)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        show_map()
        return 0

    c = json.load(open(args[0], encoding="utf-8"))
    lamps, ok, r = parallax.judge(c)
    parallax.show(c, lamps, ok, r)

    tags = lamps_blocking(c)
    hits = place(c, tags)

    print()
    print("=" * 70)
    print(" 多维度落点 —— 哪一维亮，星就落在哪一维")
    print("=" * 70)
    if not hits:
        print("   ✦ 无 BLOCK —— 这颗星已经亮过了，不用再挖。")
    for ax, ls in hits.items():
        how, found = DRILL.get(ax, ("", ""))
        print(f"   ★ {ax:<8} ← {','.join(ls)}")
        print(f"       问  {AXES.get(ax, '')}")
        print(f"       挖  {how} {found}")
        print()

    if "--add" in flags:
        n = add_star(c, tags, hits)
        print(f"✅ 钉了第 {n} 颗星 → {MAP}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
