#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视差星 · Parallax  —— 洛神第 63 节 / 判据核 #855
=================================================
天体测量里，量一颗星的距离从来不靠"看它多亮"：
两个观测点各看一次，两次视角之差 = 视差，视差才是距离。

洛神这边是同一件事：
    通道 A  别人的实测（他真跑过）
    通道 B  我的模型（我没跑过）
    残差 R = B − A                ← 这一格是我编出来的

亮灯条件（任一命中即亮）：
    L1 残差超出测量误差
    L2 模型参数里有"无源码依据"的假设
    L3 消融只在自编模型内部扫（梯度是假的）
    L4 静态检查 clean 但根本没跑真系统

用法：
    python3 tools/parallax.py                       # 跑内置案例库自检
    python3 tools/parallax.py <case.json>           # 判一个交付
    python3 tools/parallax.py --new '{"...json"}'   # 归档一个新案例

退出码：0 = 可交付；1 = 禁止交付（有灯亮）
"""
import json, os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASE_FILE = os.path.join(ROOT, ".sense", "parallax_cases.jsonl")

# 已归档案例 —— 每颗亮过的灯留一条，下次同类问题自动命中
SEED = [
    {
        "case": "omarchy#16146",
        "date": "2026-10-23",
        "channel_a": {"label": "报告者实测(60fps+hyprctl+socket2)", "value": 4, "unit": "reloads"},
        "channel_b": {"label": "我的 simulate.py", "value": 14, "unit": "reloads"},
        "tolerance": 1,
        "params": [
            {"name": "plugin_reload_on_load", "src": "workspace-modes.lua:449", "linked": False},
            {"name": "script_reload_when_missing", "src": "toggle:96-98", "linked": False},
            {"name": "floating_ready_resets_on_reload", "src": None, "linked": False},
            {"name": "titlebars_loads_plugin", "src": "workspace-modes.lua:458", "linked": False},
            {"name": "race_plugin_list_lags", "src": None, "linked": False},
        ],
        "ablation_inside_model_only": True,
        "ran_real_system": False,
        "static_check": "evalguard 0 blocker / 0 warn / 0 info → clean",
        "lesson": "我把 eval 当成 6ms 就完了，漏掉 arrange 的 24 个 dispatch（128ms）。"
                  "改做纯算术分解后：预测 101-126ms vs 实测 128-133ms，间隙 2ms，可交付。",
        "verdict": "禁止交付（模型版）→ 重做为算术分解后交付",
    },
]


def ensure_store():
    os.makedirs(os.path.dirname(CASE_FILE), exist_ok=True)
    if not os.path.exists(CASE_FILE):
        with open(CASE_FILE, "w", encoding="utf-8") as f:
            for c in SEED:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")


def load_cases():
    ensure_store()
    out = []
    with open(CASE_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def judge(c):
    """返回 (灯列表, 是否可交付, 残差)"""
    lamps = []
    a = c["channel_a"]["value"]
    b = c["channel_b"]["value"]
    tol = c.get("tolerance", 1)
    r = b - a
    ratio = (b / a) if a else float("inf")

    # L1 残差
    if abs(r) > tol:
        lamps.append({
            "lamp": "L1", "level": "BLOCK",
            "name": "残差",
            "detail": f"通道B {b} − 通道A {a} = {r:+g} {c['channel_a']['unit']}"
                      f"（倍差 {ratio:.2f}×，容忍 ±{tol}）",
            "meaning": "这一格是我编出来的。两个通道不能互相校准 → 我的模型是【喜好】，不是【因果】。",
        })

    # L2 无源码依据的假设
    bogus = [p for p in c.get("params", []) if not p.get("src")]
    if bogus:
        lamps.append({
            "lamp": "L2", "level": "BLOCK",
            "name": "未接入",
            "detail": f"{len(bogus)}/{len(c.get('params', []))} 个参数无源码依据：" +
                      ", ".join(p["name"] for p in bogus),
            "meaning": "正典 #218：无梯度 = 未接入，不等于效应为零。编出来的假设不算验证。",
        })

    # L3 消融只在自编模型内部
    if c.get("ablation_inside_model_only"):
        lamps.append({
            "lamp": "L3", "level": "BLOCK",
            "name": "假梯度",
            "detail": "消融表只在我自己编的模型内部扫",
            "meaning": "正典 #204：不得据『扫了几档』声称检验过该机制。内部扫出来的梯度是假的。",
        })

    # L4 没跑真系统 —— 是 WARN 不是 BLOCK。
    # 洛神的做法：没跑真系统时，只要只做算术 + 有源码行号 + 明写不知道的，仍可交付。
    if not c.get("ran_real_system"):
        unknowns = c.get("declared_unknowns") or []
        if unknowns:
            lamps.append({
                "lamp": "L4w", "level": "WARN",
                "name": "未跑真系统（已声明未知）",
                "detail": f"我没跑过它，但已明写 {len(unknowns)} 条不知道：" +
                          "；".join(str(u)[:40] for u in unknowns[:3]),
                "meaning": "可交付 —— 但只允许交付：有源码行号的事实、别人做的对照、被证伪的假设。",
            })
        else:
            lamps.append({
                "lamp": "L4b", "level": "BLOCK",
                "name": "未跑真系统（且未声明未知）",
                "detail": "我没跑过它，也没写清楚哪些是我不知道的",
                "meaning": "既不跑、又不声明 = 默认让读者以为我跑过。禁止交付。",
            })

    blockers = [l for l in lamps if l.get("level", "BLOCK") == "BLOCK"]
    return lamps, (len(blockers) == 0), r


def show(c, lamps, ok, r):
    print("=" * 68)
    print(f" 视差星 · {c.get('case', '未命名')}")
    print("=" * 68)
    ca, cb = c["channel_a"], c["channel_b"]
    print(f"   通道 A  {ca['label']}")
    print(f"           → {ca['value']} {ca['unit']}")
    print(f"   通道 B  {cb['label']}")
    print(f"           → {cb['value']} {cb['unit']}")
    print(f"   残差 R = B − A = {r:+g} {ca['unit']}" +
          (f"（{(cb['value']/ca['value']):.2f}×）" if ca["value"] else ""))
    print()
    bl = [l for l in lamps if l.get("level", "BLOCK") == "BLOCK"]
    wn = [l for l in lamps if l.get("level") == "WARN"]
    if lamps:
        print(f"   🚨 亮灯 {len(lamps)} 盏（BLOCK {len(bl)} · WARN {len(wn)}）：")
        for l in lamps:
            lv = l.get("level", "BLOCK")
            icon = "❌" if lv == "BLOCK" else "⚠️"
            print(f"      {icon} [{l['lamp']}] {l['name']}")
            print(f"            {l['detail']}")
            print(f"            → {l['meaning']}")
    else:
        print("   ✦ 无灯亮 —— 两个通道能互相校准 → 因果 → 可交付")
    print()
    print("=" * 68)
    if ok and any(l.get("level") == "WARN" for l in lamps):
        print(" 判定：⚠️ 可交付（附条件）")
        print("=" * 68)
        print("   只允许交付三样：有源码行号的事实 / 别人做的对照 / 被证伪的假设本身。")
        print("   凡『我推断』但未验证的，必须原样标明是推断。")
    elif ok:
        print(" 判定：✅ 可交付")
        print("=" * 68)
    else:
        print(" 判定：❌ 禁止交付")
        print("=" * 68)
        print("   判据核 #854：三遍里挂一遍即禁止交付。")
    return ok


def main():
    args = sys.argv[1:]
    ensure_store()

    if args and args[0] == "--new":
        c = json.loads(args[1])
        with open(CASE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"✅ 已归档案例：{c.get('case')}  →  {CASE_FILE}")
        lamps, ok, r = judge(c)
        show(c, lamps, ok, r)
        return 0 if ok else 1

    if args:
        c = json.load(open(args[0], encoding="utf-8"))
        lamps, ok, r = judge(c)
        return 0 if show(c, lamps, ok, r) else 1

    # 自检：跑案例库
    print("=" * 68)
    print(" 视差星 · 案例库自检")
    print("=" * 68)
    cases = load_cases()
    print(f"   已归档 {len(cases)} 个案例\n")
    bad = 0
    for c in cases:
        lamps, ok, r = judge(c)
        tag = "✦" if ok else f"🚨{len(lamps)}"
        print(f"   [{tag}] {c.get('case','?'):<22} R={r:+g}  {c.get('verdict','')[:34]}")
        if not ok:
            bad += 1
    print()
    print("=" * 68)
    print(" 这颗星下次会亮在：")
    print("   我要交付一个『我没跑过真系统』的模型时。")
    print("   它不阻止我交付 —— 它逼我把两个通道摆出来，把编的那一格标出来。")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
